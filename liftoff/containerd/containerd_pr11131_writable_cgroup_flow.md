
# PR #11131: Containerd 启用非特权容器可写 Cgroup 的控制流程解析

本笔记总结了 Containerd 中，从 `config.toml` 配置文件添加 `WritableCgroups` 配置项，到容器创建过程实际修改 Cgroup 挂载行为的完整路径。

---

## 一、配置入口层（Configuration）

在 containerd 的配置文件中添加：

```toml
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
  WritableCgroups = true
```

对应的 Go 结构体：

```go
type Options struct {
    WritableCgroups bool `toml:"writable_cgroups"`
}
```

该字段被注入到 runtime handler 的 `runtimeOptions` 中。

---

## 二、配置注入与转译层（Server -> SpecOpts）

Container 创建时，containerd 会调用：

```go
opts := []oci.SpecOpts{
    // ...
    criopts.WithWritableCgroups(runtimeOptions.WritableCgroups),
}
```

SpecOpts 是修改 `oci.Spec` 的函数类型，用于添加/修改挂载信息。

该函数定义于 `pkg/cri/opts/cgroups.go`：

```go
func WithWritableCgroups(enabled bool) oci.SpecOpts {
    return func(ctx context.Context, spec *oci.Spec) error {
        if enabled {
            // 修改 /sys/fs/cgroup 的挂载为 "rw"
        }
        return nil
    }
}
```

---

## 三、runtime 调用层（Spec 应用）

最终所有的 `SpecOpts` 会被合并，生成完整的 OCI 容器配置：

- 写入 `config.json`（OCI runtime spec）
- containerd 调用 `runc create`，指向该 spec 文件

此时，runc 会根据该配置将 `/sys/fs/cgroup` 挂载为只读或可写。

---

## 四、流程图（简要）

```text
config.toml
    |
    v
runtimeOptions.WritableCgroups
    |
    v
cri/server/container_create.go
    |
    v
[]oci.SpecOpts -> opts.WithWritableCgroups(bool)
    |
    v
生成 OCI spec（修改挂载项）
    |
    v
runc create -> 应用最终配置
```

---

## 五、术语对照表

| 概念名称 | Containerd 术语 |
|----------|----------------|
| Configuration 配置项 | `runtimeOptions` |
| Spec / Spike | `oci.Spec` |
| Server 接口调用 | `container_create.go` |
| Opts 方法 | `SpecOpts` 函数，如 `WithWritableCgroups` |

---

## 六、总结

PR #11131 通过插件化配置与 `SpecOpts` 注入机制，让 containerd 用户可控制非特权容器是否以可写方式挂载 Cgroup。该机制遵循 containerd 的标准插件与构建流程，确保灵活性与可插拔性。
