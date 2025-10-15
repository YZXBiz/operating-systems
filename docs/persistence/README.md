# 💾 Persistence

_Master storage systems: from I/O devices to distributed file systems_

---

## 📖 About This Section

Persistence is about making data survive beyond program execution. These chapters cover the entire storage stack - from hardware devices to file system abstractions - transforming complex storage concepts into practical, understandable knowledge through:

- **Bottom-up learning** - Build from device hardware → disk management → file systems → distributed systems
- **Real-world systems** - Study actual file systems (FFS, ext3, LFS, ZFS) and their design tradeoffs
- **Performance analysis** - Understand latency, throughput, and optimization techniques
- **Reliability engineering** - Learn crash consistency, RAID, checksums, and recovery mechanisms

> **💡 Why Persistence Matters**
>
> Every application needs to store data: databases, file systems, cloud storage, photo libraries, version control. Understanding how storage works - from individual disk operations to distributed file systems - is essential for building reliable, high-performance systems. This knowledge directly impacts your ability to debug performance issues, design scalable architectures, and make informed technology choices.

---

## 🗺️ Learning Path

### **Hardware Layer** (Chapters 1-3)

**[Chapter 1: I/O Devices](chapter1-io-devices.md)** (27K)
- System architecture and I/O buses
- Device protocols and communication
- Interrupts vs polling vs DMA
- Device drivers and abstraction
- **Foundation**: How the OS talks to hardware

**[Chapter 2: Hard Disk Drives](chapter2-hard-disk-drives.md)** (32K)
- Disk geometry and mechanics
- Seek time, rotation delay, transfer time
- Disk scheduling algorithms (SSTF, SCAN, C-SCAN)
- Performance modeling and calculations
- **Key skill**: Understanding storage performance

**[Chapter 3: RAID](chapter3-raid.md)** (26K)
- Striping, mirroring, and parity
- RAID levels 0, 1, 4, 5, 6
- Performance vs reliability tradeoffs
- The small-write problem
- **Engineering principle**: Balancing speed and reliability

---

### **File System Abstraction** (Chapters 4-6)

**[Chapter 4: Files and Directories](chapter4-files-directories.md)** (56K)
- File and directory abstractions
- Complete system call interface (open, read, write, lseek, fsync, link, unlink)
- Inodes and metadata
- Hard links vs symbolic links
- **Developer interface**: How applications use storage

**[Chapter 5: File System Implementation](chapter5-file-system-implementation.md)** (43K)
- Data structures (superblock, inodes, bitmaps)
- Multi-level indexing and capacity calculations
- Access paths and I/O timelines
- Free space management
- Caching strategies
- **Under the hood**: How file systems actually work

**[Chapter 6: Locality and Fast File System (FFS)](chapter6-locality-fast-file-system.md)** (31K)
- Problems with old UNIX file system
- Cylinder groups and block groups
- Locality policies for performance
- Sub-blocks and parameterization
- **Design insight**: Structure data for access patterns

---

### **Crash Consistency** (Chapters 7-9)

**[Chapter 7: Crash Consistency Problem](chapter7-crash-consistency.md)** (31K)
- The fundamental consistency problem
- FSCK and its limitations
- Atomicity requirements
- Alternative approaches overview
- **Critical challenge**: Making updates atomic

**[Chapter 8: Journaling](chapter8-journaling.md)** (29K)
- Write-ahead logging concept
- Data journaling protocol
- Metadata journaling and ordering
- Recovery mechanisms
- ext3, ext4, NTFS approaches
- **Solution 1**: Keep a log of changes

**[Chapter 9: Log-Structured File Systems (LFS)](chapter9-log-structured-file-system.md)** (24K)
- Sequential writes philosophy
- Segment-based organization
- Inode map and checkpoint regions
- Garbage collection and segment cleaning
- Modern applications (WAFL, ZFS, btrfs)
- **Solution 2**: Treat entire disk as a log

---

### **Modern Storage** (Chapters 10-11)

**[Chapter 10: Flash-Based SSDs](chapter10-flash-based-ssds.md)** (51K)
- Flash memory characteristics
- Read/write/erase operations
- Wear leveling algorithms
- Write amplification
- Flash Translation Layer (FTL)
- Performance characteristics
- **Modern reality**: SSDs are everywhere

