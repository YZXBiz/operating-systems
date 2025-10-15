# Chapter 15: Paging - Smaller Tables 📏

_Solving the page table size problem with clever data structures_

---

## 📋 Table of Contents

1. [🎯 Introduction](#1-introduction)
   - 1.1. [The Page Table Size Problem](#11-the-page-table-size-problem)
2. [📐 Simple Solution: Bigger Pages](#2-simple-solution-bigger-pages)
   - 2.1. [How Bigger Pages Help](#21-how-bigger-pages-help)
   - 2.2. [The Internal Fragmentation Problem](#22-the-internal-fragmentation-problem)
3. [🔀 Hybrid Approach: Paging and Segments](#3-hybrid-approach-paging-and-segments)
   - 3.1. [Combining Two Abstractions](#31-combining-two-abstractions)
   - 3.2. [How Hybrid Page Tables Work](#32-how-hybrid-page-tables-work)
   - 3.3. [Limitations of the Hybrid Approach](#33-limitations-of-the-hybrid-approach)
4. [🌳 Multi-Level Page Tables](#4-multi-level-page-tables)
   - 4.1. [The Core Idea](#41-the-core-idea)
   - 4.2. [How Multi-Level Tables Work](#42-how-multi-level-tables-work)
   - 4.3. [Detailed Multi-Level Example](#43-detailed-multi-level-example)
   - 4.4. [More Than Two Levels](#44-more-than-two-levels)
   - 4.5. [Translation Process with TLB](#45-translation-process-with-tlb)
5. [🔄 Inverted Page Tables](#5-inverted-page-tables)
6. [💾 Swapping Page Tables to Disk](#6-swapping-page-tables-to-disk)
7. [📝 Summary](#7-summary)

---

## 1. 🎯 Introduction

### 1.1. 📊 The Page Table Size Problem

**In plain English:** Imagine you're running a library 📚 where every book needs a catalog card. If your library has a million possible shelf locations, you need a million cards even if you only have a hundred books! The other 999,900 cards just say "empty shelf." What a waste of filing cabinets!

**In technical terms:** Linear page tables (simple arrays mapping virtual pages to physical frames) consume enormous amounts of memory. With a 32-bit address space, 4KB pages, and 4-byte page table entries (PTEs), each process needs a 4MB page table—even if it's only using a tiny fraction of its address space.

**Why it matters:** On a typical system with 100 active processes, you'd allocate hundreds of megabytes just for page tables! This overhead is unacceptable, especially when most of those entries mark unused virtual pages as invalid.

**The Math:**
```
32-bit Address Space Breakdown
───────────────────────────────
Total address space:  2^32 bytes = 4GB
Page size:           2^12 bytes = 4KB
Number of pages:     2^32 / 2^12 = 2^20 = 1,048,576 pages

Page Table Size:
─────────────────
Entries needed:      1,048,576 PTEs
Size per PTE:        4 bytes
Total size:          1,048,576 × 4 = 4,194,304 bytes = 4MB

Per Process!!! 😱
```

**Realistic scenario visualization:**
```
Virtual Address Space (sparse usage)
─────────────────────────────────────
0x00000000  ┌─────────────┐
            │    Code     │ ← Actually used (valid PTEs)
0x00100000  ├─────────────┤
            │             │
            │   UNUSED    │ ← Wasted PTEs (invalid)
            │   (huge)    │
0x40000000  ├─────────────┤
            │    Heap     │ ← Actually used (valid PTEs)
0x40100000  ├─────────────┤
            │             │
            │   UNUSED    │ ← More wasted PTEs
            │   (huge)    │
0xBFFF0000  ├─────────────┤
            │    Stack    │ ← Actually used (valid PTEs)
0xC0000000  └─────────────┘

Linear Page Table: ALL entries allocated, mostly invalid
Multi-Level Table:  ONLY valid regions allocated 🎯
```

> **💡 Insight**
>
> This is a classic **sparse data structure problem**. When most entries are empty/invalid, storing the entire array is wasteful. Computer science offers many solutions: sparse matrices, hash tables, trees. Page tables are just another instance of this fundamental problem—but the solution must be hardware-friendly (fast lookups) and space-efficient.

**THE CRUX:** 🎯 How can we make page tables smaller while maintaining fast address translation?

**Key Ideas We'll Explore:**
1. **Bigger pages** - Fewer entries needed (but wastes memory)
2. **Hybrid paging/segmentation** - One table per segment (clever but limited)
3. **Multi-level tables** - Tree structure (widely used, excellent trade-off)
4. **Inverted tables** - One entry per physical frame (extreme space saving)

---

## 2. 📐 Simple Solution: Bigger Pages

### 2.1. 🔍 How Bigger Pages Help

**In plain English:** Instead of dividing memory into 4KB chunks, use 16KB chunks. Fewer chunks means fewer catalog cards 📇. It's like organizing a warehouse with bigger bins—you need fewer bins to label.

**Progressive Example:**

**Simple:** 4KB pages (original)
```
32-bit address space, 4KB pages
────────────────────────────────
Virtual page number (VPN): 20 bits  (2^20 = 1M entries)
Page offset:              12 bits  (4KB = 2^12)

Page table size: 1M entries × 4 bytes = 4MB
```

**Intermediate:** 16KB pages (4× larger)
```
32-bit address space, 16KB pages
─────────────────────────────────
Virtual page number (VPN): 18 bits  (2^18 = 256K entries)
Page offset:              14 bits  (16KB = 2^14)

Page table size: 256K entries × 4 bytes = 1MB ✅ (4× reduction!)
```

**Visual comparison:**
```
Address Space Division
──────────────────────

4KB Pages:                    16KB Pages:
┌────┐ 0                      ┌─────────────┐ 0
├────┤ 4KB                    │             │
├────┤ 8KB                    │             │
├────┤ 12KB                   │             │
├────┤ 16KB     ──→           ├─────────────┤ 16KB
├────┤ 20KB                   │             │
├────┤ 24KB                   │             │
├────┤ 28KB                   │             │
└────┘ 32KB                   └─────────────┘ 32KB

8 PTEs needed                 2 PTEs needed
```

### 2.2. 🚨 The Internal Fragmentation Problem

**In plain English:** Bigger bins mean more wasted space in each bin. If you allocate a 16KB page but only use 1KB of it, you've wasted 15KB. This waste is called **internal fragmentation** 🗑️ (waste internal to the allocation unit).

**Why this happens:**
```
Program requests 5KB allocation
────────────────────────────────

With 4KB pages:                 With 16KB pages:
┌─────────┐                     ┌─────────────────┐
│ 4KB     │ ← Used              │ 5KB used        │
├─────────┤                     │                 │
│ 1KB     │ ← Used              ├─ ─ ─ ─ ─ ─ ─ ─ ┤
└─────────┘                     │                 │
Wasted: 3KB ✅                  │ 11KB wasted! 😱 │
                                │                 │
                                └─────────────────┘
                                Wasted: 11KB ❌
```

**Real-world impact:**
```
Application Memory Usage Pattern
─────────────────────────────────
Code:   48KB   → With 4KB pages: 12 pages (0 waste)
                 With 16KB pages: 3 pages (0 waste) ✅

Heap:   23KB   → With 4KB pages: 6 pages (1KB waste)
                 With 16KB pages: 2 pages (9KB waste) ❌

Stack:  17KB   → With 4KB pages: 5 pages (3KB waste)
                 With 16KB pages: 2 pages (15KB waste) ❌

Total waste:     4KB vs 24KB (6× more waste!)
```

> **💡 Insight**
>
> This is a fundamental **granularity trade-off** in computer systems:
> - **Finer granularity** (small pages): Less waste per allocation, more metadata overhead
> - **Coarser granularity** (large pages): More waste per allocation, less metadata overhead
>
> This same trade-off appears in disk block sizes, network packet sizes, cache line sizes. There's no perfect answer—the right choice depends on your workload.

**Modern systems approach:** 🎯
```
Multiple Page Sizes
───────────────────
Default:       4KB or 8KB    (for most allocations)
Large pages:   2MB or 4MB    (for databases, HPC applications)
Huge pages:    1GB           (for massive datasets)

Application explicitly requests large pages via:
- madvise() on Linux
- VirtualAlloc() with LARGE_PAGES on Windows
```

**Why large pages help specific workloads:**
- Databases with huge buffers 💾 (less TLB pressure)
- Scientific computing with massive arrays 🔬 (fewer TLB misses)
- Virtual machines 🖥️ (nested page tables benefit)

**Conclusion:** ❌ Bigger pages alone don't solve the general problem. We need smarter approaches.

---

## 3. 🔀 Hybrid Approach: Paging and Segments

### 3.1. 🥜 Combining Two Abstractions

**In plain English:** What if we combined chocolate 🍫 and peanut butter 🥜? We get Reese's! Similarly, what if we combined paging and segmentation? We might get the best of both worlds: segments give us sparse address spaces, paging gives us no external fragmentation.

**The key insight:** Instead of one giant page table for the entire address space, have **one page table per logical segment** (code, heap, stack). Don't allocate page tables for the huge invalid regions between segments!

**Historical context:** 🏛️
This idea came from the **Multics** system in the 1960s (Jack Dennis). Multics was groundbreaking but complex—this hybrid was one of its clever innovations.

### 3.2. ⚙️ How Hybrid Page Tables Work

**Address space structure:**
```
Without Hybrid (Linear PT)          With Hybrid (Segmented PT)
──────────────────────────          ──────────────────────────

Virtual Memory:                     Virtual Memory:
┌─────────────┐                     ┌─────────────┐
│   Code      │ VPN 0-3             │   Code      │ Segment 01
├─────────────┤                     ├─────────────┤
│             │                     │             │
│  (unused)   │ VPN 4-1023         │  (unused)   │ Segment 00 (unused)
│             │                     │             │
├─────────────┤                     ├─────────────┤
│   Heap      │ VPN 1024-1027       │   Heap      │ Segment 10
├─────────────┤                     ├─────────────┤
│             │                     │             │
│  (unused)   │ VPN 1028-4093      │  (unused)   │ Segment 00 (unused)
│             │                     │             │
├─────────────┤                     ├─────────────┤
│   Stack     │ VPN 4094-4095       │   Stack     │ Segment 11
└─────────────┘                     └─────────────┘

Page Table:                         Page Tables:
┌─────────────┐                     Code PT (4 entries)
│ 4096 PTEs   │                     ┌───┬───┬───┬───┐
│ (16KB)      │                     │PTE│PTE│PTE│PTE│
│             │                     └───┴───┴───┴───┘
│ Mostly      │                     Heap PT (4 entries)
│ invalid!    │                     ┌───┬───┬───┬───┐
└─────────────┘                     │PTE│PTE│PTE│PTE│
                                    └───┴───┴───┴───┘
Memory used: 16KB                   Stack PT (2 entries)
                                    ┌───┬───┐
                                    │PTE│PTE│
                                    └───┴───┘

                                    Memory used: ~40 bytes! 🎉
```

**Virtual address breakdown:**
```
32-bit Virtual Address Format
──────────────────────────────
31 30 29 28 ... 13 12 11 10 ... 0
├──┴──┴─────────┴──┴──┴──────┴──┘
│                │         │
Seg (2 bits)     │         Offset (12 bits, 4KB pages)
                 │
                 VPN (18 bits)

Segment Encoding:
00 → Unused (invalid)
01 → Code
10 → Heap
11 → Stack
```

**Hardware structures:**
```
Segment Base/Bounds Registers
──────────────────────────────
Segment  Base (PT physical addr)  Bounds (max valid page)
───────  ────────────────────────  ───────────────────────
Code     0x00A00000                3 (VPNs 0-2 valid)
Heap     0x00B00000                4 (VPNs 0-3 valid)
Stack    0x00C00000                2 (VPNs 0-1 valid)
```

**Address translation steps:**

**Progressive Example - Translating address 0x00002000:**

**Step 1:** Extract segment bits
```
Address: 0x00002000 = 0000 0000 0000 0000 0010 0000 0000 0000
                      ││                    │             │
                      Seg=00               VPN=2         Offset=0
```

**Step 2:** Check segment validity
```
Segment 00 → Code segment
Base register:   0x00A00000 (points to code page table)
Bounds register: 3 (VPNs 0-2 valid)
VPN 2 < 3? YES ✅ (valid access)
```

**Step 3:** Calculate PTE address
```
PTEAddr = Base[Seg] + (VPN × sizeof(PTE))
        = 0x00A00000 + (2 × 4)
        = 0x00A00008
```

**Step 4:** Read PTE, extract PFN
```
PTE at 0x00A00008 → {PFN=10, valid=1, prot=r-x}
```

**Step 5:** Form physical address
```
PhysAddr = (PFN << 12) | Offset
         = (10 << 12) | 0x000
         = 0x0000A000
```

**Validation with bounds:**
```
Translation Process (Detailed)
───────────────────────────────

Virtual Address: 0x42001234 (accessing heap)
Binary: 0100 0010 0000 0000 0001 0010 0011 0100
        ││││││││││││││││││││││││││││││││││││││
        └┴── Seg=01 (Heap)
            └─────────────┴── VPN=0x8000 (too big!)
                          └──────────┴── Offset=0x234

Bounds check:
  VPN=0x8000, Bounds=4
  0x8000 > 4? YES → SEGMENTATION FAULT! 🚨

Protection: Bounds register prevents access to invalid pages
```

### 3.3. ⚠️ Limitations of the Hybrid Approach

**Problem 1: Still uses segmentation** 🔀

**In plain English:** Segmentation assumes your program organizes memory into a few contiguous regions (code, heap, stack). But what if your heap is large and sparse? You're back to wasting page table space.

```
Sparse Heap Problem
───────────────────
Heap address space: 1GB (262,144 pages @ 4KB)
Actually used:      10MB scattered throughout
                    (only 2,560 pages used)

Hybrid approach:
  Must allocate PT for entire 1GB heap
  Page table size: 262,144 PTEs × 4 bytes = 1MB
  Most entries invalid!

Still wasteful for sparse regions 😞
```

**Problem 2: External fragmentation returns** 🧩

**In plain English:** Page tables can now be different sizes (code segment might have 100 entries, heap 10,000). Finding contiguous free memory for variable-sized page tables is harder than for fixed-size ones.

```
Memory for Page Tables
──────────────────────
Process A: Code PT (400 bytes), Heap PT (40,000 bytes), Stack PT (80 bytes)
Process B: Code PT (1,200 bytes), Heap PT (4,000 bytes), Stack PT (160 bytes)

Finding 40KB contiguous space for Process A's heap PT?
Memory might be fragmented! 😫

┌────┬──────┬────┬──────┬────┬──────┐
│Free│ PT A │Free│ PT B │Free│ PT C │
└────┴──────┴────┴──────┴────┴──────┘
      ↑ 10KB      ↑ 15KB      ↑ 8KB

Need 40KB contiguous → NOT AVAILABLE
Even though total free space > 40KB!
```

**Problem 3: Assumes specific address space layout** 📐

```
Hybrid works for:                Hybrid fails for:
────────────────                 ─────────────────
┌────────┐                       ┌────────┐
│  Code  │                       │ Code   │
├────────┤                       ├────────┤
│        │                       │ mmap 1 │
│ (free) │                       ├────────┤
│        │                       │ (free) │
├────────┤                       ├────────┤
│  Heap  │                       │ mmap 2 │
├────────┤                       ├────────┤
│        │                       │  Heap  │
│ (free) │                       ├────────┤
│        │                       │ mmap 3 │
├────────┤                       ├────────┤
│ Stack  │                       │ (free) │
└────────┘                       ├────────┤
                                 │ Stack  │
Clean segments ✅                └────────┘

                                 Multiple mapped
                                 regions ❌
                                 (too many segments!)
```

> **💡 Insight**
>
> **Hybrid approaches reveal a key systems design lesson:** Combining two techniques can work well, but you inherit the limitations of both. Segmentation's rigidity limits the hybrid approach. We need a solution that doesn't assume any particular address space layout.

---

## 4. 🌳 Multi-Level Page Tables

### 4.1. 💡 The Core Idea

**In plain English:** Instead of keeping the entire phone book 📕 even for missing entries, keep an index 📇 that tells you which pages of the phone book actually have entries. If an entire page is empty, don't print that page at all! The index page takes very little space.

**In technical terms:** Chop the page table into page-sized chunks. If an entire chunk contains only invalid entries, don't allocate that chunk. Use a **page directory** to track which chunks exist.

**The transformation:**
```
Linear Page Table                    Multi-Level Page Table
─────────────────                    ──────────────────────

One big array:                       Tree structure:
┌────────────┐
│ PTE 0      │                       ┌──────────────┐
│ PTE 1      │                       │ Page         │
│ PTE 2      │                       │ Directory    │
│ PTE 3      │                       │              │
│ (valid)    │                       │ [PDE 0] ────────┐
├────────────┤                       │ [PDE 1] X    │  │
│ PTE 4      │                       │ [PDE 2] X    │  │
│ PTE 5      │                       │ [PDE 3] ────────┼──┐
│ ...        │                       └──────────────┘  │  │
│ PTE 999    │                       Small! Fits in   │  │
│ (invalid)  │                       one page         │  │
├────────────┤                                        │  │
│ PTE 1000   │                       ┌────────────┐   │  │
│ PTE 1001   │                    ┌──│ Page of PT │   │  │
│ (valid)    │                    │  │ [PTE 0-63] │◄──┘  │
└────────────┘                    │  └────────────┘      │
                                  │                      │
All entries allocated             │  ┌────────────┐      │
(huge memory use!)                └──│ Page of PT │◄─────┘
                                     │ [PTE 192+] │
                                     └────────────┘

                                     Only used pages allocated!
                                     (massive savings!)
```

**Key advantages:** ✅
1. **Proportional allocation** - Memory used proportional to actual address space usage
2. **Page-sized units** - Each piece fits in a page (easy to allocate)
3. **No external fragmentation** - All chunks same size
4. **Supports sparse spaces** - Works for any address space layout

**Key disadvantages:** ❌
1. **Complexity** - More complex lookup logic
2. **Time-space trade-off** - TLB miss now requires multiple memory accesses

> **💡 Insight**
>
> **Time-space trade-offs** are fundamental in data structures:
> - Hash tables: Fast lookups (O(1)) but waste space on empty buckets
> - Balanced trees: Slower lookups (O(log n)) but compact storage
> - Multi-level page tables: Slower on TLB miss (2+ memory accesses) but much smaller
>
> **The TLB is crucial here:** On TLB hit (common case), speed is identical. Only on TLB miss do we pay the multi-level lookup cost.

### 4.2. 🔧 How Multi-Level Tables Work

**Simple Example - Two levels:**

**Setup:**
- 16KB virtual address space (14 bits)
- 64-byte pages (6-bit offset)
- 8-bit VPN (256 pages total)
- 4-byte PTEs

**Page table organization:**
```
Linear page table: 256 PTEs × 4 bytes = 1024 bytes
Page size: 64 bytes
PTEs per page: 64 / 4 = 16 PTEs

1024-byte table ÷ 64-byte pages = 16 pages of page table
→ Need 16 entries in page directory
→ Page directory index: 4 bits (log₂ 16)
```

**Virtual address breakdown:**
```
13 12 11 10  9  8  7  6  5  4  3  2  1  0
├──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┘
│              │                  │
PD Index       PT Index           Offset
(4 bits)       (4 bits)           (6 bits)
16 pages       16 PTEs/page       64-byte page
```

**Translation algorithm:**

**Step 1:** Extract page directory index
```c
PDIndex = (VPN & PD_MASK) >> PD_SHIFT
        = (VPN & 0xF0) >> 4
```

**Step 2:** Look up page directory entry
```c
PDEAddr = PageDirBase + (PDIndex × sizeof(PDE))
PDE = Memory[PDEAddr]

if (!PDE.valid) {
    raise SEGMENTATION_FAULT  // No page table allocated
}
```

**Step 3:** Extract page table index
```c
PTIndex = VPN & PT_MASK
        = VPN & 0x0F
```

**Step 4:** Look up page table entry
```c
PTEAddr = (PDE.PFN << SHIFT) + (PTIndex × sizeof(PTE))
PTE = Memory[PTEAddr]

if (!PTE.valid) {
    raise SEGMENTATION_FAULT  // No physical page mapped
}
```

**Step 5:** Form physical address
```c
PhysAddr = (PTE.PFN << SHIFT) | Offset
```

**Visual walkthrough:**
```
Virtual Address: 0x3F80 (binary: 11 1111 10 000000)
                                 │   │   │     │
                        PD Idx=15 ─┘   │   │     └─ Offset=0
                                 PT Idx=14 ─┘

Step 1: Page Directory Lookup
────────────────────────────────
PageDirBase = 0x200 (physical)
PDIndex = 15
PDEAddr = 0x200 + (15 × 4) = 0x23C

Memory[0x23C] = {valid=1, PFN=101}  ✅

Step 2: Page Table Lookup
──────────────────────────
PT Base = 101 << 6 = 0x1940
PTIndex = 14
PTEAddr = 0x1940 + (14 × 4) = 0x1978

Memory[0x1978] = {valid=1, PFN=55}  ✅

Step 3: Physical Address
─────────────────────────
PhysAddr = (55 << 6) | 0
         = 0x0DC0

Access Memory[0x0DC0] 🎯
```

### 4.3. 📝 Detailed Multi-Level Example

**Scenario:** Address space with sparse usage

```
16KB Virtual Address Space (VPN 0-255)
───────────────────────────────────────
VPN 0-1:     Code (valid)      ← Page 0 of PT
VPN 2-15:    (unused)          ← Page 0 of PT
VPN 16-239:  (unused)          ← Pages 1-14 NOT ALLOCATED
VPN 240-253: (unused)          ← Page 15 of PT
VPN 254-255: Stack (valid)     ← Page 15 of PT
```

**Page Directory (16 entries):**
```
Index  Valid?  PFN   What it points to
─────  ──────  ───   ─────────────────
0      1       100   First page of PT (VPNs 0-15)
1      0       —     Not allocated
2      0       —     Not allocated
3      0       —     Not allocated
4      0       —     Not allocated
5      0       —     Not allocated
6      0       —     Not allocated
7      0       —     Not allocated
8      0       —     Not allocated
9      0       —     Not allocated
10     0       —     Not allocated
11     0       —     Not allocated
12     0       —     Not allocated
13     0       —     Not allocated
14     0       —     Not allocated
15     1       101   Last page of PT (VPNs 240-255)
```

**Page of PT at PFN=100 (VPNs 0-15):**
```
PT Index  VPN  Valid?  Prot   PFN
────────  ───  ──────  ────   ───
0         0    1       r-x    10   ← Code page 0
1         1    1       r-x    23   ← Code page 1
2         2    0       —      —
3         3    0       —      —
4         4    0       —      —
5         5    0       —      —
6         6    0       —      —
7         7    0       —      —
8         8    0       —      —
9         9    0       —      —
10        10   0       —      —
11        11   0       —      —
12        12   0       —      —
13        13   0       —      —
14        14   0       —      —
15        15   0       —      —
```

**Page of PT at PFN=101 (VPNs 240-255):**
```
PT Index  VPN  Valid?  Prot   PFN
────────  ───  ──────  ────   ───
0         240  0       —      —
1         241  0       —      —
2         242  0       —      —
3         243  0       —      —
4         244  0       —      —
5         245  0       —      —
6         246  0       —      —
7         247  0       —      —
8         248  0       —      —
9         249  0       —      —
10        250  0       —      —
11        251  0       —      —
12        252  0       —      —
13        253  0       —      —
14        254  1       rw-    86   ← Stack page 0
15        255  1       rw-    15   ← Stack page 1
```

**Memory savings calculation:**
```
Linear Page Table
─────────────────
256 PTEs × 4 bytes = 1024 bytes = 16 pages worth

Multi-Level Page Table
──────────────────────
Page directory:    16 PDEs × 4 bytes = 64 bytes = 1 page
PT page 0:        16 PTEs × 4 bytes = 64 bytes = 1 page
PT page 15:       16 PTEs × 4 bytes = 64 bytes = 1 page
────────────────────────────────────────────────────────
Total:                              192 bytes = 3 pages

Savings: 16 pages → 3 pages (81% reduction! 🎉)
```

> **💡 Insight**
>
> The **savings grow with address space size**. For a 32-bit address space with sparse usage:
> - Linear: 4MB (always)
> - Multi-level: Maybe 12KB (thousands of times smaller!)
>
> This is why every modern OS uses multi-level page tables: x86, ARM, RISC-V, PowerPC.

### 4.4. 🏗️ More Than Two Levels

**When two levels aren't enough:**

**Problem:** Even the page directory might not fit in one page!

**Example - 30-bit address space, 512-byte pages:**
```
Virtual address: 30 bits
Page size:       512 bytes (9-bit offset)
VPN:            21 bits (2,097,152 pages)

PTE size:       4 bytes
PTEs per page:  512 / 4 = 128 PTEs
PT index bits:  7 bits (log₂ 128)

VPN breakdown:
30 29 28 27 26 ... 10 9 8 7 6 5 4 3 2 1 0
├──┴──┴──┴──┴──────┴──┴─┴─┴─┴─┴─┴─┴─┴─┴─┘
│                     │         │
PD Index (14 bits)    PT Index  Offset
                      (7 bits)  (9 bits)

Page Directory Problem
──────────────────────
PD entries needed: 2^14 = 16,384 PDEs
PD size: 16,384 × 4 = 65,536 bytes = 128 pages

Won't fit in one page! 😱
```

**Solution:** Add a third level!

```
Three-Level Page Table
──────────────────────
30 29 28 27 26 ... 16 15 ... 9 8 7 6 5 4 3 2 1 0
├──┴──┴──┴──┴──────┴──┴──────┴──┴─┴─┴─┴─┴─┴─┴─┘
│                  │           │         │
PD Index 0         PD Index 1  PT Index  Offset
(7 bits)           (7 bits)    (7 bits)  (9 bits)

Translation process:
1. Use PD Index 0 → Get PD level 1 entry → Points to PD level 2
2. Use PD Index 1 → Get PD level 2 entry → Points to actual PT
3. Use PT Index   → Get PTE             → Get physical page
4. Use Offset     → Get byte in page
```

**Visual representation:**
```
Level 1 PD         Level 2 PDs              Page Tables
──────────         ───────────              ───────────
┌─────┐            ┌─────┐                  ┌─────┐
│ [0] │────────────│ [0] │──────────────────│ PTE │
├─────┤            ├─────┤                  ├─────┤
│ [1] │──┐         │ [1] │  ┌───────────────│ PTE │
├─────┤  │         ├─────┤  │               └─────┘
│ [2] │  │         │ ... │  │
├─────┤  │         └─────┘  │               ┌─────┐
│ ... │  │                  └───────────────│ PTE │
└─────┘  │                                  ├─────┤
         │         ┌─────┐                  │ PTE │
         └─────────│ [0] │                  └─────┘
                   ├─────┤
                   │ [1] │──────────────────┐
                   ├─────┤                  │
                   │ ... │                  ↓
                   └─────┘               ┌─────┐
                                         │ PTE │
Fits in 1 page    Each fits in 1 page   └─────┘
```

**Modern architectures:**
```
Architecture  Levels  Page Size  Notes
────────────  ──────  ─────────  ─────────────────────────
x86 (32-bit)  2       4KB        Classic two-level
x86-64        4       4KB        48-bit addresses
ARM64         3-4     4KB/16KB   Configurable
RISC-V        3-5     4KB        Depends on mode (Sv39/Sv48)

Trend: Deeper trees for larger address spaces
```

> **💡 Insight**
>
> **Deeper trees = more TLB misses hurt more**. Each level adds one memory access:
> - 2-level: TLB miss = 2 memory accesses (PD + PT)
> - 3-level: TLB miss = 3 memory accesses
> - 4-level: TLB miss = 4 memory accesses
>
> This makes **TLB hit rate even more critical**. Modern CPUs use huge TLBs (hundreds of entries) and multiple TLB levels to avoid expensive page walks.

### 4.5. 🔄 Translation Process with TLB

**Complete control flow (hardware-managed TLB):**

```c
// Address translation with two-level page table
VPN = (VirtualAddress & VPN_MASK) >> SHIFT

// FAST PATH: TLB lookup
(Success, TlbEntry) = TLB_Lookup(VPN)
if (Success == True) {  // ⚡ TLB Hit (~99% of accesses)
    if (CanAccess(TlbEntry.ProtectBits) == True) {
        Offset = VirtualAddress & OFFSET_MASK
        PhysAddr = (TlbEntry.PFN << SHIFT) | Offset
        Register = AccessMemory(PhysAddr)
        // DONE - Single memory access! 🎉
    } else {
        RaiseException(PROTECTION_FAULT)
    }
} else {  // 🐌 TLB Miss (~1% of accesses)

    // Step 1: Page Directory lookup (MEMORY ACCESS #1)
    PDIndex = (VPN & PD_MASK) >> PD_SHIFT
    PDEAddr = PDBR + (PDIndex * sizeof(PDE))
    PDE = AccessMemory(PDEAddr)  // 💾 Memory access

    if (PDE.Valid == False) {
        RaiseException(SEGMENTATION_FAULT)  // Page table doesn't exist
    } else {

        // Step 2: Page Table lookup (MEMORY ACCESS #2)
        PTIndex = (VPN & PT_MASK) >> PT_SHIFT
        PTEAddr = (PDE.PFN << SHIFT) + (PTIndex * sizeof(PTE))
        PTE = AccessMemory(PTEAddr)  // 💾 Memory access

        if (PTE.Valid == False) {
            RaiseException(SEGMENTATION_FAULT)  // Page not mapped
        } else if (CanAccess(PTE.ProtectBits) == False) {
            RaiseException(PROTECTION_FAULT)
        } else {
            // Update TLB for future accesses
            TLB_Insert(VPN, PTE.PFN, PTE.ProtectBits)

            // Retry instruction (will hit TLB this time)
            RetryInstruction()
        }
    }
}
```

**Performance analysis:**
```
TLB Hit (Common Case)
─────────────────────
Memory accesses: 1 (actual data)
Time: ~100 CPU cycles

TLB Miss (Rare Case)
────────────────────
Memory accesses: 3 (PDE + PTE + data)
Time: ~300 CPU cycles

With 99% TLB hit rate:
Average = 0.99 × 100 + 0.01 × 300
        = 99 + 3
        = 102 cycles (only 2% overhead!)

With 90% TLB hit rate:
Average = 0.90 × 100 + 0.10 × 300
        = 90 + 30
        = 120 cycles (20% overhead 😬)

TLB effectiveness is CRITICAL! 🎯
```

**Optimization - TLB reach:**
```
TLB Reach = TLB entries × Page size
────────────────────────────────────

64-entry TLB, 4KB pages:
Reach = 64 × 4KB = 256KB

Can access 256KB without TLB miss! ✅
Working set > 256KB → More misses 😢

Larger pages help:
64-entry TLB, 2MB huge pages:
Reach = 64 × 2MB = 128MB

Can access 128MB without TLB miss! 🚀
```

> **💡 Insight**
>
> **Why multi-level tables work:** They leverage **locality**:
> - **Temporal locality:** Recently accessed pages likely accessed again (TLB helps)
> - **Spatial locality:** Nearby pages likely accessed together (same PT page)
>
> Programs don't randomly access memory. They cluster accesses in small regions. Multi-level tables exploit this by only allocating page table pages for active regions.

---

## 5. 🔄 Inverted Page Tables

**In plain English:** Instead of one page table per process (process → physical mapping), keep one page table for the entire system (physical → process mapping). Each entry describes one physical page: "Physical page 42 belongs to process 7's virtual page 100."

**The radical difference:**
```
Traditional Page Table             Inverted Page Table
─────────────────────             ───────────────────

Per-process:                      System-wide:
┌─────────────────┐               ┌─────────────────┐
│ Process 1: 4MB  │               │ Global: 256KB   │
│ Process 2: 4MB  │               │                 │
│ Process 3: 4MB  │               │ One entry per   │
│ ...             │               │ physical page   │
│ Process 100:4MB │               │                 │
└─────────────────┘               └─────────────────┘
Total: 400MB                      Total: 256KB

Size grows with:                  Size grows with:
Virtual addr space × Processes    Physical memory
```

**Inverted page table structure:**
```
Physical Memory (64MB = 16K pages @ 4KB)
────────────────────────────────────────
Inverted Page Table: 16K entries

Entry Format:
┌────────┬─────┬──────┬──────┐
│ PID    │ VPN │ Prot │ ...  │
└────────┴─────┴──────┴──────┘

Example entries:
Index (PFN)  PID    VPN     Prot   Meaning
───────────  ─────  ──────  ────   ─────────────────────────
0            7      1024    rw-    PFN 0 → Process 7, VPN 1024
1            7      1025    rw-    PFN 1 → Process 7, VPN 1025
2            42     0       r-x    PFN 2 → Process 42, VPN 0
3            42     1       r-x    PFN 3 → Process 42, VPN 1
...
16383        7      8191    rw-    PFN 16383 → Process 7, VPN 8191
```

**Translation process (the challenge):**
```
Traditional: VPN → index into PT → PFN (simple array lookup)
Inverted:    VPN → search for matching (PID,VPN) → find index=PFN

Translation with inverted table:
──────────────────────────────────
Virtual address: VPN=1024 (Process 7)

Linear search (TOO SLOW):
for (pfn = 0; pfn < 16384; pfn++) {
    if (IPT[pfn].pid == 7 && IPT[pfn].vpn == 1024) {
        return pfn;  // Found at PFN 0
    }
}
// Terrible: O(N) per memory access! 💀

Hash table solution:
hash = Hash(PID=7, VPN=1024)
bucket = HashTable[hash]
search bucket for (PID=7, VPN=1024)
if found:
    return bucket_entry.pfn
else:
    page fault
// Better: O(1) average case ✅
```

**Pros and cons:**

**Advantages:** ✅
- **Extreme space savings** - Size = physical memory, not virtual spaces
- **Fixed size** - Doesn't grow with more processes
- **Good for memory-constrained systems**

**Disadvantages:** ❌
- **Slow lookups** - Need hash table (can have collisions)
- **TLB critical** - TLB miss is very expensive
- **Shared pages complex** - Multiple (PID,VPN) map to same PFN

**Real-world usage:**
```
Architecture  Uses IPT?  Notes
────────────  ────────   ─────────────────────────────────
PowerPC       Yes        Early adopter (IBM RS/6000)
IA-64         Optional   Can use IPT or multi-level
x86           No         Multi-level only
ARM           No         Multi-level only
RISC-V        No         Multi-level only

Conclusion: Inverted page tables are rare today
Multi-level tables won the trade-off battle
```

> **💡 Insight**
>
> **Inverted page tables show extremes have costs:**
> - Traditional: Space proportional to virtual address space (can be huge)
> - Multi-level: Good balance (space proportional to usage, reasonable lookup)
> - Inverted: Space proportional to physical memory (minimal), but lookups are complex
>
> The "middle ground" (multi-level) usually wins. This pattern appears everywhere: balanced trees vs hash tables, hybrid sorting algorithms, etc.

---

## 6. 💾 Swapping Page Tables to Disk

**In plain English:** What if even our clever multi-level page tables are too big? We can use virtual memory for the page tables themselves! 🤯 Put page tables in kernel virtual memory and swap parts to disk when memory is tight.

**Recursive virtualization:**
```
Normal paging:              Paging the page tables:
──────────────              ───────────────────────
User data → Virtual         Page tables → Virtual
         ↓                               ↓
     Physical                        Physical
                                         ↓
                                      (can swap to disk!)

It's turtles all the way down! 🐢
```

**How it works:**
```
Kernel Virtual Memory Layout
────────────────────────────
┌─────────────────┐
│ Kernel Code     │ (always resident)
├─────────────────┤
│ Core Data Structures │ (always resident)
├─────────────────┤
│                 │
│ Page Tables     │ ← Can be swapped!
│ (processes 1-N) │
│                 │
├─────────────────┤
│ Other buffers   │
└─────────────────┘

When memory tight:
1. Swap out unused page table pages
2. Mark them as swapped in kernel PT
3. On access → page fault → swap back in
```

**Implications:**

**Positive:** ✅
- Can support more processes than physical memory allows
- Page tables for idle processes can be swapped out

**Negative:** ❌
- Page faults can now happen during page table walks!
- Multi-level lookup can trigger multiple page faults
- Complexity increases dramatically

**Historical example: VAX/VMS** 🏛️
```
VAX/VMS (1970s-1980s)
─────────────────────
Used kernel virtual memory for page tables
Allowed extreme overcommitment
Could run 100+ processes on 4MB physical memory
(by swapping everything, including page tables)

Performance could be terrible 🐌
But enabled timesharing on tiny machines
```

> **💡 Insight**
>
> **Meta-levels in systems design:** Using a mechanism to manage itself:
> - Virtual memory for page tables (paging the paging mechanism)
> - Databases storing their own metadata as tables
> - Compilers that compile themselves (bootstrapping)
>
> This self-reference adds power but also complexity. Use it when the benefits (flexibility, generality) outweigh the costs (complexity, potential overhead).

---

## 7. 📝 Summary

**The Page Table Size Problem:** 📊
```
32-bit address space, 4KB pages, 4-byte PTEs
→ 4MB page table per process
→ 100 processes = 400MB just for page tables! 😱
```

**Solutions Compared:**

### 📏 Bigger Pages
```
Pros: Simple, fewer entries
Cons: Internal fragmentation
Verdict: Limited use (huge pages for specific apps)
```

### 🔀 Hybrid (Paging + Segmentation)
```
Pros: Saves space for sparse regions
Cons: External fragmentation, assumes layout
Verdict: Clever but limited applicability
```

### 🌳 Multi-Level Page Tables ⭐
```
Pros:
  ✅ Space proportional to usage
  ✅ All pieces page-sized (easy allocation)
  ✅ Works with any address space layout
  ✅ No external fragmentation

Cons:
  ❌ Complex implementation
  ❌ TLB miss requires multiple memory accesses
  ❌ Time-space trade-off

Verdict: Winner! Used by all modern CPUs
```

### 🔄 Inverted Page Tables
```
Pros: Minimal size (= physical memory)
Cons: Slow lookups, requires hash table
Verdict: Rare (PowerPC used it)
```

**Key Insights:** 💡

**1. Data Structure Trade-offs**
```
Space Efficiency ←→ Time Efficiency
────────────────────────────────
Linear PT:      Fast (array index)     Huge (always 4MB)
Multi-level PT: Slower (tree walk)     Compact (proportional)
Inverted PT:    Slowest (hash search)  Minimal (= physical)
```

**2. The TLB Saves Everything** ⚡
```
With TLB hit (99%):     All approaches identical (1 memory access)
With TLB miss (1%):     Multi-level pays penalty (2-4 memory accesses)

TLB effectiveness makes complex page tables viable!
```

**3. Common Patterns in Systems**
- **Sparse data structures:** Don't allocate unused entries
- **Hierarchical organization:** Trees/indices for large datasets
- **Indirection layers:** Add levels to enable flexibility
- **Time-space trade-offs:** Faster access ↔ more memory

**Modern Practice:** 🖥️
```
x86-64: 4-level page tables
ARM64:  3-4 level page tables
RISC-V: 3-5 level page tables (Sv39/Sv48/Sv57)

Everyone uses multi-level!
```

**What's Next:** 🚀

With efficient page tables in place, we can explore:
- **Swapping:** 💾 Moving pages to/from disk
- **Page replacement policies:** 🎯 Which pages to evict
- **Working sets:** 📊 Understanding program memory behavior
- **Thrashing:** 💥 When paging goes wrong

**Final Thought:**
```
╔════════════════════════════════════════════════════════╗
║  "The best data structure is the one that solves      ║
║   your problem with acceptable trade-offs."           ║
║                                                        ║
║  Multi-level page tables:                             ║
║  - Compact for sparse address spaces ✅               ║
║  - Fast with TLB (common case) ✅                     ║
║  - Complex but manageable ✅                          ║
║                                                        ║
║  A triumph of practical systems design! 🎉            ║
╚════════════════════════════════════════════════════════╝
```

> **💡 Final Insight**
>
> **Page tables are "just" a data structure**, but their design shaped computer architecture for decades. The lessons learned—sparse structures, multi-level indexing, hardware-software co-design—apply far beyond virtual memory. Every systems programmer should understand these trade-offs.

---

**Previous:** [Chapter 14: TLBs](chapter14-tlbs.md) | **Next:** [Chapter 16: Swapping Mechanisms](chapter16-swapping-mechanisms.md)
