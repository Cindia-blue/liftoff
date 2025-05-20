 *: export RemoveVolatileOption for CRI image volumes #10274:在 overlayfs 中，volatile 是一个挂载选项，用于优化性能但牺牲稳定性。如果系统崩溃，使用 volatile 的挂载点有可能会造成文件系统不一致或数据丢失。 在 containerd 中，如果使用 overlayfs 作为 snapshotter，并在 image volume 的挂载上默认添加 volatile，可能会：为 CRI image volumes 的挂载选项移除 volatile 标志，并将该行为作为导出的可选配置项。
	•	加快拉镜像和挂载速度（尤其是短生命周期容器）；
	•	但在崩溃或重启后造成残留目录无法删除或文件结构混乱。




Add option to perform syncfs after pull #9401 :	Adds a feature flag or option to allow containerd to invoke syncfs() after pulling an image . syncfs() is a Linux system call that flushes all pending writes from the filesystem’s dirty page cache to disk for a specific file descriptor (usually tied to a mount point or file).
 
 
 
 
 eventfd leak #3961： 在 containerd 的 runtime v2 实现中，container 的状态变化（如 exit）通过 eventfd（事件文件描述符）监听；在 Wait() 调用过程中，会为每个进程创建一个新的 eventfd；若在监听过程中进程提前退出，或监听失败，eventfd 没有被显式关闭，导致 fd 泄漏。
 
 
 
 cherry-pick: runtime v2: Close platform in runc shim's Shutdown method. #3907: 在使用 runtime v2（即 shim v2）的 containerd 中，当 shim 被 shutdown 时，需要正确地关闭 platform 对象，释放资源并避免 goroutine 泄漏或 socket 持续占用。



 
 Use cached state instead of runc state. #3711:  Title: containerd PR #3711 — Eliminating Redundant runc state Calls via shim State Caching
- containerd shim originally spawns multiple `runc state` calls during container exec;
- This caused performance degradation in Kubernetes and Docker exec;
- PR #3711 caches shim status internally and reduces syscall load drastically;
- Applicable to lifecycle tracing, metrics collection, and exec path diagnostics.



Fix container pid race condition. #3857: 在 container 启动过程中，存在一个竞争条件 —— 如果 containerd 在记录 container pid 到 metadata store 之前崩溃，container 的状态将永远处于不一致状态，因为 pid 丢失，shim 无法清理，也无法恢复。修复逻辑：
	•	container 启动后，只有在成功启动、pid 获取成功且写入到 metadata 之后，才会标记 container 启动成功；
	•	启动失败的 container 将立即进入清理流程，防止“stuck in created”；
	•	这个修复实际上明确了 containerd 中“pid is part of state”的状态机完整性。


 
 
 Allow configuration of different log formats: text, json #4803: 该 PR 增加了对 containerd 守护进程日志格式的配置支持，允许用户通过 config.toml 配置为 text 或 json 格式输出日志，提升了日志的可读性与集成性.



Optimize Windows and LCOW snapshotters to only create scratch layer on the final snapshot #4643: 优化 Windows 和 LCOW 的 snapshotter，使 scratch layer 仅在最终提交的快照上创建，从而减少不必要的磁盘占用和加快容器创建速度。这一改动通过延迟 scratch 层的生成，避免在中间快照（如 Prepare 阶段）时浪费资源，提升了启动性能和存储效率，尤其适用于多阶段容器生命周期管理。

 
 
 compression: add support for the zstd algorithm #4809: 为镜像分层添加对 Zstandard (zstd) 压缩算法的支持，提升了解压速度和传输效率，特别适用于高性能镜像分发场景。通过这个改动，containerd 能够识别并解压 .zst 格式的 layer blobs，使其在镜像拉取过程中兼容更多压缩格式，并可配合支持 zstd 的 registry 使用，从而改善传输性能。



Enable to pass additional handler on pull for stargz-based remote snapshots #1431: 该 PR 允许在拉取镜像时传入额外的处理器（handler），以支持基于 Stargz 的远程快照场景，增强了 remote snapshotter 的扩展性和灵活性。这个改动使得在使用例如 stargz-snapshotter 等 lazy pull 机制时，开发者可以注入自定义处理逻辑，比如处理额外的元数据或进行内容校验，优化镜像拉取与挂载流程。



PR # 4162 Rework shim logger shutdown process: 这条 PR 通过引入 context 和 WaitGroup，确保 shim logger 在关闭时能安全退出所有读取协程，防止资源泄漏与 panic，显著提升了 containerd 运行时的稳定性与生产环境安全性。



PR #7228 Initial sandbox API CRI integration (implement Controller.Start): 该 PR 将新引入的 Sandbox API 与 CRI 接口集成，首次实现了 Controller.Start 的实际逻辑，标志着 containerd 向 pod-level runtime 抽象迈出关键一步


 Implement RuntimeConfig CRI call #8722 : 该 PR 实现了 CRI 层 RuntimeConfig gRPC 调用的支持，允许 Kubernetes kubelet 在运行中通过 CRI 动态更新 runtime 配置，例如 pause image，打通了 config runtime 热更新链路。


