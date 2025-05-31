Let's break down how **snapshotters** work in containerd, their interaction with **overlayfs**, and their relationship with the **shim** layer. Here's a step-by-step guide with code references:

---

### **1. Snapshotter Basics**
**Purpose**: Manage filesystem snapshots (layers) for containers.  
**Key Operations**:  
- **Prepare**: Create a writable layer.  
- **Commit**: Make a layer immutable (used as base for new layers).  
- **Mount**: Expose layers to containers.  

**Code Location**:  
- Interface: `github.com/containerd/containerd/snapshots/snapshotter.go`  
- OverlayFS Implementation: `github.com/containerd/containerd/snapshots/overlay`  

---

### **2. Step-by-Step: Snapshotter Workflow**
#### **Step 1: Snapshotter Initialization**
Containerd loads the snapshotter plugin (e.g., `overlayfs`) at startup:  
```go
// From cmd/containerd/server.go
if err := plugin.Register(&plugin.Registration{
    Type: plugin.SnapshotPlugin,
    ID:   "overlayfs",
    InitFn: func(ic *plugin.InitContext) (interface{}, error) {
        return overlay.NewSnapshotter(ic.Root) // Initialize overlayfs snapshotter
    },
}); err != nil {
    return fmt.Errorf("failed to register snapshotter plugin: %w", err)
}
```
**Key Parameters**:  
- `ic.Root`: Directory where snapshots are stored (default: `/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs`).  

---

#### **Step 2: Creating a Snapshot (Prepare)**
When pulling an image or creating a container:  
```go
// From pkg/cri/server/image_pull.go
mounts, err := c.snapshotter.Prepare(ctx, key, parent.String())
```
**What Happens**:  
1. **OverlayFS Layer Creation**:  
   - A new directory is created under `ic.Root/snapshots/<id>/fs`.  
   - Metadata is stored in `ic.Root/snapshots/<id>/metadata`.  
2. **Mount Specification**:  
   - Returns `mount.Mount` structs describing how to mount the layer (e.g., `overlay` with `lowerdir`, `upperdir`, `workdir`).  

**OverlayFS Mount Example**:  
```go
// From snapshots/overlay/overlay.go
return []mount.Mount{
    {
        Type:    "overlay",
        Source:  "overlay",
        Options: []string{
            fmt.Sprintf("lowerdir=%s", strings.Join(lowerDirs, ":")),
            fmt.Sprintf("upperdir=%s", path.Join(s.upperPath(id), "fs")),
            fmt.Sprintf("workdir=%s", path.Join(s.workPath(id), "work")),
        },
    },
}
```

---

#### **Step 3: Committing a Snapshot**
After modifying a layer (e.g., during image build):  
```go
// From pkg/cri/server/container_create.go
if err := c.snapshotter.Commit(ctx, containerID, key); err != nil {
    return nil, fmt.Errorf("failed to commit snapshot: %w", err)
}
```
**What Happens**:  
- The writable layer (`upperdir`) becomes immutable.  
- Metadata is updated to mark the snapshot as "committed".  

---

#### **Step 4: Mounting Snapshots for Containers**
When starting a container, the snapshotter provides mounts to the **shim**:  
```go
// From services/tasks/local.go
mounts, err := container.SnapshotMounts(ctx)
if err != nil {
    return nil, err
}
```
**Shim Interaction**:  
1. The **shim** (e.g., `containerd-shim-runc-v2`) receives the mounts via gRPC (`tasks.CreateTaskRequest`).  
2. The shim executes `runc` with the mount specifications:  
   ```bash
   runc create --bundle /path/to/bundle --mount /dev/sda1:/mnt:overlay
   ```

---

### **3. OverlayFS Structure Explained**
**Example Snapshot Directory**:  
```
/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/
   ├── snapshots/
   │   ├── 1/               # Snapshot ID
   │   │   ├── fs           # Upperdir (writable layer)
   │   │   └── work         # Workdir (OverlayFS internal)
   │   └── 2/
   │       └── fs           # Lowerdir (base layer)
   └── metadata.db          # BoltDB for snapshot metadata
```

**How Layers Stack**:  
- **Lowerdir**: Base image layers (read-only).  
- **Upperdir**: Container-specific changes (writable).  
- **Merged**: Unified view exposed to the container.  

