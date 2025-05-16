你的方向非常精准，而且这两条路径一旦你能打通，几乎就相当于掌握了 containerd runtime 层的“入口配置链路”与“观测出口链路”，具备了真正做扩展、做性能调优、做调试工具的能力。

我来帮你总结这两个关键路径的目标、挑战、方法、典型代码位置，并附上你可以动手切入的方向：

⸻

路径一：动态配置从 Kubernetes 或配置文件传入 containerd，并落地到底层 runtime（如 cgroup v2）

目标：

让上层（如 Kubelet 或自定义配置）能传入扩展字段，最终在 containerd 中落地到底层运行时（如 runc、cgroup driver），支持对 container 运行行为做更细粒度的控制。

典型场景：

你想通过一种通用路径，把例如 "memory.low": "1G" 这种 cgroup v2 扩展字段，
	•	从 Kubernetes CRI 或 yaml →
	•	通过 CRI plugin（containerd） →
	•	到 runc shim 的 CreateContainer 调用中

⸻

挑战：
	•	containerd 的 CRI 接口不直接支持任意自定义字段传递；
	•	配置链路是多层解耦的：Kubelet → CRI → OCI Spec → shim → runc；
	•	你需要决定：走 CRI 扩展字段（annotations）？还是在 containerd 层注入？

⸻

建议路线（按入手优先级排序）：

方法一：通过 annotations 机制传入配置（最现实）
	•	Kubernetes Pod Spec 支持传 annotations；
	•	containerd 在处理 CRI 创建请求时（pkg/cri/server/container_create.go）会提取这些 annotations；
	•	你可以在这里做逻辑判断：识别特定的 key，然后写入 OCI runtime spec。

入口文件：
pkg/cri/server/container_create.go →
generateLinuxResources（这里构建了 cgroup 字段）→
github.com/opencontainers/runtime-spec/specs-go.LinuxResources

方法二：直接 patch containerd config.toml 支持扩展（偏本地实验）
	•	containerd 启动时从 config.toml 加载默认配置（含 plugin 配置）；
	•	你可以定义一个 plugin 的 scoped config 并注入特定字段；
	•	适合实验性 runtime（如 metrics 插桩 runtime）。

入口文件：
cmd/containerd/config.go
pkg/config – 用于解码 config.toml

⸻

路径二：为 container lifecycle 添加日志（tracing/logging instrumentation）

目标：

打通 container 生命周期的观测链路，能看到：
	•	每次 container start 的时间、延迟分布；
	•	snapshot mount 是否异常频繁；
	•	哪些 container/shim 存在异常重试、性能抖动等。

⸻

建议打点路径（可插入 log 或自定义 metric）：

1. container start
	•	文件路径： pkg/cri/server/container_start.go
	•	可以在 StartContainer 函数开头、调用 r.Start() 前后加 log
	•	输出 container ID、namespace、start latency（用 time.Since()）

2. snapshot prepare / mount
	•	文件路径： pkg/cri/server/helpers.go 和 snapshot/service.go
	•	插入 log 记录 Prepare 被调用次数、mount key
	•	可通过 container ID + snapshot key 分析是否过度 prepare

3. shim 启动 latency
	•	文件路径： runtime/v2/shim 模块中
	•	加 log 观察 shim binary 启动时间（startShim）、是否有重启/超时

⸻

通用工具建议：
	•	加入 log.G(ctx).WithField("...").Infof(...) 语句输出 JSON 风格日志；
	•	或加一个实验性 stats 插件，把所有生命周期事件写入 prometheus metric（适合你将来想做 latency 分布图分析）

⸻

总结：你可立即开始的任务清单

路径	目标	入口文件	推荐动作
动态配置注入	从 annotations 扩展传入 cgroup v2 字段	container_create.go	解析 annotations → 写入 OCI.Linux.Resources
runtime config patch	用 config.toml 注入自定义字段	config.go, pkg/config	添加 plugin section / 解码结构体
启动日志	container start latency	container_start.go	加 log.G(ctx).Infof + time.Since
snapshot monitor	mount prepare 次数与 key	helpers.go, service.go	log snapshotter.Prepare 被调用次数
shim latency	诊断 shim 启动抖动	runtime/v2/shim	打 log 记录 shim start 时延


⸻

你已经明确了两个最核心的切入口：入口层配置注入 & 生命周期关键点观测。这两个方向未来也能构建为你入职 Pinterest 的 “小舞台起点”。

需要我帮你做一份【containerd 路径调试实践路线图】Markdown 文档归档吗？或者挑一个路径我们今天开始动手演练？