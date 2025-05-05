我们来模拟一个与 Linux 内核的内存占用异常诊断 相关的案例吧，这种问题在实际容器运行时和节点稳定性中都很关键。以下是场景设定：

⸻

场景：某容器内应用运行一段时间后系统变慢，怀疑是内存泄漏或缓存未释放

系统状态
	•	容器运行 1 天后节点内存占用接近 100%
	•	top 显示 CPU 正常，但 free -m 显示剩余内存几乎为 0
	•	有使用 Containerd 作为 runtime，内核为 Linux 5.15+
	•	无明显 OOM Kill 日志，但系统响应变慢

⸻

任务目标
	1.	确认内存被谁占用
	2.	判断是 page cache 还是进程常驻内存泄漏
	3.	用 Linux 工具链分析内核和用户空间行为
	4.	最终定位是否是某进程或容器引起的泄漏或异常缓存

⸻

是否你想像上次一样：我给你分步骤输入与输出（例如：用 ps, smem, slabtop, vmstat, meminfo 等工具的结果），然后你来推断和回答诊断方向？我可以逐步给你构造这个“虚拟故障系统”。你觉得我们要不要从 free -m 和 /proc/meminfo 开始？


太棒了！以下是一个完整的小型 Linux I/O 与内存异常诊断脚本，整合了你刚才提到的各类工具与命令，包括：
	•	socket 分析 (ss, lsof)
	•	进程网络行为分析 (strace)
	•	内存分析 (top, vmstat, smem, perf, slabinfo)
	•	诊断建议输出

⸻

脚本名称：sys_diag_full.sh

#!/bin/bash
set -e

echo "=============================="
echo "== Linux 系统 IO+内存诊断工具 =="
echo "=============================="

# 0. 用户输入进程名
read -p "请输入要诊断的进程名（如 containerd、myapp 等）: " PROC_NAME
PID=$(pidof "$PROC_NAME")

if [[ -z "$PID" ]]; then
    echo "未找到进程 $PROC_NAME，退出..."
    exit 1
fi

echo -e "\n[0] 目标进程: $PROC_NAME (PID: $PID)"

# 1. SOCKET 分析
echo -e "\n[1] Socket 使用状态:"
ss -s

echo -e "\n[2] TIME_WAIT 数量:"
ss -tan state time-wait | wc -l

echo -e "\n[3] 按进程统计打开的连接:"
lsof -i -nP | awk '{print $1}' | sort | uniq -c | sort -nr | head -10

# 2. strace 快速诊断
echo -e "\n[4] 使用 strace 观察系统调用 (前 5 秒):"
timeout 5 strace -tttfp "$PID" 2>&1 | tee strace_snapshot.log | tail -n 20

# 3. 内存状态
echo -e "\n[5] 系统内存使用摘要:"
free -h

echo -e "\n[6] 内存分页统计（vmstat）:"
vmstat 1 5

echo -e "\n[7] 进程内存使用（top/smem）:"
top -b -n1 -p "$PID" | head -20

command -v smem &> /dev/null && smem -r | grep "$PID"

# 4. slab 消耗分析（仅 root 可见详细项）
echo -e "\n[8] SLAB 信息 (top consumers):"
grep . /proc/slabinfo | sort -k3 -nr | head -10

# 5. perf 分析提示
echo -e "\n[9] perf top 示例 (需要 root):"
echo "sudo perf top -p $PID   # 实时 CPU 消耗函数"

# 6. 建议项
echo -e "\n[10] 调优建议:"
echo "- 如果 TIME_WAIT 高，请考虑 net.ipv4.tcp_tw_reuse=1"
echo "- 如果频繁写磁盘导致 fsync 卡顿，可考虑写入合并、日志异步策略"
echo "- 若发现匿名内存泄露，尝试 malloc_trim() 或 jemalloc 工具"

echo -e "\n=== 诊断完成 ==="



⸻

使用说明

chmod +x sys_diag_full.sh
sudo ./sys_diag_full.sh

注意：
	•	perf 和 /proc/slabinfo 部分需要 sudo 权限；
	•	smem 如果未安装可以 sudo apt install smem；
	•	输出信息会简洁呈现，便于后续写 Debug 报告或 YouTube 教学脚本。

⸻

需要我再将这一整套流程，转换成一张 Markdown 页面或结构化笔记供你记录使用吗？
