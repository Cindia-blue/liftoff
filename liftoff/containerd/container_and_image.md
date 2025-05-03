太好了，下面我会帮你梳理出 containerd 中从 镜像拉取（Fetch） 到 容器创建与 Cgroup 注入 的完整路径结构。这将覆盖两条主线：

⸻

一、镜像流：从 Fetch 到 Snapshot 的数据流

1. ctr images pull 或 CRI 的 PullImage 调用
	•	入口代码：client.Pull() （CLI） or pkg/cri/server/image_pull.go
	•	调用逻辑：

resolver.Resolve()
fetcher.Fetch()
contentStore.Write()
snapshotter.Prepare()
imageStore.Update()



2. 组件参与：

阶段	组件	说明
解析镜像名	resolver	默认通过 containerd 的 registry resolver
下载镜像	fetcher	分层下载每个 layer
存储数据	content.Store	文件内容写入 /var/lib/containerd/io.containerd.content.v1.content/
准备文件系统	snapshotter	比如 overlayfs，创建可挂载的根目录快照
更新元数据	image.Store	把 image 信息注册进 metadata db



⸻

二、容器流：从 Create 到 Task 与 Cgroup 管理

1. 容器创建
	•	入口代码：containerd.Client.NewContainer() 或 CRI 的 RunPodSandbox / CreateContainer
	•	包括设置容器规格（spec），包括资源限制等：

specOpts = append(specOpts,
    oci.WithMemoryLimit(...),
    oci.WithCPU(...),
    oci.WithPidsLimit(...),
)



⸻

2. Task 创建：触发 Cgroup 注入的关键阶段
	•	调用链：

container.NewTask() →
shim.Start() →
shim binary (e.g. runc-shim-v2) →
runc create →
libcontainer (via runc) →
cgroup manager.Apply()


	•	是否使用 systemd 驱动？
	•	决定于：WithSystemdCgroup = true/false
	•	对应代码路径：
	•	systemd 模式 → libcontainer/cgroups/systemd/
	•	fs 模式 → libcontainer/cgroups/fs2/（或 fs/）

⸻

3. Cgroup 设置
	•	主要调用点：

cgroups.NewManager("systemd" or "cgroupfs")
manager.Apply(pid)
manager.Set(ResourceConfig)


	•	配置写入：
	•	内核路径（cgroupfs）：/sys/fs/cgroup/<subsystem>/<container-id>/
	•	systemd scope：/sys/fs/cgroup/system.slice/containerd-xyz.scope/

⸻

4. Metrics 采集（用于 List、Stats）
	•	来源：containerd shim 的 task.Metrics()
	•	采集位置：读取 cgroup 里的 cpu.stat, memory.usage_in_bytes, pids.current 等
	•	反序列化结构：github.com/containerd/cgroups/v2.Metrics

⸻

三、Cgroup 清理
	•	正常停止：
	•	task.Delete() → shim exit → runc exit → libcontainer 清理 cgroup
	•	异常退出：
	•	PR #10590 修复了 “失败但未清理” 的问题
	•	PR #10649 增加了验证 test

⸻

总结图示（逻辑流）

  Image Pull
     ↓
Resolver → Fetcher → Content Store → Snapshotter
     ↓
  Image Record (metadata DB)

  Container Create
     ↓
 Container Spec (with cgroup limits)
     ↓
    Task.New()  ───→ shim.start() ───→ runc create
                                     ↓
                               libcontainer (apply cgroup)
                                     ↓
                          systemd or cgroupfs

  Run + Stats
     ↓
    task.Metrics() → /sys/fs/cgroup read
     ↓
   CRI / ctr stats / prometheus



⸻

太好了，我们就按模块继续深入，从你提到的几个方向开始。下面先进入 task 创建与 shim 启动链路的深度解析（重点是 task.New() 后发生了什么）：

⸻

一、task.New() 调用链：Shim 启动与容器生命周期

containerd 中的“task”指的是运行态容器实例，它由 shim 管理，并通过 runc 或 kata 等 runtime 启动。

⸻

Step 1: 创建 Container 实例

container, err := client.NewContainer(...)

这一步只会注册 metadata，不会启动进程。

⸻

Step 2: 调用 task.New() 启动容器

task, err := container.NewTask(ctx, ioCreator, taskOpts...)

这一步完成了容器进程真正的创建与运行，关键路径：

→ client.go → withTaskCreate → task.go
→ newTask()
  ├─ starts shim binary (e.g. containerd-shim-runc-v2)
  ├─ sends "Create" request to shim via TTRPC
  └─ shim 调用 runc → 创建容器



