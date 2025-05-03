
# Enabling and Verifying `SystemdCgroup` in Containerd

This guide explains how to enable the `SystemdCgroup` driver in containerd and verify that it is correctly applied.

---

## ✅ 1. Enable `SystemdCgroup` in Containerd

### Edit `/etc/containerd/config.toml`:

Locate the CRI plugin config:

```toml
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
  SystemdCgroup = true
```

This tells containerd to let `systemd` manage the cgroup hierarchy.

### Restart containerd:

```bash
sudo systemctl restart containerd
```

---

## 🧪 2. Verify SystemdCgroup is in Effect

### Method 1: Check shim process cgroup

1. Find the PID of containerd-shim:

```bash
ps -eo pid,cmd | grep containerd-shim
```

2. Inspect its cgroup:

```bash
cat /proc/<shim-pid>/cgroup
```

- If systemd is used, you’ll see something like:
  ```
  0::/system.slice/containerd.service/mycontainer.scope
  ```

- If using cgroupfs:
  ```
  0::/containerd/io.containerd.runtime.v1.linux/k8s.io/<container_id>
  ```

---

### Method 2: Ensure kubelet (if used) matches

In Kubernetes, kubelet must also use systemd driver:

```bash
ps -ef | grep kubelet
```

Look for:
```
--cgroup-driver=systemd
```

---

## 📌 Why SystemdCgroup Matters

| Reason | Benefit |
|--------|---------|
| Unified resource control | Avoids split hierarchy between systemd and containerd |
| Proper cleanup | systemd ensures containers are cleaned up reliably |
| Compatibility | Required in `cgroup v2`-based systems |
| Security | Improves visibility and security of resource delegation |

---

## ✅ Summary

Enabling `SystemdCgroup` is highly recommended on systemd-based distros (Ubuntu, Fedora, RHEL). It ensures consistency, simplifies diagnostics, and makes container cleanup and resource isolation more reliable.

