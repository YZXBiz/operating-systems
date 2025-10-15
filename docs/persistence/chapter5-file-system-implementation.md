# File System Implementation

**Chapter 5: Building a Simple File System from the Ground Up**

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Mental Models: The Way to Think](#2-mental-models-the-way-to-think)
   - 2.1. [Data Structures](#21-data-structures)
   - 2.2. [Access Methods](#22-access-methods)
3. [Overall On-Disk Organization](#3-overall-on-disk-organization)
   - 3.1. [Disk Blocks and Partitioning](#31-disk-blocks-and-partitioning)
   - 3.2. [The Data Region](#32-the-data-region)
   - 3.3. [The Inode Table](#33-the-inode-table)
   - 3.4. [Allocation Bitmaps](#34-allocation-bitmaps)
   - 3.5. [The Superblock](#35-the-superblock)
4. [File Organization: The Inode](#4-file-organization-the-inode)
   - 4.1. [Inode Addressing and Location](#41-inode-addressing-and-location)
   - 4.2. [Inode Contents and Metadata](#42-inode-contents-and-metadata)
   - 4.3. [Multi-Level Index for Large Files](#43-multi-level-index-for-large-files)
   - 4.4. [Extents vs Pointers](#44-extents-vs-pointers)
5. [Directory Organization](#5-directory-organization)
   - 5.1. [Directory Entry Structure](#51-directory-entry-structure)
   - 5.2. [Special Directory Entries](#52-special-directory-entries)
   - 5.3. [Directory Implementation Trade-offs](#53-directory-implementation-trade-offs)
6. [Free Space Management](#6-free-space-management)
   - 6.1. [Bitmap Approach](#61-bitmap-approach)
   - 6.2. [Allocation Policies](#62-allocation-policies)
7. [Access Paths: Reading and Writing](#7-access-paths-reading-and-writing)
   - 7.1. [Reading a File from Disk](#71-reading-a-file-from-disk)
   - 7.2. [Writing a File to Disk](#72-writing-a-file-to-disk)
   - 7.3. [Creating a New File](#73-creating-a-new-file)
8. [Caching and Buffering](#8-caching-and-buffering)
   - 8.1. [The Role of Caching](#81-the-role-of-caching)
   - 8.2. [Static vs Dynamic Partitioning](#82-static-vs-dynamic-partitioning)
   - 8.3. [Write Buffering Benefits](#83-write-buffering-benefits)
   - 8.4. [The Durability-Performance Trade-off](#84-the-durability-performance-trade-off)
9. [Summary](#9-summary)

---

## 1. Introduction

**In plain English:** A file system is like a library's organizational system - you need a catalog (metadata) that tells you where books are located, shelves organized into sections (disk blocks), and a system to track which shelf spaces are available.

**In technical terms:** A file system is pure software that provides organization and access methods for storing and retrieving data on disk. Unlike CPU and memory virtualization, we don't add hardware features - we build everything in software.

**Why it matters:** Understanding file system implementation is crucial because it reveals how abstractions like "files" and "directories" map to physical disk blocks, and why operations like opening files or creating directories require multiple disk I/Os.

> **🎯 Core Challenge**
>
> How can we build a simple file system? What structures are needed on the disk? What do they need to track? How are they accessed?

This chapter introduces **vsfs** (the Very Simple File System), a simplified version of a typical UNIX file system. While real file systems range from AFS (Andrew File System) to ZFS (Zettabyte File System), vsfs serves as our teaching model to introduce fundamental concepts that appear in virtually all file systems.

### 🧠 Learning Through Case Studies

File systems exhibit tremendous design flexibility. We'll learn through:

1. **vsfs (this chapter)** - Simple structures to introduce core concepts
2. **Real file systems (later chapters)** - How different designs optimize different aspects

---

## 2. Mental Models: The Way to Think

**In plain English:** To understand any file system, answer two questions: (1) How does it organize information on disk? (2) How does it translate operations like "open this file" into actual disk reads and writes?

**In technical terms:** File system understanding requires mastering two complementary aspects: data structures and access methods.

### 2.1. Data Structures

**What to understand:** What types of on-disk structures organize the file system's data and metadata?

**Simple approach:** Arrays of blocks or objects (like vsfs)
**Complex approach:** Tree-based structures (like XFS)

### 2.2. Access Methods

**What to understand:** How do system calls like `open()`, `read()`, and `write()` map to disk structures?

Key questions for your mental model:
- Which structures are read during a particular system call?
- Which structures are written?
- How efficiently are these operations performed?

> **💡 Insight**
>
> Your mental model should answer: What on-disk structures store data and metadata? What happens when a process opens a file? Which structures are accessed during reads or writes? This abstract understanding matters more than memorizing code specifics.

---

## 3. Overall On-Disk Organization

**In plain English:** Think of a disk as a bookshelf divided into equal-sized compartments. We need to decide which compartments hold actual books (user data), which hold the catalog cards (metadata), and which track available space.

### 3.1. Disk Blocks and Partitioning

**Block size:** 4 KB (common choice for simplicity)
**View:** Disk partition = series of blocks numbered 0 to N-1

**Example: 64-block disk**
```
Blocks: 0  1  2  3  4  5  6  7  ... 56 57 58 59 60 61 62 63
```

### 3.2. The Data Region

**Purpose:** Store actual user data (files content)
**Size:** Most of the disk space (e.g., 56 of 64 blocks)

```
Data Region Layout:
┌─────────────────────────────────────────────────┐
│ [Data Blocks: 8-63]                             │
│ D D D D D D D D ... D D D D D D D D            │
└─────────────────────────────────────────────────┘
  Block 8 ──────────────────────────► Block 63
```

> **📝 Note**
>
> User data should occupy most file system space. Other structures are overhead for organizing this data.

### 3.3. The Inode Table

**Purpose:** Store metadata about each file
**Content:** Which data blocks comprise a file, size, owner, permissions, timestamps

**Metadata tracked:**
- File size
- Owner and access rights
- Access/modify times
- Data block locations

**Example sizing:**
- Inode size: 256 bytes
- Block size: 4 KB
- Inodes per block: 16
- Total with 5 blocks: 80 inodes

```
Inode Table Layout:
┌───────────────────┬─────────────────────────────┐
│ [Inodes: 3-7]     │ [Data Region: 8-63]        │
│ I I I I I         │ D D D D D D D D ... D D D  │
└───────────────────┴─────────────────────────────┘
  Block 3-7            Block 8-63
```

> **⚡ Important Limitation**
>
> The inode count determines maximum files. With 80 inodes, we can have at most 80 files. Larger disks simply allocate more inode blocks.

### 3.4. Allocation Bitmaps

**Purpose:** Track which inodes and data blocks are free or in-use

**In plain English:** Like a checklist where each checkbox represents whether a specific slot is available (empty box) or occupied (checked).

**Implementation:**
- **Inode bitmap (i):** One bit per inode (0 = free, 1 = used)
- **Data bitmap (d):** One bit per data block (0 = free, 1 = used)

```
With Bitmaps:
┌───┬───┬─────────────────┬─────────────────────────┐
│ i │ d │ [Inodes: 3-7]   │ [Data: 8-63]           │
└───┴───┴─────────────────┴─────────────────────────┘
  1   2      3-7               8-63
```

**Design note:** Using full 4-KB blocks for bitmaps is overkill (can track 32K objects when we only have 80 inodes and 56 data blocks), but simplifies implementation.

### 3.5. The Superblock

**Purpose:** Store file system metadata - information about the file system itself

**Contents:**
- Number of inodes (80)
- Number of data blocks (56)
- Where inode table begins (block 3)
- Magic number identifying file system type (vsfs)

```
Complete vsfs Layout:
┌───┬───┬───┬─────────────────┬─────────────────────────┐
│ S │ i │ d │ I I I I I       │ D D D D ... D D D D    │
└───┴───┴───┴─────────────────┴─────────────────────────┘
  0   1   2   3-7                8-63

S = Superblock
i = Inode bitmap
d = Data bitmap
I = Inode table
D = Data region
```

**Mounting process:**
1. OS reads superblock first
2. Initializes parameters from superblock
3. Attaches volume to file system tree
4. System knows exactly where to find all structures

> **💡 Insight**
>
> The superblock is the file system's "table of contents" - it's the well-known starting point that tells you where everything else lives.

---

## 4. File Organization: The Inode

**In plain English:** An inode is like a detailed catalog card for a file. It doesn't contain the file's content, but tells you everything about the file: who owns it, how big it is, when it was modified, and most importantly, which disk blocks contain its actual data.

**In technical terms:** The inode (index node) is an on-disk data structure containing all metadata for a file. The name comes from UNIX where inodes are arranged in an array and accessed by index.

### 4.1. Inode Addressing and Location

**Key concept:** Each inode has an **i-number** (the low-level name of a file)

**Given an i-number, calculate disk location:**

```
Example parameters:
- Inode size: 256 bytes
- Block size: 4 KB (4096 bytes)
- Inodes per block: 16
- Inode table starts: 12 KB (block 3)
```

**Calculation formula:**
```c
// Calculate which block contains the inode
blk = (inumber * sizeof(inode_t)) / blockSize;

// Calculate sector address
sector = ((blk * blockSize) + inodeStartAddr) / sectorSize;
```

**Example: Finding inode 32**
```
Offset into inode region = 32 * 256 bytes = 8,192 bytes = 8 KB
Disk address = 12 KB + 8 KB = 20 KB
Sector (512-byte) = 20,480 / 512 = 40
→ Read sector 40 to fetch inode 32
```

**Inode table closeup:**
```
Block:     0KB    4KB    8KB    12KB   16KB   20KB   24KB   28KB   32KB
           ├──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┤
           │Super │i-bmap│d-bmap│iblk 0│iblk 1│iblk 2│iblk 3│iblk 4│
           └──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┘
Inodes:                    0-15   16-31  32-47  48-63  64-79
                                    ↑
                           inode 32 is here
```

> **🔍 Deep Dive**
>
> Disks aren't byte-addressable - they use sectors (typically 512 bytes). File systems must translate byte addresses to sector addresses when performing I/O.

### 4.2. Inode Contents and Metadata

**What's inside an inode:** Everything except the file's actual data and name

**Simplified ext2 inode structure:**

| Size | Field        | Purpose                                    |
|------|-------------|--------------------------------------------|
| 2    | mode        | Permissions (read/write/execute)           |
| 2    | uid         | User ID (owner)                            |
| 2    | gid         | Group ID                                   |
| 4    | size        | File size in bytes                         |
| 4    | time        | Last access time                           |
| 4    | ctime       | Creation time                              |
| 4    | mtime       | Last modification time                     |
| 4    | dtime       | Deletion time                              |
| 2    | links_count | Number of hard links                       |
| 4    | blocks      | Number of allocated blocks                 |
| 60   | block       | Disk pointers (15 total: 12 direct + 3 indirect) |
| 4    | generation  | File version (for NFS)                     |
| 4    | file_acl    | Extended permissions (ACLs)                |

**Key observation:** File names are NOT stored in inodes - they're stored in directory entries that point to inodes.

### 4.3. Multi-Level Index for Large Files

**The problem:** How do we support files larger than can fit with direct pointers?

**In plain English:** Imagine trying to list every page number of a 1000-page book in a single index card. Instead, you write addresses of other cards that contain the actual page numbers. For really big books, you might need cards that point to cards that point to page numbers.

#### 🔧 Direct Pointers

**Simple approach:** Inode contains disk addresses directly

```
Inode with 12 direct pointers:
┌────────────┐
│  Inode     │
├────────────┤
│  pointer 0 │──→ Data Block 0
│  pointer 1 │──→ Data Block 1
│  pointer 2 │──→ Data Block 2
│     ...    │
│  pointer 11│──→ Data Block 11
└────────────┘

Maximum file size: 12 × 4 KB = 48 KB
```

**Limitation:** Can only address 48 KB files

#### 🔧 Indirect Pointer

**Solution:** Pointer points to a block full of pointers

```
Single Indirect:
┌────────────┐
│  Inode     │
├────────────┤
│  direct 0  │──→ Data Block
│     ...    │
│  direct 11 │──→ Data Block
│  indirect  │──→ Indirect Block
└────────────┘    ┌──────────┐
                  │ ptr 0    │──→ Data Block
                  │ ptr 1    │──→ Data Block
                  │   ...    │
                  │ ptr 1023 │──→ Data Block
                  └──────────┘

Indirect block pointers: 4096 bytes / 4 bytes = 1024
Additional capacity: 1024 × 4 KB = 4 MB
Total file size: 48 KB + 4 MB ≈ 4 MB
```

#### 🔧 Double Indirect Pointer

**For even larger files:** Pointer to block of pointers to blocks of pointers

```
Double Indirect:
┌────────────┐
│  Inode     │
│  direct 0  │──→ Data
│     ...    │
│  indirect  │──→ 1024 pointers to data
│  double    │──→ Indirect Block
└────────────┘    ┌──────────┐
                  │ ptr 0    │──→ [1024 ptrs to data]
                  │ ptr 1    │──→ [1024 ptrs to data]
                  │   ...    │
                  │ ptr 1023 │──→ [1024 ptrs to data]
                  └──────────┘

Additional capacity: 1024 × 1024 × 4 KB = 4 GB
Total file size: 48 KB + 4 MB + 4 GB > 4 GB
```

#### 🔧 Triple Indirect Pointer

**For massive files:** Three levels of indirection

```
Capacity: 1024 × 1024 × 1024 × 4 KB = 4 TB
```

**Complete multi-level index:**
```
Typical inode pointer structure:
- 12 direct pointers        → 48 KB
- 1 single indirect         → 4 MB
- 1 double indirect         → 4 GB
- 1 triple indirect         → 4 TB
────────────────────────────────────
Total capacity: ~4 TB
```

> **💡 Insight**
>
> This is an **imbalanced tree** by design. Why? Because most files are small! Research consistently shows the most common file size is ~2 KB. The multi-level design optimizes for the common case (small files use direct pointers efficiently) while still supporting large files.

**File system measurement findings:**

| Observation                    | Detail                                      |
|--------------------------------|---------------------------------------------|
| Most files are small           | ~2 KB is most common size                  |
| Average file size is growing   | ~200 KB average                            |
| Most bytes in large files      | A few big files use most space             |
| Many files per file system     | ~100K files average                        |
| File systems half full         | ~50% full even as disks grow               |
| Directories are small          | Most have ≤20 entries                      |

### 4.4. Extents vs Pointers

**Alternative approach:** Instead of one pointer per block, use (pointer + length) pairs

#### Pointer-Based Approach
```
File with 5 blocks:
Pointers: [100] [101] [102] [103] [104]
→ Requires 5 pointers (20 bytes)
```

#### Extent-Based Approach
```
File with 5 contiguous blocks:
Extent: [start=100, length=5]
→ Requires 1 extent (8 bytes)
```

**Trade-offs:**

| Aspect       | Pointers                        | Extents                         |
|--------------|----------------------------------|----------------------------------|
| Flexibility  | ✅ Maximum - any block anywhere | ⚠️ Limited - needs contiguous space |
| Metadata     | ❌ Large (1 pointer per block)  | ✅ Compact (pointer + length)   |
| Best for     | Fragmented disks                | Ample free space                 |
| Used by      | ext2, ext3, UNIX               | ext4, XFS                       |

> **🎓 Learning Point**
>
> Extent-based systems work well when free space is plentiful and files can be laid out contiguously - which should be the goal of any allocation policy anyway.

---

## 5. Directory Organization

**In plain English:** A directory is just a special file containing a phone book - it maps human-readable names to inode numbers (the file system's internal IDs).

**In technical terms:** Directories are files with type field marked as "directory" rather than "regular file". Their data blocks contain directory entries instead of user data.

### 5.1. Directory Entry Structure

**Basic format:** List of (name, inode number) pairs

**Example directory `dir` (inode 5) with three files:**

```
Directory entries in data blocks:
┌──────┬────────┬────────┬─────────────────────────────┐
│inum  │ reclen │ strlen │ name                        │
├──────┼────────┼────────┼─────────────────────────────┤
│ 5    │ 12     │ 2      │ .                           │
│ 2    │ 12     │ 3      │ ..                          │
│ 12   │ 12     │ 4      │ foo                         │
│ 13   │ 12     │ 4      │ bar                         │
│ 24   │ 36     │ 28     │ foobar_is_a_pretty_longname │
└──────┴────────┴────────┴─────────────────────────────┘

Fields:
- inum:   inode number (file's low-level name)
- reclen: total bytes for entry (includes padding)
- strlen: actual name length
- name:   file/directory name
```

> **📝 Note**
>
> Record length (reclen) can exceed string length (strlen), leaving space for reusing entries after deletion or accommodating name changes.

### 5.2. Special Directory Entries

**Every directory contains:**

1. **`.` (dot):** Current directory
   - Points to directory's own inode (5 in example)

2. **`..` (dot-dot):** Parent directory
   - Points to parent's inode (2 = root in example)

**Why they matter:**
- Enable relative path navigation (`cd ..`)
- Allow programs to traverse directory tree
- Provide context for path resolution

### 5.3. Directory Implementation Trade-offs

**Simple approach (vsfs):** Linear list in data blocks
- **Pros:** Simple to implement
- **Cons:** Slow for large directories (must scan entire list)

**Advanced approach (XFS):** B-tree structure
- **Pros:** Fast lookups, inserts, deletes (O(log n))
- **Cons:** More complex implementation
- **Best for:** Directories with many entries

**Deletion handling:**
```
When file deleted (unlink()):
- Entry marked with reserved inode (e.g., 0)
- Space can be reused via reclen field
- New entry might reuse larger old entry
```

> **💪 Power Feature**
>
> Directories are just special files. They have inodes, occupy data blocks, and can even use indirect pointers for large directories. The file system's on-disk structure remains consistent.

---

## 6. Free Space Management

**In plain English:** Before writing data, the file system needs to know which storage slots are available. This is like a hotel keeping track of vacant rooms.

### 6.1. Bitmap Approach

**vsfs choice:** Two bitmaps (simple and popular)

1. **Inode bitmap:** Track free/used inodes
2. **Data bitmap:** Track free/used data blocks

**How bitmaps work:**
```
Bit value:
0 = free/available
1 = in-use/allocated

Example data bitmap (8 blocks):
[1][1][1][0][0][1][0][0]
 │  │  │  │  │  │  │  │
 0  1  2  3  4  5  6  7

Blocks 0,1,2,5 are in use
Blocks 3,4,6,7 are free
```

**Memory efficiency:**
```
Single 4 KB bitmap can track:
4096 bytes × 8 bits/byte = 32,768 objects

vsfs has:
- 80 inodes    → bitmap uses 10 bytes, wastes 4086 bytes
- 56 data blocks → bitmap uses 7 bytes, wastes 4089 bytes

Trade-off: Waste space for simplicity
```

#### Alternative: Free List

**Linked list approach:**
```
Superblock → First free block → Next free block → ...
             ┌────────────┐     ┌────────────┐
             │ next: 47   │ ──→ │ next: 51   │ ──→ ...
             └────────────┘     └────────────┘
```

**Comparison:**

| Aspect          | Bitmap                    | Free List              |
|-----------------|---------------------------|------------------------|
| Space          | Fixed overhead            | Variable (0 when full) |
| Speed          | Fast random access        | Sequential traversal   |
| Complexity     | Simple                    | More complex           |
| Used by        | Most modern FSs           | Early file systems     |

**Modern approaches:**
- XFS uses B-trees to compactly represent free chunks
- Different data structures offer different time-space trade-offs

### 6.2. Allocation Policies

**Challenge:** Where to place new files for best performance?

#### Pre-allocation Heuristic

**Strategy:** Find contiguous free blocks when creating files

**Example (ext2/ext3):**
```
When creating file:
1. Search bitmap for 8 consecutive free blocks
2. Allocate all 8 to new file
3. File data is contiguous on disk
4. Sequential reads are fast (no seeking)
```

**Benefits:**
- Reduces fragmentation
- Improves sequential read/write performance
- Anticipates file growth

> **⚡ Important**
>
> Allocation bitmaps are ONLY consulted during allocation. When reading existing files, the inode already contains block pointers - no need to check if blocks are allocated.

---

## 7. Access Paths: Reading and Writing

**In plain English:** Understanding file operations means following the trail of disk reads and writes from system call to completion. Like watching a detective follow clues, we trace which data structures are accessed and in what order.

**Setup assumptions:**
- File system is mounted (superblock in memory)
- All inodes and directories start on disk
- Root inode number is well-known (typically 2)

### 7.1. Reading a File from Disk

**Scenario:** Open `/foo/bar`, read 12 KB (3 blocks), then close

#### Step 1: Opening the File

**System call:** `open("/foo/bar", O_RDONLY)`

**Process:**

```
1. Start at root directory
   └─→ Read inode 2 (root inode - well-known location)
       └─→ Inode contains pointers to root's data blocks
           └─→ Read root directory data blocks
               └─→ Find entry "foo" → get inode number (e.g., 44)

2. Traverse to /foo
   └─→ Read inode 44 (foo's inode)
       └─→ Read foo's data blocks (directory contents)
           └─→ Find entry "bar" → get inode number (e.g., 67)

3. Open bar
   └─→ Read inode 67 (bar's inode)
       └─→ Check permissions
       └─→ Allocate file descriptor
       └─→ Return file descriptor to process
```

**I/O count for open:**
```
Disk reads performed:
1. Root inode (block with inode 2)
2. Root directory data (1+ blocks)
3. foo inode (block with inode 44)
4. foo directory data (1+ blocks)
5. bar inode (block with inode 67)
────────────────────────────────
Minimum: 5 reads
```

#### Step 2: Reading File Data

**System call:** `read(fd, buffer, 4096)` - three times for 12 KB

**Process for each read:**

```
1. Consult inode for block location
   └─→ Read in-memory inode (already cached from open)
       └─→ Get pointer to data block

2. Read data block
   └─→ Read 4 KB from disk

3. Update metadata
   └─→ Update last-accessed time in inode
   └─→ Write inode back to disk

4. Update file position
   └─→ Increment offset in open file table
```

**I/O count per read:**
```
Each read operation:
1. Read inode (to find block pointer)    - 1 read
2. Read data block                       - 1 read
3. Update inode (access time)            - 1 write
────────────────────────────────────────
Per read: 2 reads + 1 write = 3 I/Os

For 3 reads (12 KB):
3 × 3 I/Os = 9 I/Os
```

#### Step 3: Closing the File

**System call:** `close(fd)`

**Process:**
```
1. Deallocate file descriptor
2. Remove entry from open file table
────────────────────────────────
No disk I/O required!
```

**Complete timeline visualization:**

```
Operation         Disk Structure Accessed           I/O Type
──────────────────────────────────────────────────────────────
open("/foo/bar")  root inode                        Read
                  root data blocks                  Read
                  foo inode                         Read
                  foo data blocks                   Read
                  bar inode                         Read

read() #1         bar inode (find block pointer)    Read
                  bar data block 0                  Read
                  bar inode (update atime)          Write

read() #2         bar inode                         Read
                  bar data block 1                  Read
                  bar inode (update atime)          Write

read() #3         bar inode                         Read
                  bar data block 2                  Read
                  bar inode (update atime)          Write

close()           [no disk I/O]                     -
──────────────────────────────────────────────────────────────
Total I/O:        14 reads + 3 writes = 17 I/Os
```

> **⚠️ Warning**
>
> Pathname length directly impacts I/O cost! Each directory level adds 2+ reads (inode + data). Path `/a/b/c/d/e/file.txt` requires ~12 reads just to open.

### 7.2. Writing a File to Disk

**Scenario:** Open existing file `/foo/bar` and overwrite 4 KB

**Key difference from reading:** Writing may require allocation if writing to new blocks

#### Writing to Existing Blocks (Overwrite)

**Process:**
```
1. Open file (same as reading)
   └─→ 5 reads to traverse path

2. write() system call
   └─→ Read inode to find block pointer       - 1 read
   └─→ Write data to existing block           - 1 write
   └─→ Update inode (mtime, size)             - 1 write
────────────────────────────────────────────
Total: 5 reads (open) + 1 read + 2 writes = 8 I/Os
```

#### Writing to New Blocks (Append)

**Process - much more expensive:**

```
1. Open file
   └─→ 5 reads

2. Allocate new block
   └─→ Read data bitmap                       - 1 read
   └─→ Update data bitmap (mark allocated)    - 1 write
   └─→ Read inode                             - 1 read
   └─→ Update inode (add block pointer)       - 1 write
   └─→ Write actual data                      - 1 write
────────────────────────────────────────────
Per write: 2 reads + 3 writes = 5 I/Os

For 3 new blocks (12 KB file):
Open:   5 reads
Write1: 2 reads + 3 writes
Write2: 2 reads + 3 writes
Write3: 2 reads + 3 writes
────────────────────────────
Total: 11 reads + 9 writes = 20 I/Os
```

### 7.3. Creating a New File

**Scenario:** Create `/foo/bar` and write 12 KB (3 blocks)

**This is the most expensive operation!**

#### File Creation Process

**System call:** `open("/foo/bar", O_CREAT | O_WRONLY)`

```
1. Traverse to /foo
   └─→ Read root inode                        - 1 read
   └─→ Read root data                         - 1 read
   └─→ Read foo inode                         - 1 read
   └─→ Read foo data                          - 1 read

2. Allocate inode for bar
   └─→ Read inode bitmap                      - 1 read
   └─→ Update inode bitmap                    - 1 write
   └─→ Write new inode (bar)                  - 1 write

3. Add entry to foo directory
   └─→ Update foo directory data              - 1 write
   └─→ Read foo inode                         - 1 read
   └─→ Update foo inode (mtime)               - 1 write
────────────────────────────────────────────
Creation: 6 reads + 4 writes = 10 I/Os
```

#### Writing Data to New File

**Each write allocates a new block:**

```
Per write (allocating):
└─→ Read data bitmap                          - 1 read
└─→ Write data bitmap                         - 1 write
└─→ Read inode                                - 1 read
└─→ Write inode (add pointer)                 - 1 write
└─→ Write data block                          - 1 write
────────────────────────────────────────────
Per write: 2 reads + 3 writes = 5 I/Os

For 3 writes:
3 × (2 reads + 3 writes) = 6 reads + 9 writes
```

**Complete creation + write timeline:**

```
Operation              Structure Accessed         I/O Type
─────────────────────────────────────────────────────────────
create("/foo/bar")     root inode                 Read
                       root data                  Read
                       foo inode                  Read
                       foo data                   Read
                       inode bitmap               Read
                       inode bitmap               Write
                       bar inode (new)            Write
                       foo data (add entry)       Write
                       foo inode (update)         Read
                       foo inode                  Write

write() #1 (4KB)       data bitmap                Read
                       data bitmap                Write
                       bar inode                  Read
                       bar inode                  Write
                       bar data block 0           Write

write() #2 (4KB)       data bitmap                Read
                       data bitmap                Write
                       bar inode                  Read
                       bar inode                  Write
                       bar data block 1           Write

write() #3 (4KB)       data bitmap                Read
                       data bitmap                Write
                       bar inode                  Read
                       bar inode                  Write
                       bar data block 2           Write
─────────────────────────────────────────────────────────────
Total I/O: 12 reads + 13 writes = 25 I/Os
```

> **🎯 Core Challenge**
>
> Even the simplest operations like opening, reading, or writing a file incur huge numbers of I/Os scattered across the disk. How can a file system reduce these costs?

**Answer:** Caching and buffering (next section)

---

## 8. Caching and Buffering

**In plain English:** Imagine looking up the same word in a dictionary 100 times. After the first lookup, you'd remember the page number. File systems do the same thing with disk data - keep frequently accessed information in fast memory to avoid slow disk reads.

### 8.1. The Role of Caching

**Problem:** Every operation requires multiple disk I/Os (slow!)

**Solution:** Cache important blocks in DRAM (fast!)

#### Read Caching Impact

**Without caching:**
```
Opening /1/2/3/4/5/file.txt:
- 12+ disk reads just to traverse path
- Every open, every time
```

**With caching:**
```
First open:  12+ disk reads
Second open: 0 disk reads (all cached)
Third open:  0 disk reads (all cached)
```

**What gets cached:**
- Inode blocks (especially root and frequently accessed directories)
- Directory data blocks
- Recently accessed file data
- Metadata structures

> **💡 Insight**
>
> Caching is most effective for metadata (inodes, directories) because the same paths are traversed repeatedly. Once `/usr/bin` is cached, opening any program in that directory is fast.

#### Historical Approach: Fixed-Size Cache

**Early file systems (pre-2000s):**
```
Memory allocation at boot:
┌──────────────────┬────────────────┐
│ File cache (10%) │ Other uses (90%) │
└──────────────────┴────────────────┘

Example with 1 GB RAM:
- 100 MB for file system cache
- 900 MB for applications, kernel, etc.
```

**Problem:** What if file system doesn't need 10%? Wasted memory!

### 8.2. Static vs Dynamic Partitioning

#### Static Partitioning

**Characteristics:**
- Fixed proportions set at boot
- Predictable performance
- Simple to implement
- **Drawback:** Inflexible, can waste resources

```
Example:
Memory: 4 GB
File cache: 400 MB (10% - fixed)

Scenario: File system only needs 200 MB
Result: 200 MB wasted (can't be used elsewhere)
```

#### Dynamic Partitioning

**Characteristics:**
- Flexible allocation over time
- Better utilization
- More complex to implement
- **Advantage:** Adapts to workload

```
Modern unified page cache:
┌─────────────────────────────────┐
│   Unified Page Cache (4 GB)    │
│                                 │
│  ┌──────────┐  ┌─────────────┐ │
│  │ File     │  │ Process     │ │
│  │ System   │  │ Virtual     │ │
│  │ Pages    │  │ Memory      │ │
│  │          │  │ Pages       │ │
│  └──────────┘  └─────────────┘ │
│      ↑              ↑           │
│      └──────┬───────┘           │
│        Dynamically allocated    │
│        based on demand          │
└─────────────────────────────────┘

Allocation changes based on workload:
Time 1: 60% files, 40% process memory
Time 2: 30% files, 70% process memory
```

**Modern approach:**
- Linux, Windows, macOS use unified page cache
- Same memory pool for file pages and virtual memory pages
- System dynamically adjusts allocation
- Maximizes memory utilization

> **📊 Trade-off Analysis**
>
> Static: Predictable, simple, guaranteed resources, potential waste
> Dynamic: Efficient, flexible, complex, potential contention

### 8.3. Write Buffering Benefits

**Key insight:** Unlike reads (which can be eliminated with caching), writes must eventually reach disk for durability. However, buffering still helps!

#### Benefit 1: Batching Updates

**Problem:** Repeated updates to same structure

```
Without buffering:
create("file1")     → write inode bitmap
create("file2")     → write inode bitmap
create("file3")     → write inode bitmap
────────────────────
Result: 3 disk writes
```

```
With buffering:
create("file1")     → update bitmap in memory
create("file2")     → update bitmap in memory
create("file3")     → update bitmap in memory
[5 seconds later]   → write bitmap once
────────────────────
Result: 1 disk write
```

#### Benefit 2: I/O Scheduling

**Buffering allows reordering:**

```
Pending writes (unordered):
- Write block 5000
- Write block 1000
- Write block 3000

Scheduler can optimize:
- Write block 1000  ←
- Write block 3000  ← Reduce seek time
- Write block 5000  ← by writing in order
```

#### Benefit 3: Avoiding Writes Entirely

**Short-lived files:**

```
Timeline:
0s:  create("temp.txt")       → buffer in memory
1s:  write("hello world")     → buffer in memory
2s:  delete("temp.txt")       → buffer in memory
5s:  [buffering timeout]      → nothing to write!

Result: File lived only in memory, 0 disk I/Os
```

**Benefits:**
- Create temporary files with no disk cost
- Compiler scratch files
- Build system intermediate files

> **🚀 Performance Impact**
>
> Write buffering typical values:
> - 5-30 second delay before disk write
> - Longer delay = better performance, more data at risk
> - Shorter delay = less performance, safer data

### 8.4. The Durability-Performance Trade-off

**The fundamental tension:**

```
Fast Performance          Durability
       ↑                      ↑
       │                      │
   Buffer writes          Write immediately
   in memory              to disk
       │                      │
   ✅ Fast                 ✅ Safe
   ❌ Risky               ❌ Slow
```

#### Default File System Behavior

**Most file systems:**
```
write("data")
└─→ Returns immediately (data in memory buffer)
    └─→ Writes to disk after 5-30 seconds

If crash occurs before disk write:
└─→ Data is LOST
```

**Trade-off:**
- **Pros:** Fast perceived performance
- **Cons:** Recent writes lost on crash

#### Applications That Need Durability

**Databases, critical systems:**

```c
// Force immediate write to disk
write(fd, data, size);
fsync(fd);  // Block until data on disk
```

**Alternative approaches:**

1. **Direct I/O:** Bypass cache entirely
```c
fd = open("file", O_DIRECT);  // No caching
```

2. **Raw disk interface:** Skip file system
```c
fd = open("/dev/sda1", O_RDWR);  // Direct disk access
```

3. **Synchronous writes:**
```c
fd = open("file", O_SYNC);  // Every write is durable
```

**Trade-off table:**

| Approach        | Speed | Durability | Use Case                    |
|-----------------|-------|------------|-----------------------------|
| Buffered write  | ⚡⚡⚡ | ❌         | Normal files, temp data     |
| fsync()         | ⚡     | ✅         | Databases, critical saves   |
| O_SYNC          | ⚡     | ✅         | Log files, audit trails     |
| O_DIRECT        | ⚡⚡   | ✅         | High-perf databases         |
| Raw disk        | ⚡⚡   | ✅         | Database internals          |

> **💰 Real-world Impact**
>
> "What if the system crashes before my write completes?"
> - For downloads: Probably fine, re-download
> - For bank transactions: NOT fine, must be durable
>
> Most applications accept the trade-off. Critical applications opt out.

---

## 9. Summary

**What we've learned:** The complete anatomy of a simple file system

### 🗂️ Key Data Structures

1. **Superblock:** File system metadata and parameters
2. **Inode bitmap:** Track which inodes are free/used
3. **Data bitmap:** Track which data blocks are free/used
4. **Inode table:** Store file metadata (one inode per file)
5. **Data region:** Store actual file contents

### 🔧 Core Concepts

**Inodes:**
- Contain all metadata except file name
- Use multi-level indexing (direct, indirect, double indirect, triple indirect)
- Designed for small files (most common case)
- Can support huge files when needed

**Directories:**
- Special files containing (name → inode number) mappings
- Have their own inodes
- Use data blocks like regular files
- Can use advanced structures (B-trees) for large directories

**Free space management:**
- Bitmaps are simple and popular
- Alternative: free lists, B-trees
- Only consulted during allocation (not reads!)

### 🌊 Access Patterns

**Reading requires:**
- Traversing pathname (inode + data per directory level)
- Reading file's inode
- Reading file's data blocks
- Updating access time

**Writing requires:**
- Everything reading requires
- Plus: allocating blocks (bitmap operations)
- Updating multiple metadata structures

**Creating requires:**
- Traversing to parent directory
- Allocating inode (inode bitmap)
- Allocating data blocks (data bitmap)
- Updating parent directory
- Writing new inode
- Most expensive operation!

### ⚡ Performance Optimizations

**Caching:**
- Modern systems use unified page cache
- Dramatically reduces read I/O
- Especially effective for metadata
- Dynamic memory allocation is superior

**Write buffering:**
- Batches updates to reduce I/Os
- Enables I/O scheduling
- Can avoid writes entirely (short-lived files)
- Trade-off: performance vs durability

### 🎓 Key Insights

1. **File systems are pure software** - tremendous design freedom
2. **Multi-level indexing optimizes for common case** - most files are small
3. **Allocation structures only used during allocation** - not during reads
4. **Pathname length directly impacts performance** - each level costs I/Os
5. **Caching is essential** - without it, performance would be unacceptable
6. **Durability vs performance is fundamental** - applications choose their trade-off

### 🚀 Looking Forward

The design freedom in file systems leads to incredible variety:
- Simple structures (vsfs, ext2) vs complex structures (XFS, ZFS)
- Different optimization targets (small files, large files, databases)
- Various allocation policies (where to place files?)
- Advanced features (snapshots, compression, deduplication)

**Next chapters explore:**
- Real file system implementations and their trade-offs
- Allocation policies and their performance impacts
- Advanced features and optimizations
- Crash consistency and journaling

> **💡 Final Insight**
>
> Understanding file systems requires building two mental models:
> 1. **Structural:** What's on disk and how it's organized
> 2. **Behavioral:** What happens during operations
>
> Master both, and you understand file systems deeply.

---

**Previous:** [Chapter 4: Files and Directories](chapter4-files-directories.md) | **Next:** [Chapter 6: Locality and Fast File System](chapter6-locality-fast-file-system.md)
