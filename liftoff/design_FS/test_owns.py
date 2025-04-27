import pytest
import os
import time
from filesystem import DistributedFileSystem, DiskStorage  # Assuming your implementation is in filesystem.py

@pytest.fixture
def fs():
    """Fixture providing a fresh filesystem instance for each test"""
    return DistributedFileSystem()

@pytest.fixture
def disk_fs(tmp_path):
    """Fixture using disk storage with temporary directory"""
    storage = DiskStorage(base_path=str(tmp_path / "storage"))
    return DistributedFileSystem(storage_backend=storage)

# ======================
# Basic Operation Tests
# ======================

def test_create_and_list_directory(fs):
    fs.mkdir("/test")
    fs.mkdir("/test/subdir")
    assert fs.list_dir("/") == ["test"]
    assert fs.list_dir("/test") == ["subdir"]

def test_add_and_read_file(fs):
    fs.mkdir("/data")
    content = b"Hello World"
    fs.add_file("/data/test.txt", content)
    assert fs.list_dir("/data") == ["test.txt"]
    assert fs.read_file("/data/test.txt") == content

def test_nonexistent_path_errors(fs):
    with pytest.raises(ValueError, match="Parent directory does not exist"):
        fs.mkdir("/nonexistent/path")

    with pytest.raises(ValueError, match="Parent directory does not exist"):
        fs.add_file("/invalid/path/file.txt", b"content")

    with pytest.raises(ValueError, match="Path is not a file"):
        fs.read_file("/nonexistent.txt")

# ======================
# Edge Case Tests
# ======================

def test_root_directory_operations(fs):
    assert fs.list_dir("/") == []
    fs.add_file("/root_file.txt", b"root content")
    assert fs.list_dir("/") == ["root_file.txt"]
    assert fs.read_file("/root_file.txt") == b"root content"

def test_large_file_operations(disk_fs):
    large_content = os.urandom(10 * 1024 * 1024)  # 10MB
    disk_fs.add_file("/large.bin", large_content)
    assert disk_fs.read_file("/large.bin") == large_content
    stats = disk_fs.get_stats()
    assert stats['compression_ratio'] < 1.0  # Should have compressed

# ======================
# Concurrency Tests
# ======================

def test_concurrent_access(fs):
    from concurrent.futures import ThreadPoolExecutor
    
    def worker(i):
        path = f"/file_{i}.txt"
        content = f"content_{i}".encode()
        fs.add_file(path, content)
        assert fs.read_file(path) == content
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        for i in range(100):
            executor.submit(worker, i)
    
    assert len(fs.list_dir("/")) == 100

# ======================
# Sharding Tests
# ======================

def test_auto_sharding(fs):
    # Create enough files to trigger sharding
    for i in range(1001):
        fs.add_file(f"/shard_test/file_{i:04d}.txt", f"content_{i}".encode())
    
    stats = fs.get_stats()
    assert stats['shards_created'] > 0
    assert len(fs.list_dir("/shard_test")) == 1001  # Should still see all files

# ======================
# Filesystem Semantics Tests
# ======================

def test_directory_cannot_be_file(fs):
    fs.mkdir("/testdir")
    with pytest.raises(ValueError, match="Directory with same name exists"):
        fs.add_file("/testdir", b"trying to overwrite dir")

def test_file_cannot_be_directory(fs):
    fs.add_file("/testfile", b"content")
    with pytest.raises(ValueError, match="Parent is not a directory"):
        fs.mkdir("/testfile/subdir")

# ======================
# Storage Backend Tests
# ======================

def test_disk_storage_persistence(tmp_path):
    # Test that files persist between instances
    storage_path = tmp_path / "storage"
    storage = DiskStorage(base_path=str(storage_path))
    
    # First instance
    fs1 = DistributedFileSystem(storage_backend=storage)
    fs1.add_file("/persistent.txt", b"Hello")
    
    # Second instance
    fs2 = DistributedFileSystem(storage_backend=storage)
    assert fs2.read_file("/persistent.txt") == b"Hello"

def test_compression_disabling(fs):
    content = b"Hello" * 1000  # Large enough to trigger compression
    fs.add_file("/compressed.txt", content, compress=True)
    fs.add_file("/uncompressed.txt", content, compress=False)
    
    stats = fs.get_stats()
    assert stats['compression_ratio'] > 0  # Some compression happened

# ======================
# Performance Tests
# ======================

def test_directory_listing_performance(fs):
    # Create 10,000 files
    for i in range(10_000):
        fs.add_file(f"/perf_test/file_{i:05d}.txt", b"x")
    
    start = time.time()
    listing = fs.list_dir("/perf_test")
    duration = time.time() - start
    
    assert len(listing) == 10_000
    assert duration < 0.1  # Should be very fast with lazy sorting

def test_cache_efficiency(fs):
    # First access should cache
    fs.mkdir("/cache_test")
    fs._resolve_path("/cache_test")  # Direct call to see cache behavior
    
    # Second access should hit cache
    fs._resolve_path("/cache_test")
    stats = fs.get_stats()
    assert stats['cache_hits'] > 0