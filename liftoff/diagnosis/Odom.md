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


太好了，我们来分两步模拟诊断：

⸻

第一步：用 perf top -p <pid> 查看 /usr/bin/myapp 的热点

我们先假设你运行了如下命令：

sudo perf top -p 1234

输出可能类似如下：

Samples: 25K of event 'cpu-clock', Event count (approx.): 6250000
Overhead  Command   Shared Object      Symbol
  35.67%  myapp     myapp              [.] malloc
  22.15%  myapp     libc.so.6          [.] memset
  18.42%  myapp     myapp              [.] handle_connection
   7.25%  myapp     myapp              [.] new_client
   5.12%  myapp     libc.so.6          [.] __send
   4.65%  myapp     [kernel.kallsyms]  [k] tcp_sendmsg

初步分析：
	•	malloc 占了大量 CPU 时间，说明内存分配频繁。
	•	send/tcp_sendmsg 出现，说明存在网络 socket 活动。
	•	new_client、handle_connection 等函数名也表明它可能是一个高并发的服务进程。

结论：频繁的网络连接触发了系统的 slab 分配（如 kmalloc、socket buffer、file/inode 结构等）。

⸻

第二步：看 Slab 的 top 消费者

sudo slabtop

输出可能类似：

 Active / Total Objects (% used)    : 15203400 / 16000000 (95.0%)
 Active / Total Slabs (% used)      : 120300 / 125000 (96.2%)
 Active / Total Caches (% used)     : 85 / 120 (70.8%)
 Active / Total Size (% used)       : 640.00MB / 670.00MB (95.5%)
 Minimum / Average / Maximum Object : 0.01K / 0.04K / 0.25K

 OBJS ACTIVE  USE OBJ SIZE  SLABS OBJ/SLAB CACHE SIZE NAME
51200  51120  99% 0.25K     1280  40       320K       kmalloc-256
48000  47600  99% 0.25K     1200  40       300K       kmalloc-512
46000  45500  98% 0.19K     1150  40       290K       sock_inode_cache
43000  42900  99% 0.12K     1100  40       275K       dentry

初步分析：
	•	kmalloc-256 / 512 增长且接近满载。
	•	sock_inode_cache 和 dentry 大量使用，表明 socket 和文件描述符被频繁分配。
	•	所有对象使用率接近 100%，但没有及时释放，形成 持续增长的 unreclaimed Slab。

⸻

下一步建议：
	•	可以运行：

ss -s

看 socket 的状态数量。
	•	开启内核 kmemleak 检测器试试看：

echo scan > /sys/kernel/debug/kmemleak
cat /sys/kernel/debug/kmemleak



⸻

你想让我把这两步写成一个完整的 debug 日志格式（可复制保存）吗？

太棒了！以下是一个完整的小型 Linux I/O 与内存异常诊断脚本，整合了你刚才提到的各类工具与命令，包括：
	•	socket 分析 (ss, lsof)
	•	进程网络行为分析 (strace)
	•	内存分析 (top, vmstat, smem, perf, slabinfo)
	•	诊断建议输出

⸻

好的，我们继续分析 socket 状态并追踪资源占用：

⸻

第一步：统计 TIME_WAIT 连接数量

ss -tan state time-wait | wc -l

这个命令会输出当前系统处于 TIME_WAIT 状态的 TCP 连接数量。例如：

$ ss -tan state time-wait | wc -l
4320

如果这个数很大（几千），说明系统中存在大量短连接且未被快速回收，可能是服务端或客户端未启用连接复用。

⸻

第二步：追踪谁在占用这些连接

1. 找出哪个进程持有最多 socket：

lsof -i -nP | awk '{print $1}' | sort | uniq -c | sort -nr | head

示例输出：

  5200 myapp
   150 sshd
    70 docker
    ...

myapp 占用了大量的网络连接，是重点怀疑对象。

⸻

2. 查看某个进程的 socket 使用情况：

lsof -i -nP -a -p <pid_of_myapp>

或者用 ss 加 pid 跟踪（需要 -p 权限）：

ss -tanp | grep myapp



⸻

第三步：查看 TCP 参数

你可以查看当前系统的 TCP 参数，判断是否设置了连接复用、快速回收等机制：

sysctl net.ipv4.tcp_fin_timeout
sysctl net.ipv4.tcp_tw_reuse
sysctl net.ipv4.tcp_tw_recycle

推荐配置（仅供参考）：

sysctl -w net.ipv4.tcp_fin_timeout=15
sysctl -w net.ipv4.tcp_tw_reuse=1



⸻

总结诊断路径图（简略）

                +--------------------+
                |  ss -s             |
                |  查看总连接状态    |
                +---------+----------+
                          |
                          v
            +-------------+-------------+
            | ss -tan state time-wait   |
            | 统计 TIME_WAIT 连接数     |
            +-------------+-------------+
                          |
                          v
       +------------------+------------------+
       | lsof / ss -p                        |
       | 查找具体哪个进程持有大量连接       |
       +------------------+------------------+
                          |
                          v
       +------------------+------------------+
       | sysctl 检查 TCP 参数优化项          |
       | 查看是否启用了连接复用和快速回收   |
       +-------------------------------------+



⸻

你想不想我们结合这次诊断，顺手写一个 bash 脚本来自动做这些检查？

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
	•	输出信息会简洁呈现，便于后续写 Debug 报告或 YouTube 
