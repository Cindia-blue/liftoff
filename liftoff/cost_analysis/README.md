分别制定两个模块的系统性准备路径：

1. Code Review 技能提升（以避免 Incident）

重点在于结构性判断、风险预估与回归保护能力：
	•	模块化审查能力
	•	熟悉常见设计反模式（e.g. tight coupling, hidden state）
	•	识别代码中的 side-effect 与不可预测路径
	•	安全性 & 并发性审查
	•	Thread-safety（如 Mutex、Atomic）、goroutine 泄漏点识别
	•	input validation、防御性编程
	•	部署和回归保障
	•	判断是否需要增加 test coverage 或增加 regression test
	•	审查 feature flag、backward compatibility 与 migration strategy
	•	Lint & 审查流程
	•	制定 Cloud Runtime 的 review checklist（我可以帮你起草）

⸻

2. AWS 成本分析与效率优化

重点在于架构层、资源分配与工具监控三层策略：
	•	资源使用结构分析
	•	EC2 实例类型选型（e.g. spot vs reserved vs on-demand）
	•	EBS、S3、Network egress 的计费模型与优化方法
	•	Kubernetes/Runtime 层的优化
	•	container resource requests/limits 的设定与 oversubscription 设计
	•	idle instance 和 overprovisioning 检测与治理
	•	使用工具与评估
	•	AWS Cost Explorer / Compute Optimizer 的使用
	•	Prometheus + CloudWatch 联动成本指标（e.g. $/pod, $/job）
	•	成本效率指标设计（如 $/RPS, $/job-success）

请展示一个Code Review实例（比如摘取containerd的PR diff为蓝本） + 一个AWS成本优化案例，结合实际例子 给出核心原则讲解