⸻

Step 3: shim 启动
	•	containerd 会启动 shim 可执行文件（如 containerd-shim-runc-v2）：

cmd := exec.Command(shimBinary, ...)
cmd.Start()


	•	shim 自身是一个 gRPC 服务，注册了 TaskService
	•	shim 的 Create() 方法被调用时：

├─ 创建容器的工作目录
├─ 调用 runc create
├─ 写入 bundle/config.json
└─ 启动 sandbox + task + io copy goroutine



⸻

Step 4: runc create + cgroup 应用
	•	runc 是一个 CLI 工具，接收 config.json 作为标准 OCI runtime 配置。
	•	在 runc create 执行过程中：

├─ 创建 namespace（mnt, net, pid, etc）
├─ 应用 resource 限制（cgroup） ← 这里关键
└─ 进入容器 init 流程，挂起等待 containerd 调用 start


	•	若配置了 WithSystemdCgroup()，则会进入 systemd 代码路径。

⸻

Step 5: containerd 调用 task.Start() 触发启动

task.Start(ctx)

	•	shim 再次调用 runc，运行容器主进程（runc start）
	•	容器此时开始运行，状态更新为 RUNNING

⸻

二、关键数据结构

类型	用途
runtime.TaskCreateRequest	containerd → shim 的初始化配置
oci.Spec	config.json 的映射结构体，定义资源、挂载、cgroup
Process	runc 执行的命令（容器主进程）
Manager	libcontainer 内部使用的 cgroup 管理器，封装了 systemd 与 fs



⸻

三、Shim 的作用再总结一次：
	•	为每个 container 提供 进程隔离与生命周期管理
	•	拥有自己的 TTRPC 接口 → containerd 通过它管理任务状态
	•	自持 container 的 stdout/stderr 管道
	•	屏蔽 runtime 细节（如 runc、gVisor）给 containerd 层

⸻
太好了！接下来我们来深挖 containerd 中的 Cgroups 设置逻辑，包括：
	•	如何通过 libcontainer 设置 cgroup
	•	systemd vs cgroupfs 的路径区别
	•	cgroups.Manager.Apply() 是如何工作的
	•	containerd 中如何传递配置、如何调用这个逻辑

⸻

一、容器的资源限制由谁负责？

入口在 runc（或 kata、gVisor）

containerd 通过 shim → runc 来真正创建容器，而 资源限制是 runc 的职责，由它通过 libcontainer 进行设置。

⸻

二、关键路径总览

containerd.NewTask()
    ↓
shim.Create() → runc create
    ↓
runc 调用 libcontainer
    ↓
libcontainer -> cgroups.NewManager()
    ↓
manager.Apply(pid)
    ↓
写入 /sys/fs/cgroup/... 或 systemd.slice



⸻

三、libcontainer 的 cgroup 管理核心代码

1. libcontainer/cgroups/manager.go

这是抽象接口：

type Manager interface {
    Apply(pid int) error
    Set(resources *configs.Resources) error
    GetStats() (*Stats, error)
    Destroy() error
}

创建 manager 的工厂函数是：

func NewManager(c *configs.Cgroup, opts ...func(*manager)) (Manager, error)

这个 configs.Cgroup 来自 config.json 中的 .linux.resources 字段。

⸻

2. 决定使用 systemd 还是 cgroupfs

判断逻辑在：

if c.Systemd {
    return systemd.New(c, paths)
}
return fs2.New(c, paths)

	•	如果传入的 configs.Cgroup.Systemd 为 true，就走 systemd 路径
	•	否则就走 cgroupfs 路径（fs2 是 Cgroup V2 版本）

⸻

四、以 CgroupFS 为例的 Apply 流程

路径：libcontainer/cgroups/fs2/fs2.go

核心操作：

// Mount points like /sys/fs/cgroup/memory/
path := getCgroupPath(subsystem, cgroupsPath)

// Ensure directory exists
os.MkdirAll(path, 0755)

// Write values
ioutil.WriteFile(path+"/memory.max", []byte("536870912"), 0700)

每一个子系统（memory, cpu, pids…）都有自己的文件路径，最终都是：

/sys/fs/cgroup/<controller>/<cgroup name>/

写入的是：
	•	memory.max / memory.current
	•	cpu.max
	•	pids.max / pids.current

⸻

五、Cgroup V2 vs V1

