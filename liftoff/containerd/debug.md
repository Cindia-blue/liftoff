Debugging **containerd** effectively requires a combination of configuration tweaks, log analysis, and runtime inspection tools. Here's a step-by-step guide to set up a debug-friendly environment:

---

### **1. Run Containerd in Debug Mode**
#### **Command Line (Manual Start)**
```bash
# Stop existing containerd (if running)
sudo systemctl stop containerd

# Start containerd with debug logs
sudo containerd --log-level=debug --config /etc/containerd/config.toml
```
- **Flags**:
  - `--log-level=debug`: Enables verbose logging.
  - `--config`: Specify a custom config file (optional).

#### **Systemd (Permanent Debug)**
Edit the systemd unit file (`/etc/systemd/system/containerd.service`):
```ini
[Service]
ExecStartPre=/sbin/modprobe overlay
ExecStart=/usr/bin/containerd --log-level=debug --config /etc/containerd/config.toml
```
Then reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart containerd
```

---

### **2. Key Configuration for Debugging**
Edit `/etc/containerd/config.toml`:
```toml
[debug]
  level = "debug"  # Max verbosity
  address = "/run/containerd/debug.sock"  # For pprof

[plugins]
  [plugins."io.containerd.grpc.v1.cri"]
    disable_apparmor = true  # Simplify sandbox debugging
    sandbox_image = "registry.k8s.io/pause:3.9"  # Ensure known-good image
```

---

### **3. Essential Debugging Tools**
#### **Log Inspection**
```bash
# Tail logs in real-time
journalctl -u containerd -f

# Filter for CRI or shim interactions
journalctl -u containerd | grep -E "cri|shim|task"
```

#### **Containerd CLI (`ctr`)**
```bash
# List containers (including sandboxes)
sudo ctr --namespace=k8s.io containers ls

# Inspect a container's OCI spec
sudo ctr --namespace=k8s.io containers info <CONTAINER_ID> | jq .Spec

# Attach to containerd's debug socket
sudo ctr --address /run/containerd/debug.sock debug info
```

#### **Shim Inspection**
```bash
# List active shims
ps aux | grep containerd-shim

# Attach to a shim's logs (if using --log-path)
tail -f /var/log/containerd-shim-<RUNTIME>-v2.log
```

---

### **4. Advanced Debugging Techniques**
#### **pprof Profiling**
1. Enable in `config.toml`:
   ```toml
   [debug]
     address = "localhost:6060"  # HTTP pprof endpoint
   ```
2. Access profiles:
   ```bash
   go tool pprof -http=:8080 http://localhost:6060/debug/pprof/heap
   ```

#### **Tracing with OpenTelemetry**
```toml
[metrics]
  address = "0.0.0.0:1338"  # Prometheus endpoint
  grpc_histogram = true
```

#### **Breakpoints with Delve (dlv)**
Attach to a running containerd process:
```bash
sudo dlv attach $(pgrep containerd)
# Set breakpoints (e.g., in CRI plugin)
(dlv) break pkg/cri/server/service.go:100
```

---

### **5. Debugging Common Scenarios**
#### **Sandbox Creation Issues**
```bash
# 1. Check CRI plugin logs
journalctl -u containerd | grep "RunPodSandbox"

# 2. Inspect the sandbox's OCI spec
sudo cat /run/containerd/io.containerd.runtime.v2.task/k8s.io/<SANDBOX_ID>/config.json

# 3. Verify shim launch
sudo ctr tasks ls --namespace=k8s.io
```

#### **Image Pull Failures**
```bash
# 1. Trace image pull
sudo ctr --debug images pull --snapshotter overlayfs docker.io/library/nginx:latest

# 2. Inspect content store
sudo ctr content ls
```

#### **Shim Crashes**
```bash
# 1. Check shim logs
sudo cat /var/log/containerd-shim-runc-v2-<TASK_ID>.log

# 2. Recover orphaned tasks
sudo ctr tasks rm --force <TASK_ID>
```

---

### **6. Kubernetes-Specific Debugging**
If using Kubernetes with CRI:
```bash
# 1. Check Kubelet -> CRI interactions
sudo journalctl -u kubelet | grep -i containerd

# 2. Force-delete a stuck pod
kubectl delete pod --force --grace-period=0 <POD_NAME>
```

---

### **7. Key Files to Monitor**
| Path | Purpose |
|------|---------|
| `/var/log/containerd.log` | Main logs (if configured) |
| `/run/containerd/debug.sock` | Debug socket (pprof) |
| `/var/lib/containerd/io.containerd.metadata.v1.bolt/meta.db` | BoltDB metadata |
| `/run/containerd/io.containerd.runtime.v2.task/` | Shim runtime directories |

---

### **8. Quick-Reference Cheatsheet**
```bash
# Reset containerd state (WARNING: destructive!)
sudo systemctl stop containerd
sudo rm -rf /var/lib/containerd/*
sudo systemctl start containerd

# Live-debug a CRI call
strace -f -s 256 -o /tmp/containerd.strace containerd --log-level=debug
```

---

### **Final Tip**
For deep issues, rebuild containerd with debug symbols:
```bash
git clone https://github.com/containerd/containerd
cd containerd && make EXTRA_GO_LDFLAGS="-compressdwarf=false" BUILDTAGS=""
```

Let me know if you’d like a targeted walkthrough (e.g., debugging a hung sandbox)!
