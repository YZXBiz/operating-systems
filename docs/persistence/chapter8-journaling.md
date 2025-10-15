# 📝 Chapter 8: Crash Consistency - FSCK and Journaling

File system crash consistency, journaling (write-ahead logging), recovery mechanisms, and metadata journaling techniques.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [The Crash Consistency Problem](#2-the-crash-consistency-problem)
   - 2.1. [A Detailed Example](#21-a-detailed-example)
   - 2.2. [Crash Scenarios](#22-crash-scenarios)
   - 2.3. [Understanding the Problem](#23-understanding-the-problem)
3. [Solution #1: File System Checker (FSCK)](#3-solution-1-file-system-checker-fsck)
   - 3.1. [How FSCK Works](#31-how-fsck-works)
   - 3.2. [Limitations of FSCK](#32-limitations-of-fsck)
4. [Solution #2: Journaling (Write-Ahead Logging)](#4-solution-2-journaling-write-ahead-logging)
   - 4.1. [Basic Concepts](#41-basic-concepts)
   - 4.2. [Data Journaling](#42-data-journaling)
   - 4.3. [Recovery Process](#43-recovery-process)
   - 4.4. [Batching Log Updates](#44-batching-log-updates)
   - 4.5. [Making the Log Finite](#45-making-the-log-finite)
5. [Metadata Journaling](#5-metadata-journaling)
   - 5.1. [Ordered Journaling](#51-ordered-journaling)
   - 5.2. [Block Reuse Challenges](#52-block-reuse-challenges)
   - 5.3. [Protocol Timeline](#53-protocol-timeline)
6. [Other Approaches](#6-other-approaches)
   - 6.1. [Soft Updates](#61-soft-updates)
   - 6.2. [Copy-On-Write](#62-copy-on-write)
   - 6.3. [Modern Techniques](#63-modern-techniques)
7. [Summary](#7-summary)

---

## 1. Introduction

**In plain English:** Imagine writing a book and the power goes out mid-sentence. When you turn the computer back on, you'd want to know exactly where you left off—not discover half-written gibberish scattered throughout your manuscript.

**In technical terms:** File systems must maintain persistent data structures that survive power loss or system crashes. The challenge is ensuring these structures remain consistent when updates are interrupted mid-operation.

**Why it matters:** Every time your computer crashes or loses power during a write operation, the file system must recover to a consistent state. Without proper mechanisms, you could lose data, corrupt files, or render the entire file system unmountable.

### 🎯 The Core Challenge

File systems manage data structures (inodes, bitmaps, directory entries) that must persist across power failures. Unlike in-memory data structures, these must survive crashes while potentially being updated.

> **💡 Insight**
>
> The crash-consistency problem is fundamentally about atomicity: how do we make multiple related disk writes appear as a single atomic operation when disks can only service one request at a time?

**The Crux:** How do we update the disk despite crashes? The system may crash or lose power between any two writes, leaving the on-disk state only partially updated. How do we ensure the file system can always recover to a reasonable state?

---

## 2. The Crash Consistency Problem

### 2.1. A Detailed Example

Let's examine what happens when appending a single 4KB data block to an existing file.

**The Setup:**

```
Simple File System Layout:
┌──────┬──────┬────────┬──────────────┐
│Inode │Data  │        │              │
│Bitmap│Bitmap│ Inodes │ Data Blocks  │
└──────┴──────┴────────┴──────────────┘
```

**Initial State:**
- File has inode #2 (marked in inode bitmap)
- File has 1 data block (#4, marked in data bitmap)
- Inode version 1 (I[v1]) points to block 4

**Inode v1 Contents:**
```
owner: remzi
permissions: read-write
size: 1
pointer[0]: 4
pointer[1]: null
pointer[2]: null
pointer[3]: null
```

**The Append Operation requires three updates:**

1. **Inode (I[v2])** - Updated size and new pointer
2. **Data Bitmap (B[v2])** - Mark block 5 as allocated
3. **Data Block (Db)** - The actual new data

**Updated Inode v2:**
```
owner: remzi
permissions: read-write
size: 2
pointer[0]: 4
pointer[1]: 5    ← New!
pointer[2]: null
pointer[3]: null
```

**Updated Bitmap (B[v2]):** `00001100` (blocks 4 and 5 allocated)

### 2.2. Crash Scenarios

Since disks service one request at a time, crashes can leave the system in various inconsistent states.

#### 📊 Single Write Succeeds

**Scenario 1: Only data block (Db) written**
```
Result: Data exists but nothing points to it
Impact: ✅ No consistency problem (data is simply lost)
```

**Scenario 2: Only inode (I[v2]) written**
```
Result: Inode points to unwritten data at block 5
Impact: ⚠️ File-system inconsistency + garbage data
        - Bitmap says block 5 is free
        - Inode says block 5 is allocated
        - Reading block 5 returns garbage
```

**Scenario 3: Only bitmap (B[v2]) written**
```
Result: Block 5 marked allocated but nothing points to it
Impact: ⚠️ File-system inconsistency + space leak
        - Block 5 can never be used again
```

#### 📊 Two Writes Succeed

**Scenario 4: Inode + Bitmap written, not data**
```
Result: Metadata consistent but points to garbage
Impact: ⚠️ File system looks consistent
        - But block 5 contains garbage data
```

**Scenario 5: Inode + Data written, not bitmap**
```
Result: Correct data but metadata inconsistent
Impact: ⚠️ Inode points to correct data
        - But bitmap disagrees about allocation
```

**Scenario 6: Bitmap + Data written, not inode**
```
Result: Data written and marked allocated
Impact: ⚠️ But no inode knows which file it belongs to
        - Orphaned data block
```

### 2.3. Understanding the Problem

**In plain English:** It's like trying to update a ledger with three entries that must all match. If you only complete one or two entries before the power fails, your books won't balance.

**In technical terms:** The crash-consistency problem (or consistent-update problem) arises because we cannot atomically commit multiple disk writes. The disk commits one write at a time, and crashes between updates leave inconsistent state.

> **⚠️ Warning**
>
> Details matter! While the general idea of crash consistency is simple, building a working system requires thinking through every edge case. The tricky cases often hide in block reuse, recovery ordering, and disk scheduling.

---

## 3. Solution #1: File System Checker (FSCK)

### 3.1. How FSCK Works

**In plain English:** FSCK is like a forensic accountant who examines your entire ledger after a disaster, finding and fixing inconsistencies. But checking every entry takes a very long time.

**In technical terms:** FSCK (File System Checker, pronounced "eff-ess-see-kay" or "eff-suck") is a UNIX tool that scans the entire disk partition to find and repair inconsistencies. It runs before mounting the file system after a crash.

#### 🔧 FSCK Phases

**Phase 1: Superblock Checks**
```
Action: Verify superblock sanity
Checks: - File system size > allocated blocks
        - Valid magic numbers
        - Reasonable parameters
Recovery: Use alternate superblock if suspect
```

**Phase 2: Free Block Analysis**
```
Action: Build allocation bitmap from scratch
Process:
  1. Scan all inodes
  2. Follow all indirect blocks
  3. Determine which blocks are truly allocated
  4. Rebuild allocation bitmaps from this truth
Result: Trust inodes over bitmaps
```

**Phase 3: Inode State Verification**
```
Checks: - Valid type fields (file, directory, symlink)
        - Reasonable block counts
        - Valid permission bits
Action: Clear suspect inodes and update bitmaps
```

**Phase 4: Link Count Verification**
```
Process:
  1. Traverse entire directory tree from root
  2. Count references to each inode
  3. Compare with inode's link count field
  4. Fix mismatches in inodes
  5. Move orphaned files to lost+found/
```

**Phase 5: Duplicate Pointer Detection**
```
Problem: Two inodes pointing to same block
Solutions:
  - Clear obviously bad inode
  - Copy block to give each inode its own copy
```

**Phase 6: Bad Block Pointers**
```
Check: Pointer addresses within valid range
Action: Clear any pointer outside partition bounds
```

**Phase 7: Directory Integrity**
```
Checks: - "." and ".." are first entries
        - All referenced inodes are allocated
        - No directory linked more than once
Action: Fix directory structure violations
```

### 3.2. Limitations of FSCK

**❌ Too Slow**
- Scan time: O(size-of-disk-volume)
- Multi-TB disks = hours of recovery
- RAID arrays make it even worse

**❌ Wasteful**
- Scanning entire disk to fix 3-block update
- Like searching entire house for keys when you dropped them in the bedroom

**❌ Can't Fix Everything**
- Metadata can be consistent while pointing to garbage data
- User data guarantees are limited

> **💡 Insight**
>
> The fundamental inefficiency of FSCK comes from its lazy approach: let inconsistencies happen, then fix everything later. This was acceptable when disks were small but becomes prohibitive at modern scales.

---

## 4. Solution #2: Journaling (Write-Ahead Logging)

### 4.1. Basic Concepts

**In plain English:** Before making changes to your actual documents, write a note to yourself describing what you're about to do. If the power fails, you can read your note and know exactly what to finish.

**In technical terms:** Write-ahead logging (called "journaling" in file systems) means recording intended updates in a log before applying them to actual locations. After a crash, the system reads the log to replay or complete pending operations.

**Why it matters:** Journaling reduces recovery time from O(size-of-disk) to O(size-of-log), typically from hours to seconds. This technique came from database systems and is now used in ext3, ext4, NTFS, XFS, and many others.

#### 🏗️ File System Structure

**Without Journaling (ext2):**
```
┌───────┬────────┬────────┬───┬────────┐
│ Super │Group 0 │Group 1 │...│Group N │
└───────┴────────┴────────┴───┴────────┘
```

**With Journaling (ext3):**
```
┌───────┬─────────┬────────┬────────┬───┬────────┐
│ Super │ Journal │Group 0 │Group 1 │...│Group N │
└───────┴─────────┴────────┴────────┴───┴────────┘
```

The journal is a dedicated area for recording pending operations before they're committed to final locations.

### 4.2. Data Journaling

#### 📝 Writing a Transaction

**Step 1: Write to Journal**

For our append example (inode I[v2], bitmap B[v2], data Db):

```
Journal Layout:
┌─────┬──────┬──────┬────┬─────┐
│ TxB │I[v2] │B[v2] │ Db │ TxE │
└─────┴──────┴──────┴────┴─────┘
```

**Components:**

1. **Transaction Begin (TxB)**
   - Transaction ID (TID)
   - Final addresses of blocks
   - Metadata about the update

2. **Block Contents**
   - I[v2]: Updated inode
   - B[v2]: Updated bitmap
   - Db: Actual data
   - Uses **physical logging** (exact block contents)

3. **Transaction End (TxE)**
   - End marker with matching TID
   - Must be 512 bytes for atomic write

> **💡 Insight**
>
> Physical logging writes exact block contents to the journal. An alternative, **logical logging**, writes compact descriptions like "append block Db to file X." Logical logging saves space but adds complexity.

#### ⚡ Write Protocol (3 Phases)

**Phase 1: Journal Write**
```
Action: Write TxB, I[v2], B[v2], Db to journal
Important: Do NOT write TxE yet
Wait: Until all blocks reach disk
```

**Why not write everything at once?** Disk scheduling could complete writes out of order, potentially writing TxB and TxE but not all content blocks. This would create a "valid" transaction with garbage data.

**Phase 2: Journal Commit**
```
Action: Write TxE (transaction end block)
Wait: Until TxE reaches disk
Result: Transaction is now committed
```

The 512-byte atomic write guarantee ensures TxE either fully writes or doesn't write at all.

**Phase 3: Checkpoint**
```
Action: Write I[v2], B[v2], Db to final locations
Result: File system is now updated
Note: No waiting required between individual writes
```

#### 🔄 Complete Protocol Sequence

```
Time ↓
─────────────────────────────────────────────
Issue:    TxB, I[v2], B[v2], Db → Journal
Wait:     All writes complete
Issue:    TxE → Journal
Wait:     TxE complete               [Committed]
Issue:    I[v2], B[v2], Db → Final locations
Complete: Checkpoint finished
```

> **⚠️ Warning: Disk Write Caches**
>
> Modern disks use write caches and may report writes as "complete" when they're only in memory cache. This breaks ordering guarantees! Solutions:
> - Disable write buffering (slower)
> - Use explicit write barriers (modern approach)
> - Recent research shows some disks ignore barriers for "performance" (dangerous!)

### 4.3. Recovery Process

**In plain English:** After a crash, check the journal's notes. If a note is complete (has begin AND end markers), redo the work. If incomplete, skip it.

**In technical terms:** This is called **redo logging**.

#### 🔍 Recovery Algorithm

```python
def recover():
    for transaction in journal:
        if has_complete_markers(transaction):  # Has TxB and TxE
            replay(transaction)  # Write blocks to final locations
        else:
            skip(transaction)   # Incomplete, ignore

    mount_filesystem()
```

**Cases:**

1. **Crash before Phase 2 (before TxE written)**
   - Transaction is incomplete
   - Action: Skip the update entirely
   - Result: File system is as before the operation

2. **Crash after Phase 2 (after TxE written)**
   - Transaction is committed
   - Action: Replay all writes from journal to final locations
   - Result: File system update completes successfully

3. **Crash during Phase 3 (during checkpoint)**
   - Some writes may have reached final locations
   - Action: Replay anyway (redundant writes are safe)
   - Result: File system update completes successfully

> **💡 Insight**
>
> Replaying already-completed writes is called **idempotence**. As long as the same operation produces the same result when repeated, recovery is safe even if we don't know exactly which writes completed.

#### ⏱️ Performance Benefits

```
FSCK:      O(size of entire disk)      → Hours
Journaling: O(size of journal)         → Seconds
```

### 4.4. Batching Log Updates

**The Problem:** Naive journaling creates excessive writes.

**Example: Creating Two Files**

Without batching, create `file1` and `file2` in same directory:

```
Transaction 1 (file1):
- Write inode bitmap
- Write inode for file1
- Write directory data block
- Write directory inode

Transaction 2 (file2):
- Write SAME inode bitmap again!
- Write inode for file2
- Write SAME directory data block again!
- Write SAME directory inode again!
```

**The Solution: Global Transactions**

```
Instead of:  Commit(file1) → Commit(file2)
Do:         Buffer both → Commit(file1 + file2)
```

**How It Works:**
1. Mark updates as dirty in memory
2. Add to current global transaction
3. After timeout (e.g., 5 seconds), commit everything together
4. Shared blocks (directory inode, bitmap) written only once

> **💡 Insight**
>
> Batching transforms many small transactions into fewer large ones, dramatically reducing journal traffic. This is why your disk doesn't constantly spin during regular file operations.

### 4.5. Making the Log Finite

**The Problem:** Logs can't grow forever.

```
Journal (filling up):
┌────┬────┬────┬────┬────┬────┬────┐
│Tx1 │Tx2 │Tx3 │Tx4 │Tx5 │Tx6 │... │ → Eventually full!
└────┴────┴────┴────┴────┴────┴────┘
```

**Issues with full log:**
1. Recovery time increases (must replay everything)
2. No space for new transactions (file system becomes unusable)

#### 🔄 Circular Log Solution

**Concept:** Treat the log as circular, reusing space after checkpointing.

```
Journal with Superblock:
┌───────┬────┬────┬────┬────┬────┬──────┐
│ Super │ Tx1│ Tx2│ Tx3│Tx4 │Tx5 │ ...  │
└───────┴────┴────┴────┴────┴────┴──────┘
           ↑                    ↑
         Oldest            Newest
      (checkpointed)    (not yet)
```

**Journal Superblock tracks:**
- Oldest non-checkpointed transaction
- Newest transaction
- All other space is free for reuse

**Updated Protocol (4 Phases):**

```
1. Journal Write:  Write transaction to log
2. Journal Commit: Write TxE to log (committed)
3. Checkpoint:     Write to final locations
4. Free:           Mark log space as reusable ← New!
```

> **⚠️ Warning**
>
> We're now writing each data block **twice**: once to journal, once to final location. This doubles write traffic! Is there a way to reduce this overhead?

---

## 5. Metadata Journaling

### 5.1. Ordered Journaling

**In plain English:** Instead of writing data twice, write it directly to its final location, but be careful about the order. Write the data before writing the metadata that points to it.

**In technical terms:** **Metadata journaling** (or **ordered journaling**) only writes metadata to the journal. User data goes directly to final locations, halving I/O traffic since most disk traffic is data, not metadata.

#### 📝 Modified Journal Layout

**Data Journaling:**
```
┌─────┬──────┬──────┬────┬─────┐
│ TxB │I[v2] │B[v2] │ Db │ TxE │  ← Data in journal
└─────┴──────┴──────┴────┴─────┘
```

**Metadata Journaling:**
```
┌─────┬──────┬──────┬─────┐
│ TxB │I[v2] │B[v2] │ TxE │  ← No data block!
└─────┴──────┴──────┴─────┘
                          Db → Written to final location only
```

#### ⚡ The Ordering Problem

**❌ Wrong Order (Metadata First):**

```
1. Write metadata (I[v2], B[v2]) to journal
2. Commit transaction
3. Write data (Db)
[CRASH BEFORE STEP 3]

Result: I[v2] points to block 5
        Block 5 contains garbage!
```

**✅ Correct Order (Data First):**

```
1. Write data (Db) to final location
2. Write metadata to journal
3. Commit transaction

[CRASH AT ANY POINT]
Result: Either Db not linked (safe)
        Or Db properly linked (complete)
```

#### 🔧 Metadata Journaling Protocol (5 Phases)

```
1. Data Write:
   Write Db to final location
   Wait: Optional (can overlap with step 2)

2. Journal Metadata Write:
   Write TxB, I[v2], B[v2] to journal
   Wait: Until complete

3. Journal Commit:
   Write TxE to journal
   Wait: Until complete [Transaction committed]

4. Checkpoint Metadata:
   Write I[v2], B[v2] to final locations

5. Free:
   Mark journal space as reusable
```

**Timeline Visualization:**

```
Time ↓
─────────────────────────────────────────────
Issue:    Db → Final location
Issue:    TxB, I[v2], B[v2] → Journal
Wait:     Db and journal writes complete
          ─────────────────────── [Barrier]
Issue:    TxE → Journal
Wait:     TxE complete               [Committed]
Issue:    I[v2], B[v2] → Final locations
Complete: Done
```

> **💡 Insight**
>
> The fundamental rule: **"Write the pointed-to object before the object that points to it."** This principle underlies all crash consistency schemes. A pointer should never reference garbage or incomplete data.

### 5.2. Block Reuse Challenges

**In plain English:** The hairiest problems in journaling involve deleting files and reusing their blocks. If you're not careful, recovery can overwrite current data with old journal entries.

#### ⚠️ The Delete-Then-Reuse Problem

**Scenario:** (Using metadata journaling)

**Step 1: Create directory**
```
Directory foo → Block 1000
Journal: [ TxB | I[foo] ptr:1000 | D[foo] data | TxE ]
```

**Step 2: Delete directory and its contents**
```
Block 1000 is freed
Journal: Still contains old D[foo] at block 1000
```

**Step 3: Create new file reusing block 1000**
```
File foobar → Block 1000 (data)
Journal: [ TxB | I[foobar] ptr:1000 | TxE ]
Note: foobar's DATA not in journal (metadata journaling)
```

**Step 4: Crash and replay**
```
Replay transaction 1: Write old D[foo] to block 1000
Result: foobar's data is now OVERWRITTEN with old directory data!
```

#### 🛡️ Solutions

**Option 1: Delay Block Reuse**
- Don't reuse blocks until their delete is checkpointed
- Conservative but simple

**Option 2: Revoke Records (Linux ext3's approach)**
```
When deleting:
  Write revoke record to journal

During recovery:
  1. Scan for revoke records first
  2. Skip replaying any revoked blocks
  3. Never overwrite current data
```

**Revoke Record Format:**
```
┌──────────────┬─────────┐
│ Revoke: 1000 │ TxID: 1 │
└──────────────┴─────────┘
```

### 5.3. Protocol Timeline

#### 📊 Data Journaling Timeline

```
Phase                Journal                   File System
                     TxB  Data  Meta  TxE      Data  Metadata
─────────────────────────────────────────────────────────────
Issue                 ●     ●     ●
Complete              ●     ●     ●
                     ─────────────────────
Issue                              ●
Complete                           ●
                     ───────────────────── [Transaction Committed]
Issue                                         ●      ●
Complete                                      ●      ●
─────────────────────────────────────────────────────────────
```

#### 📊 Metadata Journaling Timeline

```
Phase                Journal         File System
                     TxB  Meta  TxE  Data  Metadata
──────────────────────────────────────────────────────
Issue                 ●     ●         ●
Complete              ●     ●         ●
                     ───────────────────────
Issue                       ●
Complete                    ●
                     ─────────────── [Transaction Committed]
Issue                                  ●
Complete                               ●
──────────────────────────────────────────────────────
```

**Key Differences:**
- Data journaling: Data in journal, then checkpointed
- Metadata journaling: Data written directly, before metadata commits

> **💡 Insight**
>
> Horizontal dashed lines show **write barriers**—ordering points that must be enforced. Modern file systems use explicit barrier commands rather than waiting for each write individually.

---

## 6. Other Approaches

### 6.1. Soft Updates

**In plain English:** Instead of logging changes, carefully order every write so the disk is never in an inconsistent state—like updating a spreadsheet one cell at a time in the perfect sequence.

**In technical terms:** Soft Updates carefully orders all writes to ensure on-disk structures are never inconsistent. For example, write pointed-to data blocks before inodes that point to them.

**Advantages:**
- No journal overhead
- Fast normal operation

**Disadvantages:**
- Complex implementation (requires deep file system knowledge)
- Must track ordering constraints for every structure
- Can't easily be layered on existing file systems

**Example Ordering Rules:**
```
1. Write data block before inode pointing to it
2. Write inode before directory entry referencing it
3. Write directory entry before updating directory inode
4. Clear bitmap bits after all pointers are removed
```

### 6.2. Copy-On-Write

**In plain English:** Never modify existing data. Always write changes to new locations, then atomically flip a pointer to make the new version active—like saving a new copy of a document instead of editing the original.

**In technical terms:** Copy-On-Write (COW) file systems never overwrite data in place. They write updates to unused locations, then atomically update the root pointer. Used in ZFS, Btrfs, and Log-Structured File Systems (LFS).

**How It Works:**
```
1. Write new data blocks to unused location
2. Write new metadata pointing to new data
3. Atomically update root pointer
4. Old version is now garbage (or kept for snapshots)
```

**Advantages:**
- Naturally crash-consistent (atomic root switch)
- Easy snapshots (keep old root pointers)
- No write-twice overhead

**Disadvantages:**
- Fragmentation over time
- Garbage collection needed
- Random writes become sequential (can be good or bad)

> **💡 Insight**
>
> LFS (Chapter 43) was an early COW file system. Modern systems like ZFS and Btrfs build on these ideas, adding features like checksums, compression, and native RAID support.

### 6.3. Modern Techniques

#### 🚀 Backpointer-Based Consistency (BBC)

**Concept:** Add back pointers to every block. During access, verify forward and back pointers match.

```
Traditional:   Inode → Data Block
BBC:          Inode ⇄ Data Block
              (bidirectional reference)
```

**Verification:**
```python
def read_block(inode, block_num):
    data_block = read_disk(inode.pointers[block_num])
    if data_block.back_pointer == inode.number:
        return data_block  # Consistent!
    else:
        return ERROR       # Inconsistent, avoid garbage
```

**Benefits:**
- No write ordering required
- Lazy consistency checking
- Detect inconsistencies on access

#### ⚡ Optimistic Crash Consistency

**Concept:** Issue writes in parallel without waiting, use checksums to detect incomplete transactions.

**Approach:**
```
1. Issue all writes at once (no barriers)
2. Include checksum in transaction markers
3. During recovery, verify checksums
4. Discard transactions with checksum mismatches
```

**Benefits:**
- 10x performance improvement for some workloads
- Fewer disk stalls

**Requirements:**
- Requires disk interface changes
- Must trust disk behavior
- Needs careful checksum design

#### 🔧 Optimized Log Writes

**Problem:** Original protocol waits for TxB and data before writing TxE (extra rotation).

**Solution (Linux ext4):**
```
1. Include checksum in TxB and TxE
2. Write entire transaction at once (including TxE)
3. During recovery:
   - Compute checksum of transaction contents
   - Compare with stored checksum
   - Discard if mismatch (incomplete write)
```

**Benefits:**
- Eliminates extra rotation wait
- Faster common-case performance
- More reliable (checksums catch corruption)

---

## 7. Summary

### 🎯 Key Takeaways

**The Problem:**
- File systems must survive crashes during multi-block updates
- Disks service one write at a time, leaving inconsistent states
- Solutions must balance consistency, performance, and recovery time

**Solution Evolution:**

| Approach | Recovery Time | Write Overhead | Complexity |
|----------|---------------|----------------|------------|
| FSCK | O(disk size) - Hours | None | Medium |
| Data Journaling | O(log size) - Seconds | 2x writes | Low |
| Metadata Journaling | O(log size) - Seconds | ~1x writes | Medium |
| Soft Updates | O(disk size) | None | High |
| Copy-On-Write | O(log size) | 1x writes | Medium |

**Modern Practice:**

Most file systems use **ordered metadata journaling** (ext3/ext4 default):
- Fast recovery (seconds, not hours)
- Reasonable write overhead (metadata only, doubled)
- Metadata always consistent
- Data consistency depends on ordering

**Core Principles:**

1. **Atomicity through logging:** Write intentions before changes
2. **Ordering matters:** Pointed-to before pointer
3. **Idempotence enables recovery:** Safe to replay operations
4. **Batching reduces overhead:** Group updates into transactions
5. **Details are critical:** Block reuse, checksums, barriers all matter

> **💡 Final Insight**
>
> Crash consistency is solved, but ongoing research continues to improve performance and guarantees. The tension between consistency, performance, and simplicity drives innovation in file system design.

### 🔍 Implementation Choices

**For Applications:**
- Use `fsync()` for critical data (forces commit)
- Understand your file system's guarantees
- Test recovery scenarios

**For File Systems:**
- Choose journaling mode based on workload
- Data mode: Strongest guarantees, highest overhead
- Ordered mode: Balanced approach, most popular
- Unordered mode: Fastest, metadata-only guarantees

**Current Research:**
- Better guarantees for user data
- Reducing journal overhead
- Hardware support for atomicity
- Application-level crash consistency

---

**Previous:** [Chapter 7: Crash Consistency](chapter7-crash-consistency.md) | **Next:** [Chapter 9: Log-Structured File System](chapter9-log-structured-file-system.md)
