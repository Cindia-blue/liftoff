
# PR #10705: EROFS Snapshotter and Differ – 技术结构整理

该 PR 为 containerd 引入了对 [EROFS](https://elixir.bootlin.com/linux/latest/source/fs/erofs) 的 snapshotter 与 differ 支持，目的是提升在只读、高压缩镜像场景下的运行效率。

---

## 一、文件结构

```text
containerd/
└── snapshots/
    └── erofs/
        ├── erofs.go            # snapshotter 主入口
        ├── differ.go           # layer diff 实现
        ├── config.go           # 插件配置结构
        └── ...                 # mount/prepare/commit 相关实现
```

---

## 二、Snapshotter 插件注册流程

containerd 使用 plugin 框架注册 snapshotter：

```go
plugin.Register(&plugin.Registration{
    Type: plugin.SnapshotPlugin,
    ID:   "erofs",
    Requires: []plugin.Type{
        plugin.ContentPlugin,
        plugin.MetadataPlugin,
    },
    Config: &Config{},
    InitFn: func(ic *plugin.InitContext) (interface{}, error) {
        ...
        return NewSnapshotter(...)
    },
})
```

---

## 三、EROFS Snapshotter 行为特点

- **只读挂载**（压缩镜像层）
- **冷启动优化**（跳过解压）
- **按需读取支持**
- **Snapshot 操作接口**：
  - `Prepare()`
  - `Mounts()`
  - `Commit()`
  - `Remove()`

---

## 四、EROFS Differ 模块

实现插件：

```go
plugin.Register(&plugin.Registration{
    Type: plugin.DifferPlugin,
    ID:   "erofs",
    ...
})
```

用于 image layer 的差异比较，与 snapshotter 协同构建只读镜像。

---

## 五、EROFS vs Overlay 对比

| 特性         | EROFS Snapshotter | Overlay Snapshotter |
|--------------|-------------------|----------------------|
| 是否可写     | 否（只读）        | 是（支持写层）       |
| 支持层级合并 | 是                | 是                   |
| 最佳用途     | 镜像加速、readonly 场景 | 通用容器开发、写入容器 |
| 文件系统支持 | 内核 EROFS        | overlayfs（VFS）     |

---

## 六、Plugin Discovery 到 Snapshot 创建的调用链

```text
containerd daemon 启动
│
├── 加载 config.toml
│
├── 插件系统扫描 plugin 注册项（通过 init() 函数）
│   └── 注册 erofs snapshotter 插件
│       └── plugin.Registration{
│             Type: SnapshotPlugin,
│             ID: "erofs",
│             InitFn: -> NewSnapshotter(...)
│           }
│
├── 创建 snapshot service -> 调用 InitFn -> 返回 snapshotter 实例
│
├── 插件通过 containerd.New() 被统一注册到 services.SnapshotService
│
└── 客户端指定 --snapshotter=erofs 使用该插件
```

---

## 七、总结

- 该 PR 体现 containerd 对高性能、按需读取镜像系统的持续扩展；
- 插件化注册、只读挂载、与镜像层紧耦合，是未来镜像优化方向的重要构件；
- EROFS 与 overlay 各有专长，适合结合使用。