Sandbox API #6703:该 PR 定义并注册了一个全新的 Sandbox gRPC API，建立了 containerd 对 pod sandbox 的原生抽象，为支持更丰富的 pod-level runtime 模型（如微虚拟机、gVisor、Kata）打下基础。



 Transfer service #7320 : 新增了 TransferService 接口及默认实现：
	•	定义在 services/transfer/service.go
	•	实现了 TransferService 的两大核心方法：
	•	Export：将镜像导出为 tar/OCI layout 等格式
	•	Import：将 tar/OCI layout 文件导入为镜像

核心调用链包含：
	1.	TransferServiceServer 实现了 gRPC 接口，并注册到 containerd server。
	2.	TransferServer 的方法中使用 content.Store, images.Store, snapshots.Snapshotter 等组件完成导入导出。
	3.	对 Export 和 Import 请求中引入了 streaming 与 lease 的处理逻辑。

增加了 proto 定义：
	•	在 api/services/transfer/v1/ 中新增了 proto 文件 transfer.proto
	•	gRPC 支持 Export / Import 请求 + 响应结构

⸻

这个 PR 解决什么问题 / 提供什么能力？

引入统一 Transfer 接口，目标是：
	•	替代或统一之前的镜像导出路径（如 ctr image export）
	•	构建镜像迁移的基础能力（image mirroring / replication）
	•	便于外部调用方将镜像持久化到外部系统，如 remote registry、tar、OCI layout

也就是说：containerd 从这一步开始，为“镜像的 Import/Export 生命周期”搭建了独立可编排的服务模块。

⸻

这个 PR 的设计为什么重要？（你的技术 narrative）

你可以这样说：

This PR introduces the TransferService abstraction into containerd, which decouples image import/export logic from CLI tools and exposes it via a dedicated gRPC API. It’s a foundational step toward building image replication and mirroring strategies that operate independent of the runtime interface. Architecturally, it separates the concern of content packaging from image management.