**[Chapter 11: Data Integrity and Protection](chapter11-data-integrity.md)** (68K)
- Latent sector errors vs corruption
- Checksum algorithms (CRC, Fletcher)
- Checksum layout strategies
- Misdirected write detection
- Disk scrubbing
- End-to-end data protection
- **Reliability**: Detecting and correcting errors

---

### **Distribution** (Chapters 12-13)

**[Chapter 12: Distributed Systems](chapter12-distributed-systems.md)** (32K)
- NFS (Network File System) architecture
- Client-server protocols
- Caching and consistency
- Stateless vs stateful design
- **Scaling out**: Storage across machines

**[Chapter 13: AFS and Summary](chapter13-summary.md)** (25K)
- AFS (Andrew File System) design
- Whole-file caching strategy
- Callback mechanisms
- Scale and performance analysis
- **Alternative approach**: Different design decisions

---

## 🎯 Quick Navigation

### By Topic

**Getting Started**
- [How I/O devices work](chapter1-io-devices.md#2-system-architecture)
- [Understanding disk performance](chapter2-hard-disk-drives.md#3-disk-io-time)
- [File system basics](chapter4-files-directories.md#1-introduction)

**Performance**
- [Disk scheduling algorithms](chapter2-hard-disk-drives.md#5-disk-scheduling)
- [RAID for performance](chapter3-raid.md#3-raid-level-0-striping)
- [Locality optimization](chapter6-locality-fast-file-system.md#4-policies-how-to-allocate-files-and-directories)
- [SSD performance](chapter10-flash-based-ssds.md#6-ssd-performance-and-cost)

**Reliability**
- [RAID for redundancy](chapter3-raid.md#4-raid-level-1-mirroring)
- [Crash consistency](chapter7-crash-consistency.md#3-the-crash-consistency-problem)
- [Journaling](chapter8-journaling.md#3-data-journaling)
- [Data integrity](chapter11-data-integrity.md#4-checksum-functions)

**System Design**
- [File system implementation](chapter5-file-system-implementation.md#2-overall-organization)
- [FFS design principles](chapter6-locality-fast-file-system.md#3-ffs-cylinder-groups)
- [LFS architecture](chapter9-log-structured-file-system.md#2-writing-to-disk-sequentially)
- [NFS protocol](chapter12-distributed-systems.md#3-nfs-protocol)

### By Skill Level

**Beginner** (Start here if new to storage systems)
1. [Chapter 1: I/O Devices](chapter1-io-devices.md)
2. [Chapter 2: Hard Disk Drives](chapter2-hard-disk-drives.md)
3. [Chapter 4: Files and Directories](chapter4-files-directories.md)
4. [Chapter 5: File System Implementation](chapter5-file-system-implementation.md)

**Intermediate** (Building real systems)
1. [Chapter 3: RAID](chapter3-raid.md)
2. [Chapter 6: FFS](chapter6-locality-fast-file-system.md)
3. [Chapter 7: Crash Consistency](chapter7-crash-consistency.md)
4. [Chapter 8: Journaling](chapter8-journaling.md)
5. [Chapter 10: SSDs](chapter10-flash-based-ssds.md)

**Advanced** (Deep understanding and alternatives)
1. [Chapter 9: Log-Structured FS](chapter9-log-structured-file-system.md)
2. [Chapter 11: Data Integrity](chapter11-data-integrity.md)
3. [Chapter 12-13: Distributed Systems](chapter12-distributed-systems.md)

---

## 💡 Key Insights

### The Storage Hierarchy
**Speed vs Capacity vs Cost** - Each layer makes tradeoffs:
- **Registers/Cache**: Fast, tiny, expensive (nanoseconds, KB-MB)
- **DRAM**: Moderate, medium, moderate (microseconds, GB)
- **SSD**: Slower, larger, cheaper (microseconds, TB)
- **HDD**: Slow, huge, cheapest (milliseconds, TB)
- **Tape/Cloud**: Slowest, unlimited, pennies (seconds-minutes, PB)

### Three Fundamental Challenges

1. **Performance Gap** - Disks are 100,000× slower than memory
   - *Solution*: Caching, prefetching, scheduling, parallelism

2. **Crash Consistency** - System crashes mid-update
   - *Solution*: Journaling, copy-on-write, careful ordering

3. **Reliability** - Hardware fails, data corrupts
   - *Solution*: RAID, checksums, replication, scrubbing

### The Core Tradeoff
- **Durability**: Data must survive crashes (fsync, journaling)
- **Performance**: Can't wait for every write to disk
- **Balance**: Clever techniques (write-back cache, group commit, async replication)

---

## 🔧 Practical Resources

### Essential System Calls

**File Operations**
```c
open()     // Open/create file
read()     // Read data
write()    // Write data
lseek()    // Change position
close()    // Close file descriptor
fsync()    // Force data to disk
```

**Directory Operations**
```c
mkdir()    // Create directory
rmdir()    // Remove empty directory
opendir()  // Open directory for reading
readdir()  // Read directory entries
```

**Metadata Operations**
```c
stat()     // Get file metadata
link()     // Create hard link
unlink()   // Remove link (delete file)
rename()   // Atomic rename
chmod()    // Change permissions
```

### Performance Tools

**Disk I/O Analysis**
```bash
iostat     # I/O statistics
iotop      # I/O by process
blktrace   # Block layer tracing
fio        # I/O benchmarking
```

**File System Tools**
```bash
df         # Disk free space
du         # Disk usage
fsck       # File system check
tune2fs    # ext2/3/4 tuning
```

**Debugging**
```bash
strace     # System call tracing
ltrace     # Library call tracing
perf       # Performance analysis
```

---

## 📚 Chapter Details

| Chapter | Title | Size | Focus | Key Takeaway |
|---------|-------|------|-------|--------------|
| 1 | [I/O Devices](chapter1-io-devices.md) | 27K | Hardware interface | OS device communication |
| 2 | [Hard Disk Drives](chapter2-hard-disk-drives.md) | 32K | Mechanical storage | Understanding latency |
| 3 | [RAID](chapter3-raid.md) | 26K | Redundancy | Speed vs reliability |
| 4 | [Files and Directories](chapter4-files-directories.md) | 56K | Abstraction | Application interface |
| 5 | [File System Implementation](chapter5-file-system-implementation.md) | 43K | Data structures | How FSs actually work |
| 6 | [FFS](chapter6-locality-fast-file-system.md) | 31K | Locality | Structure for performance |
| 7 | [Crash Consistency](chapter7-crash-consistency.md) | 31K | Problem | Atomic updates challenge |
| 8 | [Journaling](chapter8-journaling.md) | 29K | Solution 1 | Write-ahead logging |
| 9 | [LFS](chapter9-log-structured-file-system.md) | 24K | Solution 2 | Everything is a log |
| 10 | [SSDs](chapter10-flash-based-ssds.md) | 51K | Modern storage | Flash characteristics |
| 11 | [Data Integrity](chapter11-data-integrity.md) | 68K | Reliability | Detecting corruption |
| 12 | [NFS](chapter12-distributed-systems.md) | 32K | Distribution | Network file systems |
| 13 | [AFS](chapter13-summary.md) | 25K | Alternative | Different design |

**Total: 496 KB of learnable content**

---

## 🎓 Learning Outcomes

After completing this section, you will:

✅ **Understand** storage hardware from devices to RAID arrays
✅ **Design** file system data structures and allocation policies
✅ **Implement** crash consistency mechanisms (journaling, COW)
✅ **Optimize** for performance using caching and locality
✅ **Ensure** data integrity with checksums and scrubbing
✅ **Debug** I/O performance issues systematically
✅ **Compare** different file system architectures (FFS, LFS, journaling)
✅ **Reason** about distributed storage tradeoffs

---

## ⚠️ Common Pitfalls to Avoid

1. **Forgetting fsync()** - Buffered writes aren't durable until flushed
2. **Assuming atomicity** - File operations aren't atomic without care (TOCTTOU bugs)
3. **Ignoring failure modes** - Disks fail, corruption happens, plan for it
4. **Poor locality** - Random access is 100× slower than sequential
5. **Over-synchronous I/O** - Waiting for every write kills performance
6. **Ignoring alignment** - Misaligned I/O triggers extra operations
7. **Not using O_DIRECT for databases** - Bypass cache when you have your own
8. **Assuming instant metadata** - Even metadata updates take time

---

## 🚀 Advanced Topics

**After mastering persistence fundamentals, explore:**

- **Copy-on-Write File Systems** - ZFS, btrfs, WAFL
- **Distributed Storage** - Ceph, GFS, HDFS
- **Object Storage** - S3, Swift, MinIO
- **Database Storage Engines** - InnoDB, RocksDB, WiredTiger
- **Flash-Optimized Systems** - F2FS, NILFS
- **Persistent Memory** - NVMe, Optane, PMDK

---

## 🔬 File System Zoo

Real systems you'll encounter:

**Traditional Unix**
- **ext2/3/4** - Linux standard, journaling (ext3+)
- **XFS** - High performance, large files
- **UFS/FFS** - BSD, original locality optimizations

**Modern Copy-on-Write**
- **ZFS** - Data integrity focus, checksums, snapshots
- **btrfs** - Linux COW, snapshots, compression
- **APFS** - Apple's modern FS, encryption

**Special Purpose**
- **F2FS** - Flash-optimized for mobile
- **NTFS** - Windows, journaling, ACLs
- **FAT32/exFAT** - Portable media

**Network/Distributed**
- **NFS** - Network File System
- **SMB/CIFS** - Windows sharing
- **AFS** - Andrew File System

---

## 📊 Performance Characteristics

### Typical Latencies (Orders of Magnitude)

```
Operation                          Latency
─────────────────────────────────  ──────────────
L1 cache reference                 0.5 ns
L2 cache reference                 7 ns
Main memory reference              100 ns
SSD random read                    150 μs
SSD sequential read                1 MB in 1 ms
HDD seek                           10 ms
HDD sequential read                1 MB in 20 ms
Network: same datacenter           500 μs
Network: cross-country             50 ms
```

### Throughput Rules of Thumb

```
Device              Sequential    Random (4KB)
─────────────────   ──────────    ────────────
SATA SSD           500 MB/s      80K IOPS
NVMe SSD           3-7 GB/s      500K IOPS
HDD (7200 RPM)     150 MB/s      100 IOPS
HDD (15K RPM)      200 MB/s      200 IOPS
```

---

## 📖 Historical Context

The evolution of storage systems reflects increasing scale and complexity:

- **1960s-70s**: Simple flat file systems, no hierarchy
- **1970s**: Unix file system (UFS) with inodes and hierarchy
- **1980s**: FFS brings locality, ext2 for Linux
- **1990s**: Journaling (ext3, NTFS, JFS), LFS research
- **2000s**: Copy-on-Write (ZFS, btrfs), distributed systems
- **2010s**: SSD optimization (F2FS), cloud storage
- **2020s**: Persistent memory, CXL, computational storage

---

## 🔗 Related Topics

- [Concurrency Section](../concurrency/) - Locking in file systems
- [Virtualization Section](../virtualization/) - I/O virtualization
- Database internals and storage engines
- Operating system kernel development
- Distributed systems and consensus algorithms

---

## 💭 Design Principles

**Key lessons from decades of storage system design:**

1. **Amortize Costs** - Group small operations to reduce overhead
2. **Exploit Locality** - Place related data together
3. **Cache Aggressively** - Memory is 100,000× faster than disk
4. **Fail Carefully** - Preserve invariants even when crashing
5. **Measure Everything** - Intuition is often wrong about performance
6. **Simplicity Matters** - Complex systems have subtle bugs
7. **End-to-End Arguments** - Don't rely on lower layers for correctness
8. **Embrace Constraints** - Work with hardware characteristics, not against them

---

_Storage systems are the foundation of persistent computing. Master these concepts, and you'll understand how every database, file server, and cloud storage system really works._

**Start here:** [Chapter 1: I/O Devices →](chapter1-io-devices.md)
