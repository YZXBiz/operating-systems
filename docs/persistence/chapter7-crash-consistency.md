# ⚠️ Chapter 7: Crash Consistency - FSCK and Journaling

**In plain English:** When your computer suddenly loses power while saving a file, how does the file system ensure your data structures don't become corrupted?

**In technical terms:** The crash-consistency problem addresses how file systems maintain data structure integrity despite power losses or system crashes during multi-step disk updates.

**Why it matters:** Without crash consistency mechanisms, a single power outage could corrupt your entire file system, making data unrecoverable. This problem affects every computer system that stores data persistently.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Understanding the Crash-Consistency Problem](#2-understanding-the-crash-consistency-problem)
   - 2.1. [A Detailed Example](#21-a-detailed-example)
   - 2.2. [Crash Scenarios](#22-crash-scenarios)
3. [Solution #1: File System Checker (fsck)](#3-solution-1-file-system-checker-fsck)
   - 3.1. [How fsck Works](#31-how-fsck-works)
   - 3.2. [Limitations of fsck](#32-limitations-of-fsck)
4. [Solution #2: Journaling (Write-Ahead Logging)](#4-solution-2-journaling-write-ahead-logging)
   - 4.1. [Basic Journaling Concepts](#41-basic-journaling-concepts)
   - 4.2. [Data Journaling Protocol](#42-data-journaling-protocol)
   - 4.3. [Recovery Process](#43-recovery-process)
   - 4.4. [Optimizations](#44-optimizations)
   - 4.5. [Metadata Journaling](#45-metadata-journaling)
   - 4.6. [Block Reuse Challenges](#46-block-reuse-challenges)
5. [Solution #3: Other Approaches](#5-solution-3-other-approaches)
6. [Summary](#6-summary)

---

## 1. Introduction

File systems manage persistent data structures that must survive across power losses and system crashes. Unlike in-memory data structures that disappear when a program terminates, file system structures on disk must maintain consistency over the long term.

> **💡 Insight**
>
> The fundamental challenge: disk writes happen one at a time, but file system updates often require multiple related writes. A crash between these writes leaves the system in an inconsistent state.

### 🎯 The Core Challenge

**THE CRUX: HOW TO UPDATE THE DISK DESPITE CRASHES**

The system may crash or lose power between any two writes, leaving on-disk state only partially updated. After the crash, the system must mount the file system again to access files. How do we ensure the file system keeps the on-disk image in a reasonable state despite crashes at arbitrary points?

**Key characteristics of the problem:**
- Disk services only one request at a time
- Crashes can occur between any two writes
- Partial updates create inconsistent states
- File system must be mountable after recovery

---

## 2. Understanding the Crash-Consistency Problem

### 2.1. A Detailed Example

Let's examine a concrete scenario: appending a single data block to an existing file.

**The workload:**
```c
// User-level operation
open(file);
lseek(file, 0, SEEK_END);    // Move to end of file
write(file, data, 4096);      // Write 4KB block
close(file);
```

**Initial file system state:**

```
Inode Bitmap | Data Bitmap | Inodes | Data Blocks
   [1 bit]   |   [1 bit]   |  I[v1] | Da
```

**Initial inode (I[v1]):**
```
owner       : remzi
permissions : read-write
size        : 1
pointer     : 4        (points to data block Da)
pointer     : null
pointer     : null
pointer     : null
```

**Required updates for append operation:**

The append requires writing three structures to disk:

1. **Updated inode (I[v2])** - points to new block, records larger size
2. **New data block (Db)** - contains the appended data
3. **Updated data bitmap (B[v2])** - marks new block as allocated

**Updated inode (I[v2]):**
```
owner       : remzi
permissions : read-write
size        : 2              ← Size increased
pointer     : 4
pointer     : 5              ← New pointer added
pointer     : null
pointer     : null
```

**Updated data bitmap (B[v2]):**
```
Binary: 00001100             ← Block 5 now allocated
```

**Desired final state:**
```
Inode Bitmap | Data Bitmap | Inodes | Data Blocks
             |   [B[v2]]   |  I[v2] | Da | Db
```

### 2.2. Crash Scenarios

#### 📊 Single-Write Crash Scenarios

If only one of the three writes completes before a crash:

**Scenario 1: Only data block (Db) written**
- ✅ **Result:** No corruption
- **State:** Data exists on disk but no metadata references it
- **Effect:** Write appears never to have occurred
- ⚠️ **Note:** Data is lost, but file system remains consistent

**Scenario 2: Only inode (I[v2]) written**
- ❌ **Result:** Corruption
- **State:** Inode points to disk address 5, but Db not written there
- **Problem 1:** Reading file returns garbage data
- **Problem 2:** File system inconsistency (bitmap says block 5 is free, inode says it's allocated)

**Scenario 3: Only bitmap (B[v2]) written**
- ❌ **Result:** Inconsistency
- **State:** Bitmap marks block 5 as allocated, but no inode references it
- **Problem:** Space leak - block 5 can never be used again

#### 📊 Two-Write Crash Scenarios

If two of the three writes complete before a crash:

**Scenario 4: Inode (I[v2]) and bitmap (B[v2]) written**
- ⚠️ **Result:** Metadata consistent, data corrupted
- **State:** File system metadata looks correct
- **Problem:** Block 5 contains garbage instead of intended data

**Scenario 5: Inode (I[v2]) and data (Db) written**
- ❌ **Result:** Inconsistency
- **State:** Correct data on disk, inode points to it
- **Problem:** Bitmap inconsistency (says block 5 is free, but it's in use)

**Scenario 6: Bitmap (B[v2]) and data (Db) written**
- ❌ **Result:** Inconsistency
- **State:** Data written, bitmap marks it allocated
- **Problem:** No inode points to the data - orphaned block

> **💡 Insight**
>
> The crash-consistency problem is fundamentally about atomicity. We need to move from one consistent state to another atomically, but the disk only commits one write at a time. This creates a window of vulnerability during every multi-write operation.

---

## 3. Solution #1: File System Checker (fsck)

### 🔧 Overview

Early file systems adopted a **lazy approach**: let inconsistencies happen during crashes, then fix them later during reboot. The tool that performs this repair is `fsck` (file system checker).

**Key characteristics:**
- Runs before file system is mounted
- Assumes no other file system activity during operation
- Cannot fix all problems (e.g., inode pointing to garbage)
- Goal: Make file system metadata internally consistent

### 3.1. How fsck Works

fsck operates in multiple phases, scanning disk structures systematically:

#### 🔍 Phase 1: Superblock Check

**Purpose:** Verify superblock integrity

**Actions:**
- Sanity check file system size vs. allocated blocks
- Verify superblock looks reasonable
- Use alternate superblock copy if primary is corrupt

**Example check:**
```
if (superblock.fs_size < superblock.allocated_blocks) {
    // Superblock is corrupt
    use_alternate_superblock();
}
```

#### 🔍 Phase 2: Free Blocks Check

**Purpose:** Rebuild allocation bitmaps

**Actions:**
- Scan all inodes, indirect blocks, double indirect blocks
- Build understanding of which blocks are allocated
- Produce correct allocation bitmaps
- Resolve inconsistencies by trusting inode information

**Logic:**
```
1. Scan all inodes → determine which blocks they reference
2. Build correct bitmap from inode data
3. Compare with existing bitmap
4. Update bitmap if inconsistencies found
5. Repeat for inode bitmaps
```

#### 🔍 Phase 3: Inode State Check

**Purpose:** Verify each inode's integrity

**Actions:**
- Check each allocated inode for corruption
- Verify valid type field (regular file, directory, symlink)
- Clear suspect inodes that can't be fixed
- Update inode bitmap accordingly

**Valid inode types:**
- Regular file
- Directory
- Symbolic link
- Block device
- Character device
- FIFO (named pipe)
- Socket

#### 🔍 Phase 4: Inode Links Check

**Purpose:** Verify link counts

**Explanation:**
- Link count = number of directories referencing a file
- fsck scans entire directory tree from root
- Builds its own link count for every file/directory

**Actions:**
- Compare calculated link count with inode's link count
- Fix count within inode if mismatch found
- Move orphaned allocated inodes to `lost+found/` directory

**Example scenario:**
```
File inode says:  link_count = 2
fsck calculates:  link_count = 1
Action: Update inode link_count to 1
```

#### 🔍 Phase 5: Duplicates Check

**Purpose:** Find duplicate block pointers

**Problem:** Two inodes reference the same block

**Actions:**
- Clear obviously bad inode
- Or copy the block, giving each inode its own copy

#### 🔍 Phase 6: Bad Blocks Check

**Purpose:** Identify invalid block pointers

**Definition of "bad pointer":**
- Points outside valid range
- Address exceeds partition size
- References superblock or other reserved areas

**Action:** Clear the pointer from inode or indirect block

#### 🔍 Phase 7: Directory Checks

**Purpose:** Verify directory structure integrity

**Directory-specific checks:**
- "." and ".." are first entries
- Every referenced inode is allocated
- No directory is linked more than once in hierarchy
- Directory entries are properly formatted

**Example directory validation:**
```
Directory entry format:
[inode_number] [entry_length] [name_length] [name]

Checks:
- inode_number exists and is allocated
- entry_length is valid
- name_length matches actual name
```

### 3.2. Limitations of fsck

#### ⚠️ Performance Problems

**The fundamental issue:** Too slow for modern systems

**Why it's slow:**
- Must scan entire disk volume
- Must read entire directory tree
- Recovery time proportional to disk size

**Real-world impact:**
```
Small disk (100 GB):   Minutes to scan
Large disk (10 TB):    Hours to scan
RAID array (100 TB):   Days to scan
```

> **💡 Insight**
>
> As disks grew in capacity and RAIDs grew in popularity, fsck performance became prohibitive. The tool's approach is fundamentally inefficient: scanning an entire house to find keys dropped in one room.

#### 🧠 Philosophical Problem

**The inefficiency analogy:**
- **Problem:** Three blocks need updating
- **fsck approach:** Scan entire disk to fix those three blocks
- **Analogy:** Drop keys in bedroom → search entire house starting from basement

**Better approach:** Remember where the update was happening, fix only that area

---

## 4. Solution #2: Journaling (Write-Ahead Logging)

### 4.1. Basic Journaling Concepts

#### 🎨 The Core Idea

**Borrowed from database systems:** Write-ahead logging

**In file systems:** Called journaling for historical reasons

**Basic principle:**
1. Before overwriting structures in place
2. Write a note describing what you're about to do
3. Write the note to a well-known location (the journal/log)
4. If crash occurs, read the note and retry the update

**Benefits:**
- Know exactly what to fix after crash
- No need to scan entire disk
- Recovery time proportional to log size, not disk size

> **💡 Insight**
>
> Journaling trades a small amount of extra work during normal operation (writing to the journal) for dramatically faster recovery. Instead of O(disk-size) recovery, we get O(log-size) recovery.

#### 📋 File System Structure Changes

**Original ext2 file system (no journaling):**
```
[Super] [Group 0] [Group 1] ... [Group N]
```

**ext3 file system with journaling:**
```
[Super] [Journal] [Group 0] [Group 1] ... [Group N]
```

**Journal location options:**
- Within the same partition (common)
- On a separate device (for performance)
- As a file within the file system

### 4.2. Data Journaling Protocol

#### 📝 Writing to the Journal

Using our canonical example (append operation updating I[v2], B[v2], Db):

**Journal structure:**
```
[TxB] [I[v2]] [B[v2]] [Db] [TxE]
  ↑      ↑       ↑      ↑     ↑
  |      |       |      |     |
Begin  Inode  Bitmap  Data   End
```

**Transaction Begin Block (TxB):**
- Information about the update
- Final addresses of blocks (I[v2], B[v2], Db)
- Transaction identifier (TID)

**Middle blocks (I[v2], B[v2], Db):**
- Exact physical contents of blocks
- This is **physical logging** (actual block contents)
- Alternative: **logical logging** (compact representation)

**Transaction End Block (TxE):**
- Marker indicating transaction completion
- Contains matching TID

#### ⚡ The Write Protocol

**Initial protocol (simplified):**

**Step 1: Journal Write**
- Write transaction to log (TxB, data, metadata, TxE)
- Wait for writes to complete

**Step 2: Checkpoint**
- Write pending data and metadata to final locations
- If successful, file system is updated

**Problem with simple approach:**

If we write all five blocks simultaneously, disk internal scheduling may complete them in any order:

```
Possible disk ordering:
Write order sent:    [TxB] [I[v2]] [B[v2]] [Db] [TxE]
Actual completion:   [TxB] [I[v2]] [B[v2]] [TxE] [Db]  ← Db written last
```

**Danger:** If power lost after TxE but before Db:
```
Journal contains:  [TxB][I[v2]][B[v2]][??][TxE]
                                         ↑
                                      garbage
```

**Why this is dangerous:**
- Transaction looks valid (has matching TxB and TxE)
- During recovery, will replay transaction
- Will copy garbage to Db location
- Could corrupt critical structures (e.g., superblock)

#### ✅ Safe Write Protocol

**Solution:** Write in two steps with ordering

**Step 1: Journal Write (excluding TxE)**
```
[TxB] [I[v2]] [B[v2]] [Db]
```
- Issue all blocks except TxE
- Wait for completion

**Step 2: Journal Commit**
```
[TxB] [I[v2]] [B[v2]] [Db] [TxE]
```
- Issue TxE block only
- Wait for completion
- Transaction now committed

**Step 3: Checkpoint**
- Write I[v2], B[v2], Db to final locations
- File system now updated

#### 🔒 Atomicity Guarantee

**Disk guarantee:** Any 512-byte write is atomic
- Either the entire write happens
- Or none of it happens
- Never half-written

**Implementation:** Make TxE a single 512-byte block

**Final protocol summary:**

1. **Journal write:** Write contents (TxB, metadata, data) to log; wait for completion
2. **Journal commit:** Write TxE to log; wait for completion; transaction committed
3. **Checkpoint:** Write metadata and data to final locations

#### 🚀 Write Barriers and Ordering

**Old approach (simple but slow):**
```c
write_to_disk(block_A);
wait_for_completion(block_A);
write_to_disk(block_B);  // Guaranteed to be after A
```

**Modern complication:** Disk write caches

**Write caching problem:**
- Disk reports write complete when in cache (not on disk)
- Called "immediate reporting"
- Subsequent writes may reach disk out of order

**Solutions:**

**Option 1:** Disable write buffering
- Slower but safe
- Loses performance benefits of caching

**Option 2:** Explicit write barriers
```c
write_to_disk(block_A);
write_barrier();  // Ensure A completes before any later writes
write_to_disk(block_B);
```

> **⚠️ Warning**
>
> Recent research shows some disk manufacturers ignore write-barrier requests to appear faster. This risks data corruption. As Kahan said, "the fast almost always beats out the slow, even if the fast is wrong."

### 4.3. Recovery Process

#### 🔄 How Recovery Works

**Crash timing scenarios:**

**Scenario 1: Crash before journal commit**
- Transaction not safely in log (TxE not written)
- **Action:** Skip the pending update
- **Result:** As if update never happened

**Scenario 2: Crash after journal commit, before checkpoint**
- Transaction fully in log (TxE written)
- Checkpoint incomplete or not started
- **Action:** Replay the transaction

**Recovery process:**
1. Scan the journal
2. Look for committed transactions (those with TxE)
3. Replay committed transactions in order
4. Write blocks to their final locations
5. Mount file system

**This is called redo logging.**

#### ✅ Recovery Safety Properties

**Idempotent operations:**
- Safe to replay transactions multiple times
- Crash during checkpoint? Replay again during recovery
- Some updates may be redundant, but that's fine

**Why redundant writes are acceptable:**
- Recovery is rare (only after crashes)
- Correctness more important than recovery performance
- Few redundant writes won't hurt

### 4.4. Optimizations

#### 🎯 Batching Log Updates

**Problem:** Excessive disk traffic without batching

**Example scenario:**
```c
create("file1");  // In directory /foo
create("file2");  // In directory /foo
```

**Required updates per file creation:**
- Inode bitmap (allocate new inode)
- New file inode
- Parent directory data (new directory entry)
- Parent directory inode (updated modification time)

**Without batching:**
- Each file creation = separate transaction
- Same blocks written multiple times
- Parent directory structures written twice
- Inefficient use of disk bandwidth

**With batching (ext3 approach):**

```
Buffer updates in memory:
- Mark blocks as dirty
- Add to current global transaction
- Don't commit immediately

After timeout (e.g., 5 seconds):
- Single transaction commits all updates
- Parent directory written once
- Shared structures written once
```

**Benefits:**
- Reduced disk traffic
- Better performance for bursty workloads
- Single fsync() can commit multiple operations

#### 🔄 Making the Log Finite

**Problem:** Log fills up over time

```
[Tx1][Tx2][Tx3][Tx4][Tx5]... → Log full!
```

**Consequences of full log:**

1. **Longer recovery time**
   - Must replay all transactions
   - Recovery time = O(log size)

2. **System becomes unusable**
   - No space for new transactions
   - File system can't commit updates
   - System effectively frozen

**Solution:** Circular log (reuse log space)

**Implementation:**

```
Journal structure:
[Super][Tx1][Tx2][Tx3][Tx4][Tx5]...
   ↑
   └─ Tracks oldest and newest uncheckpointed transactions
```

**Journal superblock contains:**
- Oldest uncheckpointed transaction
- Newest uncheckpointed transaction
- All other space is free

**After checkpointing:**
1. Transaction's data written to final locations
2. Mark transaction free in journal superblock
3. Space becomes available for reuse

**Complete protocol with freeing:**

1. **Journal write:** Write transaction to log; wait for completion
2. **Journal commit:** Write TxE to log; wait for completion
3. **Checkpoint:** Write contents to final locations
4. **Free:** Mark transaction free in journal superblock

#### ⚡ Optimizing Log Writes (Transaction Checksums)

**Original problem:**

```
Step 1: Write [TxB][I[v2]][B[v2]][Db]
        Wait for completion  ← Extra disk rotation wasted

Step 2: Write [TxE]
```

**Cost:** Extra disk rotation between steps

**Solution (Prabhakaran et al.):**

Include checksum in TxB and TxE blocks:

```c
TxB structure:
- TID
- Block addresses
- Checksum of all transaction data

TxE structure:
- TID
- Checksum of all transaction data (duplicate)
```

**New protocol:**
1. Write entire transaction at once: [TxB][I[v2]][B[v2]][Db][TxE]
2. No wait between TxB and TxE

**During recovery:**
```c
if (compute_checksum(transaction) == TxB.checksum) {
    // Transaction is valid, replay it
    replay(transaction);
} else {
    // Crash during write, discard update
    skip(transaction);
}
```

**Benefits:**
- Faster writes (no extra rotation)
- Increased reliability (corruption detection)
- Adopted in Linux ext4
- Shipped on millions of machines (including Android)

> **🎓 Learning Point**
>
> This optimization demonstrates how small protocol changes can have massive real-world impact. A simple checksum addition improved performance and reliability for millions of devices worldwide.

### 4.5. Metadata Journaling

#### 📊 The Performance Problem with Data Journaling

**Data journaling cost:** Every data block written twice
1. Once to the journal
2. Once to final location

**Impact on sequential writes:**
```
Peak bandwidth:        100 MB/s
With data journaling:   50 MB/s  (half speed)
```

**Additional overhead:** Seek between journal and final location

#### 🎯 Metadata-Only Journaling

**Also called:** Ordered journaling

**Key difference:** User data NOT written to journal

**Journal contains only:**
```
[TxB] [I[v2]] [B[v2]] [TxE]
        ↑       ↑
     metadata only
```

**Data block (Db):** Written directly to final location (only once)

**Benefit:** Dramatically reduced I/O load

#### 📝 Write Ordering for Metadata Journaling

**Critical question:** When to write data blocks?

**Wrong approach:** Write Db after transaction commits

**Problem scenario:**
1. Transaction commits: [TxB][I[v2]][B[v2]][TxE]
2. Checkpoint I[v2] and B[v2]
3. Crash before Db written
4. During recovery: Replay transaction
5. **Result:** I[v2] points to garbage data!

**File system state:**
- Metadata is consistent ✅
- But I[v2] points to whatever was in Db's location ❌

**Correct approach:** Write data BEFORE metadata journal

**Safe protocol:**

**Step 1: Data Write**
```
Write Db to final location
(Optional: wait for completion)
```

**Step 2: Journal Metadata Write**
```
Write [TxB][I[v2]][B[v2]] to log
Wait for completion
```

**Step 3: Journal Commit**
```
Write [TxE] to log
Wait for completion
Transaction committed
```

**Step 4: Checkpoint Metadata**
```
Write I[v2] and B[v2] to final locations
```

**Step 5: Free**
```
Mark transaction free in journal superblock
```

> **💡 Insight**
>
> The golden rule of crash consistency: "Write the pointed-to object before the object that points to it." This principle ensures pointers never reference garbage data.

#### ⚡ Performance Optimization

**Relaxed ordering:** Steps 1 and 2 can be concurrent

**Safe approach:**
```
Issue concurrently:
- Data write (Db)
- Transaction begin (TxB)
- Metadata writes (I[v2], B[v2])

Wait for all to complete

Then issue:
- Transaction commit (TxE)
```

**Only requirement:** Steps 1 and 2 complete before Step 3

#### 🔧 Journaling Modes Comparison

| Mode | Data in Journal | Metadata in Journal | Data Consistency | Performance |
|------|----------------|-------------------|-----------------|-------------|
| **Data** | ✅ Yes | ✅ Yes | Strong | Slow (2x writes) |
| **Ordered** | ❌ No | ✅ Yes | Moderate | Fast |
| **Unordered** | ❌ No | ✅ Yes | Weak | Fastest |

**Popular implementations:**
- **Linux ext3:** All three modes available
- **Windows NTFS:** Metadata journaling
- **SGI XFS:** Metadata journaling
- **Linux ext4:** All three modes available

**Default choice:** Most systems use ordered/metadata journaling

### 4.6. Block Reuse Challenges

#### 🐛 The Block Reuse Problem

**Quote from Stephen Tweedie (ext3 developer):**
> "What's the hideous part of the entire system? ... It's deleting files. Everything to do with delete is hairy. Everything to do with delete... you have nightmares around what happens if blocks get deleted and then reallocated."

#### 📝 Example Scenario

**Step 1: Create directory `foo`**
```
Journal: [TxB][I[foo], ptr:1000][D[foo], addr:1000][TxE]
                    ↑                ↑
              inode points      directory data
              to block 1000     in block 1000
```

**Step 2: Delete directory `foo`**
- Frees block 1000 for reuse
- Journal still contains old transaction

**Step 3: Create file `foobar`**
- Reuses block 1000 for file data (not journaled in metadata mode)
```
Journal: [TxB][I[foo], ptr:1000][D[foo], addr:1000][TxE]
         [TxB][I[foobar], ptr:1000][TxE]
                          ↑
                    points to block 1000
```

**Step 4: Crash and recovery**
- Recovery replays all transactions in journal
- Replays: Write old `D[foo]` directory data to block 1000
- **Result:** Overwrites `foobar` file data with old directory contents!

**This is incorrect and surprising for users.**

#### ✅ Solutions

**Solution 1: Delayed reuse**
- Never reuse blocks until delete is checkpointed
- Block freed from journal before reallocation
- Simple but may delay reuse unnecessarily

**Solution 2: Revoke records (ext3 approach)**

**Revoke record:** Special journal entry

**Process:**
1. When deleting directory, write revoke record to journal
2. Revoke record says: "Don't replay data for block 1000"

**Recovery with revokes:**
```c
// First pass: Scan for revoke records
for (transaction in journal) {
    if (transaction.contains_revoke(block_num)) {
        mark_revoked(block_num);
    }
}

// Second pass: Replay transactions
for (transaction in journal) {
    for (block in transaction) {
        if (!is_revoked(block.address)) {
            replay(block);  // Safe to replay
        } else {
            skip(block);     // Skip revoked blocks
        }
    }
}
```

**Benefits:**
- Blocks can be reused immediately
- Safe recovery guaranteed
- No false replays of old data

#### 🎨 Protocol Timeline Visualizations

**Data Journaling Timeline:**

```
Time
 ↓
Issue:  [TxB][Data][Metadata]    ← Can issue together
 |
 |      -------------------- Wait barrier
 |
Complete: [TxB][Data][Metadata]  ← May complete in any order
 |
 |      -------------------- Wait barrier
 |
Issue:  [TxE]                    ← Must wait for above
 |
 |      -------------------- Wait barrier
 |
Complete: [TxE]
 |
 |      -------------------- Wait barrier
 |
Issue:  [Data][Metadata]        ← Checkpoint
 |
Complete: [Data][Metadata]
```

**Metadata Journaling Timeline:**

```
Time
 ↓
Issue:  [Data][TxB][Metadata]   ← Can issue together
 |
 |      -------------------- Wait barrier
 |
Complete: [Data][TxB][Metadata]  ← May complete in any order
 |
 |      -------------------- Wait barrier
 |
Issue:  [TxE]                    ← Must wait for above
 |
 |      -------------------- Wait barrier
 |
Complete: [TxE]
 |
 |      -------------------- Wait barrier
 |
Issue:  [Metadata][Data]        ← Checkpoint
 |
Complete: [Metadata][Data]
```

**Key points:**
- Horizontal dashed lines = ordering requirements
- Within a section, operations can complete in any order
- Ordering enforced only at wait barriers

---

## 5. Solution #3: Other Approaches

Beyond fsck and journaling, several alternative approaches exist:

### 🔧 Soft Updates

**Developed by:** Ganger and Patt (1994)

**Core idea:** Carefully order all writes to ensure on-disk structures never become inconsistent

**Key principle:**
- Write pointed-to blocks before pointers
- Example: Write data block before inode that points to it
- Inode never points to garbage

**Ordering rules apply to:**
- Data blocks and inodes
- Directory entries and inodes
- Bitmaps and blocks

**Advantages:**
- No journal needed
- No double writes
- Consistency maintained through ordering

**Disadvantages:**
- Complex implementation
- Requires intimate knowledge of file system structures
- More intricate than journaling layer
- Harder to maintain and verify

### 🐮 Copy-on-Write (COW)

**Used by:** Sun's ZFS, log-structured file systems (LFS)

**Core idea:** Never overwrite data in place

**Process:**
1. Write updates to previously unused locations
2. After updates complete, flip root pointer
3. Root pointer atomically points to new structures

**Simple COW example:**
```
Before:
Root → [Old inode] → [Old data]

After:
Root → [New inode] → [New data]
       [Old inode] → [Old data]  (unreachable)
```

**Benefits:**
- Consistency straightforward (atomic root pointer update)
- Old versions preserved (snapshots essentially free)
- No complex ordering requirements

**Characteristics:**
- Write to new locations only
- Old data garbage collected later
- Root structure updated atomically

### 🔗 Backpointer-Based Consistency (BBC)

**Developed at:** University of Wisconsin

**Core idea:** Add backward pointers to every block

**Structure:**
```
Inode → Data block
  ↖         ↙
   Back pointer
```

**Each data block contains:**
- Actual data
- Back pointer to owning inode

**Consistency check:**
```c
// When accessing file
inode = get_inode(file);
block = get_block(inode.pointer);

if (block.back_pointer == inode.address) {
    // Consistent: forward and backward pointers match
    return block.data;
} else {
    // Inconsistent: pointers don't match
    return ERROR;
}
```

**Properties:**
- No write ordering enforced
- Lazy consistency checking
- Check happens during access, not during recovery
- Inconsistent files return errors

**Benefits:**
- No journal overhead
- No ordering overhead
- Simple implementation

**Tradeoff:**
- Errors discovered late (on access)
- Extra space for back pointers

### ⚡ Optimistic Crash Consistency

**Developed at:** University of Wisconsin (Chidambaram et al.)

**Goal:** Reduce number of times journal protocol waits for disk

**Technique:** Generalized transaction checksum

**Approach:**
1. Issue as many writes as possible concurrently
2. Use checksums to detect inconsistencies
3. During recovery, validate with checksums
4. Discard inconsistent transactions

**Benefits:**
- Order of magnitude performance improvement for some workloads
- More reliable (checksums detect corruption)

**Requirements:**
- Slightly different disk interface
- More sophisticated recovery

**Status:**
- Research prototype
- Demonstrates potential for future systems

---

## 6. Summary

### 🎯 Key Takeaways

**The crash-consistency problem:**
- File systems update multiple structures atomically
- Disk services one write at a time
- Crashes create window of inconsistency
- Solution required for every persistent storage system

**Three major approaches:**

#### 1️⃣ File System Checker (fsck)
- **Strategy:** Fix problems after crash
- **Speed:** O(disk-size) recovery
- **Status:** Too slow for modern systems

#### 2️⃣ Journaling
- **Strategy:** Write-ahead logging
- **Speed:** O(log-size) recovery
- **Variants:**
  - Data journaling: Journal everything (slow, strong guarantees)
  - Metadata journaling: Journal metadata only (fast, moderate guarantees)
  - Unordered: No ordering guarantees (fastest, weak guarantees)
- **Status:** Most popular modern approach

#### 3️⃣ Alternative Approaches
- **Soft Updates:** Careful write ordering
- **Copy-on-Write:** Never overwrite in place
- **Backpointer-Based:** Lazy consistency checking
- **Optimistic:** Minimize synchronous waits

### 💡 Core Principles

**Golden rules of crash consistency:**
1. Write pointed-to objects before pointers
2. Ensure atomic transitions between consistent states
3. Enable fast recovery (don't scan entire disk)
4. Balance performance vs. consistency guarantees

**Journaling insights:**
- Trades small overhead during updates for fast recovery
- Metadata journaling provides best performance/consistency balance
- Checksums enable optimization without sacrificing safety
- Circular log allows infinite journal reuse

### 🔮 Future Directions

**Current limitations:**
- User data guarantees still imperfect
- Research ongoing in this area
- Different workloads need different tradeoffs

**Modern systems:**
- Most use journaling (ext3, ext4, NTFS, XFS)
- COW gaining popularity (ZFS, Btrfs)
- Hybrid approaches emerging

> **🎓 Final Insight**
>
> Crash consistency is about managing the fundamental tension between atomicity requirements and physical disk constraints. Every solution makes different tradeoffs between performance during normal operation and guarantees during recovery.

---

**Previous:** [Chapter 6: Locality and Fast File System](chapter6-locality-fast-file-system.md) | **Next:** [Chapter 8: Journaling](chapter8-journaling.md)
