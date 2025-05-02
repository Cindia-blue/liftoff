
PR #8259 - Add ReadonlyMounts to make overlay mounts readonly： 解决 overlayfs 多重挂载 diff 异常问题，通过 ReadonlyMount 避免 upperdir 冲突

PR #9401 - Add option to perform syncfs after pull： 该 PR 在镜像拉取（pull）完成后添加了可选的 syncfs 步骤，以确保文件系统缓存被同步到磁盘，避免因系统崩溃或断电导致的数据丢失或层不一致问题。

PR #6478 - oci: use readonly mount to read user/group info：该 PR 在创建容器时使用 readonly mount 挂载 rootfs，以只读方式读取 /etc/passwd 和 /etc/group 等文件，从而避免在 OCI spec 生成过程中因读写冲突或 snapshot 状态异常导致解析失败或权限风险。 ⸻ 额外提示（加深理解）： 这个 PR 实际上跟你前面总结的 #8259 属于同一类设计方向：临时访问活动 snapshot 的文件系统时，统一使用只读挂载，避免写入层冲突和 overlayfs 不确定行为。 OCI Spec 是由 containerd 在容器创建阶段生成的 JSON 文件，用于指导底层 runtime（如 runc）如何启动容器进程。其生成过程会触发读取容器文件系统中的元数据，比如 /etc/passwd，以解析用户信息并完成 spec 配置。

PR #3304 - leases: support resource management：该 PR 为 containerd 的 lease 子系统添加资源追踪能力，使每个 lease 可以显式关联 snapshot、image、content 等资源，便于在租约释放时自动清理相关资源，防止 orphan data 残留。

⸻

加深理解：为什么需要这个 PR？ • 原始问题： containerd 中大量资源（如 pulled image layers、snapshots）并未自动绑定到操作 lease 上，导致在租期结束后仍残留资源，造成空间泄露。 • 该 PR 的核心设计： • 为每类资源新增一个 AddResource / ListResources 接口 • 在 leases 表中追踪资源类型和关联 ID（如 snapshot, content, image） • 当 lease 过期或显式删除时，可统一回收相关资源

⸻

这类设计属于 containerd 的垃圾回收（GC）机制基础设施建设，对后续实现镜像自动清理、snapshot 清扫等功能非常关键。 在 containerd 的上下文中，Proxy 通常指的是一种插件机制，允许通过本地 gRPC 套接字将外部服务集成到 containerd 的核心功能中。这些 Proxy 插件可以扩展 containerd 的能力，例如提供自定义的快照器（snapshotter）、内容存储（content store）或差异服务（diff service） 。 ￼在 PR #3304 中，虽然主要关注点是增强租约（lease）系统以支持资源管理，但提到的 Proxy 插件机制可能与租约系统的扩展有关。通过 Proxy 插件，外部组件可以与 containerd 的租约系统交互，管理资源的生命周期。这种设计使得 containerd 更加模块化和可扩展，允许开发者根据特定需求定制其功能。总之，Proxy 插件 是 containerd 提供的一种机制，用于通过本地 gRPC 套接字将外部服务集成到其核心功能中，扩展其能力。在 PR #3304 中，Proxy 插件可能与租约系统的扩展相关，允许外部组件参与资源的管理和生命周期控制。

PR #10611 - core/mount: use ptrace instead of go:linkname： 该 PR 将 core/mount 模块中对 /proc/self/mountinfo 的解析实现，从不安全的 go:linkname hack 替换为使用标准的 ptrace 技术，以提高安全性、兼容性，并减少对 Go 内部符号的依赖。

⸻

背景与目的： • go:linkname 是一种 Go 编译器级的非公开链接方式，允许绕过包可见性限制调用私有符号。 • 在早期实现中，containerd 使用 go:linkname 强行访问 Go runtime 的内部 mountinfo 解析逻辑。 • 这种做法存在几个问题： • 不稳定：随着 Go 的升级，内部符号和结构可能发生变化。 • 不安全：可能触发 undefined behavior。 • 违反封装：不利于维护和跨平台移植。

⸻

这次修改做了什么？ • 改为使用标准的 ptrace 技术手动读取 /proc/[pid]/mountinfo，从目标进程中解析挂载信息。 • 保持了对容器挂载状态获取的能力，但实现更符合 Unix/Linux 系统标准行为。 • 提高了整体代码的健壮性和可维护性。

⸻

你可以记住的简化理解：

该 PR 是一次“摆脱 hack、走向正规”的安全性提升，用系统级 ptrace 替代了 Go 非公开技巧，确保 containerd 的挂载检测逻辑在长期可维护。当然可以！我们来对比 containerd 在读取 mountinfo 或容器内部信息时，使用 go:linkname（早期方式）与 ptrace（PR #10611 引入的新方式）之间的区别，从以下几个维度进行分析：

⸻

一、核心用途相同：

无论 go:linkname 还是 ptrace，目的都是：

在容器初始化或诊断阶段，从容器进程中获取 /proc/[pid]/mountinfo 等信息，用于判断挂载结构、执行用户/组解析、构建 OCI spec 等。

⸻

二、方式对比

对比项 go:linkname（旧方案） ptrace（新方案） 实现原理 利用 Go 编译器内部机制，强行链接到私有函数（如 internal/pkg/mountinfo.parseInfo） 使用 Linux ptrace 系统调用，挂起目标进程并读取其 /proc/[pid]/mountinfo 对目标进程的干扰 无需暂停目标进程，读的是宿主 /proc 的视图 会 ptrace attach，暂停目标进程 读其真实 /proc 内容 依赖不稳定性 高，严重依赖 Go runtime 内部结构，易随 Go 版本变化而崩 低，依赖的是 标准 Linux 接口（syscall + /proc），跨语言、长期稳定 代码可维护性 巧但危险；可读性差，不易维护 清晰、可调试、安全性强 安全审计友好性 不友好，行为绕过语言封装层 审计透明，符合系统安全模型 Go 官方支持性 不推荐、未来可能被彻底禁止 完全支持、平台中立

