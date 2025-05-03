
# Comparison of `cgroupfs` vs `systemd` Cgroup Driver in containerd

This document compares how containerd injects `cgroup` configuration when using `cgroupfs` vs `systemd` drivers.

---

## 1. **Overview of the Two Modes**

| Driver Type | Description |
|-------------|-------------|
| `cgroupfs`  | Container runtime (e.g. containerd) directly creates and manages cgroup hierarchy in `/sys/fs/cgroup` |
| `systemd`   | containerd interacts with systemd (e.g. via dbus) to manage cgroup slices and scopes |

---

## 2. **Relevant Source Paths in containerd**

| Area                  | Path |
|-----------------------|------|
| Runtime config logic  | `runtime/v2/runc/options.go` |
| runc shim options     | `runtime/v2/runc/runc.go` |
| Cgroup injection      | `pkg/cgroups/...` |
| Plugin config parsing | `config/config.go` |

---

## 3. **Cgroup Injection in container Creation**

### a. `cgroupfs` Flow

```go
// Code path
// -> options.SystemdCgroup = false (default)
// -> NewCgroupManager("cgroupfs")
// -> creates /sys/fs/cgroup/... directly

runcOptions := &options.Options{
    SystemdCgroup: false,
}
cgroupManager := cgroups.NewManager("cgroupfs")
cgroupManager.Apply(pid)
```

- containerd uses pure Go libraries (e.g. `opencontainers/runc/libcontainer/cgroups/fs`)
- It manually mounts and writes to:
  - `/sys/fs/cgroup/cpu/...`
  - `/sys/fs/cgroup/memory/...` etc.

---

### b. `systemd` Flow

```go
// -> options.SystemdCgroup = true
// -> NewCgroupManager("systemd")
// -> creates systemd slice/unit via dbus or system calls

runcOptions := &options.Options{
    SystemdCgroup: true,
}
cgroupManager := cgroups.NewManager("systemd")
cgroupManager.Apply(pid)
```

- containerd creates a scope under a slice:
  - `/sys/fs/cgroup/system.slice/containerd.service/<container-id>.scope`
- Calls are delegated to `systemd` via:
  - `org.freedesktop.systemd1` dbus interface
  - or internal systemctl helpers

---

## 4. **Behavioral Differences**

| Behavior                | `cgroupfs`          | `systemd`                        |
|-------------------------|---------------------|----------------------------------|
| Cgroup creation         | Manual via containerd | Automatic via systemd           |
| Cleanup                 | Needs manual handling | Automatically done by systemd   |
| Integration with host   | Weak                 | Strong (aligned with services)  |
| Compatibility with cgroup v2 | Limited         | Preferred / Required            |

---

## ✅ Recommendation

- Use `SystemdCgroup = true` on systemd-enabled systems and for all `cgroup v2` environments.
- `cgroupfs` is suitable only for lightweight testing or when systemd is not present.