对比	Cgroup V1	Cgroup V2
控制器	分布在多个子目录	所有控制器统一管理
配置	各 subsystem 独立配置	统一格式
containerd 默认	V2 if kernel >= 5.4	否则 fallback



⸻

六、Systemd 模式

路径：libcontainer/cgroups/systemd/
	•	创建的是一个 systemd scope，名如：

containerd-<container-id>.scope


	•	设置资源的方式是写入 systemd-run 或 dbus 接口：

m.unitName = fmt.Sprintf("containerd-%s.scope", containerID)


	•	路径是：

/sys/fs/cgroup/system.slice/containerd-xxxx.scope/



⸻

七、在 containerd 中如何触发这些逻辑？

路径：

→ runtime/v2/runc/task.go
   ├─ startShim()
   ├─ shim.CreateTask() ← 发送 TTRPC 到 shim
   └─ shim → runc create → libcontainer.Apply(pid)

容器的 config.json 中定义 .linux.resources 是资源限制来源
	•	memory.limit
	•	cpu.shares
	•	pids.max
	•	…

这些字段被 shim 写入到 bundle 中 → 交给 runc。

⸻

八、诊断技巧

你可以用如下方法验证：

# 查看某个 container 的 cgroup 配置
cat /sys/fs/cgroup/<controller>/<container-id>/memory.max
cat /sys/fs/cgroup/<controller>/<container-id>/pids.max

或者在 container 中运行：

cat /proc/self/cgroup

也可配合 ctr tasks metrics 来看到当前使用情况。

⸻

太好了，这一步是资源限制配置从 containerd 的 config 注入 → 到 runc → 到 libcontainer → 到 Apply(pid) 的关键传递链。

下面我将带你逐步过一遍：从 containerd 构建 spec（config.json）到 runc 处理 .linux.resources 的整个流向。

⸻

一、整体流向概览

containerd.NewTask()
    ↓
Generate OCI Spec (config.json)
    ↓
Write bundle/config.json
    ↓
shim 调用 runc create --bundle <bundle>
    ↓
runc → libcontainer → Apply(pid)
    ↓
libcontainer 写入 /sys/fs/cgroup



⸻

二、containerd 端如何构造 config.json

1. Spec 的生成：containerd/oci/spec.go

containerd 生成 config.json 的入口是：

oci.GenerateSpec(ctx, client, container, ...opts)

这些 opts 是调用方（如 CRI）提供的，比如：

oci.WithMemoryLimit(512 * 1024 * 1024),
oci.WithPidsLimit(100),
oci.WithCPUShares(512),

内部结构最终写入：

spec.Linux.Resources = &specs.LinuxResources{
    CPU: &specs.LinuxCPU{Shares: uint64ptr(512)},
    Memory: &specs.LinuxMemory{Limit: int64ptr(536870912)},
    Pids: &specs.LinuxPids{Limit: int64ptr(100)},
}

生成完成后，会被写入 config.json 到 bundle 目录。

⸻

三、shim 启动 runc 并传递 config.json

containerd 的 shim（比如 containerd-shim-runc-v2）会执行：

runc create --bundle /run/containerd/io.containerd.runtime.v2.task/k8s.io/<id>

此时 runc 读取的是：

/run/containerd/.../<container-id>/config.json

该文件就是包含了 .linux.resources 的完整 OCI 配置。

⸻

四、runc 内部处理 config.json 的路径

runc 内部流程：

main.go → createCommand.Run()
    → loadSpec()
    → createContainer()
        → libcontainer.New()
        → libcontainer.Create()
            → cgroups.NewManager()
            → manager.Apply(pid)

关键结构体：
	•	config.json → 转为 configs.Config
	•	.linux.resources → 转为 configs.Resources

type Config struct {
    Rootfs string
    Cgroups *configs.Cgroup
}

type Cgroup struct {
    Resources *configs.Resources
    Parent    string
    Path      string
    Systemd   bool
}



⸻

五、最终写入 cgroup 的行为（libcontainer）

以 CgroupFS 为例：

manager.Apply(pid)
  └── cgroupfs.CreateCgroupPath()
  └── fs.apply()
        → write /sys/fs/cgroup/memory/<path>/memory.max
        → write /sys/fs/cgroup/pids/<path>/pids.max
        → ...

systemd 则是通过 dbus 注册 .scope 并设置资源属性。

⸻

六、调试验证方法

1. 查看 config.json

你可以用如下方式检查：

cat /run/containerd/.../<container-id>/config.json | jq .linux.resources

2. 查看 kernel 路径

