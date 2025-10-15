# ⚡ Chapter 10: Flash-Based SSDs

**A Complete Guide to Solid-State Storage Technology**

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Understanding Flash Storage](#2-understanding-flash-storage)
   - 2.1. [Storing a Single Bit](#21-storing-a-single-bit)
   - 2.2. [From Bits to Banks and Planes](#22-from-bits-to-banks-and-planes)
3. [Basic Flash Operations](#3-basic-flash-operations)
   - 3.1. [The Three Core Operations](#31-the-three-core-operations)
   - 3.2. [A Detailed Write Example](#32-a-detailed-write-example)
4. [Flash Performance and Reliability](#4-flash-performance-and-reliability)
   - 4.1. [Performance Characteristics](#41-performance-characteristics)
   - 4.2. [Reliability and Wear Out](#42-reliability-and-wear-out)
5. [Building an SSD: The Flash Translation Layer](#5-building-an-ssd-the-flash-translation-layer)
   - 5.1. [Why a Direct-Mapped Approach Fails](#51-why-a-direct-mapped-approach-fails)
   - 5.2. [Log-Structured FTL](#52-log-structured-ftl)
6. [Garbage Collection](#6-garbage-collection)
   - 6.1. [The Garbage Problem](#61-the-garbage-problem)
   - 6.2. [How Garbage Collection Works](#62-how-garbage-collection-works)
   - 6.3. [The TRIM Operation](#63-the-trim-operation)
7. [Managing Mapping Tables](#7-managing-mapping-tables)
   - 7.1. [The Mapping Table Size Problem](#71-the-mapping-table-size-problem)
   - 7.2. [Block-Based Mapping](#72-block-based-mapping)
   - 7.3. [Hybrid Mapping](#73-hybrid-mapping)
   - 7.4. [Page Mapping with Caching](#74-page-mapping-with-caching)
8. [Wear Leveling](#8-wear-leveling)
9. [SSD Performance and Cost Analysis](#9-ssd-performance-and-cost-analysis)
   - 9.1. [Performance Comparison](#91-performance-comparison)
   - 9.2. [Cost Considerations](#92-cost-considerations)
10. [Summary](#10-summary)

---

## 1. Introduction

**In plain English:** Flash storage is like memory (fast, no moving parts) but keeps your data even when power is off, unlike regular RAM which forgets everything.

**In technical terms:** Solid-state drives (SSDs) are persistent storage devices built entirely from transistors, combining the speed advantages of semiconductor technology with the data retention capabilities required for permanent storage.

**Why it matters:** After decades of mechanical hard drives dominating storage, SSDs represent a fundamental shift in how we store data - offering dramatically faster random access with no moving parts to fail.

> **💡 Insight**
>
> The transition from mechanical to solid-state storage isn't just an incremental improvement - it's a complete paradigm shift. Hard drives are mechanical marvels constrained by physics (spinning platters, moving heads). SSDs are electronic devices constrained by electron physics (charge accumulation, program/erase cycles). This fundamental difference requires completely different design approaches.

### 🎯 The Core Challenge

Flash storage introduces two unique constraints that make building SSDs challenging:

1. **Erase-before-write requirement:** To write to a page, you must first erase the entire containing block (destroying all data within)
2. **Wear out:** Repeated erase/program cycles gradually damage the flash, eventually making it unusable

**CRUX: HOW TO BUILD A FLASH-BASED SSD**

How can we build a flash-based SSD? How can we handle the expensive nature of erasing? How can we build a device that lasts a long time, given that repeated overwrite will wear the device out?

---

## 2. Understanding Flash Storage

### 2.1. Storing a Single Bit

**In plain English:** Think of a transistor as a tiny battery that can hold different charge levels. By measuring the charge, we can tell if it represents a 0, 1, or even multiple bits.

**In technical terms:** Flash chips store data by trapping electrical charge within transistors. The level of trapped charge is mapped to binary values.

#### 📊 Three Types of Flash Cells

**Single-Level Cell (SLC)**
- Stores 1 bit per transistor
- Two states: 0 or 1
- Highest performance
- Longest lifetime (100,000 P/E cycles)
- Most expensive

**Multi-Level Cell (MLC)**
- Stores 2 bits per transistor
- Four charge levels: 00, 01, 10, 11
- Medium performance
- Medium lifetime (10,000 P/E cycles)
- Moderate cost

**Triple-Level Cell (TLC)**
- Stores 3 bits per transistor
- Eight charge levels
- Lower performance
- Shorter lifetime
- Least expensive

> **📝 Note**
>
> More bits per cell means higher density and lower cost, but also reduced performance and reliability. The challenge of distinguishing between more charge levels makes TLC more error-prone and slower than SLC.

### 2.2. From Bits to Banks and Planes

**In plain English:** Just as books are organized into chapters, then paragraphs, then sentences, flash is organized into banks, blocks, and pages. You can read individual sentences (pages), but if you want to edit one, you have to rewrite the whole paragraph (block).

#### 🗂️ Flash Organization Hierarchy

```
Flash Chip
    └── Bank/Plane
            └── Erase Block (128 KB - 256 KB)
                    └── Page (1 KB - 8 KB)
```

**Key terminology (careful - these differ from disk and VM terminology):**
- **Block (Erase Block):** Large unit (128-256 KB) that must be erased together
- **Page:** Small unit (1-8 KB) that can be read or programmed individually

**Example structure:**

```
Block 0          Block 1          Block 2
┌────────┐      ┌────────┐      ┌────────┐
│ Page 00│      │ Page 04│      │ Page 08│
│ Page 01│      │ Page 05│      │ Page 09│
│ Page 02│      │ Page 06│      │ Page 10│
│ Page 03│      │ Page 07│      │ Page 11│
└────────┘      └────────┘      └────────┘
```

> ⚠️ **Terminology Warning**
>
> The terms "block" and "page" mean different things in different contexts:
> - **Flash blocks** are erase units (128-256 KB)
> - **Disk blocks** are individual sectors (512 bytes - 4 KB)
> - **Memory pages** are virtual memory units (4 KB)
>
> Always pay attention to context when reading about storage systems!

---

## 3. Basic Flash Operations

### 3.1. The Three Core Operations

Flash chips support three fundamental operations that determine everything about how SSDs work:

#### 📖 Read (a page)

**What it does:** Retrieves data from a specific page

**Performance:** Fast (~25-75 microseconds depending on cell type)

**Characteristics:**
- Random access - can read any page equally fast
- No location dependency (unlike disks with seek times)
- Does not change page state

**In plain English:** Reading is the easy part - point to any page and get the data quickly, regardless of what you read before.

#### 🧹 Erase (a block)

**What it does:** Resets an entire block, setting all bits to 1

**Performance:** Slow (1.5-4.5 milliseconds)

**Characteristics:**
- Operates on entire block, not individual pages
- Destroys all data in the block
- Must save any needed data elsewhere first
- Required before programming

**In plain English:** Erasing is like clearing an entire whiteboard before you can write on any part of it again. You can't just erase one word - you must erase the whole board, so save anything you need first!

#### ✍️ Program (a page)

**What it does:** Writes data to a page by changing some 1's to 0's

**Performance:** Medium (~200-1350 microseconds)

**Characteristics:**
- Can only change 1's to 0's (not 0's to 1's)
- Must erase block first if page was previously programmed
- Pages should be programmed in order (low to high) to minimize disturbance

**In plain English:** Programming flips switches from ON (1) to OFF (0). Once a switch is OFF, you can't turn it back ON without erasing the entire block.

#### 🔄 Page State Transitions

```
INVALID → (Erase Block) → ERASED → (Program Page) → VALID
                             ↑                           │
                             └───────(Erase Block)───────┘
```

**State machine example:**
```
Initial state:     [i][i][i][i]  (all pages invalid)

Erase() →         [E][E][E][E]  (pages now erased, programmable)

Program(page 0) → [V][E][E][E]  (page 0 now valid)

Program(page 1) → [V][V][E][E]  (page 1 now valid)

Program(page 0) → ERROR!        (cannot reprogram without erasing)

Erase() →         [E][E][E][E]  (back to erased state)
```

### 3.2. A Detailed Write Example

Let's walk through what happens when you want to update a single page in a block.

**Initial state - a valid block with data:**

```
Block 0 (4 pages, 8 bits each)
┌────────────┬────────────┬────────────┬────────────┐
│  Page 0    │  Page 1    │  Page 2    │  Page 3    │
│ 00011000   │ 11001110   │ 00000001   │ 00111111   │
│  [VALID]   │  [VALID]   │  [VALID]   │  [VALID]   │
└────────────┴────────────┴────────────┴────────────┘
```

**Goal:** Update Page 0 to contain `00000011`

**Step 1: Save the data we want to keep**

Read pages 1, 2, and 3 and store them in memory:
- Page 1: `11001110`
- Page 2: `00000001`
- Page 3: `00111111`

**Step 2: Erase the entire block**

```
Block 0 after erase
┌────────────┬────────────┬────────────┬────────────┐
│  Page 0    │  Page 1    │  Page 2    │  Page 3    │
│ 11111111   │ 11111111   │ 11111111   │ 11111111   │
│ [ERASED]   │ [ERASED]   │ [ERASED]   │ [ERASED]   │
└────────────┴────────────┴────────────┴────────────┘
```

> ⚠️ **Critical Point**
>
> Notice that ALL pages are now erased, even though we only wanted to update page 0. The previous contents of pages 1, 2, and 3 are gone! This is why we saved them in step 1.

**Step 3: Program the new page 0**

```
Block 0 after programming page 0
┌────────────┬────────────┬────────────┬────────────┐
│  Page 0    │  Page 1    │  Page 2    │  Page 3    │
│ 00000011   │ 11111111   │ 11111111   │ 11111111   │
│  [VALID]   │ [ERASED]   │ [ERASED]   │ [ERASED]   │
└────────────┴────────────┴────────────┴────────────┘
```

**The Problem:** We've updated page 0, but lost pages 1, 2, and 3!

**Why this matters:** This inefficient process is why a naive approach to building SSDs doesn't work. We need a smarter strategy - which we'll see in the Flash Translation Layer section.

#### 📋 Summary of Flash Operations

**Reading:**
✅ Fast and straightforward
✅ Random access performance
✅ No state changes

**Writing:**
❌ Complex multi-step process
❌ Must erase entire block first
❌ Destroys other data in block
❌ Repeated writes cause wear out

> **💡 Insight**
>
> The erase-before-write requirement isn't a design flaw - it's a fundamental property of how flash physics works. Building a high-performance SSD is all about hiding this complexity from the user while maximizing performance and lifetime.

---

## 4. Flash Performance and Reliability

### 4.1. Performance Characteristics

**Raw flash performance by cell type:**

| Device | Read (µs) | Program (µs) | Erase (µs) |
|--------|-----------|--------------|------------|
| SLC    | 25        | 200-300      | 1500-2000  |
| MLC    | 50        | 600-900      | ~3000      |
| TLC    | ~75       | ~900-1350    | ~4500      |

#### 🎯 Key Performance Observations

**1. Read is fastest** (10s of microseconds)
- Excellent random read performance
- Much faster than hard drives
- Comparable regardless of location

**2. Program is moderate** (100s of microseconds)
- 4-13× slower than reads
- Slower for higher density (TLC worst)
- Need parallelism for good write performance

**3. Erase is slowest** (milliseconds)
- 20-60× slower than programs
- 60-180× slower than reads
- This cost drives FTL design decisions

> **💡 Insight**
>
> The 100:1 performance ratio between erases and reads explains why modern SSDs use log-structured designs. By avoiding frequent erases, SSDs can achieve write performance that rivals or exceeds their read performance - despite erase operations being fundamentally slow.

### 4.2. Reliability and Wear Out

#### 🔧 The Wear Out Problem

**In plain English:** Each time you erase and reprogram a flash block, it's like bending a paperclip. Do it once, it's fine. Do it 10,000 times, it breaks.

**In technical terms:** Each program/erase (P/E) cycle causes a small amount of electrical charge to accumulate in the transistor. Eventually, this makes it impossible to differentiate between 0 and 1, rendering the block unusable.

**Rated lifetimes:**
- **SLC:** 100,000 P/E cycles
- **MLC:** 10,000 P/E cycles
- **TLC:** 3,000-5,000 P/E cycles (typical)

> **📝 Note**
>
> Recent research shows actual lifetimes are often much longer than manufacturer ratings. However, designs must assume rated limits for reliability.

#### 🐛 Program and Read Disturbance

**What it is:** Accessing a page can accidentally flip bits in neighboring pages

**Two types:**
- **Read disturb:** Bits flip during read operations
- **Program disturb:** Bits flip during program operations

**Mitigation:** Program pages sequentially (low to high) within each block to minimize disturbance effects.

#### ⚡ Compared to Hard Drives

**Hard drives can fail from:**
- Head crashes (physical contact with platter)
- Motor failures
- Bearing wear
- Platters degrading

**SSDs have:**
- No mechanical parts to fail
- But... predictable wear out from P/E cycles
- And... disturbance effects from neighbors

> **💡 Insight**
>
> SSDs trade mechanical unpredictability for electrical predictability. Hard drives fail randomly from many causes. SSDs wear out gradually and predictably. This predictability allows us to design systems that actively manage wear and extend device lifetime.

---

## 5. Building an SSD: The Flash Translation Layer

**In plain English:** The Flash Translation Layer (FTL) is like a translator that makes flash chips speak "hard drive language." It takes simple read/write commands and converts them into the complex erase/program operations flash requires.

**In technical terms:** The FTL transforms the standard block-device interface (read/write logical blocks) into low-level flash operations (read pages, erase blocks, program pages) while optimizing for performance and reliability.

#### 🏗️ SSD Architecture

```
┌─────────────────────────────────────────┐
│         Host Interface Logic            │
│    (Appears as standard block device)   │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│    Flash Translation Layer (FTL)        │
│  - Logical to physical mapping          │
│  - Wear leveling                        │
│  - Garbage collection                   │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│  Memory (SRAM for caching & mapping)    │
└─────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│     Flash Controller                    │
└─────────┬───────┬───────┬───────────────┘
          │       │       │
    ┌─────▼─┐ ┌──▼───┐ ┌─▼─────┐
    │Flash  │ │Flash │ │ Flash │  ...
    │Chip 0 │ │Chip 1│ │Chip 2 │
    └───────┘ └──────┘ └───────┘
```

### 5.1. Why a Direct-Mapped Approach Fails

**The naive approach:** Map logical page N directly to physical page N

**When reading logical page N:**
✅ Simple: Just read physical page N

**When writing logical page N:**
1. Read entire block containing page N
2. Erase the block
3. Program all pages (old ones + new page N)

#### 💔 Why This Fails Catastrophically

**Performance disaster:**
```
Single page write = 1 read + 1 erase + N programs

With 64 pages per block:
- 1 read (100 µs)
- 1 erase (2000 µs)
- 64 programs (64 × 300 µs = 19,200 µs)
Total: ~21,300 µs = 21.3 milliseconds per 4KB write!

Hard drive: ~7-10 ms for random write
Direct-mapped SSD: ~21 ms for random write

SSD is SLOWER than a hard drive! ❌
```

**Write amplification:**
- Client writes 4 KB
- Device writes 64 pages × 4 KB = 256 KB
- Write amplification = 256 KB / 4 KB = **64×**

**Reliability disaster:**
```
If file system repeatedly updates a metadata block:
- Direct mapping always erases/programs the same block
- With 10,000 updates, block wears out
- Even though SSD has thousands of other blocks!

Device failure from workload pattern ❌
```

> ⚠️ **Critical Lesson**
>
> Direct mapping gives the client too much control over which physical blocks are used. A good FTL must control physical placement to distribute wear evenly and batch operations efficiently.

### 5.2. Log-Structured FTL

**In plain English:** Instead of updating data in place, always write new data to the next available location. Keep a map showing where each logical block currently lives.

**In technical terms:** The FTL appends all writes to the next free page in the currently-active block and maintains an in-memory mapping table translating logical block addresses to physical page addresses.

#### 📝 How It Works

**Write operation:**
1. Find next free page in log
2. Program the data to that page
3. Update mapping table: logical block → physical page

**Read operation:**
1. Look up logical block in mapping table
2. Get physical page address
3. Read from that physical page

#### 🔍 Detailed Example

Let's trace through a sequence of writes to see how log-structuring works.

**Initial state - empty SSD:**
```
Memory                          Flash
┌──────────────┐              Block 0        Block 1        Block 2
│ Mapping Table│              [i][i][i][i]  [i][i][i][i]  [i][i][i][i]
│  (empty)     │              Pages 0-3      Pages 4-7      Pages 8-11
└──────────────┘
```

**Operation 1: Write(100) = "a1"**

Device erases block 0, then programs page 0:
```
Memory                          Flash
┌──────────────┐              Block 0        Block 1        Block 2
│ Mapping Table│              ┌───────┐
│  100 → 0     │              │a1 [V] │      [i][i][i][i]  [i][i][i][i]
└──────────────┘              │  [E]  │
                               │  [E]  │
                               │  [E]  │
                               └───────┘
```

**Operation 2: Write(101) = "a2"**
```
Memory                          Flash
┌──────────────┐              Block 0        Block 1        Block 2
│ Mapping Table│              ┌───────┐
│  100 → 0     │              │a1 [V] │      [i][i][i][i]  [i][i][i][i]
│  101 → 1     │              │a2 [V] │
└──────────────┘              │  [E]  │
                               │  [E]  │
                               └───────┘
```

**Operations 3-4: Write(2000) = "b1", Write(2001) = "b2"**
```
Memory                          Flash
┌──────────────┐              Block 0        Block 1        Block 2
│ Mapping Table│              ┌───────┐
│  100 → 0     │              │a1 [V] │      [i][i][i][i]  [i][i][i][i]
│  101 → 1     │              │a2 [V] │
│  2000 → 2    │              │b1 [V] │
│  2001 → 3    │              │b2 [V] │
└──────────────┘              └───────┘
```

**Now overwrite blocks 100 and 101:**

**Operations 5-6: Write(100) = "c1", Write(101) = "c2"**

Device must erase block 1 first, then programs:
```
Memory                          Flash
┌──────────────┐              Block 0        Block 1        Block 2
│ Mapping Table│              ┌───────┐      ┌───────┐
│  100 → 4     │←─────────────│a1 [V] │      │c1 [V] │      [i][i][i][i]
│  101 → 5     │←─────────────│a2 [V] │      │c2 [V] │
│  2000 → 2    │              │b1 [V] │      │  [E]  │
│  2001 → 3    │              │b2 [V] │      │  [E]  │
└──────────────┘              └───────┘      └───────┘
                                ↑ garbage!
```

> **💡 Insight**
>
> Notice that pages 0 and 1 in block 0 are now garbage - they contain old versions of logical blocks 100 and 101. The mapping table points to the new locations (pages 4 and 5). This garbage accumulation is inevitable with log-structuring and must be cleaned up through garbage collection.

#### ✅ Advantages of Log-Structured FTL

**Performance benefits:**
- No read-modify-write for small updates
- Erases only needed when opening new blocks
- Write amplification: ~1× for sequential writes (optimal)
- Can use parallelism across multiple flash chips

**Reliability benefits:**
- FTL controls physical placement
- Can distribute writes across all blocks (wear leveling)
- Workload cannot repeatedly hammer one block

**The trade-off:**
- Creates garbage that needs collection
- Requires memory for mapping tables
- More complex than direct mapping

---

## 6. Garbage Collection

### 6.1. The Garbage Problem

**In plain English:** When you move to a new house and leave your old stuff behind, the old house fills up with your abandoned belongings. Eventually, someone needs to clear it out. That's garbage collection.

**In technical terms:** Log-structured writes create old versions of data scattered throughout flash blocks. These dead pages consume space and prevent blocks from being reused. Garbage collection reclaims this space.

#### 🗑️ When Does Garbage Form?

Whenever a logical block is overwritten, the old physical page becomes garbage:

```
Before overwrite of logical block 100:
Block 0: [100:a1][101:a2][102:b1][103:b2]  ← All pages live
         └──────── Mapping: 100→page0

After Write(100) = "c1":
Block 0: [100:a1][101:a2][102:b1][103:b2]  ← Page 0 is now GARBAGE
         ↑ dead!
Block 1: [100:c1][...]                      ← Page 4 has new data
         └──────── Mapping: 100→page4
```

### 6.2. How Garbage Collection Works

#### 🔄 The GC Process

**Step 1: Identify a block with garbage**
- Choose block with most dead pages (best efficiency)
- Or choose any block with some dead pages

**Step 2: Save live data**
- Identify which pages are still referenced by mapping table
- Read those pages into memory

**Step 3: Write live data to log**
- Append saved pages to current log location
- Update mapping table with new addresses

**Step 4: Reclaim the block**
- Erase the block
- Mark it as available for future writes

#### 📊 Example: Garbage Collection

**Before GC:**
```
Mapping Table:
  100 → 4  (in block 1)
  101 → 5  (in block 1)
  2000 → 2 (in block 0)
  2001 → 3 (in block 0)

Block 0                          Block 1
┌──────────┐                    ┌──────────┐
│100:a1 [V]│ ← GARBAGE!         │100:c1 [V]│ (page 4)
│101:a2 [V]│ ← GARBAGE!         │101:c2 [V]│ (page 5)
│2000:b1[V]│ (page 2) LIVE      │     [E]  │
│2001:b2[V]│ (page 3) LIVE      │     [E]  │
└──────────┘                    └──────────┘
  2 dead pages                    0 dead pages
  2 live pages
```

**GC Decision:** Collect block 0 (50% garbage)

**Step 1: Identify live pages in block 0**
- Check mapping table
- Page 0: Was 100, but 100→4 now, so DEAD ☠️
- Page 1: Was 101, but 101→5 now, so DEAD ☠️
- Page 2: Is 2000, and 2000→2, so LIVE ✅
- Page 3: Is 2001, and 2001→3, so LIVE ✅

**Step 2-3: Read live data and write to log**
```
Read pages 2 and 3 from block 0
Write to pages 6 and 7 in block 1
Update mapping: 2000→6, 2001→7
```

**Step 4: Erase block 0**

**After GC:**
```
Mapping Table:
  100 → 4  (in block 1)
  101 → 5  (in block 1)
  2000 → 6 (in block 1)
  2001 → 7 (in block 1)

Block 0                          Block 1
┌──────────┐                    ┌──────────┐
│    [E]   │                    │100:c1 [V]│ (page 4)
│    [E]   │ ← Now available!   │101:c2 [V]│ (page 5)
│    [E]   │                    │2000:b1[V]│ (page 6)
│    [E]   │                    │2001:b2[V]│ (page 7)
└──────────┘                    └──────────┘
```

#### ⚡ GC Performance Impact

**Cost of garbage collection:**
- Read live pages (cost depends on # of live pages)
- Write live pages to new location (write amplification)
- Erase block (expensive but necessary anyway)

**Best case:** Block contains only dead pages
- No reads or writes needed
- Just erase and reuse
- Write amplification = 0

**Worst case:** Block contains mostly live pages
- Must read and rewrite most pages
- High write amplification
- Much wasted work

> **💡 Insight**
>
> The ideal GC candidate is a block full of dead pages (instant reclamation) or a block with just a few live pages (minimal copying). Blocks with mostly live pages should be left alone. Good FTL design tries to create blocks with these extreme characteristics rather than blocks with mixed live/dead pages.

#### 🎯 Reducing GC Overhead

**Overprovisioning:**
- Add extra flash capacity (e.g., 280 GB of flash for a 256 GB SSD)
- Provides breathing room for GC
- Can defer GC to idle times
- Reduces impact on user workload

**Example:**
```
256 GB SSD with 10% overprovisioning:
  Physical capacity: 280 GB
  User-visible capacity: 256 GB
  Reserved for GC: 24 GB

Benefits:
✅ More free blocks available
✅ GC can be more selective (choose blocks with most garbage)
✅ Can batch GC operations
✅ Better sustained performance
```

### 6.3. The TRIM Operation

**In plain English:** TRIM is like telling your SSD "I deleted that file, so you don't need to keep track of those blocks anymore." Without TRIM, the SSD thinks you might still need the data.

**In technical terms:** TRIM is an interface operation that informs the device when logical blocks have been deleted, allowing the FTL to immediately mark those pages as dead without waiting for them to be overwritten.

#### 🔧 Why TRIM Matters

**Without TRIM:**
```
User deletes a 1 GB file in the file system

File system marks blocks as free in its own structures
     ↓
SSD has no idea those blocks were deleted
     ↓
SSD still tracks mappings for those blocks
     ↓
GC must still copy those pages around
     ↓
Wasted work + write amplification
```

**With TRIM:**
```
User deletes a 1 GB file

File system sends TRIM(blocks 1000-262143)
     ↓
FTL removes those entries from mapping table
     ↓
Corresponding physical pages marked as dead
     ↓
GC can immediately reclaim those pages
     ↓
Better performance + reduced wear
```

> **💡 Insight**
>
> TRIM demonstrates how implementation shapes interface design. Hard drives use a simple read/write interface because they have static mappings. SSDs need a richer interface (read/write/trim) because they have dynamic mappings. The device's internal architecture drives what operations it exposes to the system.

---

## 7. Managing Mapping Tables

### 7.1. The Mapping Table Size Problem

**In plain English:** Imagine having to remember where you put every single sock in your house. That's what a full page-level mapping table does - it tracks the location of every single 4 KB page.

**In technical terms:** A page-level FTL maintains one mapping entry per logical page. For large SSDs, this requires impractical amounts of memory.

#### 💾 The Size Calculation

**Example: 1 TB SSD with 4 KB pages**

```
Total pages = 1 TB / 4 KB
           = 1,099,511,627,776 bytes / 4,096 bytes
           = 268,435,456 pages

Mapping entry size = 4 bytes (32-bit address)

Total memory needed = 268,435,456 × 4 bytes
                    = 1,073,741,824 bytes
                    = 1 GB of RAM

Just for the mapping table! ❌
```

**The problem:** 1 GB of expensive SRAM on every SSD is cost-prohibitive.

**We need a better solution:**
- Block-based mapping (reduce table size)
- Hybrid mapping (balance size and performance)
- Page mapping with caching (keep only active entries in memory)

### 7.2. Block-Based Mapping

**In plain English:** Instead of tracking every page individually, track groups of pages together. It's like remembering which bookshelf a book is on instead of its exact position.

**In technical terms:** Maintain one mapping entry per flash block instead of per page. Logical addresses are divided into chunk number and offset.

#### 🗂️ Address Structure

```
Logical Block Address
┌─────────────────┬──────────┐
│  Chunk Number   │  Offset  │
└─────────────────┴──────────┘
     (high bits)    (low bits)

Example with 4 pages per block:
  Logical block 2000 = chunk 500, offset 0
  Logical block 2001 = chunk 500, offset 1
  Logical block 2002 = chunk 500, offset 2
  Logical block 2003 = chunk 500, offset 3
```

#### 📊 Example: Block-Based Mapping

**State after writing blocks 2000-2003:**

```
Mapping Table:
  Chunk 500 → Page 4 (start of block 1)

Flash Block 1
┌────────────────────┐
│ Page 4:  2000:a    │  (offset 0)
│ Page 5:  2001:b    │  (offset 1)
│ Page 6:  2002:c    │  (offset 2)
│ Page 7:  2003:d    │  (offset 3)
└────────────────────┘
```

**Reading logical block 2002:**
1. Extract chunk number: 2002 / 4 = 500
2. Extract offset: 2002 % 4 = 2
3. Look up chunk 500 → page 4
4. Add offset: 4 + 2 = page 6
5. Read page 6 → "c"

**Memory savings:**

```
Before (page-level):
  1 TB SSD = 1 GB mapping table

After (block-level with 64 pages per block):
  1 TB SSD = 1 GB / 64 = 16 MB mapping table

64× reduction! ✅
```

#### 💔 The Fatal Flaw: Small Writes

**Problem scenario: Update a single page**

```
Before: Write(2002) = "c'"

Block 1: [2000:a][2001:b][2002:c][2003:d]
         └──────────chunk 500──────────┘

Steps required:
1. Read live pages from block 1: a, b, d
2. Erase block 1
3. Write to new location: a, b, c', d
4. Update mapping: chunk 500 → new block

Cost:
  3 reads (a, b, d)
  1 erase
  4 programs (a, b, c', d)

Write amplification = 4× for a single page update! ❌
```

> ⚠️ **Critical Problem**
>
> Block-based mapping requires reading and rewriting all pages in a logical chunk when updating any single page. With 64+ pages per block, a 4 KB write turns into a 256+ KB write. This defeats the purpose of using an SSD!

### 7.3. Hybrid Mapping

**In plain English:** Keep a small notebook for frequently changing items (log table with per-page entries) and a big ledger for stable items (data table with per-block entries). When the notebook fills up, transfer completed groups to the ledger.

**In technical terms:** Maintain two mapping tables:
1. **Log table:** Per-page mappings for a small number of actively-written log blocks
2. **Data table:** Per-block mappings for the majority of blocks

#### 🏗️ Hybrid FTL Structure

```
┌─────────────────────────────────────┐
│         Memory                      │
│                                     │
│  ┌──────────────────┐              │
│  │   Log Table      │              │
│  │  (per-page)      │              │
│  │  1000 → 0        │  Small       │
│  │  1001 → 1        │  (few KB)    │
│  │  1002 → 2        │              │
│  └──────────────────┘              │
│                                     │
│  ┌──────────────────┐              │
│  │   Data Table     │              │
│  │  (per-block)     │              │
│  │  Chunk 0 → 8     │  Large       │
│  │  Chunk 1 → 16    │  (MBs)       │
│  │  Chunk 2 → 24    │              │
│  │  ...             │              │
│  └──────────────────┘              │
└─────────────────────────────────────┘
```

#### 🔍 Read Operation

```
To read logical block N:
  1. Check log table
     ├─ Found? Read from that page ✅
     └─ Not found?
        └─ Check data table
           ├─ Found? Read from block+offset ✅
           └─ Not found? Block was never written ❌
```

#### ✍️ Write Operation

```
To write logical block N:
  Write to next free page in log block
  Add entry to log table: N → page_number
```

Simple! No read-modify-write needed.

#### 🔄 The Three Merge Types

When log blocks fill up, the FTL must convert them to data blocks. Three scenarios arise:

**1. Switch Merge (Best Case)**

**Scenario:** Log block contains sequential updates to pages in same chunk

```
Initial state:
  Data table: chunk 250 → page 8
  Block 2: [1000:a][1001:b][1002:c][1003:d]

User overwrites in exact order: 1000, 1001, 1002, 1003
  Log table: 1000→0, 1001→1, 1002→2, 1003→3
  Block 0: [1000:a'][1001:b'][1002:c'][1003:d']

Switch merge:
  1. Update data table: chunk 250 → page 0
  2. Erase block 2, convert to log block
  3. Clear log table entries

Cost: Zero I/O! Just pointer manipulation ✅
```

**2. Partial Merge (Medium Case)**

**Scenario:** Log block contains partial updates to a chunk

```
Initial state:
  Data table: chunk 250 → page 8
  Block 2: [1000:a][1001:b][1002:c][1003:d]

User overwrites only 1000 and 1001:
  Log table: 1000→0, 1001→1
  Block 0: [1000:a'][1001:b'][E][E]
  Block 2: [1000:a][1001:b][1002:c][1003:d]
                          ↑      ↑
                       still needed!

Partial merge:
  1. Read pages 10, 11 from block 2 (c, d)
  2. Program pages 2, 3 in block 0
  3. Update data table: chunk 250 → page 0
  4. Erase block 2
  5. Clear log table entries

Cost: 2 reads + 2 programs (moderate) ⚠️
```

**3. Full Merge (Worst Case)**

**Scenario:** Log block contains scattered updates to many chunks

```
Log block contains updates to blocks 0, 4, 8, 12
(four different chunks: 0, 1, 2, 3)

Full merge must:
  For chunk 0:
    - Read blocks 1, 2, 3 from old locations
    - Write blocks 0, 1, 2, 3 together
  For chunk 1:
    - Read blocks 5, 6, 7 from old locations
    - Write blocks 4, 5, 6, 7 together
  ... and so on for chunks 2 and 3

Cost: Many reads + many programs (expensive!) ❌
```

> **💡 Insight**
>
> Hybrid mapping works well when workloads create switch merges (sequential overwrites) or partial merges (partial updates to same chunk). Full merges are expensive and should be avoided. Good FTL designs use multiple log blocks, each dedicated to a specific chunk range, to minimize full merges.

### 7.4. Page Mapping with Caching

**In plain English:** Instead of keeping the entire phone book in your pocket, just carry the pages for people you actually call.

**In technical terms:** Keep the full page-level mapping table on flash, but cache only the actively-used portions in memory.

#### 🔄 How It Works

```
┌─────────────────────────────────────┐
│         Memory (SRAM)               │
│                                     │
│  ┌──────────────────┐              │
│  │  Mapping Cache   │  Small       │
│  │   (hot entries)  │  (10-100 MB) │
│  │                  │              │
│  │  100 → 0         │              │
│  │  101 → 1         │              │
│  │  ...             │              │
│  └──────────────────┘              │
└─────────────────────────────────────┘
              ↕ cache miss/eviction
┌─────────────────────────────────────┐
│         Flash                       │
│                                     │
│  ┌──────────────────┐              │
│  │  Full Mapping    │  Large       │
│  │  Table (on SSD)  │  (1 GB)      │
│  │                  │              │
│  │  All entries     │              │
│  │  stored here     │              │
│  └──────────────────┘              │
└─────────────────────────────────────┘
```

#### ✅ When It Works Well

**Workload with high locality:**
```
Program repeatedly accesses blocks 1000-1500

These mappings stay cached in memory
     ↓
All reads/writes are fast (no extra flash reads)
     ↓
Memory needed: ~500 entries × 4 bytes = 2 KB ✅
```

#### ❌ When It Fails

**Workload with low locality (random access):**
```
Program accesses blocks scattered across entire SSD

Frequent cache misses
     ↓
Must read mapping from flash before reading data
     ↓
Every data read becomes: mapping read + data read
     ↓
2× read amplification ❌

Worse: Evicting dirty mappings requires writes
     ↓
3× total I/O: mapping read + data read + mapping write ❌
```

> **💡 Insight**
>
> Page mapping with caching bets on workload locality. It works brilliantly for workloads that access small working sets (databases, virtual machines) but poorly for random access patterns. This is why understanding workload characteristics is crucial for storage system design.

#### 📊 Comparison of Mapping Schemes

| Approach | Memory Size | Small Write Cost | Best For |
|----------|-------------|------------------|----------|
| **Page-level** | Very large (1 GB) | Low (optimal) | Unlimited budget |
| **Block-level** | Small (16 MB) | Very high (4-64×) | Read-only or sequential writes |
| **Hybrid** | Medium (100 MB) | Medium (depends on merge type) | Mixed workloads |
| **Page + Cache** | Small (10-100 MB) | Low to high (depends on locality) | High-locality workloads |

---

## 8. Wear Leveling

**In plain English:** If you always sit in the same spot on your couch, that cushion wears out while others stay new. Wear leveling is like rotating where you sit so all cushions wear evenly.

**In technical terms:** Wear leveling distributes erase/program cycles evenly across all flash blocks, ensuring the entire device wears out uniformly rather than having hotspots fail prematurely.

### 🎯 The Wear Leveling Problem

**Scenario without wear leveling:**
```
File system frequently updates inode table at blocks 0-10
     ↓
Log-structured FTL writes updates sequentially...
     ↓
But GC keeps moving that data back to free up log space
     ↓
Same physical blocks get erased/programmed repeatedly
     ↓
Blocks 0-10 wear out after 10,000 cycles
     ↓
Device fails even though blocks 11-1000 are fresh! ❌

Device lifetime: 10,000 cycles
Wasted capacity: 99% of blocks unused
```

**Goal of wear leveling:**
```
Spread 10,000 writes to inode data across ALL blocks
     ↓
Each block receives 10,000 / 1000 = 10 cycles
     ↓
Device fails when all blocks wear out simultaneously ✅

Device lifetime: Still 10,000 total cycles
But full capacity utilized before failure
```

### 🔄 How Wear Leveling Works

**Dynamic wear leveling** (basic log-structured FTL already does this):
- Writes go to next free page in log
- Naturally spreads write load across blocks
- Works well for frequently-updated data

**Static wear leveling** (additional mechanism needed):
- Some blocks contain cold data (rarely updated)
- These blocks never get erased through normal GC
- They don't receive their "fair share" of P/E cycles

**Solution:**
```
Periodically:
  1. Identify cold blocks (valid data, not recently erased)
  2. Read their live data
  3. Write data to log (or other blocks)
  4. Erase cold block
  5. Mark as available for new writes

Result: Cold blocks re-enter the write pool
```

### 📊 Example: Static Wear Leveling

```
Block wear status:
  Block 0: 5,000 P/E cycles (frequently updated metadata)
  Block 1: 5,000 P/E cycles (frequently updated data)
  Block 2: 10 P/E cycles (cold data - user photo)
  Block 3: 10 P/E cycles (cold data - user document)
  Block 4: 5,000 P/E cycles (frequently updated data)

Without static wear leveling:
  Blocks 0, 1, 4 wear out at 10,000 cycles
  Blocks 2, 3 still fresh
  Device fails! ❌

With static wear leveling:
  Periodically:
    1. Read photo and document from blocks 2, 3
    2. Write to blocks 5, 6
    3. Erase blocks 2, 3
    4. Use blocks 2, 3 for new writes

  Result: All blocks reach ~10,000 cycles together ✅
```

### ⚖️ The Wear Leveling Trade-off

**Benefit:**
- Full device capacity utilized
- Predictable lifetime
- Maximum total data written

**Cost:**
- Extra reads (to relocate cold data)
- Extra writes (to copy cold data)
- Increased write amplification
- Reduced performance during wear leveling

**The balance:**
```
Too little wear leveling:
  → Blocks wear unevenly
  → Premature failure
  → Wasted capacity

Too much wear leveling:
  → Excessive data copying
  → High write amplification
  → Poor performance

Sweet spot:
  → Monitor wear distribution
  → Level only when variance exceeds threshold
  → Background operation during idle time
```

> **💡 Insight**
>
> Wear leveling is another example of storage systems trading performance for longevity. By occasionally doing "unnecessary" work (moving cold data), the SSD ensures that all blocks age together. This controlled overhead is far better than unpredictable early failure.

---

## 9. SSD Performance and Cost Analysis

### 9.1. Performance Comparison

**Real-world SSD vs HDD performance (in MB/s):**

| Device | Random Read | Random Write | Sequential Read | Sequential Write |
|--------|-------------|--------------|-----------------|------------------|
| Samsung 840 Pro SSD | 103 | 287 | 421 | 384 |
| Seagate 600 SSD | 84 | 252 | 424 | 374 |
| Intel 335 SSD | 39 | 222 | 344 | 354 |
| Seagate Savvio 15K.3 HDD | **2** | **2** | 223 | 223 |

#### 🚀 Key Performance Insights

**1. Random I/O: SSDs dominate (50-140× faster)**

```
SSD random read: 39-103 MB/s
HDD random read: 2 MB/s

Why?
  HDD: Must seek + rotate for each access (~7-10 ms)
  SSD: Direct page access (~25-75 µs)

Real-world impact:
  Random database queries
  Virtual machine I/O
  Application launches
  → SSDs transform user experience ✅
```

**2. Sequential I/O: SSDs still win (1.5-2× faster)**

```
SSD sequential: 344-424 MB/s
HDD sequential: 223 MB/s

Why smaller gap?
  HDD: Can stream data once positioned
  SSD: Still limited by chip bandwidth

Real-world impact:
  Video editing
  Large file copies
  Sequential scans
  → SSDs better, but HDD acceptable
```

**3. Random writes surprisingly fast on SSDs**

```
SSD random write: 222-287 MB/s
SSD random read: 39-103 MB/s

Random writes faster than reads? How?
  Log-structured FTL converts random writes → sequential programs
  Multiple flash chips in parallel
  Write buffering in memory

This is FTL magic at work! ✨
```

**4. Sequential vs random gap smaller on SSDs**

```
HDD:
  Random: 2 MB/s
  Sequential: 223 MB/s
  Ratio: 111×

SSD:
  Random: ~75 MB/s (average)
  Sequential: ~390 MB/s (average)
  Ratio: 5×

Implication:
  File system optimizations for sequential access still help SSDs
  But not as critical as with HDDs
```

### 9.2. Cost Considerations

#### 💰 Price per Capacity (approximate, varies over time)

```
SSD: $150 for 250 GB
     = $0.60 per GB

HDD: $50 for 1 TB
     = $0.05 per GB

Cost ratio: 12× more expensive for SSDs
```

#### 🎯 When to Choose SSDs

**SSD is optimal when:**
- ✅ Performance is critical (databases, VMs)
- ✅ Random access dominates workload
- ✅ Low latency required (real-time systems)
- ✅ Power efficiency matters (laptops, mobile)
- ✅ Physical durability needed (no moving parts)
- ✅ Budget allows premium pricing

**Examples:**
- OS boot drives
- Database transaction logs
- Virtual machine storage
- High-frequency trading systems
- Laptop primary storage

#### 📁 When HDDs Still Make Sense

**HDD is optimal when:**
- ✅ Capacity is primary concern
- ✅ Sequential access dominates
- ✅ Cost per GB is critical
- ✅ Archival/cold storage use case
- ✅ Write endurance needs exceed SSD lifetime

**Examples:**
- Video surveillance archives
- Backup systems
- Media libraries
- Data warehouses
- Large-scale cloud storage

#### 🔀 Hybrid Approaches

**Hot/cold tiering:**
```
┌─────────────────────────┐
│    SSD Tier             │
│  (Small, fast)          │
│                         │
│  - Frequently accessed  │
│  - Critical metadata    │
│  - Active databases     │
└─────────────────────────┘
           ↕
    (migrate data based on access patterns)
           ↕
┌─────────────────────────┐
│    HDD Tier             │
│  (Large, cheap)         │
│                         │
│  - Infrequently accessed│
│  - Archival data        │
│  - Bulk storage         │
└─────────────────────────┘

Benefits:
  ✅ SSD performance for hot data
  ✅ HDD economics for cold data
  ✅ Best of both worlds
```

> **💡 Insight**
>
> The SSD vs HDD decision isn't binary. As SSDs continue to drop in price and HDDs increase in capacity, the sweet spot shifts. Most modern systems use both: SSDs for performance-critical data and HDDs for capacity. Understanding your workload's access patterns determines the right balance.

---

## 10. Summary

Flash-based SSDs represent a fundamental transformation in storage technology, replacing mechanical precision with semiconductor physics.

### 🎯 Core Concepts Mastered

**1. Flash storage basics:**
- Transistors store charge levels representing bits
- Organized hierarchically: banks → blocks → pages
- Three operations: read (fast), program (medium), erase (slow)
- Erase-before-write requirement drives all design decisions

**2. Performance characteristics:**
- Random access ~100× faster than HDDs
- Sequential access ~2× faster than HDDs
- Erase operations are expensive (milliseconds)
- Different cell types (SLC, MLC, TLC) trade density for performance

**3. Reliability challenges:**
- Wear out from repeated P/E cycles (10,000-100,000 cycle lifetime)
- Read and program disturbance
- Predictable degradation vs HDD's mechanical unpredictability

**4. Flash Translation Layer (FTL):**
- Translates logical blocks to physical pages
- Log-structured design avoids expensive erases
- Maintains mapping table (logical → physical)
- Critical for hiding flash complexity from host

**5. Garbage collection:**
- Reclaims space from dead pages
- Trades performance (copying live data) for capacity
- Overprovisioning reduces impact
- TRIM operation helps identify dead pages early

**6. Mapping strategies:**
- Page-level: Maximum flexibility, excessive memory
- Block-level: Minimal memory, poor small-write performance
- Hybrid: Balanced approach with log and data tables
- Cached page mapping: Memory-efficient for localized workloads

**7. Wear leveling:**
- Distributes P/E cycles across all blocks
- Dynamic leveling: Natural from log structure
- Static leveling: Periodically moves cold data
- Increases write amplification but extends lifetime

### 📊 Key Metrics to Remember

| Metric | Value | Impact |
|--------|-------|--------|
| Read latency | 25-75 µs | Excellent random access |
| Program latency | 200-1350 µs | Good write performance |
| Erase latency | 1500-4500 µs | Drives log-structured design |
| SLC lifetime | 100,000 P/E | Longest lasting |
| MLC lifetime | 10,000 P/E | Standard consumer grade |
| Cost premium | ~12× vs HDD | Limits adoption for capacity |
| Random I/O advantage | 50-140× vs HDD | Transforms user experience |

### 🔧 Design Principles

**1. Write amplification is the enemy**
- Every write beyond what the user requested reduces performance and lifetime
- Good FTL design minimizes amplification through clever mapping and GC

**2. Locality is your friend**
- Workloads with spatial/temporal locality benefit most from SSDs
- Caching, prefetching, and access pattern prediction all leverage locality

**3. Trade-offs are everywhere**
- Performance vs lifetime (wear leveling overhead)
- Memory vs flexibility (mapping table size)
- Simplicity vs efficiency (direct mapping vs log structure)

**4. Interfaces matter**
- TRIM operation shows how implementation shapes interface
- Future interfaces may expose more SSD characteristics to software

### 🚀 The Future

SSDs continue to evolve:
- Higher densities (QLC: 4 bits/cell, PLC: 5 bits/cell)
- New technologies (3D NAND stacking)
- Better endurance (improved manufacturing)
- Lower costs (approaching HDD economics)
- New interfaces (NVMe, computational storage)

> **💡 Final Insight**
>
> Understanding SSDs isn't just about knowing flash physics - it's about appreciating how constraints drive innovation. The erase-before-write limitation seemed like a fatal flaw, but clever software (log-structuring, wear leveling, garbage collection) transformed it into a triumph. This pattern repeats throughout computer systems: seemingly impossible constraints inspire creative solutions that define the next generation of technology.

### 📚 Going Deeper

This chapter provides foundational knowledge, but SSD research continues:
- FTL design innovations
- Multi-tenant performance isolation
- Emerging storage-class memory
- Distributed flash-based systems
- End-to-end performance optimization

The field remains active and exciting. Dive deeper into recent research and watch for the next revolutionary storage technology!

---

**Previous:** [Chapter 9: Log-Structured File System](chapter9-log-structured-file-system.md) | **Next:** [Chapter 11: Data Integrity](chapter11-data-integrity.md)