⸻

三、行为区别

早期版本（使用 go:linkname）配置示例：

//go:linkname parseInfo internal/mountinfo.parseInfo func parseInfo(...) ... ... mounts, err := parseInfo(f)

•	非公开调用，极易随 Go 内部改动报错或 panic；
•	在某些平台/版本无法编译或运行。
⸻

PR #10611 后（使用 ptrace）大致行为：

// Attach to target process syscall.PtraceAttach(pid) // Read /proc/[pid]/mountinfo info := readMountInfo(pid) // Detach syscall.PtraceDetach(pid)

•	完整遵守 Unix 语义；
•	可在 sandbox、gVisor 等安全环境中运作；
•	对目标进程有可控的暂停行为。
⸻

四、迁移意义总结：

使用 ptrace 替代 go:linkname 的本质，是从“对语言 hack 的依赖”迁移到“对系统原语的标准调用”。 这样不仅提升了 containerd 的可移植性和可维护性，也为未来在更复杂容器环境（如 eBPF、sandbox、gVisor）中运行提供了基础。

⸻

*PR #10906 - : should align pipe’s owner with init process

一句话总结：

该 PR 修复了在容器启动时创建的 pipe 文件（如控制 pipe）的属主不一致问题，通过将其所有者（owner）对齐为容器 init 进程（PID 1）所属的用户，从而避免权限异常或进程间通信失败。

⸻

背景：为什么这个修复重要？ • containerd 或 runc 在启动容器时，常会通过 控制 pipe 来与 init 进程通信，例如同步生命周期信号； • 这些 pipe 文件最初可能由 containerd 以 root 或 host 用户身份创建； • 如果最终运行容器的是非 root 用户（e.g. UID 1001），pipe 的属主与其不一致，可能会导致： • 写入/读取失败（EACCES） • 权限泄露 • 安全审计异常

⸻

这个 PR 做了什么？ • 在 container 启动初始化阶段，对控制用 pipe 文件的属主进行 chown； • 将其 uid/gid 设置为容器 init 进程的 uid/gid； • 修改适用于多个子系统（因 PR 名为 *:，表明涉及多个包）； • 修复了多个使用 NewPipe() 或 StdioPipe() 生成的控制流场景。

⸻

一句话记忆点：

保证所有容器通信用的 pipe 属主和容器 init 进程一致，防止权限冲突，是 runtime 启动阶段的关键细节之一。

*PR #11605 - : image volume feature’s follow-up

一句话总结：

该 PR 对 containerd 的 Image Volume 功能进行后续完善，包括确保镜像中声明的卷路径正确初始化为持久 volume、与容器生命周期解耦，并修复卷未绑定容器时可能的清理与挂载异常问题。

⸻

背景说明：什么是 Image Volume？ • 它来自 OCI image spec 的一个设计：镜像可以在 config.Volumes 字段中声明特定路径为 volume（例如 /var/lib/data）； • containerd 新增此特性后，会在容器首次启动时自动为这些路径创建挂载点； • 类似 docker 默认行为中的 匿名 volume； • 该机制要求 container runtime 跟踪并初始化这些 volume 目录、并在运行时挂载进去，否则用户数据丢失或行为异常。

⸻

这次 PR 做了什么？ • 修复初始化逻辑：确保在未显式绑定 host volume 时，也能为 image volume 预创建挂载点； • 修复清理逻辑：在容器删除时妥善处理未挂载 volume 的释放，防止挂载泄漏或残留； • 提升一致性：使 image volume 行为在不同 runtime backend 上（如 containerd-shim）表现一致； • 更精确的资源绑定关系处理：与 lease/subresource 机制联动。

⸻

简洁记忆句：

该 PR 补全了 image volume 的行为闭环，确保镜像中声明的匿名挂载路径能正确初始化、挂载并被清理，保障数据不丢失、容器运行一致。

*PR #11605 - : image volume feature’s follow-up

一句话总结：

该 PR 对 containerd 的 Image Volume 功能进行后续完善，包括确保镜像中声明的卷路径正确初始化为持久 volume、与容器生命周期解耦，并修复卷未绑定容器时可能的清理与挂载异常问题。

⸻

背景说明：什么是 Image Volume？ • 它来自 OCI image spec 的一个设计：镜像可以在 config.Volumes 字段中声明特定路径为 volume（例如 /var/lib/data）； • containerd 新增此特性后，会在容器首次启动时自动为这些路径创建挂载点； • 类似 docker 默认行为中的 匿名 volume； • 该机制要求 container runtime 跟踪并初始化这些 volume 目录、并在运行时挂载进去，否则用户数据丢失或行为异常。

⸻

这次 PR 做了什么？ • 修复初始化逻辑：确保在未显式绑定 host volume 时，也能为 image volume 预创建挂载点； • 修复清理逻辑：在容器删除时妥善处理未挂载 volume 的释放，防止挂载泄漏或残留； • 提升一致性：使 image volume 行为在不同 runtime backend 上（如 containerd-shim）表现一致； • 更精确的资源绑定关系处理：与 lease/subresource 机制联动。

⸻

简洁记忆句：

该 PR 补全了 image volume 的行为闭环，确保镜像中声明的匿名挂载路径能正确初始化、挂载并被清理，保障数据不丢失、容器运行一致。