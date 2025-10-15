# 📜 Chapter 9: Log-Structured File Systems

_Turning the write problem into a sequential solution_

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [The Core Challenge](#2-the-core-challenge)
3. [Writing to Disk Sequentially](#3-writing-to-disk-sequentially)
   - 3.1. [Basic Sequential Writing](#31-basic-sequential-writing)
   - 3.2. [The Rotation Problem](#32-the-rotation-problem)
4. [Write Buffering and Segments](#4-write-buffering-and-segments)
   - 4.1. [The Segment Concept](#41-the-segment-concept)
   - 4.2. [How Much to Buffer](#42-how-much-to-buffer)
5. [Finding Data in LFS](#5-finding-data-in-lfs)
   - 5.1. [The Inode Problem](#51-the-inode-problem)
   - 5.2. [Solution: The Inode Map](#52-solution-the-inode-map)
   - 5.3. [The Checkpoint Region](#53-the-checkpoint-region)
6. [Reading Files in LFS](#6-reading-files-in-lfs)
7. [Directories in LFS](#7-directories-in-lfs)
8. [Garbage Collection](#8-garbage-collection)
   - 8.1. [The Garbage Problem](#81-the-garbage-problem)
   - 8.2. [Segment Cleaning](#82-segment-cleaning)
   - 8.3. [Determining Block Liveness](#83-determining-block-liveness)
   - 8.4. [Cleaning Policy](#84-cleaning-policy)
9. [Crash Recovery](#9-crash-recovery)
10. [Summary](#10-summary)

---

## 1. Introduction

In the early 1990s, a research team at Berkeley led by Professor John Ousterhout and graduate student Mendel Rosenblum observed a fundamental shift in how computer systems were being used. They noticed four critical trends that would reshape file system design:

**The Four Key Observations:**

1. **Memory is growing** - As RAM increases, more data gets cached, meaning disk traffic consists increasingly of writes rather than reads
2. **Sequential vs. random I/O gap is widening** - Hard drives improved sequential bandwidth dramatically, but seek times barely improved
3. **Existing file systems waste performance** - Even FFS requires many small writes with seeks between them to create a single file
4. **File systems ignore RAID** - Systems like RAID-4 and RAID-5 suffer from the small-write problem that file systems don't try to avoid

**In plain English:** File systems were designed when disks were different. The old approach of carefully placing data in fixed locations was causing unnecessary seeks and rotations, wasting the disk's sequential speed.

**In technical terms:** Traditional file systems like FFS perform update-in-place, requiring multiple random writes to update metadata structures (inodes, bitmaps, directory blocks). This approach fails to exploit the growing gap between sequential and random I/O performance.

**Why it matters:** By 1990, a disk could read/write at 10+ MB/s sequentially but only achieve 1-2 MB/s with random I/Os. File systems were leaving 80-90% of disk bandwidth on the table.

> **💡 Insight**
>
> LFS represents a fundamental shift in thinking: instead of treating the disk as an array of fixed blocks that can be updated in place, LFS treats it as an append-only log. This simple conceptual change solves multiple problems at once: it maximizes sequential bandwidth, works well with RAID, and simplifies crash recovery.

---

## 2. The Core Challenge

**The Crux:**

> How can a file system transform all writes into sequential writes? For reads, this is impossible - you must read from wherever the data lives. But for writes, the file system always has a choice about where to place new data.

The answer that Rosenblum and Ousterhout proposed was elegant: **write everything sequentially to an unused part of the disk, treating the entire disk as a log.**

**The LFS approach:**

1. Buffer all updates (data AND metadata) in memory
2. When the buffer is full, write it to disk in one long sequential transfer
3. Never overwrite existing data - always write to free space
4. Keep track of where things are with an indirection layer

Because LFS writes in large chunks to fresh locations, it achieves near-peak disk bandwidth.

---

## 3. Writing to Disk Sequentially

### 3.1. Basic Sequential Writing

Let's start with a simple example. When you write a data block `D` to a file, a traditional file system would:

1. Seek to the data block location
2. Write the data block
3. Seek to the inode location
4. Write the updated inode
5. Possibly update bitmap and other metadata with more seeks

**LFS does something different** - it writes both the data block and inode together:

```
Sequential Write on Disk:
┌─────────────┬─────────────┐
│ Data Block  │   Inode     │
│     D       │      I      │
│ [data...]   │ blk[0]: A0  │
└─────────────┴─────────────┘
    Address A0     Address A1
```

Both structures are written sequentially, in one operation, to wherever there's free space on the disk.

### 3.2. The Rotation Problem

**But there's a catch.** Simply writing blocks one at a time sequentially isn't enough.

**The problem:** If you write a block at time T, then wait a bit and write the next block at time T+δ, the disk has rotated in between. The second write will wait for nearly a full rotation before it can be committed to the platter.

**In plain English:** Imagine the disk is like a record player. If you write one song, stop, and then try to write the next song, the record has already spun past where you need to write. You have to wait for it to come back around.

**The math:** If rotation time is Trotation and you wait δ seconds between writes, you waste Trotation - δ seconds waiting for the disk to come back around.

**The solution:** Write buffering - collect many updates in memory, then write them all at once as one large sequential write.

---

## 4. Write Buffering and Segments

### 4.1. The Segment Concept

LFS introduces the concept of a **segment** - a large chunk of updates that are written together.

**How it works:**

1. LFS keeps track of updates in memory
2. When enough updates have accumulated, LFS writes them all at once
3. The entire segment (typically several MB) is written sequentially
4. The disk is used efficiently because positioning overhead is amortized over the large write

**Example segment write:**

```
File j updated (4 blocks) + File k updated (1 block):
┌──────┬──────┬──────┬──────┬─────────┬──────┬─────────┐
│D[j,0]│D[j,1]│D[j,2]│D[j,3]│ Inode[j]│D[k,0]│ Inode[k]│
└──────┴──────┴──────┴──────┴─────────┴──────┴─────────┘
  A0     A1     A2     A3       A4       A5       A6

All written sequentially in one operation
```

The data blocks, inodes, and all other structures are written together to unused disk space.

### 4.2. How Much to Buffer

**The mathematical question:** How large should segments be to achieve good performance?

Let's define our variables:
- **Tposition** = time for positioning (seek + rotation), e.g., 10ms
- **Rpeak** = peak transfer rate, e.g., 100 MB/s
- **D** = amount of data to write (what we're solving for)
- **F** = desired efficiency fraction, e.g., 0.9 (90% of peak)

**The formula:**

The time to write D megabytes is:
```
Twrite = Tposition + (D / Rpeak)
```

The effective write rate is:
```
Reffective = D / Twrite = D / (Tposition + D/Rpeak)
```

We want: Reffective = F × Rpeak

**Solving for D:**
```
D = (F / (1-F)) × Rpeak × Tposition
```

**Concrete example:**
- Tposition = 10ms = 0.01 seconds
- Rpeak = 100 MB/s
- F = 0.9 (want 90% efficiency)

```
D = (0.9 / 0.1) × 100 MB/s × 0.01s
D = 9 × 1 MB = 9 MB
```

**Interpretation:** To achieve 90% of peak bandwidth with this disk, LFS should buffer at least 9 MB before writing. For 95% efficiency, you'd need 19 MB. For 99%, you'd need 99 MB.

> **💡 Insight**
>
> The math shows why modern SSDs don't need buffering as much - they have near-zero positioning time. But for hard drives, write buffering is essential. This is also why LFS works beautifully with RAID - a single large write avoids the small-write problem entirely.

---

## 5. Finding Data in LFS

### 5.1. The Inode Problem

Now we face a serious challenge: **how do we find anything?**

**In traditional file systems (like FFS):**
- Inodes are stored in a fixed array at a known location
- Given inode number N, you can calculate its address: `inode_start + (N × inode_size)`
- This is fast and straightforward

**In LFS:**
- Inodes are scattered all over the disk
- Each write creates a new version of the inode at a new location
- The latest version keeps moving
- We can't use fixed locations without destroying write performance

**The challenge:** We need fast inode lookup, but inodes are constantly moving to new locations.

### 5.2. Solution: The Inode Map

LFS introduces a level of indirection called the **inode map** (imap).

**What it does:** The imap takes an inode number as input and returns the disk address of the most recent version of that inode.

**Structure:**
- A simple array with 4-byte entries (disk pointers)
- Entry N contains the disk address of inode N
- Updated whenever an inode is written to a new location

**The clever part:** The imap itself is also written sequentially with the data!

```
Writing file k:
┌──────────┬─────────┬─────────────┐
│Data Block│ Inode[k]│  Imap Chunk │
│    D     │blk[0]:A0│  map[k]:A1  │
└──────────┴─────────┴─────────────┘
   Addr A0    Addr A1     Addr A2
```

The imap chunk at A2 says "inode k is at address A1", and the inode at A1 says "data is at address A0".

**Why this works:**
- The imap can be cached in memory (it's small relative to data)
- Only the imap needs to be updated when inodes move
- No fixed locations required except for one...

### 5.3. The Checkpoint Region

**The final piece:** How do we find the imap chunks?

The **checkpoint region (CR)** is a fixed location on disk (typically at the start) that points to the latest imap chunks.

```
Disk Layout:
┌─────────────────┐
│ Checkpoint      │  ← Fixed location (address 0)
│ Region (CR)     │     Points to imap chunks
└─────────────────┘
        ↓
┌─────────────────┐
│ Imap Chunk      │  ← Multiple chunks, scattered
│ [k...k+N]: A2   │     Point to inodes
└─────────────────┘
        ↓
┌─────────────────┐
│ Inode[k]        │  ← Points to data blocks
│ blk[0]: A0      │
└─────────────────┘
        ↓
┌─────────────────┐
│ Data Block      │
│ [actual data]   │
└─────────────────┘
```

**Performance trick:** The CR is only updated periodically (every 30 seconds), so updating it doesn't hurt performance. All the frequent updates go to the log.

> **💡 Insight**
>
> The imap solves another critical problem called the "recursive update problem." In a file system that never updates in place, changing an inode would normally require updating its parent directory, which would require updating the grandparent directory, all the way to the root. The imap breaks this chain - only the imap needs to know about the inode's new location, not the directory.

---

## 6. Reading Files in LFS

Let's walk through reading a file from a cold start (nothing cached):

**Step-by-step process:**

1. **Read the checkpoint region** (fixed location on disk)
   - Get pointers to all imap chunks

2. **Read and cache the entire inode map**
   - Store imap in memory for fast lookups

3. **Look up the inode**
   - Given inode number N, consult the cached imap
   - Find the disk address of inode N
   - Read the inode from that address

4. **Read the data**
   - Use direct/indirect pointers in the inode (just like traditional UNIX)
   - Read the actual data blocks

**Performance in the common case:**
- After the imap is cached, LFS reads files with the same number of I/Os as a traditional file system
- The extra work is just an in-memory imap lookup
- No performance penalty for reads

---

## 7. Directories in LFS

**Good news:** Directories work almost exactly like in traditional UNIX file systems.

**Directory structure:**
- A directory is a collection of (name, inode number) mappings
- Directory data is just another file that LFS writes sequentially

**Example - creating a file "foo":**

```
┌─────────┬─────────┬────────────┬──────────┬──────────┐
│ Data[k] │ Inode[k]│Directory   │Inode[dir]│  Imap    │
│  [...]  │blk[0]:A0│Data        │blk[0]:A2 │map[k]:A1 │
│         │         │(foo, k)    │          │map[dir]:A3│
└─────────┴─────────┴────────────┴──────────┴──────────┘
   A0         A1         A2           A3          A4
```

Everything written sequentially:
1. New file data
2. New file inode pointing to data
3. Updated directory data (now includes "foo -> k" mapping)
4. Updated directory inode
5. Imap chunk tracking both inodes

**Reading a file by path:**

To read `/dir/foo`:
1. Look up inode for `dir` in imap (cached) → address A3
2. Read directory inode → tells us directory data is at A2
3. Read directory data → tells us "foo" has inode number k
4. Look up inode k in imap → address A1
5. Read inode k → tells us data is at A0
6. Read data at A0

The directory never needs to store disk addresses - only inode numbers. The imap handles the indirection.

---

## 8. Garbage Collection

### 8.1. The Garbage Problem

LFS has a fundamental challenge: **it never overwrites data in place, leaving old versions scattered across the disk.**

**Example - updating a file:**

```
Before update:
┌──────────┬─────────┐
│ Data (D0)│ Inode[k]│
│  [old]   │blk[0]:A0│
└──────────┴─────────┘
   A0          A1

After update:
┌──────────┬─────────┬──────────┬─────────┐
│ Data (D0)│ Inode[k]│Data (D0')│ Inode[k]│
│  [old]   │blk[0]:A0│  [new]   │blk[0]:A4│
└──────────┴─────────┴──────────┴─────────┘
   A0          A1        A4          A5
   ←─── garbage ───→    ←─── live ──→
```

The old blocks at A0 and A1 are now garbage - they're not referenced by any current file structure.

**Two options:**

1. **Keep old versions** (versioning file system) - Allow users to recover old file versions
2. **Reclaim space** (LFS choice) - Clean up garbage to free space for new writes

LFS chooses option 2: periodically clean garbage to reclaim disk space.

### 8.2. Segment Cleaning

**Why segment-based cleaning?**

If LFS cleaned individual blocks, the disk would become fragmented with small holes. This would destroy write performance - LFS couldn't find large contiguous regions for sequential writes.

**Solution:** Clean entire segments at once.

**The cleaning process:**

1. **Read** M old segments (partially full of garbage)
2. **Identify** which blocks are still live
3. **Compact** live blocks into N new segments (where N < M)
4. **Write** the N segments to fresh disk locations
5. **Free** the original M segments for reuse

**Example:**

```
Before Cleaning:
Segment 1: [live][dead][dead][live]
Segment 2: [dead][live][dead][dead]
Segment 3: [live][live][dead][dead]

After Cleaning:
Segment 4: [live][live][live][live]  ← Compacted live blocks
Segments 1,2,3: [free] [free] [free] ← Available for new writes
```

### 8.3. Determining Block Liveness

**The mechanism question:** How does LFS know if a block is live or dead?

**Solution:** Each segment includes a **segment summary block** at its head.

**Segment summary contains:**
- For each data block D in the segment:
  - Inode number N (which file owns this block)
  - Offset T (which block number within the file)

**Liveness check algorithm:**

```
To check if block at address A is live:

1. Read segment summary[A] → get (N, T)
2. Look up inode N in imap → get inode address
3. Read inode N from disk
4. Check inode[T] (the T-th block pointer)
5. If inode[T] == A:
      Block is LIVE (current version)
   Else:
      Block is GARBAGE (outdated version)
```

**Example:**

```
Segment Summary Block:
┌────────────────┐
│ SS: A0: (k,0)  │ ← Says "block at A0 is file k, offset 0"
└────────────────┘

Data Block:
┌────────────────┐
│ Data Block     │
│ [file k data]  │
└────────────────┘
  Address A0

Inode[k] (from imap):
┌────────────────┐
│ blk[0]: A0     │ ← Points to A0
│ blk[1]: A5     │
└────────────────┘
  Address A1

Check: inode[k].blk[0] == A0? YES → Block at A0 is LIVE
```

**Optimization:** LFS also stores version numbers. When a file is deleted or truncated, LFS increments the version number in the imap. By comparing version numbers, LFS can quickly identify dead blocks without reading inodes.

### 8.4. Cleaning Policy

**Two policy questions:**

1. **When to clean?** → Easier to answer
2. **Which segments to clean?** → More challenging

**When to clean:**
- Periodically (background process)
- During idle time
- When disk is getting full (necessary)

**Which segments to clean:**

The original LFS paper identified two types of segments:

**Hot segments:**
- Contents are frequently overwritten
- Many blocks will soon become garbage naturally
- **Policy:** Wait longer before cleaning
- More blocks will be dead by the time you clean it

**Cold segments:**
- Contents are relatively stable
- Few blocks becoming garbage over time
- **Policy:** Clean sooner
- Most blocks will remain live, so clean now to consolidate

**The trade-off:**

```
Hot Segment Strategy:
Time: ────────────────────────────────────→
Blocks: [live|live|live|live]
        └→[dead|dead|dead|dead] ← Wait and many blocks die

Clean later: [dead|dead|dead|dead] → Very efficient (all garbage)

Cold Segment Strategy:
Time: ────────────────────────────────────→
Blocks: [live|live|live|dead]
        └→[live|live|live|dead] ← Few blocks die over time

Clean sooner: [live|live|live|dead] → Less efficient but still valuable
```

**Why this matters:** The efficiency of garbage collection directly impacts write amplification. Poor cleaning policy can waste significant bandwidth on rewriting live data.

> **💡 Insight**
>
> The hot/cold segmentation policy reveals a deeper pattern in system design: understanding workload behavior enables better resource management. Modern SSDs use similar techniques, and even memory allocators separate short-lived and long-lived objects for more efficient garbage collection.

---

## 9. Crash Recovery

**The final challenge:** What happens if the system crashes while LFS is writing?

### Two Critical Points of Failure

**1. Crash during segment write**
**2. Crash during checkpoint region update**

### Protecting the Checkpoint Region

**The problem:** The CR must be updated atomically, but disk writes aren't atomic.

**The solution:** LFS keeps **two** checkpoint regions, one at each end of the disk.

**Update protocol:**

1. Write header block with timestamp T1
2. Write body of CR
3. Write footer block with timestamp T2
4. Alternate between CR at disk start and CR at disk end

**Crash detection:**

```
If T1 == T2:
    CR is consistent → Use this CR
Else:
    CR is inconsistent → Discard, use previous CR
```

**Result:** LFS always has at least one consistent CR. It uses the most recent CR with matching timestamps.

### Recovering Recent Writes

**The problem:** The CR is only updated every 30 seconds. A crash could lose 30 seconds of writes.

**The solution:** **Roll forward** (borrowed from database systems).

**Roll forward process:**

1. Read the last consistent CR
2. Find the end of the log (CR contains this pointer)
3. Scan forward through subsequent segments
4. Check each segment for valid data (using checksums)
5. If valid, update the file system with that segment's contents
6. Continue until no more valid segments found

**Result:** LFS recovers most writes between the last CR update and the crash, not just the data from 30 seconds ago.

**Example timeline:**

```
Timeline:
0s: ──────────30s────────────45s──────────60s→
    CR #1            Crash     CR #2
           [segments written but not in CR]

Recovery:
1. Read CR #1 (last consistent checkpoint)
2. Roll forward through segments written at 5s, 10s, 15s...45s
3. Recover approximately 45 seconds of work instead of losing 15 seconds
```

---

## 10. Summary

### The LFS Revolution

LFS introduced a fundamentally different approach to file system design:

**Core idea:** Treat the entire disk as an append-only log
- Never update data in place
- Always write to free space
- Write large sequential chunks
- Clean garbage in the background

**Key innovations:**

1. **Write buffering with segments** - Amortize positioning costs over large writes
2. **Inode map** - Indirection layer that allows inodes to move freely
3. **Checkpoint region** - Fixed starting point with periodic updates
4. **Segment cleaning** - Garbage collection that preserves sequential write performance
5. **Crash recovery** - Dual CRs and roll forward for consistency

### Performance Characteristics

**Strengths:**
- Excellent write performance (near peak sequential bandwidth)
- Works wonderfully with RAID (avoids small-write problem)
- Modern SSDs also benefit from large sequential writes
- Simplified crash recovery through logging

**Weaknesses:**
- Garbage collection overhead (write amplification)
- Complexity of cleaning policy
- Random read performance similar to traditional file systems
- Memory overhead for imap caching

### Legacy and Impact

While LFS itself isn't widely deployed, its ideas live on in:

**Modern file systems:**
- **NetApp WAFL** - Uses copy-on-write, turns cleaning overhead into snapshot feature
- **Sun ZFS** - Copy-on-write with similar log-structuring
- **Linux btrfs** - Copy-on-write design
- **Flash-based SSDs** - Flash Translation Layers (FTLs) use log-structuring internally

**The deeper lesson:**

LFS shows how rethinking fundamental assumptions (update-in-place) can lead to dramatic improvements. By matching the file system design to the hardware characteristics (fast sequential I/O, slow random I/O), LFS achieves performance that approaches theoretical limits.

> **💡 Insight**
>
> The intellectual legacy of LFS extends beyond file systems. The core pattern - turn random updates into sequential appends through logging and indirection - appears throughout modern systems: databases (write-ahead logging), distributed systems (event sourcing), and storage devices (log-structured merge trees). Understanding LFS gives you a lens for understanding an entire class of high-performance systems.

**The trade-off:** LFS exchanges some complexity (garbage collection, indirection) for dramatic performance gains. This trade-off proved worthwhile - the patterns LFS pioneered are now fundamental to modern high-performance storage systems.

---

**Previous:** [Chapter 8: Journaling](chapter8-journaling.md) | **Next:** [Chapter 10: Flash-Based SSDs](chapter10-flash-based-ssds.md)
