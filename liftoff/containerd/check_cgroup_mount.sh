#!/bin/bash

# 用法: ./check_cgroup_mount.sh <container_name>
# 需要: sudo 权限, ctr 工具, jq

CONTAINER_NAME="$1"

if [ -z "$CONTAINER_NAME" ]; then
  echo "Usage: $0 <container_name>"
  exit 1
fi

# 获取容器 PID
PID=$(sudo ctr -n k8s.io task ls --quiet | grep "$CONTAINER_NAME" | xargs -I {} sudo ctr -n k8s.io task info {} | jq -r '.Pid')

if [ -z "$PID" ] || [ "$PID" = "null" ]; then
  echo "Unable to find PID for container: $CONTAINER_NAME"
  exit 1
fi

echo "Found PID: $PID"
echo "Entering mount namespace of container..."

# 使用 nsenter 进入容器的 mount namespace，查看 cgroup 挂载情况
sudo nsenter --target "$PID" --mount -- bash -c 'echo "--- /sys/fs/cgroup mount info ---"; mount | grep /sys/fs/cgroup; echo ""; echo "--- findmnt result ---"; findmnt /sys/fs/cgroup || true'