---

### **4. Debugging Snapshotters**
#### **Inspect Snapshots**  
```bash
# List all snapshots
ctr snapshot ls

# Inspect a snapshot's mounts
ctr snapshot mounts /var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/1
```

#### **Trace OverlayFS Calls**  
```bash
# Monitor overlayfs kernel calls
sudo strace -f -e trace=mount,umount2 -p $(pgrep containerd)
```

#### **Check Shim Logs**  
```bash
# View shim logs for mount errors
journalctl -u containerd | grep shim | grep overlay
```

---

### **5. Key Code References**
| File | Purpose |
|------|---------|
| **`snapshots/overlay/overlay.go`** | OverlayFS snapshotter implementation. |
| **`internal/cri/server/image_pull.go`** | Calls `snapshotter.Prepare` during image pull. |
| **`services/tasks/local.go`** | Passes mounts to the shim. |
| **`pkg/shim/v2/shim.go`** | Shim processes mounts from containerd. |

---

### **6. Common Issues & Fixes**
1. **"Invalid OverlayFS Lowerdir"**  
   - **Cause**: Missing base layers.  
   - **Fix**: Re-pull the image or check snapshotter metadata.  

2. **"Permission Denied" on Mounts**  
   - **Cause**: SELinux or user namespace restrictions.  
   - **Fix**: Add `:z` to mount options (e.g., `upperdir=/path:z`).  

3. **Shim Fails to Apply Mounts**  
   - **Debug**: Check `strace -f -p $(pgrep containerd-shim)` for mount syscalls.  

---

### **Summary**
1. **Snapshotter** manages filesystem layers (OverlayFS).  
2. **Shim** applies mounts when launching containers.  
3. **Debug Tools**: `ctr`, `strace`, `journalctl`.  

Need a deeper dive into a specific step (e.g., how the shim processes mounts)? Let me know!


Let's break down the precise flow of how a **committed snapshot's mount information** is passed from containerd's snapshotter to the **shim** (e.g., `containerd-shim-runc-v2`) when starting a container. Here's the step-by-step journey with code references:

---

### **1. Snapshot Commit Recap**
When a snapshot is committed (e.g., during image creation or container setup), it becomes an immutable layer. The snapshotter (like `overlayfs`) stores its metadata and prepares mount specifications for future use.

**Key Functions**:
- `snapshotter.Commit()`: Marks a layer as immutable.
- `snapshotter.Mounts()`: Retrieves mount points for a snapshot.

---

### **2. Mount Propagation Flow**
#### **Step 1: Get Mounts from Snapshotter**
When a container is created, containerd queries the snapshotter for mounts associated with the container's root filesystem:
```go
// File: pkg/cri/server/container_create.go
mounts, err := c.snapshotter.Mounts(ctx, containerID)
if err != nil {
    return nil, fmt.Errorf("failed to get snapshot mounts: %w", err)
}
```
- **Input**: `containerID` (snapshot key).
- **Output**: `[]mount.Mount` (OverlayFS mount specifications).

**Example Output (OverlayFS)**:
```go
[]mount.Mount{
    {
        Type:    "overlay",
        Source:  "overlay",
        Options: []string{
            "lowerdir=/var/lib/containerd/.../snapshots/1/fs",
            "upperdir=/var/lib/containerd/.../snapshots/2/fs",
            "workdir=/var/lib/containerd/.../snapshots/2/work",
        },
    },
}
```

---

#### **Step 2: Attach Mounts to Container Config**
The mounts are embedded in the container's OCI specification (`config.json`):
```go
// File: pkg/cri/server/container_create.go
spec, err := oci.GenerateSpec(..., mounts)
```
- The `oci.GenerateSpec` function merges snapshot mounts with other OCI specs (e.g., namespaces, cgroups).

**Resulting OCI Spec Snippet**:
```json
{
  "mounts": [
    {
      "type": "overlay",
      "source": "overlay",
      "options": [
        "lowerdir=...",
        "upperdir=...",
        "workdir=..."
      ]
    }
  ]
}
```

---

