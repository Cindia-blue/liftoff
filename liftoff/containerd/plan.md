Containerd PR Filter 关键词建议表

关键词	含义说明	适用方向
snapshot	与 snapshotter（如 overlayfs、erofs）相关的实现与优化	存储子系统、容器文件系统管理
plugin	containerd plugin 机制（snapshotter、runtime、content、differ 等）	模块架构分析、动态注入机制
bolt / boltdb	与 boltdb content store 实现、优化或迁移相关	内容存储层（content store）
recovery	涉及任务恢复、异常状态自愈机制	稳定性、状态管理
security	seccomp、AppArmor、mount masks、rootless 模式等	容器安全控制
shim	与 shim v2 通信、task 生命周期（start/exit）管理相关	容器运行态、调度链路
mount	与挂载行为有关，如挂载 flag、overlay 层配置	文件系统接入、FS 层 debug
metrics	容器运行状态采集、Prometheus 集成、监控指标导出	可观测性、运营支撑
gc	content / snapshot 垃圾回收逻辑	生命周期管理、资源优化
namespace	多租户隔离、跨组件命名空间绑定逻辑	租户模型、资源隔离性
auth	registry 凭证、image pull 认证流程	镜像访问权限、身份验证
leases	生命周期资源管理（lease 绑定 snapshot、content、container）	清理流程、租约绑定
plumbing	底层逻辑 glue code（如 server/client 交互接口、proto 接口定义）	架构粘合层、跨模块调用路径梳理



⸻

基础过滤器模板

你可以用如下 filter 作为模板，替换其中关键词：

repo:containerd/containerd is:pr is:merged <关键词> created:2023-01-01..2025-05-01 label:size/XL

是否需要我根据你明天的重点方向（比如 plugin or snapshot）提前列一组推荐 PR？我可以帮你直接筛出前 5 个。