fix: shimv1 leak issue (#9344)
Commit: 449912857
理由：
	•	涉及 shimv1 进程泄漏问题 → 直接影响 container 生命周期管理；
	•	若未清理，可能造成 orphaned shim，占用资源 & 无法清理；
	•	属于典型的 长期运行系统资源回收风险，值得深入理解如何 shim shutdown、如何 hook reaper、以及 containerd shim model。
归类建议： shim / recovery



Expose usage of deprecated features (#9315)
Commits:
	•	60d48ffea ctr: new deprecations command
	•	b708f8bfa deprecation: new package for deprecations
	•	9b7ceee54 warning: new service for deprecations
理由：
	•	建立了一套内建 deprecation 监控/可观测性框架；
	•	可以记录 plugin/config/pull API 层面正在使用的 deprecated features；
	•	对 Cloud Runtime 稳定性演进、配置迁移策略、版本兼容影响评估都极其关键；
	•	属于 observability + feature lifecycle 管理层重要机制改进。





fix: cri: add deprecation warnings for mirrors, auths, configs (#9327)
Commits： 多个 commit 拆分 warning 来源
	•	689a1036d auth
	•	152c57e91 config
	•	8c38975bf mirrors
理由：
	•	对用户 registry 配置行为增加告警；
	•	结合 #9315 的 deprecation framework，这相当于在 CRI 层提前探测不兼容风险；
	•	可帮助团队主动发现未来的 break risk，防止 registry pull 问题导致 incident。
 
 
 
 
 
 
 PR #9252 中，开发者为转换后的 Docker Schema 1 镜像添加了一个新的标签。这个标签的作用是标识这些镜像的来源格式，从而在后续的处理过程中提供更好的兼容性和可追溯性。

 
 
 PR #9235（“remotes: add handling for missing basic auth credentials”）中，开发者针对在拉取私有镜像时可能遇到的 “no basic auth credentials” 错误，增强了 containerd 的远程模块（remotes）的处理能力。
PR #9235 的核心改动： 该 PR 的主要目的是提升 containerd 在处理私有镜像仓库认证时的健壮性。
在实际应用中，用户可能通过配置文件（如 config.toml）或命令行参数提供认证信息。
该 PR 通过增强 remotes 模块的逻辑，使其在缺失基本认证信息时，能够更优雅地处理错误，避免程序崩溃或返回不明确的错误信息。



PR #9209 旨在修复 containerd-shim-runc-v2 中 create handler 可能导致的死锁问题。
在 containerd-shim-runc-v2 中，create handler 负责处理容器创建请求。
Note that handleStarted needs to be aware of whether s.mu is already held
// when it is called. If s.mu has been held, we don't need to lock it when
// calling handleProcessExit.
具体来说，containerd-shim-runc-v2 只有 4 个队列来处理大量的 goroutine，当并发量很大时，这些队列可能成为瓶颈，导致处理延迟或阻塞


PR #9299（Fix ambiguous TLS fallback），该修复主要解决了在处理镜像拉取时 TLS 回退逻辑不明确的问题。
在某些配置场景下，containerd 在尝试从私有镜像仓库拉取镜像时，可能会错误地回退到不安全的 HTTP 连接，或在 TLS 验证失败时未能正确处理，导致镜像拉取失败或安全风险。



PR #9299 对此进行了修复，明确了 TLS 回退的逻辑，确保在配置了自签名证书或跳过 TLS 验证的情况下，containerd 能够正确处理镜像拉取请求，避免不必要的失败或安全隐患。


PR#9819 Propagate deprecation list to runtime status (#9819)
	•	解决了什么？
在 CRI 返回的 runtime status 中未传递出已废弃的配置项，导致上层（如 kubelet）无法感知底层组件 deprecation 状态。
	•	改了哪里？
修改了 pkg/cri/server 的 status 构建逻辑，附带将 deprecated 字段注入返回值。
	•	归类建议： plumbing（属于跨层 glue 信息传递）



Fix image pinning when image is not pulled through cri (#9785)
	•	解决了什么？
当镜像不是通过 CRI 拉取（如用 ctr 工具或其它方式）时，pin 标记未正确设置，导致镜像可能被 GC 回收。
	•	改了哪里？
修改了 image 管理逻辑中的 pin 状态判断，确保即使绕过 CRI 也能被标记保留。
	•	归类建议： gc


PR # 9409 ImagePull should close http connection if there is no available data to read. #9409: 该 PR 修复了在镜像拉取过程中，当 HTTP 响应体为空时未及时关闭连接的问题，防止资源泄露并提高系统稳定性。

⸻

改了什么？怎么改的？
	•	问题背景：在使用 ImagePull 拉取镜像时，如果 HTTP 响应体没有可读数据，连接可能未被及时关闭，导致资源泄露。
	•	修复方式：
	•	在检测到无可读数据的情况下，显式关闭 HTTP 连接。
	•	确保所有异常路径都能正确释放资源，防止连接泄露。

⸻

关键词分类建议：
	•	归类关键词：auth / plumbing
	•	推荐理由：该 PR 涉及镜像拉取过程中的连接管理，属于底层逻辑优化，提升了系统的健壮性和资源管理能力。
	


PR #9768 Add timeout to drain exec io: 该 PR 为容器 exec I/O 的 drain 操作增加了超时机制，防止在进程退出后 I/O 阻塞导致容器或调用方卡住的问题。

⸻

改了什么？怎么改的？
	•	问题背景：当容器内 exec 的子进程退出后，containerd 会尝试 drain 掉其 stdout/stderr。但某些情况下，这个 drain 操作会 hang（如：没有及时关闭 FD 或输出管道卡死），从而导致整个命令的调用链阻塞。
	•	新增行为：
	•	增加配置项 DrainExecSyncIOTimeout，用于控制 drain 的最大时长；
	•	若超时未完成 drain，containerd 会跳过此步骤并发出日志警告；
	•	支持通过 CRI 配置文件显式开启或禁用该功能；
	•	添加了针对超时配置的验证逻辑和单测。


PR #9828 runc-shim: process exec exits before init (w/o extra locks!) #9828: 是对 containerd-shim 的关键修复，旨在解决当容器的 init 进程和 exec 进程几乎同时退出时，事件上报顺序错误的问题。该问题可能导致 docker exec 命令挂起，因为 Docker 在接收到 init 的退出事件后会删除容器，从而无法处理后续的 exec 退出事件。 ￼

改动内容：
该修复引入了一个 pendingExecs 机制，用于在处理 init 进程的退出事件之前，确保所有挂起的 exec 退出事件已被处理。通过这种方式，确保了事件的正确顺序，避免了客户端在处理 exec 退出事件时遇到问题。 ￼


PR #9927 Update runc-shim to process exec exits before init:  该 PR 修复了 runc-shim 在处理 exec 进程退出顺序时可能发生的竞态条件，确保 exec 退出事件优先于 init，增强任务生命周期的稳定性。

改了什么？怎么改的？
	•	修改了 runc-shim 的 task handler，使得当有 exec 进程时，其退出状态优先被上报，避免与 init 的 wait 顺序冲突。
	•	对 shim 的 wait 和 processExit 流程进行了顺序控制，解决可能出现的“exec 进程已退出但未被正确上报”的问题


PR #10008 Add support for HPC port forwarding : 该 PR 为 containerd 增加了 HPC 环境下的端口转发功能，允许用户在受限网络中通过安全隧道访问容器内的服务。


PR [release/1.7] Fix issue with using invalid token to retry fetching layer #10065 的一句话总结如下：
修复了 Containerd 在拉取镜像 layer 时，因重复使用已失效的认证 token 导致拉取失败的问题，确保在认证失败后能正确地重新获取新的 token 进行重试。

⸻

主要解决的问题：
在某些 registry（如 Docker Hub 或私有仓库）中，token 认证机制比较严格，如果 Containerd 在尝试拉取镜像 layer 失败后继续复用原来的 token，那么第二次尝试依然会失败。这会导致整个 pull 操作失败，尤其在网络环境不稳定或 token 有效期较短的场景下更易复现。

⸻

核心改动位置与逻辑：
	1.	remote/handlers.go：在 blob 拉取失败（特别是遇到 401 Unauthorized）之后，不再重用旧的 token，而是：
	•	强制重新走一次 resolver 的认证流程；
	•	清除旧的 token header；
	•	重新构造带新 token 的请求进行 retry。
	2.	增强 retry 机制：增加对认证失败（401）的 retry path 的特殊处理逻辑，不再对所有错误统一处理。
	3.	测试保障：虽然 PR 本身没有添加复杂的测试，但它修复了 已报告的问题 #9794，并得到了用户验证。

⸻

是否值得看？
是的，特别是如果你将来要负责 Container Runtime 的网络交互或认证链路，这种 token-based authentication 与 retry policy 是基础能力。PR 展现了如何在请求链路中优雅地处理认证失败并重新触发身份认证流程，非常值得作为学习网络安全和重试机制的范例。





Automatically decompress archives for transfer service import #9989 [release/1.7]:为 Transfer Service 的 Import 操作添加了对 .tar.gz、.tgz、.tar.xz 等压缩格式的自动解压支持，提升用户使用 Transfer Service 进行镜像导入的便捷性。

⸻

主要解决的问题：
之前 Transfer Service 的 Import 接口只能处理已解压的 .tar 文件；但用户往往从其他系统（如备份或构建流水线）中拿到的是压缩格式的 .tar.gz、.tgz 或 .tar.xz 文件。这种情况下需要用户手动解压再导入，不方便也易出错。

⸻

核心改动位置与逻辑：
	1.	检测文件类型：在 importer.go 中增加逻辑，根据文件的 magic number 检测文件是否为 gzip、xz 等压缩格式。
	2.	自动解压路径：
	•	如果是 .tar.gz 或 .tgz，使用 gzip reader；
	•	如果是 .tar.xz，使用 xz reader；
	•	如果是 .tar，直接处理。
	3.	错误处理增强：对于无法识别或解压失败的情况，会返回更明确的错误，避免 silent failure。
	4.	测试用例补充：增加了多个不同压缩格式下的单元测试，确保兼容性与稳定性。

⸻

是否值得看？
是的，特别适合你现在关注 Transfer Service 和 Containerd 分发路径时看这个 PR。它展现了如何优雅地将自动格式检测与解压整合进已有的 import 流程，并提升用户体验，是代码清晰、变更粒度合理的一个典范。




PR（#8268）是 containerd 对 sandbox 模块进行架构重构 的关键性变更，其核心目标是将原本集中在 runtime/v2/service_sandbox.go 中的沙箱控制逻辑进行模块化（plugin 化），并支持通过配置注入 sandboxer 行为，从而增强灵活性和扩展性： 将 sandbox 控制器抽象为插件，并引入 sandboxer 配置机制，使 containerd 更易于支持不同类型的沙箱实现。

⸻

关键改动内容：
	1.	引入 sandboxer.Config 结构：
	•	用于支持通过 runtime 配置注入 sandboxer 的行为控制。
	•	如：sandbox root 路径、平台配置等。
	2.	将 sandbox controller 移入 plugin 系统中管理：
	•	每个 sandboxer 实现现在以 plugin 注册。
	•	控制器逻辑不再集中在 core，而是注册为插件。
	•	插件通过接口如 sandbox.Controller 实现控制逻辑。
	3.	模块拆分路径如下：
	•	services/sandbox/controller_service.go: gRPC 层服务定义，暴露 sandbox 控制 API。
	•	sandbox/controller.go: 定义 Controller 接口，各 plugin 通过实现它来支持自己的 sandbox 控制逻辑。
	•	sandbox/plugin.go: 注册插件的实际逻辑。
	•	sandbox/config/config.go: 定义 sandbox 配置结构，支持通过 TOML 文件配置。
	4.	默认实现（shim sandboxer）也被移至 plugin 中，路径：
	•	sandbox/runtime/runhcs-v1: Windows 的 shim 实现。
	•	sandbox/runtime/test: 测试用的 shim 实现。

⸻

为什么这么做？
	•	原问题： 原先所有 sandbox 控制都在 runtime/v2/service_sandbox.go，难以支持多平台或 shim 类型扩展。
	•	目标： 提供统一的接口和插件机制，让不同平台（如 Linux, Windows）可以自定义控制器而不互相干扰。
	•	附带收益： 让 shimless sandbox、multi-tenant runtime、以及 future abstraction 更加可行。





PR #9736「Store bootstrap parameters in sandbox metadata」的主要目标是将沙箱（sandbox）初始化时的关键参数持久化存储到其元数据中。这一改动增强了 containerd 在运行时对沙箱配置的可追溯性和可管理性，尤其在调试和状态恢复等场景中具有重要意义。

🧩 主要改动内容
	1.	引入 Bootstrap 参数结构体：PR 中定义了一个新的结构体 Bootstrap，用于封装沙箱初始化所需的关键参数，如命名空间（namespace）、运行时名称（runtime name）、运行时选项（runtime options）等。
	2.	存储至沙箱元数据中：这些 bootstrap 参数被序列化后，存储在沙箱的元数据扩展字段（Extensions["bootstrap"]）中。这样，containerd 的其他组件或插件可以在需要时访问这些初始化参数。
	3.	更新元数据处理逻辑：为了支持新的 bootstrap 参数，PR 对相关的元数据处理逻辑进行了调整，确保在创建和管理沙箱时能够正确处理这些参数。

🔧 技术细节
	•	结构定义：Bootstrap 结构体包含了沙箱初始化所需的所有关键参数。
	•	元数据存储：使用 typeurl.MarshalAny 将 Bootstrap 实例序列化，并存储到沙箱的元数据扩展字段中。
	•	访问方式：其他组件可以通过 GetExtension("bootstrap") 方法访问并反序列化这些参数，以获取沙箱的初始化信息。

🧠 影响与意义
	•	增强可观测性：通过将初始化参数持久化，containerd 在运行时可以更容易地追踪和调试沙箱的配置问题。
	•	提高稳定性：在系统重启或异常恢复的情况下，持久化的 bootstrap 参数有助于恢复沙箱的原始状态，确保系统的稳定运行。
	•	支持扩展性：这一改动为未来 containerd 的功能扩展提供了基础，例如更复杂的沙箱管理策略或与其他系统的集成。


PR #8989: Add image delete target

一、改动目的：
	•	为 image 对象增加了可配置的 delete target 行为。
	•	以前删除镜像时，只会清除 image object（元信息），但不会清理对应的内容地址（content blobs）。
	•	该 PR 增加了明确的 “删除目标” 配置，让调用者可以选择是否清除 content store 中的内容。

二、关键改动：
	•	引入新的删除模式 DeleteTarget（例如：
	•	DeleteTargetOnlyImage：仅删除 image record；
	•	DeleteTargetWithContent：删除 image 及其所有 content blob；
	•	修改了 client.ImageService().Delete(...) 接口与行为逻辑；
	•	增加测试用例验证两种模式下的行为是否正确。

三、为何要这样做？
	•	在实际场景中（如自动化清理、多租户系统、GC 优化）用户可能希望镜像删除时自动清除 content；
	•	也有用户希望保留 content（例如多个 tag 共用同一 blob）；
	•	提供显式控制可以满足更丰富的运维策略。



PR #10762 “Enable HTTP debug and trace for transfer based puller” 是 containerd 2.1.0-rc.0 版本中的一个重要更新，旨在增强 transfer-based puller 的调试能力，特别是在处理多层镜像拉取（如 multipart layer fetch）时。 ￼

主要改动

该 PR 引入了对 transfer-based puller 的 HTTP 调试和追踪功能，允许开发者通过命令行选项 --http-dump 和 --http-trace 来启用详细的 HTTP 请求和响应的日志记录。这对于诊断镜像拉取过程中的网络问题、认证错误或性能瓶颈等非常有帮助。 ￼

背景与动机

在实际使用中，用户可能会遇到镜像拉取速度慢或失败的情况，但由于缺乏详细的调试信息，难以定位问题。通过启用 HTTP 调试和追踪，用户可以获取更丰富的上下文信息，如请求的目标主机、使用的协议（IPv4 或 IPv6）、响应状态码等，从而更容易识别和解决问题。

实际应用

如果你正在开发或维护基于 containerd 的容器平台，特别是涉及到镜像分发和拉取的功能，那么了解和使用这一调试功能将对你有很大帮助。它不仅可以提升问题定位的效率，还可以帮助你更深入地理解 containerd 在处理镜像拉取时的内部机制。

总之，PR #10762 提供了增强的调试工具，对于需要深入分析 containerd 镜像拉取过程的开发者和运维人员来说，是一个非常有价值的更新。




PR #10649 integration: regression test for issue 10589: 为修复 bind mount 目录在多容器共享时被误删的问题，添加了回归测试用例，确保生命周期 teardown 行为不再破坏共享挂载点。
	•	背景知识：多个容器 bind mount 同一 host path 时，如果生命周期管理不当，可能导致其他容器的挂载目录被提前清除。
	•	本 PR 解决了什么：复现并验证 issue #10589 中提到的问题行为，确保后续容器仍能访问共享的挂载路径。
	•	实现要点：
	•	使用 integration test 复现 bug 行为；
	•	并发启动多个容器共享同一挂载；
	•	验证 container teardown 不会破坏挂载目录；
	•	防止 future regression
在 containerd 的源码中，plugins/fifo/fifo_unix.go 文件定义了一个名为 new 的函数，用于创建一个新的 PEP FIFO（命名管道）。关键点修正如下：
	•	trigger 是写入端（writer）
用于主动“触发”某个事件 —— 它打开 FIFO 进行写操作（O_WRONLY），用于通知另一方某个条件成立。
	•	waiter 是读取端（reader）
被动“等待”某个事件 —— 它打开 FIFO 进行读操作（O_RDONLY），会阻塞直到 trigger 写入。

也就是说：
trigger 写，waiter 读。

这和原来我所述的理解反了过来，你指出得非常准确。

⸻

为什么这样设计？

这背后是基于 UNIX FIFO 的阻塞行为：
	•	O_RDONLY 读取端会阻塞，直到有写者；
	•	O_WRONLY 写入端会阻塞，直到有读取者；

在 containerd 中，借助这一机制来实现跨进程或 goroutine 的同步。

⸻

具体应用示例

在 containerd 的运行时（如 shim 层），trigger 和 waiter 常用于：
	•	等待容器启动完成；
	•	监听某个 shim 生命周期状态；
	•	等待 clean exit 等事件。

例如，在 containerd 的任务执行过程中，可能需要等待某个条件满足后再继续执行。此时，可以使用 new 函数创建一个 FIFO，并将其作为 “waiter” 使用，等待某个事件的发生；而在事件发生时，可以将该 FIFO 作为 “trigger” 使用，通知等待方事件已发生。总之，new 函数提供了一种创建和使用 FIFO 文件的机制，以实现 containerd 中的事件同步和通信。





PR #10651: runc-shim: Fix races / prevent init exits from being dropped

一句话总结（What changed）

修复了 runc-shim 中处理容器 init 进程退出时的竞态条件，防止容器状态未被正确记录或遗失 init exit 状态。

⸻

为什么这么做（Why）

在高并发或快速容器销毁的情况下，init 进程的退出信号可能会在 shim 的 serve loop 启动前发生，导致：
	•	容器退出事件丢失
	•	容器状态不一致
	•	调用方永远等待不到 exit 状态（严重影响可靠性）

⸻

主要改动（Where）
	1.	重构了 shim 的 initExitCh 注册与处理时序：
	•	提前初始化 shim 状态跟踪通道。
	•	避免 race：在 serve 启动前，先准备好 exit 状态处理通路。
	2.	增强 monitor 与 task 的交互逻辑：
	•	引入更早期的监听 init exit 的路径。
	•	解决任务退出时未能上报的问题。

⸻

效果（Impact）
	•	提高容器状态一致性与可靠性：即使容器快速退出，也不会错过 init 退出信号。
	•	对依赖快速 spin-up/down 的 serverless 或 ephemeral 容器工作负载尤其关键。
	•	消除 shim 层的潜在僵尸任务与资源泄露风险。
在 PR #10651 中提到的问题是：Fix races / prevent init exits from being dropped

也就是：init 容器进程的退出信号 race 掉了，原因之一是监听 goroutine 和处理退出 goroutine 并发执行，Wait() 可能先执行完，而 notify 还没 setup。所以该 PR 在多个关键路径上加强了 lifecycleMu 的使用，确保退出信号在生命周期管理中不会被 “掉” 掉。





PR #10177: Multipart Layer Fetch: 为 containerd 增加了对镜像 layer 的**多线程并发分块下载（multipart fetch）**能力，以提升大镜像拉取性能。

⸻

为什么这么做（Why）

为了解决在拉取大型镜像（特别是大 layer）时存在的单线程 I/O 瓶颈，尤其在高速网络或分布式节点环境中会导致镜像下载时间过长。

⸻

主要改动（Where）
	1.	引入新的配置项 performance：
	•	包含 MaxConcurrentDownloads 与 ChunkSize。
	•	可通过配置文件注入到 resolver 行为中。
	2.	修改 fetch 调用链：
	•	在 remotes/docker/fetcher.go 中增加并发 chunk fetch 的逻辑。
	•	条件触发：只有在 performance 被显式设置时才使用 multipart fetch。
	3.	统一通过 fetchHandler 注入 fetch 策略：
	•	包括 chunk fetch 和 fallback 逻辑，确保兼容性。

⸻

效果（Impact）

用户可以通过配置项启用并发拉取镜像 layer，极大地提升了容器 cold start 时镜像下载的性能，尤其对大模型镜像、AI 推理框架等镜像场景非常友好。



PR #11006: Add content create event: 此 PR 为 containerd 添加了一个新的事件类型 ContentCreate，用于在内容创建时发出通知，增强了系统的可观测性和事件驱动能力。

⸻

背景知识

在 containerd 中，内容（content）是镜像和层（layer）的基础构建块。之前，containerd 的事件系统缺少对内容创建的直接通知，导致上层系统需要通过轮询来检测内容的变化，效率较低。

Issue #10508 指出，在某些情况下，内容创建后没有相应的事件通知，影响了系统的响应能力。

⸻

这个 PR 做了什么
	1.	定义新事件类型：在 API 中新增了 ContentCreate 事件类型。
	2.	在内容创建时发送事件：修改了内容存储逻辑，在内容创建成功后发送 ContentCreate 事件。
	3.	更新事件处理机制：确保新的事件类型被正确处理和传递。

⸻

实现要点
	•	事件定义：在 api/events/content.proto 中定义了新的事件类型。
	•	事件发送：在内容创建逻辑中，调用事件发送接口，发布 ContentCreate 事件。
	•	事件处理：更新了事件处理器，确保新的事件类型被正确识别和处理。

⸻

影响范围
	•	增强可观测性：上层系统可以通过监听 ContentCreate 事件，实时获取内容创建信息，减少了轮询的需求。
	•	提高响应能力：系统可以更快地对内容变化做出反应，提升整体性能。

⸻

阅读建议
	•	查看 api/events/content.proto，了解新事件类型的定义。
	•	阅读内容创建逻辑，了解事件发送的时机和条件。
	•	了解事件处理机制，确保对新事件类型的支持。

⸻

如果你需要，我可以帮助你生成这个 PR 的 Markdown 总结文件，或者我们可以继续分析下一个 PR。请告诉我你的选择。

PR #10649: integration: regression test for issue 10589: 这个 PR 添加了一个集成测试，用于验证 issue #10589 中提到的问题是否已修复 —— 当 container exit 事件发生得非常快时，task 状态可能未能被 containerd 正确记录。

⸻

背景知识
	•	问题根源：在极端情况下，容器启动后立即退出，containerd 的事件处理逻辑可能来不及观察 exit event，导致 task.Status() 返回不准确（如返回为 running）。
	•	场景：容器生命周期短暂，如命令为 /bin/true 或 /bin/echo hello 等。
	•	Issue #10589 报告：如果你立即检查容器状态，可能会读到旧值或者状态不一致。

⸻

这个 PR 做了什么
	1.	添加测试文件：
test/integration/container_task_test.go
	2.	新增测试函数：

func TestTaskStatusAfterExit(t *testing.T) {


	3.	测试逻辑：
	•	创建一个非常快退出的容器（如 /bin/true）。
	•	调用 task.Start(ctx)。
	•	立刻调用 task.Wait() 等待其退出。
	•	然后调用 task.Status(ctx) 检查状态必须为 stopped。
	•	最后清理资源。

⸻

实现要点
	•	使用 require.Eventually 等待状态变为 stopped，避免 race。
	•	强调 task 状态反映必须准确，否则可能引起上层 scheduler、metrics 系统误判。

⸻

影响范围
	•	仅添加测试，对现有逻辑无功能性修改。
	•	提高了 containerd 在短生命周期容器处理上的可靠性回归保障。

⸻

阅读建议

这个 PR 的代码量不大、逻辑简单清晰，建议你可以：
	•	顺带翻一翻 task.Status() 的调用实现（在 runtime/v2/shim 下）。
	•	快速过一下 testutil 工具和 Wait() 的实现，看下 signal 是怎么被通知的。

⸻




PR #10375 — cri: get pid count from container metrics: 为 CRI 的容器统计接口增加了 当前进程数（PID count） 的上报能力，提升了容器资源可观测性。

⸻

背景知识：

在 Kubernetes 使用 containerd 时，ContainerStats 接口用于提供每个容器的资源使用信息（CPU、内存、IO 等），但此前并没有包含容器中的进程数（pids）。而在实际运维与限额管理中，监控容器内的进程数非常重要（尤其是避免 PID 爆炸）。

Linux cgroup 提供了 pids.current 字段，可以精确地反映容器中的活跃进程数。

⸻

这个 PR 解决了什么问题？
	•	补全了 CRI 容器统计中对 PID 数量的缺失
	•	使 crictl stats 之类的工具可以获取到 PID 信息
	•	有助于 Kubernetes 基于 metrics 进行容器健康检查或自动限流

⸻

实现要点：
	•	修改了 pkg/cri/server/container_stats.go
	•	调用 ContainerMetrics 接口，获取容器的 metrics 报文
	•	从 metrics 中提取 pids.current 字段，填入 ContainerStats 的 Process 字段中
	•	最终在 CRI 响应中增加 stats.Process.Pids.Current 字段



PR #9470：add use systemd cgroup e2e
	•	改动内容：为 containerd 添加了使用 systemd cgroup 驱动的端到端（e2e）测试配置选项。
	•	影响效果：验证 containerd 在启用 SystemdCgroup = true 场景下的行为，提升对 systemd 驱动下资源隔离功能的测试覆盖率与稳定性保障。


PR #10980：Remove confusing warning in cri runtime config migration
	•	改动内容：移除了在 CRI runtime 配置迁移期间输出的误导性 warning 日志。
	•	影响效果：减少用户在 containerd 升级或运行时看到无实际影响的警告信息，提升日志可读性与用户信任感。


PR #175：Fix race between serve and immediate shutdown on the server
	•	改动内容：修复了在测试场景下，当 Serve() 和 Shutdown() 几乎同时调用时，server 因所有 listener 已关闭而阻塞在 Accept() 的竞态问题。
	•	影响效果：确保 server 在 listener 已关闭后能优雅退出，避免测试中 Serve() 被卡死或挂起。

PR #11131 – Enable Writable cgroups for Unprivileged Containers

一句话总结：

该 PR 引入对 “unprivileged containers” 写入自身 cgroup 路径的支持（在 cgroup v2 环境下），使非特权容器能够在内核允许的范围内动态调整其资源配置，从而提升灵活性并保持兼容性。

⸻

背景知识：

✅ 什么是 Unprivileged Container？
	•	没有 CAP_SYS_ADMIN、不能访问 /sys/fs/cgroup 的 rootless 容器；
	•	在 Kubernetes/Podman 等环境中广泛使用，以提升隔离性和安全性。

✅ 什么是 Writable Cgroup？
	•	是否允许容器自身（非 containerd/shim）写入其对应的 cgroup 控制文件；
	•	在 cgroup v2 中，默认行为是不可写（尤其在 rootless 模式下）。

⸻

这个 PR 解决了什么问题？

问题点：
	•	在某些 workload（如 self-regulating processes / ML workload）中，容器内进程需要调整自身的 CPU/memory 限额或添加子进程；
	•	当前 containerd 的默认策略是禁写（即使宿主系统允许），导致无法运行此类 workload。

解决方案：
	•	添加一个新的配置项（例如 AllowWritableCgroups）；
	•	当启用该配置，并且宿主系统允许时，containerd 会将 cgroup 挂载为 rw 并放行写入；
	•	兼容 cgroup v2 环境，同时仍保留默认 ro（安全第一）的行为。

⸻

实现要点：
	•	修改了 cgroup.go 中的挂载参数；
	•	判断是否是 unprivileged container；
	•	增加安全性提示 & 注释，说明使用该功能的风险；
	•	加入配置解析与插件注入，确保不会影响已有运行时。



PR #10705 - EROFS snapshotter and differ: 该 PR 为 containerd 增加了对 EROFS（Enhanced Read-Only File System） 的 snapshotter 与 differ 支持，使得容器可以使用高压缩率、只读优化的镜像格式进行运行，显著提升冷启动性能与存储效率，特别适用于云原生环境与 image acceleration 场景。

⸻

重点价值

✅ 什么是 EROFS？
	•	一种 只读压缩文件系统，由阿里云开发，已合并进 Linux 内核；
	•	支持 块级随机访问 + 页缓存直通，比 SquashFS 更适合容器场景；
	•	主要用于：
	•	镜像加速（如 Nydus、Dragonfly、Kata）
	•	无状态容器
	•	低 I/O 环境（云原生节点、边缘设备）

✅ 这次 PR 做了什么？
	1.	引入了 erofs 类型的 snapshotter 插件（plugin 注册方式，和 overlayfs snapshotter 平行）；
	2.	实现了 erofs differ 模块，用于 layer diff 比较；
	3.	接入 snapshot plugin 体系（支持 plugin discovery / lazy loading）；
	4.	提供了 EROFS-specific 配置项支持；
	5.	通过 CI 验证，标记为 experimental。






PR #10745 - Add no_sync option to boost boltDB performance on ephemeral environments: 该 PR 引入了一个 no_sync 配置选项，允许在易失性（ephemeral）环境中跳过对 BoltDB 的 fsync 调用，从而显著提高 metadata 读写性能，适用于测试、CI、短生命周期容器等非持久化场景。

⸻

为什么它值得关注？

✅ 重要背景：
	•	containerd 使用 BoltDB 存储元数据（如 leases、snapshots、content refs 等）；
	•	默认情况下，BoltDB 每次事务提交都会调用 fsync，确保数据写入磁盘；
	•	在 临时容器环境（如 CI、test containers、短命任务）中，这个 fsync 代价高且 没有必要，因为：
	•	容器生命周期短；
	•	文件系统本身可能是 tmpfs（内存盘）或 sandbox；
	•	持久化安全性不是目标，性能才是重点。

✅ 这个 PR 的改动点：
	•	添加了一个配置字段 no_sync（布尔值）；
	•	如果启用该选项，将在使用 BoltDB 时关闭 fsync；
	•	明确只推荐在 ephemeral/test environments 中使用。


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


Update CRI to use transfer service for image pull by default #8515：此更新提议将 CRI（Container Runtime Interface）默认使用 transfer service 来拉取镜像，取代之前的混合实现方式。 这样可以利用 transfer store 的新功能，如沙箱解包、凭证助手和镜像验证等