#### **Step 3: Task Creation (Passing Mounts to Shim)**
When starting the container, containerd's **TaskService** sends the mounts to the shim via gRPC:
```go
// File: services/tasks/local.go
resp, err := service.CreateTask(ctx, &tasks.CreateTaskRequest{
    ContainerID: container.ID(),
    Bundle:      bundlePath,      // Contains OCI spec with mounts
    RootFS:      mounts,          // Direct mount definitions
    // ... (other options)
})
```
- **gRPC Proto**: Defined in `api/services/tasks/v1/tasks.proto`.
- **Key Field**: `RootFS` is a repeated `Mount` message.

**Protobuf Definition**:
```protobuf
message Mount {
    string type = 1;
    string source = 2;
    repeated string options = 3;
}
```

---

#### **Step 4: Shim Processes Mounts**
The shim (e.g., `containerd-shim-runc-v2`) receives the mounts and applies them when launching the runtime (e.g., `runc`):
```go
// File: pkg/shim/v2/shim.go (simplified)
func (s *Shim) Create(ctx context.Context, r *shimapi.CreateTaskRequest) {
    // 1. Parse mounts from gRPC request
    mounts := make([]mount.Mount, len(r.RootFS))
    for i, m := range r.RootFS {
        mounts[i] = mount.Mount{
            Type:    m.Type,
            Source: m.Source,
            Options: m.Options,
        }
    }

    // 2. Prepare rootfs (e.g., overlayfs mounts)
    if err := mount.All(mounts, "/path/to/rootfs"); err != nil {
        return nil, err
    }

    // 3. Launch runtime (runc) with the prepared rootfs
    cmd := exec.Command("runc", "create", "--bundle", r.Bundle, "container-id")
    cmd.Dir = "/path/to/rootfs"
}
```
- **Critical Action**: `mount.All()` applies the OverlayFS mounts to the container's root filesystem directory.

---

### **3. Debugging Mount Propagation**
#### **1. Inspect Mounts Before Shim**
```bash
# Check mounts sent to shim (from containerd logs)
journalctl -u containerd -f | grep "CreateTaskRequest" | grep -A 10 "RootFS"
```

#### **2. Trace Shim Mount Operations**
```bash
# Attach strace to the shim process
sudo strace -f -p $(pgrep containerd-shim) -e mount,umount2
```
**Expected Output**:
```
mount("overlay", "/path/to/rootfs", "overlay", MS_RDONLY, "lowerdir=...") = 0
```

#### **3. Verify Final Mounts in Container**
```bash
# Enter the container's mount namespace
sudo nsenter -m -t $(pgrep -f "runc init") mount | grep overlay
```
**Expected**:
```
overlay on / type overlay (rw,lowerdir=...,upperdir=...,workdir=...)
```

---

### **4. Key Code Locations**
| File | Purpose |
|------|---------|
| **`pkg/cri/server/container_create.go`** | Retrieves mounts from snapshotter. |
| **`services/tasks/local.go`** | Sends mounts to shim via gRPC. |
| **`pkg/shim/v2/shim.go`** | Applies mounts in the shim. |
| **`api/services/tasks/v1/tasks.proto`** | gRPC message definitions. |

---

### **5. Common Issues & Fixes**
#### **1. "Invalid Argument" for OverlayFS Mounts**
- **Cause**: Missing `workdir` or incorrect `lowerdir` paths.  
- **Fix**: Validate paths in `snapshotter.Mounts()` output.

#### **2. Shim Fails to Apply Mounts**
- **Debug**: Check `strace` for `ENOSPC` (no space) or `EPERM` (permission) errors.  
- **Solution**: Ensure `/var/lib/containerd` has enough inodes and space.

#### **3. Mounts Not Reflected in Container**
- **Check**: Verify the runtime (`runc`) supports the mount type (e.g., `overlay` vs. `overlay2`).  

---

### **Summary**
1. **Snapshotter** generates mount specs (`lowerdir`, `upperdir`, etc.).  
2. **Containerd TaskService** passes mounts to the shim via gRPC (`CreateTaskRequest`).  
3. **Shim** applies mounts using `mount.All()` before launching the runtime.  

For deeper inspection, use `ctr`, `strace`, and `journalctl` as shown above. Let me know if you'd like to explore a specific edge case!