cat /sys/fs/cgroup/memory/<container-cgroup>/memory.max
cat /sys/fs/cgroup/pids/<container-cgroup>/pids.max

3. runc debug 启动

用 runc --debug 可以观察实际 Apply 过程。

⸻

总结图（核心链路）

containerd.NewTask()
  ↓
oci.With*() 注入资源 → spec.Linux.Resources
  ↓
config.json 写入 bundle
  ↓
shim → runc create --bundle <bundle>
  ↓
runc 读取 config.json
  ↓
libcontainer → NewManager()
  ↓
Apply(pid) → 写入 /sys/fs/cgroup/



⸻

太好了！接下来我们就深入 libcontainer 内部，逐个揭示它是如何将每个资源字段转换为具体的 cgroup 文件写入操作的。这是 Apply(pid) 的核心内容。

⸻

一、代码主线入口

以 Cgroup V2 为例，主要路径在：

runc → libcontainer → cgroups/fs2/manager.go

入口函数为：

func (m *Manager) Apply(pid int) error

内部调用了：

m.controllers.Apply(dirPath, cgroup, pid)



⸻

二、资源字段的转换总览

libcontainer 接收的资源字段是：

type Resources struct {
    Memory      *Memory
    CPU         *CPU
    PidsLimit   int64
    ...
}

每个字段会被转换为 Linux cgroupfs 下的对应文件写入，如下所示：

字段	写入路径（Cgroup v2）	示例值
Memory.Limit	memory.max	536870912
Memory.Swap	memory.swap.max	0
CPU.Weight	cpu.weight	100
CPU.Max	cpu.max	100000 1000000
PidsLimit	pids.max	100



⸻

三、每个字段具体写入逻辑

我们以 fs2/unified_hierarchy.go 为主，分析每种资源如何转换：

⸻

1. Memory 限制

// resources.Memory.Limit: int64
if resources.Memory != nil {
    if resources.Memory.Limit != nil {
        writeFile(dir, "memory.max", strconv.FormatInt(*resources.Memory.Limit, 10))
    }
    if resources.Memory.Swap != nil {
        writeFile(dir, "memory.swap.max", strconv.FormatInt(*resources.Memory.Swap, 10))
    }
}

路径：

/sys/fs/cgroup/<cgroup-path>/memory.max



⸻

2. CPU 限制

if resources.CPU != nil {
    if resources.CPU.Weight != nil {
        writeFile(dir, "cpu.weight", strconv.FormatUint(*resources.CPU.Weight, 10))
    }

    // Convert CPU quota/period to cpu.max
    if resources.CPU.Quota != nil && resources.CPU.Period != nil {
        val := fmt.Sprintf("%d %d", *resources.CPU.Quota, *resources.CPU.Period)
        writeFile(dir, "cpu.max", val)
    }
}

路径：

/sys/fs/cgroup/<cgroup-path>/cpu.weight
/sys/fs/cgroup/<cgroup-path>/cpu.max



⸻

3. PIDs 限制

if resources.PidsLimit > 0 {
    writeFile(dir, "pids.max", strconv.FormatInt(resources.PidsLimit, 10))
}

路径：

/sys/fs/cgroup/<cgroup-path>/pids.max



⸻

四、写入函数是如何调用的？

最终写入由 writeFile() 实现：

func writeFile(dir, file, value string) error {
    f := filepath.Join(dir, file)
    return ioutil.WriteFile(f, []byte(value), 0644)
}

也就是说，每一个资源字段都是被转成字符串，写入到特定的 cgroup v2 文件中。

⸻

五、systemd 模式则不同

systemd 会通过 D-Bus 接口调用：

// For example
dbus.SetUnitProperties(scope, true, []dbus.Property{
    Prop("MemoryMax", memoryInBytes),
    Prop("CPUQuotaPerSecUSec", ...),
    ...
})

这些转换逻辑在 libcontainer/cgroups/systemd/unified.go 中实现。

⸻

六、如何调试验证？

你可以在容器运行后，检查对应路径：

cat /sys/fs/cgroup/<your-cgroup>/memory.max
cat /sys/fs/cgroup/<your-cgroup>/cpu.max
cat /sys/fs/cgroup/<your-cgroup>/pids.max

也可以在 config.json → .linux.resources 中确认写入内容。

⸻

你还可以选择：
	•	查看 CPU throttling（配额与爆发） 如何设置
	•	理解 memory.high vs memory.max vs memory.min 的区别
	•	分析 systemd 如何设置这些属性
	•	或者切换回 snapshot 子系统继续深入分析 overlay 创建流程
