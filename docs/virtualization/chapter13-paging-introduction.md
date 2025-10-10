# Chapter 13: Paging - Introduction 📄

_How fixed-size chunks solve the fragmentation problem_

---

## 📋 Table of Contents

1. [🎯 Introduction](#1-introduction)
   - 1.1. [The Fragmentation Problem](#11-the-fragmentation-problem)
   - 1.2. [The Paging Solution](#12-the-paging-solution)
2. [🖼️ A Simple Example and Overview](#2-a-simple-example-and-overview)
   - 2.1. [Virtual Pages and Physical Frames](#21-virtual-pages-and-physical-frames)
   - 2.2. [The Page Table](#22-the-page-table)
   - 2.3. [Address Translation Example](#23-address-translation-example)
3. [💾 Where Are Page Tables Stored?](#3-where-are-page-tables-stored)
   - 3.1. [Size Calculations](#31-size-calculations)
   - 3.2. [Storage Location](#32-storage-location)
4. [🗂️ What's Actually in the Page Table?](#4-whats-actually-in-the-page-table)
   - 4.1. [Linear Page Table Structure](#41-linear-page-table-structure)
   - 4.2. [Page Table Entry Bits](#42-page-table-entry-bits)
   - 4.3. [x86 Page Table Entry](#43-x86-page-table-entry)
5. [⚡ Paging: Also Too Slow](#5-paging-also-too-slow)
   - 5.1. [Performance Cost](#51-performance-cost)
   - 5.2. [Memory Access Protocol](#52-memory-access-protocol)
6. [🔍 A Memory Trace](#6-a-memory-trace)
   - 6.1. [Understanding the Code](#61-understanding-the-code)
   - 6.2. [Setting Up the Scenario](#62-setting-up-the-scenario)
   - 6.3. [Tracing Memory Accesses](#63-tracing-memory-accesses)
7. [📝 Summary](#7-summary)

---

## 1. 🎯 Introduction

### 1.1. The Fragmentation Problem

**In plain English:** Imagine you're organizing a closet 🚪 where you let people store boxes 📦 of different sizes. Person A takes 3 feet, Person B takes 1 foot, Person C takes 5 feet. Now Person B leaves, creating a 1-foot gap. When Person D arrives with a 4-foot box, it won't fit in that gap even though you have 6 total feet free (1 + 5 elsewhere). Your closet becomes like Swiss cheese 🧀—full of unusable holes.

**In technical terms:** Operating systems face two fundamental approaches when managing space:

```
Approach 1: Variable-Sized Pieces     Approach 2: Fixed-Sized Pieces
────────────────────────────────      ──────────────────────────────
Segmentation (Chapter 12)             Paging (this chapter)
↓                                     ↓
Code: 4KB                             All chunks: 4KB
Heap: 10KB                            Code: 1 page
Stack: 2KB                            Heap: 3 pages
                                      Stack: 1 page
Problem: Fragmentation ❌             Problem: None! ✅
```

**Why it matters:** Variable-sized segments lead to **external fragmentation**—free memory becomes scattered into small, unusable gaps. Over time, you might have plenty of total free memory but can't satisfy allocation requests because no single chunk is big enough. This is like having $100 in pennies when someone asks for a $5 bill.

> **💡 Insight**
>
> The **fixed-size vs variable-size** trade-off appears throughout computer science:
> - **Memory:** Pages (fixed) vs Segments (variable)
> - **Disk:** Blocks (fixed) vs Extents (variable)
> - **Networks:** Fixed packets vs Variable frames
> - **Databases:** Fixed-width records vs Variable-length records
>
> Fixed sizes simplify allocation but may waste space. Variable sizes use space efficiently but complicate management. This tension drives many system design decisions.

### 1.2. 🧩 The Paging Solution

**In plain English:** Instead of letting people store oddly-shaped boxes, give everyone standardized containers 📦📦📦 all the same size. Now when someone leaves, their container slot can be filled by anyone else. No more Swiss cheese—just a grid of uniform slots that can be freely allocated.

**In technical terms:** **Paging** divides the virtual address space into fixed-size units called **pages** and physical memory into fixed-size units called **page frames** (or physical pages). Each page is typically 4KB (though sizes like 2MB and 1GB exist for "huge pages").

**The transformation:**

```
Segmentation (Variable)               Paging (Fixed)
───────────────────────               ──────────────
Virtual Address Space:                Virtual Address Space:
┌──────────────┐                      ┌──────────────┐
│ Code (4KB)   │                      │ Page 0 (4KB) │ ← Code
├──────────────┤                      ├──────────────┤
│ Heap (10KB)  │                      │ Page 1 (4KB) │ ← Heap
│              │                      ├──────────────┤
│              │                      │ Page 2 (4KB) │ ← Heap
│              │                      ├──────────────┤
├──────────────┤                      │ Page 3 (4KB) │ ← Heap
│ Stack (2KB)  │                      ├──────────────┤
└──────────────┘                      │ Page 4 (4KB) │ ← Stack (partial)
                                      └──────────────┘

Maps to Physical Memory:              Maps to Physical Memory:
Complex, must find                    Simple, find any N free
contiguous chunks ❌                  frames ✅
```

### 🎯 The Core Challenge

**THE CRUX:** How can we virtualize memory with pages, avoiding segmentation's problems? What are the basic techniques? How do we make them work efficiently with minimal space and time overhead?

**Key advantages of paging:**

1. **No external fragmentation** 🎉
   - All chunks are same size
   - Any free frame works for any page

2. **Flexibility** 🤸
   - Sparse address spaces work naturally
   - Don't need to know heap/stack growth direction
   - Pages can be scattered anywhere in physical memory

3. **Simplicity** 🔧
   - Free-space management is trivial
   - Just maintain a list of free frames
   - Allocation = grab N frames from list

> **💡 Insight**
>
> Paging trades **space overhead** (page tables can be huge) for **management simplicity** (no fragmentation). This is a classic OS design pattern: use a data structure (page table) to solve an allocation problem (fragmentation). You'll see this repeatedly—OS designers love using clever data structures to transform hard problems into simple table lookups.

---

## 2. 🖼️ A Simple Example and Overview

### 2.1. 🔍 Virtual Pages and Physical Frames

Let's start with a tiny example to build intuition before scaling to realistic sizes.

**Example setup:**
- **Virtual address space:** 64 bytes (tiny! 🐜)
- **Page size:** 16 bytes
- **Number of virtual pages:** 64 ÷ 16 = 4 pages
- **Physical memory:** 128 bytes
- **Number of physical frames:** 128 ÷ 16 = 8 frames

**Virtual address space layout:**

```
Address    Content               Page Number
──────────────────────────────────────────────
0-15       Page 0 (code)         VPN 0
16-31      Page 1 (heap)         VPN 1
32-47      Page 2 (stack)        VPN 2
48-63      Page 3 (unused)       VPN 3
```

**In plain English:** Think of the virtual address space as an apartment building 🏢 with 4 units (pages). Each unit is exactly 16 square feet (bytes). The building's address is 0-63 Main Street. But these are just virtual addresses—the actual furniture (data) is stored in a warehouse 🏭 elsewhere.

**Physical memory layout:**

```
Frame #    Address       Contents
────────────────────────────────────
0          0-15          OS Reserved 🔒
1          16-31         OS Reserved 🔒
2          32-47         Page 3 (VPN 3) 📦
3          48-63         Page 0 (VPN 0) 📦
4          64-79         (unused/free) ⬜
5          80-95         Page 2 (VPN 2) 📦
6          96-111        (unused/free) ⬜
7          112-127       Page 1 (VPN 1) 📦
```

**Observation:** Virtual pages are scattered throughout physical memory! 🎯

- Virtual Page 0 → Physical Frame 3
- Virtual Page 1 → Physical Frame 7
- Virtual Page 2 → Physical Frame 5
- Virtual Page 3 → Physical Frame 2

This is the **power of paging**: pages don't need to be contiguous in physical memory. The OS can place them anywhere, eliminating fragmentation.

**Visual representation:**

```
Virtual Address Space        Physical Memory
(Process's view)            (Hardware reality)

┌─────────────┐              ┌─────────────┐
│  Page 0     │──────┐       │  Frame 0    │ (OS) 🔒
│  (Code)     │      │       ├─────────────┤
├─────────────┤      │       │  Frame 1    │ (OS) 🔒
│  Page 1     │──┐   │       ├─────────────┤
│  (Heap)     │  │   │       │  Frame 2    │ ← Page 3 📦
├─────────────┤  │   │       ├─────────────┤
│  Page 2     │┐ │   └──────→│  Frame 3    │ ← Page 0 📦
│  (Stack)    ││ │            ├─────────────┤
├─────────────┤│ │            │  Frame 4    │ (free) ⬜
│  Page 3     ││ │            ├─────────────┤
│  (unused)   ││ └───────────→│  Frame 5    │ ← Page 2 📦
└─────────────┘└─────────────→├─────────────┤
                              │  Frame 6    │ (free) ⬜
                              ├─────────────┤
                              │  Frame 7    │ ← Page 1 📦
                              └─────────────┘
```

### 2.2. 🗺️ The Page Table

**In plain English:** The page table is like a directory 📖 that tells you "if you want to visit Virtual Apartment 0, the actual furniture is in Warehouse Slot 3." It's a mapping from virtual page numbers to physical frame numbers.

**In technical terms:** The operating system maintains a **per-process data structure** called a **page table** that stores address translations for each virtual page. This is critical: each process has its own page table, giving it a private virtual address space.

**Our example's page table:**

```
Virtual Page    →    Physical Frame
────────────────────────────────────
VPN 0                PFN 3
VPN 1                PFN 7
VPN 2                PFN 5
VPN 3                PFN 2
```

**Per-process isolation:**

```
Process A's Page Table         Process B's Page Table
──────────────────────         ──────────────────────
VPN 0 → PFN 3                  VPN 0 → PFN 8
VPN 1 → PFN 7                  VPN 1 → PFN 12
VPN 2 → PFN 5                  VPN 2 → PFN 15
VPN 3 → PFN 2                  VPN 3 → PFN 9

Both processes can use             But they map to
virtual address 0 ✅              different physical memory ✅
```

**Why this matters:** Two processes can both use virtual address 0 without conflict. The page table ensures they access different physical memory. This provides **memory isolation** 🔒—Process A cannot accidentally (or maliciously) access Process B's data.

> **💡 Insight**
>
> The **page table is a level of indirection** that solves multiple problems:
> 1. **Protection:** Each process has isolated memory
> 2. **Flexibility:** Pages can be anywhere in physical memory
> 3. **Sharing:** Multiple processes can map to same physical frame (for shared libraries)
> 4. **Virtualization:** Total virtual memory can exceed physical memory (via swapping)
>
> This demonstrates a fundamental CS principle: "All problems in computer science can be solved by another level of indirection" (except the problem of too many levels of indirection 😄).

### 2.3. 🔄 Address Translation Example

**Step 1: Understanding the virtual address structure** 🧮

Let's translate virtual address **21** to its physical address.

First, we need to break down the 6-bit virtual address:

```
Virtual address: 21 (decimal) = 010101 (binary)

┌─────────────┬──────────────┐
│     VPN     │    Offset    │
├─────────────┼──────────────┤
│   0  1      │ 0  1  0  1   │
└─────────────┴──────────────┘
  2 bits         4 bits

VPN = 01 (binary) = 1 (decimal)
Offset = 0101 (binary) = 5 (decimal)
```

**Why this split?**

- **Page size = 16 bytes** → Need 4 bits to address within a page (2^4 = 16)
- **4 pages total** → Need 2 bits to select page (2^2 = 4)
- **Total = 6 bits** (2 + 4)

**In plain English:** Virtual address 21 means "byte 5 of virtual page 1" 📍. It's like saying "Apartment 1, 5 feet from the entrance."

**Step 2: Look up the page table** 📖

```
Page Table Lookup:
──────────────────
VPN 1 → PFN 7
```

Virtual page 1 is stored in physical frame 7.

**Step 3: Construct the physical address** 🏗️

Replace the VPN with the PFN, keep the offset the same:

```
Virtual Address              Physical Address
───────────────              ────────────────
VPN    Offset                PFN     Offset
01     0101         →        111     0101

Decimal: 21                  Decimal: 117
```

**Calculation:**
- Physical address = (PFN × Page Size) + Offset
- Physical address = (7 × 16) + 5
- Physical address = 112 + 5 = **117** ✅

**Step 4: Access the memory** 💾

```assembly
movl 21, %eax    # Process issues this instruction
```

**What happens:**

```
1. CPU sees virtual address 21
2. MMU extracts VPN = 1, Offset = 5
3. MMU looks up page table: VPN 1 → PFN 7
4. MMU constructs physical address: 117
5. Memory controller fetches byte at physical address 117
6. Data loaded into register %eax ✅
```

**Complete translation diagram:**

```
Virtual Address 21 (010101)
        │
        ├─────────────────────────┐
        │                         │
    VPN = 01                  Offset = 0101
        │                         │
        ↓                         │
   Page Table                     │
   ┌──────────┐                   │
   │ VPN 0→3  │                   │
   │ VPN 1→7  │ ← Lookup here     │
   │ VPN 2→5  │                   │
   │ VPN 3→2  │                   │
   └──────────┘                   │
        │                         │
    PFN = 111                     │
        │                         │
        └─────────────────────────┤
                                  ↓
        Physical Address 117 (1110101)
                                  ↓
                          Physical Memory[117]
```

> **💡 Insight**
>
> Notice that the **offset is never translated**—it stays the same in both virtual and physical addresses. This makes sense: if you want byte 5 of a page, it doesn't matter which frame that page lives in; you still want byte 5 of that frame. Only the page number changes during translation. This design simplifies the hardware and speeds up translation.

**Progressive example:**

**Simple:** Single memory access
```
Virtual address 21 → Physical address 117
```

**Intermediate:** Multiple accesses showing pattern
```
Virtual 0  (page 0, offset 0)  → Physical 48  (frame 3, offset 0)
Virtual 16 (page 1, offset 0)  → Physical 112 (frame 7, offset 0)
Virtual 21 (page 1, offset 5)  → Physical 117 (frame 7, offset 5)
Virtual 47 (page 2, offset 15) → Physical 95  (frame 5, offset 15)
```

**Advanced:** Understanding the full process
```c
// Pseudocode for address translation
uint32_t translate(uint32_t virtual_addr) {
    uint32_t vpn = virtual_addr >> 4;        // Upper 2 bits
    uint32_t offset = virtual_addr & 0xF;    // Lower 4 bits

    uint32_t pfn = page_table[vpn];          // Table lookup
    uint32_t physical_addr = (pfn << 4) | offset;

    return physical_addr;
}

// For virtual address 21:
// vpn = 21 >> 4 = 1
// offset = 21 & 0xF = 5
// pfn = page_table[1] = 7
// physical = (7 << 4) | 5 = 112 + 5 = 117
```

---

## 3. 💾 Where Are Page Tables Stored?

### 3.1. 📊 Size Calculations

**In plain English:** Our toy example had a tiny 4-entry page table. But real computers? The page tables are **enormous** 🐘—so big they make our tiny CPU caches look like Post-it notes compared to encyclopedias.

**Realistic example: 32-bit address space with 4KB pages**

Let's calculate:

```
Address space:  32 bits  → 2^32 = 4GB virtual memory
Page size:      4KB      → 2^12 = 4096 bytes per page

How many pages?
───────────────
4GB ÷ 4KB = 2^32 ÷ 2^12 = 2^20 = 1,048,576 pages 😱

Virtual address breakdown:
┌────────────────────┬──────────────┐
│    VPN             │   Offset     │
│   20 bits          │   12 bits    │
└────────────────────┴──────────────┘
```

**Page table size:**

```
Entries needed:    2^20 = 1,048,576 entries
Bytes per entry:   4 bytes (to store PFN + flags)
                   ─────────────────────────────
Total size:        4MB per process! 📏
```

**Impact with multiple processes:**

```
Processes Running    Page Table Memory
─────────────────    ─────────────────
1                    4MB
10                   40MB
100                  400MB ⚠️
1000                 4GB 💥
```

**Even worse: 64-bit address space**

```
If we used the same approach for 64-bit...

Address space: 64 bits → 2^64 = 16 exabytes
Page size: 4KB

Pages needed: 2^64 ÷ 2^12 = 2^52 = 4,503,599,627,370,496 pages
Page table size: 2^52 × 8 bytes = 36 petabytes 💀

(Don't worry, we use multi-level page tables for 64-bit, covered later!)
```

> **💡 Insight**
>
> This size problem demonstrates why **flat structures don't scale**. A linear array works great for small problems (our 4-entry example) but becomes impractical as size grows. This is why later chapters introduce hierarchical page tables, inverted page tables, and other clever structures. The pattern: start simple, then optimize when the simple solution breaks.

### 3.2. 🏠 Storage Location

**Where NOT to store page tables:**

```
❌ In CPU registers
   - Too big! Modern CPUs have ~16-32 general-purpose registers
   - Our page table has 1,048,576 entries

❌ In CPU cache
   - Too big! L1 cache is ~32KB, L2 is ~256KB, L3 is ~8MB
   - Our page table is 4MB (won't fit, and we need cache for data!)

❌ In special MMU hardware
   - Older systems (like early VAX) tried this
   - Not scalable, expensive, inflexible
```

**Where page tables ARE stored:**

```
✅ In main memory (RAM)
   - Plenty of space (GBs available)
   - Flexible (OS can manage dynamically)
   - Per-process (different processes = different tables)
```

**Current architecture:**

```
┌─────────────────────────────────────┐
│         Physical Memory             │
├─────────────────────────────────────┤
│  OS Kernel Code & Data              │ 🔒
├─────────────────────────────────────┤
│  Process A's Page Table (4MB)       │ 📋
├─────────────────────────────────────┤
│  Process B's Page Table (4MB)       │ 📋
├─────────────────────────────────────┤
│  Process C's Page Table (4MB)       │ 📋
├─────────────────────────────────────┤
│  Process A's Actual Data/Code       │ 📦
├─────────────────────────────────────┤
│  Process B's Actual Data/Code       │ 📦
├─────────────────────────────────────┤
│  Process C's Actual Data/Code       │ 📦
└─────────────────────────────────────┘
```

**How the CPU finds the page table:**

```
Special CPU Register: Page Table Base Register (PTBR)
─────────────────────────────────────────────────────
Points to physical address where page table starts

When context switching from Process A → Process B:
1. Save Process A's state (including PTBR)
2. Load Process B's PTBR
3. Now all translations use Process B's page table ✅
```

**Interesting consequence:**

Page tables themselves reside at **physical addresses**, but the data they describe uses **virtual addresses**. This creates a bootstrapping question: "How do we look up the page table without already having translation working?" Answer: We store the page table's location as a physical address in PTBR, so no translation is needed to access the table itself.

> **💡 Insight**
>
> Storing page tables in regular RAM creates a recursive opportunity: page tables can themselves be **paged**! The OS can mark parts of a page table as "not present" and swap them to disk if memory is tight. When accessing an address that requires a paged-out page table entry, a page fault occurs to bring it back. This is "paging all the way down" 🐢🐢🐢.

---

## 4. 🗂️ What's Actually in the Page Table?

### 4.1. 📑 Linear Page Table Structure

**In plain English:** The simplest page table is just an array 📊. Use the virtual page number as the index, and the array value tells you the physical frame number. It's like looking up a word in a dictionary by flipping to the right letter.

**In technical terms:** A **linear page table** is an array indexed by VPN:

```c
// Conceptual page table structure
struct pte {
    uint32_t pfn : 20;      // Physical frame number (20 bits)
    uint32_t flags : 12;    // Various flags (12 bits)
};

struct pte page_table[1048576];  // 2^20 entries

// To translate:
physical_addr = page_table[vpn].pfn << 12 | offset;
```

**Array access:**

```
VPN                     PTE (Page Table Entry)
───                     ───────────────────────
0        →    page_table[0]    = {pfn: 42,  valid: 1, ...}
1        →    page_table[1]    = {pfn: 105, valid: 1, ...}
2        →    page_table[2]    = {pfn: 7,   valid: 1, ...}
...
1048575  →    page_table[1048575] = {pfn: 0, valid: 0, ...}
```

**Key characteristic:** Every VPN has an entry, even if that virtual page isn't used. This is why the table is so large—it's **dense** rather than **sparse**.

### 4.2. 🏷️ Page Table Entry Bits

**What information does each PTE contain beyond just the PFN?**

```
┌──────────┬───────────────────────────────────┐
│   PFN    │         Control Bits              │
├──────────┼───────────────────────────────────┤
│ 20 bits  │  12 bits (flags/metadata)         │
└──────────┴───────────────────────────────────┘
```

#### 1️⃣ Valid Bit (V)

**In plain English:** Is this page table entry actually being used? 🚦 Like a parking spot that's either occupied (valid) or available (invalid).

**Purpose:**
- Supports **sparse address spaces**
- Most of your address space is unused (the gap between heap ↑ and stack ↓)
- Invalid entries don't need physical frames allocated

**Example:**

```
Process Memory Layout               Page Table
─────────────────────               ──────────────────────
0x00000000: Code (16KB)             VPN 0-3:   Valid ✅
0x00004000: (64KB unused)           VPN 4-19:  Invalid ❌
0x00014000: Heap (4KB)              VPN 20:    Valid ✅
0x00015000: (huge gap)              VPN 21-...: Invalid ❌
...                                 ...
0x7FFFFF00: Stack (16KB)            VPN 524287: Valid ✅
```

**What happens on access to invalid page:**

```c
if (!page_table[vpn].valid) {
    raise_exception(SEGMENTATION_FAULT);  // 💥 SIGSEGV
    // Process terminated: "Segmentation fault (core dumped)"
}
```

This is why accessing a null pointer (virtual address 0, often marked invalid) crashes your program! 🐛

#### 2️⃣ Protection Bits (R/W/X)

**In plain English:** What operations are allowed on this page? 🛡️ Like permissions on a file—read only, write allowed, executable code?

**Three bits:**

```
R (Read)    - Can load data from this page?
W (Write)   - Can store data to this page?
X (Execute) - Can run code from this page?
```

**Example usage:**

```
Memory Region       Protection Bits      Rationale
─────────────       ───────────────      ─────────
Code section        R-X (read/execute)   Execute code, no modification
                                         Prevents code injection 🔒

Const data          R-- (read only)      Prevents accidental bugs
                                         Compiler enforces const

Heap/Stack          RW- (read/write)     Data manipulation
                                         No execution (prevents attacks)

Guard page          --- (no access)      Catch stack overflow 🚨
```

**Security benefit: W^X (Write XOR Execute)**

Modern systems enforce: a page is either **writable** or **executable**, never both. This prevents **code injection attacks** 🛡️.

```
Attack scenario (prevented):
1. Attacker writes malicious code to heap (writable) ✅
2. Attacker jumps to heap to execute code ❌ (not executable!)
   → CPU raises protection fault
   → Process terminated
```

#### 3️⃣ Present Bit (P)

**In plain English:** Is this page currently in physical memory 💾 or has it been swapped out to disk 💿? Like knowing if a book is on the shelf (present) or checked out (swapped).

**Two states:**

```
P = 1: Page is in physical memory
       → PFN is valid, can access immediately ✅

P = 0: Page is valid but swapped to disk
       → Must trigger page fault
       → OS loads page from disk → memory
       → Update PTE with new PFN
       → Retry instruction ✅
```

**Swapping example:**

```
Initial state:
VPN 5 → {PFN: 42, P: 1, V: 1}  ✅ In memory

Memory pressure, OS swaps page to disk:
VPN 5 → {Disk_Addr: 0x8A3000, P: 0, V: 1}  💿 On disk

Process accesses VPN 5:
1. MMU sees P=0 → Page Fault! 🚨
2. OS reads page from disk address 0x8A3000
3. OS finds free frame, loads page → Frame 105
4. OS updates PTE: {PFN: 105, P: 1, V: 1}
5. OS returns from exception
6. Instruction retries, now succeeds ✅
```

This mechanism enables **virtual memory larger than physical memory** 🎯!

#### 4️⃣ Dirty Bit (D)

**In plain English:** Has this page been modified since loading into memory? 📝 Like tracking if you've written in a library book (dirty) or just read it (clean).

**Purpose:** Optimization for swapping out pages

```
When evicting a page to free memory:

If D = 0 (clean):
    → Page identical to disk version
    → Just discard, don't write back ⚡ (fast!)

If D = 1 (dirty):
    → Page modified in memory
    → Must write back to disk 💾 (slower)
```

**Example:**

```c
// Load page from disk
load_page(vpn);
page_table[vpn].dirty = 0;  // Clean initially

// Process writes to page
store(virtual_addr, value);
page_table[vpn].dirty = 1;  // Mark dirty! ✍️

// Later, swap out this page
if (page_table[vpn].dirty) {
    write_to_disk(vpn);  // Must save changes
} else {
    // Just drop it, still on disk
}
```

**Performance impact:**

```
Evicting 1000 clean pages:  ~0ms (just mark as free)
Evicting 1000 dirty pages:  ~50ms (write to disk first)
                            ──────
                            50x slower! ⚠️
```

#### 5️⃣ Reference/Accessed Bit (A)

**In plain English:** Has this page been accessed recently? 👀 Like tracking which books in a library are popular (frequently accessed) vs. dusty (rarely accessed).

**Purpose:** Helps page replacement algorithms decide what to evict

```
Page Replacement Scenario:
─────────────────────────
Memory is full, need to evict one page.
Which should go?

VPN 10: A=1, recently accessed     → Keep! 🔥
VPN 25: A=0, not accessed in ages  → Evict! ❄️
VPN 42: A=1, recently accessed     → Keep! 🔥
```

**How it works:**

```
1. OS periodically clears all A bits to 0
2. Hardware sets A=1 whenever page is accessed
3. After some time, OS checks:
   - A=1 means page was used recently (hot 🔥)
   - A=0 means page wasn't used (cold ❄️)
4. Evict cold pages first
```

**Algorithms that use this:**

- **Clock/Second-Chance:** Scan for A=0 pages
- **LRU approximation:** Track access patterns
- **Working set:** Determine active pages

> **💡 Insight**
>
> The dirty and accessed bits demonstrate **hardware-OS cooperation**. The hardware automatically sets these bits (since it knows when memory is accessed/modified), while the OS reads and clears them (to implement policies). This division is clean: hardware provides mechanisms, OS implements policies.

### 4.3. 🖥️ x86 Page Table Entry

**Real-world example:** Let's look at an actual PTE from x86 architecture

```
31               12 11  9 8 7 6 5 4 3 2 1 0
┌──────────────────┬────┬─┬─┬─┬─┬─┬─┬─┬─┬─┐
│       PFN        │IGN │G│0│D│A│ │ │ │ │P│
│    (20 bits)     │    │ │ │ │ │ │ │ │ │ │
│                  │    │ │ │ │ │ │ │ │ │ │
│                  │    │ │ │ │ │P│P│U│R│ │
│                  │    │ │ │ │ │C│W│/│/│ │
│                  │    │ │ │ │ │D│T│S│W│ │
└──────────────────┴────┴─┴─┴─┴─┴─┴─┴─┴─┴─┘
```

**Bit breakdown:**

| Bit(s) | Name | Meaning |
|--------|------|---------|
| 0 | P | **Present:** 1=in memory, 0=swapped/invalid |
| 1 | R/W | **Read/Write:** 0=read-only, 1=read-write |
| 2 | U/S | **User/Supervisor:** 0=kernel only, 1=user accessible |
| 3 | PWT | **Page Write-Through:** Cache write policy |
| 4 | PCD | **Page Cache Disable:** 1=don't cache this page |
| 5 | A | **Accessed:** Set by hardware on any access |
| 6 | D | **Dirty:** Set by hardware on write |
| 7 | PAT | **Page Attribute Table:** Memory type |
| 8 | G | **Global:** Don't flush from TLB on context switch |
| 9-11 | IGN | **Ignored:** Available for OS use |
| 12-31 | PFN | **Page Frame Number:** Physical address bits 31-12 |

**Example PTE:**

```
PTE value: 0x00042067 (hexadecimal)

Binary: 0000 0000 0000 0100 0010 0000 0110 0111

Decoding:
───────
PFN = 0x00042 (frame 66 decimal)
G   = 0
D   = 1 (dirty! ✍️)
A   = 1 (accessed! 👀)
PCD = 0
PWT = 0
U/S = 1 (user accessible ✅)
R/W = 1 (writable ✅)
P   = 1 (present ✅)

Translation:
This is a user-accessible, writable page at physical frame 66
that has been both accessed and modified.
```

**Why no explicit "Execute" bit?** 🤔

Older x86 (32-bit) doesn't have a separate execute bit! Any readable page was executable. x86-64 (64-bit) added the **NX (No eXecute) bit** in bit 63 of the 64-bit PTE to enable W^X protection.

**Reference:** For complete details, see Intel Architecture Manual Volume 3 📚

> **💡 Insight**
>
> Real hardware is **messy and historical**. The x86 PTE has weird bits (PWT, PCD, PAT) for cache control because Intel needed to support specific optimization scenarios. When you design systems, you'll face similar pressures: theoretical purity vs. practical requirements. Understanding real hardware teaches you that clean abstractions often hide complex realities underneath.

---

## 5. ⚡ Paging: Also Too Slow

### 5.1. 🐌 Performance Cost

**In plain English:** We solved the fragmentation problem 🎉, but we created a new problem: **slowness** 🐌. Every memory access now requires TWO memory accesses—one to read the page table, one to get the actual data. It's like having to check a directory before reading every sentence in a book 📖.

**The performance problem:**

```
Without Paging:
──────────────
movl 0x1234, %eax
     ↓
1 memory access → Get value at 0x1234 → Done! ⚡

With Paging (naive):
───────────────────
movl 0x1234, %eax
     ↓
1. Memory access → Read page table[VPN] to get PFN 📋
2. Memory access → Read physical[PFN:offset] to get data 📦
     ↓
2× slower! 🐌
```

**Impact on a real instruction:**

```assembly
movl 21, %eax    # Load data from address 21 into register eax
```

**What happens with paging:**

```
Step 1: Fetch instruction (movl) from memory
        → Requires page table lookup 📋
        → Then instruction fetch 📦
        = 2 memory accesses

Step 2: Execute instruction (load data from address 21)
        → Requires page table lookup 📋
        → Then data fetch 📦
        = 2 memory accesses

Total: 4 memory accesses for 1 instruction! 💥
```

**Compared to no paging: 2 memory accesses (instruction + data)**

Result: **2× slowdown** at minimum! In practice, could be worse.

### 5.2. 🔧 Memory Access Protocol

**Detailed walkthrough of address translation:**

```c
// Pseudocode for complete translation process
int AccessMemory(VirtualAddress) {
    // 1. Extract VPN and offset
    VPN = (VirtualAddress & VPN_MASK) >> SHIFT;
    offset = VirtualAddress & OFFSET_MASK;

    // 2. Calculate PTE address
    //    (This is where page table base register helps)
    PTEAddr = PageTableBaseRegister + (VPN * sizeof(PTE));

    // 3. Fetch PTE from memory (MEMORY ACCESS #1 📋)
    PTE = AccessMemory(PTEAddr);

    // 4. Check validity
    if (PTE.Valid == False) {
        RaiseException(SEGMENTATION_FAULT);  // 💥
        return ERROR;
    }

    // 5. Check permissions
    if (CanAccess(PTE.ProtectBits) == False) {
        RaiseException(PROTECTION_FAULT);    // 🛡️💥
        return ERROR;
    }

    // 6. Check if present in memory
    if (PTE.Present == False) {
        RaiseException(PAGE_FAULT);          // 💾→📦
        // OS will handle, load page, retry
        return RETRY;
    }

    // 7. Construct physical address
    PhysAddr = (PTE.PFN << SHIFT) | offset;

    // 8. Fetch actual data (MEMORY ACCESS #2 📦)
    data = AccessMemory(PhysAddr);

    // 9. Update accessed bit (and dirty if write)
    PTE.Accessed = 1;

    return data;
}
```

**Visual timeline:**

```
Time  Action                           Memory Accesses    Cumulative
────────────────────────────────────────────────────────────────────
0     CPU wants to load from addr 21   0                  0
1     Calculate VPN=1, offset=5        0                  0
2     Calculate PTE addr               0                  0
3     Read page_table[1]               1 📋              1
4     Check valid bit (OK ✅)          0                  1
5     Check protection (OK ✅)         0                  1
6     Check present (OK ✅)            0                  1
7     Extract PFN=7                    0                  1
8     Calculate phys addr=117          0                  1
9     Read memory[117]                 1 📦              2
10    Return data to CPU               0                  2
────────────────────────────────────────────────────────────────────
Total: 2 memory accesses per virtual memory access
```

**Memory speed comparison:**

```
Operation                    Latency
────────────────────────────────────────
CPU register access          ~0.3 ns  ⚡
L1 cache access              ~1 ns    🚀
L2 cache access              ~3 ns    ⚡
L3 cache access              ~12 ns   🏃
Main memory (RAM)            ~100 ns  🐌
────────────────────────────────────────

With naive paging:
One virtual memory access = 2 RAM accesses = 200 ns
Slowdown vs. cache = 200× ⚠️
```

**Why this is catastrophic:**

```
Without paging:
    10 billion instructions/sec × 1 memory access = 10B mem ops/sec

With naive paging:
    10 billion instructions/sec × 2 memory accesses = 20B mem ops/sec
    But memory can only do 10B ops/sec
    → CPU starved, runs at 50% speed! 💥
```

> **💡 Insight**
>
> This is a **classic space-time tradeoff**. We used extra space (page tables) to solve a problem (fragmentation), but created a time problem (slowness). The solution? Add **more hardware** (Translation Lookaside Buffer, or TLB, covered in next chapter) to cache page table entries. This pattern recurs in OS design: solve a problem with data structures, then add caching to make it fast.

**The good news:** Later chapters introduce the **TLB (Translation Lookaside Buffer)** 🎯, a special cache for page table entries that reduces the overhead from 2× to ~1-5% in practice. We'll explore this critical optimization soon!

---

## 6. 🔍 A Memory Trace

### 6.1. 💻 Understanding the Code

**Example C program:** Simple array initialization

```c
int array[1000];

for (i = 0; i < 1000; i++)
    array[i] = 0;
```

**In plain English:** This code creates an array of 1000 integers and sets each one to zero. Simple, right? But let's see what's actually happening at the assembly and memory level! 🔬

**Compile and disassemble:**

```bash
$ gcc -o array array.c -Wall -O
$ objdump -d array     # Linux
$ otool -tV array      # macOS
```

**Resulting x86 assembly:**

```assembly
Address   Instruction               Comments
────────────────────────────────────────────────────────────
1024      movl $0x0,(%edi,%eax,4)  # array[i] = 0
1028      incl %eax                 # i++
1032      cmpl $0x03e8,%eax         # Compare i with 1000
1036      jne 1024                  # Jump if not equal (loop)
```

**Instruction breakdown:**

1. **movl $0x0,(%edi,%eax,4)**
   - `$0x0`: Immediate value 0
   - `%edi`: Base address of array
   - `%eax`: Loop counter (i)
   - Multiply by 4: Each int is 4 bytes
   - Address = edi + (eax × 4)
   - Action: Store 0 at computed address

2. **incl %eax**
   - Increment eax (i++)

3. **cmpl $0x03e8,%eax**
   - Compare eax with 0x03e8 (1000 in decimal)
   - Sets CPU flags

4. **jne 1024**
   - Jump if Not Equal
   - If i ≠ 1000, go back to address 1024
   - If i = 1000, fall through (loop done)

**Register usage:**

```
%edi = Base address of array (constant during loop)
%eax = Loop counter i (0, 1, 2, ..., 999)

Iteration 0: Address = %edi + 0×4   = %edi + 0
Iteration 1: Address = %edi + 1×4   = %edi + 4
Iteration 2: Address = %edi + 2×4   = %edi + 8
...
Iteration 999: Address = %edi + 999×4 = %edi + 3996
```

### 6.2. 🎯 Setting Up the Scenario

**Memory layout assumptions:**

```
Virtual Address Space: 64KB (tiny, unrealistic, but good for examples)
Page Size: 1KB
Number of Pages: 64

Code location: Virtual address 1024 (VPN=1)
Array location: Virtual address 40000 (VPN=39-42)
```

**Why VPN=1 for code at address 1024?**

```
Virtual address: 1024 = 0x0400 (binary: 0000 0100 0000 0000)
Page size: 1KB = 1024 bytes

VPN = 1024 ÷ 1024 = 1
Offset = 1024 % 1024 = 0

So instruction at address 1024 is at:
  VPN 1, offset 0 ✅
```

**Array mapping calculation:**

```
Array size: 1000 ints × 4 bytes = 4000 bytes
Array start: 40000
Array end: 40000 + 4000 = 44000

VPN calculation:
40000 ÷ 1024 = 39.0625 → VPN 39 (starting page)
44000 ÷ 1024 = 42.9687 → VPN 42 (ending page)

Pages needed: VPN 39, 40, 41, 42 (4 pages total)
```

**Page table setup:**

```
Virtual Page    →    Physical Frame
──────────────────────────────────────
VPN 1 (code)         PFN 4
VPN 39 (array)       PFN 7
VPN 40 (array)       PFN 8
VPN 41 (array)       PFN 9
VPN 42 (array)       PFN 10
```

**Physical address calculations:**

```
Code (VPN 1, offset 0) → (PFN 4, offset 0) = 4096
Array start:
  Virtual 40000 = VPN 39, offset 64
  → Physical: PFN 7 = frame start 7×1024 = 7168
              + offset 64 = 7232 ✅
```

### 6.3. 📊 Tracing Memory Accesses

**What happens during the first iteration (i=0)?**

```
Iteration 0: array[0] = 0
─────────────────────────

Step 1: Fetch instruction at virtual address 1024
        1a. Translate 1024: VPN=1 → PFN=4 → Physical 4096
        1b. Read page_table[1]                    [Memory access 1 📋]
        1c. Read instruction at physical 4096     [Memory access 2 📦]

Step 2: Execute "movl $0x0,(%edi,%eax,4)"
        Address = %edi + 0×4 = 40000 + 0 = 40000
        2a. Translate 40000: VPN=39 → PFN=7 → Physical 7232
        2b. Read page_table[39]                   [Memory access 3 📋]
        2c. Write 0 to physical 7232              [Memory access 4 📦]

Step 3: Fetch next instruction at 1028
        (Same VPN=1 as before)
        3a. Read page_table[1]                    [Memory access 5 📋]
        3b. Read instruction at physical 4100     [Memory access 6 📦]

Step 4: Execute "incl %eax"
        (Register only, no memory access)

Step 5: Fetch instruction at 1032
        5a. Read page_table[1]                    [Memory access 7 📋]
        5b. Read instruction at physical 4104     [Memory access 8 📦]

Step 6: Execute "cmpl $0x03e8,%eax"
        (Register only, no memory access)

Step 7: Fetch instruction at 1036
        7a. Read page_table[1]                    [Memory access 9 📋]
        7b. Read instruction at physical 4108     [Memory access 10 📦]

Step 8: Execute "jne 1024"
        Jump taken (i ≠ 1000), back to 1024

Total: 10 memory accesses for 1 loop iteration! 😱
```

**Pattern for iterations 0-4:**

```
Iteration    Instruction Fetches    Data Access       Page Table    Total
─────────────────────────────────────────────────────────────────────────
0            4 fetches (1024-1036)  1 write (40000)   5 lookups     10
1            4 fetches (1024-1036)  1 write (40004)   5 lookups     10
2            4 fetches (1024-1036)  1 write (40008)   5 lookups     10
3            4 fetches (1024-1036)  1 write (40012)   5 lookups     10
4            4 fetches (1024-1036)  1 write (40016)   5 lookups     10
─────────────────────────────────────────────────────────────────────────
Total for 5 iterations:                                             50
```

**Memory access visualization:**

```
Virtual Addresses Accessed                    Physical Addresses Accessed
──────────────────────────                    ────────────────────────────

Code (instructions):                          Code (instructions):
1024, 1028, 1032, 1036 ↺                     4096, 4100, 4104, 4108 ↺
(VPN 1, repeating)                            (PFN 4, repeating)

Page Table Lookups:                           Page Table (in physical mem):
VPN 1  → PTE @ 1024+1×4 = 1028 ↺             Physical 1028 ↺
VPN 39 → PTE @ 1024+39×4 = 1180 ↺            Physical 1180 ↺

Array (data):                                 Array (data):
40000, 40004, 40008, 40012, ...               7232, 7236, 7240, 7244, ...
(VPN 39, sequential)                          (PFN 7, sequential)
```

**Graphical timeline (first 5 iterations):**

```
Time →
────────────────────────────────────────────────────────────────────

Page Table Accesses (light gray):
PT[1]  PT[39] PT[1] PT[1] PT[1] | PT[1] PT[39] PT[1] PT[1] PT[1] | ...
  ↓      ↓     ↓     ↓     ↓         ↓     ↓     ↓     ↓     ↓
iter 0                              iter 1

Code Accesses (black):
1024   1028   1032  1036   JUMP  | 1024  1028   1032  1036  JUMP  | ...
 ↓      ↓      ↓     ↓       ↓       ↓     ↓      ↓     ↓     ↓

Array Accesses (dark gray):
     40000                       | 40004                          | ...
       ↓                              ↓
```

**Key observations:**

1. **Code locality** 🎯
   - Instructions at 1024-1036 accessed repeatedly
   - All in same page (VPN 1)
   - Page table entry VPN 1 accessed frequently
   - **Opportunity:** Cache this PTE! (TLB will do this)

2. **Array locality** 📦
   - Array accesses are sequential: 40000, 40004, 40008...
   - Stay in same page for 256 iterations (1024 bytes ÷ 4 bytes/int)
   - **Opportunity:** Cache array PTEs too!

3. **Instruction vs data ratio** ⚖️
   - 4 instruction fetches per 1 data access
   - Typical for many programs
   - Instruction cache (I-cache) is crucial for performance

**What changes after iteration 255?**

```
Iteration 255: array[255] = 0
Address = 40000 + 255×4 = 41020

Page boundary!
41020 ÷ 1024 = 40.05 → Now accessing VPN 40 instead of VPN 39

New PTE needed:
VPN 40 → PFN 8

Page table access pattern changes:
Old: PT[1], PT[39], PT[1], PT[1], PT[1] ↺
New: PT[1], PT[40], PT[1], PT[1], PT[1] ↺
              ^^^^
           Different PTE!
```

**Complete memory access summary:**

```
Loop iterations: 1000
Instructions per iteration: 4
Data accesses per iteration: 1

Total virtual memory accesses:
  Instructions: 1000 × 4 = 4000
  Data:         1000 × 1 = 1000
  Total:                   5000

Total physical memory accesses (with paging):
  Page table lookups: 5000
  Actual fetches:     5000
  Total:              10000 ⚠️

Overhead: 2× slowdown from paging!
```

> **💡 Insight**
>
> This trace reveals **spatial and temporal locality**—fundamental principles that make caching effective:
>
> - **Temporal locality:** Code at 1024-1036 accessed repeatedly over time
> - **Spatial locality:** Array elements accessed sequentially in memory
>
> The TLB (next chapter) exploits these patterns to cache PTEs, reducing the 10,000 memory accesses down to perhaps 5,100 (most PT lookups hit in TLB cache). Understanding access patterns is key to performance optimization throughout computing: CPU caches, disk buffers, CDNs, database query caches—all exploit locality.

---

## 7. 📝 Summary

**Key Takeaways:** 🎯

### 1. **Paging Solves Segmentation's Problems** 🧩

**Fixed-size chunks eliminate fragmentation:**
```
Segmentation (Variable)    →    Paging (Fixed)
────────────────────            ──────────────
External fragmentation ❌       No fragmentation ✅
Complex allocation ❌           Simple allocation ✅
Inflexible ❌                   Very flexible ✅
```

### 2. **Core Paging Concepts** 📚

```
Virtual Memory              Physical Memory
──────────────              ───────────────
Pages (fixed-size)    ⟷     Frames (fixed-size)
Virtual Page Number   →     Physical Frame Number
(VPN)                       (PFN)

Mapping stored in: Page Table (per-process) 📋
```

### 3. **Address Translation Process** 🔄

```
Virtual Address → Split → VPN + Offset
                           ↓
                    Page Table Lookup
                           ↓
                    PFN ← PTE[VPN]
                           ↓
            Physical Address ← PFN + Offset
```

**Key insight:** Offset unchanged; only page number translated! 🎯

### 4. **Page Table Entry Contents** 🗂️

```
┌──────┬───┬───┬───┬───┬───┬───────┐
│ PFN  │ V │ R │ W │ X │ P │ D │ A │
└──────┴───┴───┴───┴───┴───┴───────┘
         │   └──┬──┘   │   │   └─ Accessed (for replacement)
         │      │      │   └───── Dirty (needs writeback)
         │      │      └───────── Present (in memory vs disk)
         │      └──────────────── Protection (read/write/execute)
         └─────────────────────── Valid (in use)
```

### 5. **Two Critical Problems** ⚠️

**Problem 1: Space overhead** 💾
```
32-bit address, 4KB pages:
→ 2^20 entries × 4 bytes = 4MB per process
→ 100 processes = 400MB just for page tables! 😱
```

**Problem 2: Performance overhead** ⚡
```
Each virtual memory access requires:
1. Page table lookup     [Memory access 1 📋]
2. Actual data access    [Memory access 2 📦]
→ 2× slowdown! 😱
```

### 6. **Advantages of Paging** ✅

1. **No external fragmentation** 🎉
   - All chunks same size
   - Any free frame works

2. **Flexibility** 🤸
   - Sparse address spaces (mark unused pages invalid)
   - No assumptions about growth direction
   - Pages can scatter anywhere in physical memory

3. **Simple free-space management** 🔧
   - Just maintain list of free frames
   - Allocation = grab frames from list

4. **Per-process isolation** 🔒
   - Each process has own page table
   - Cannot access others' memory

5. **Enables virtual memory** 💿
   - Swap pages to disk (via Present bit)
   - Virtual address space > physical memory

### 7. **What's Next** 🚀

The next chapters will solve paging's performance and space problems:

**Performance solutions:**
- **TLB (Translation Lookaside Buffer)** 📋
  - Cache for page table entries
  - Reduces 2× overhead to ~1-5%

**Space solutions:**
- **Multi-level page tables** 🏗️
  - Tree structure instead of flat array
  - Only allocate page table space for used regions

- **Inverted page tables** 🔄
  - One entry per physical frame (not per virtual page)
  - Trades lookup complexity for space savings

```
Current State              After Optimizations
─────────────             ────────────────────
✅ No fragmentation       ✅ No fragmentation
❌ Huge page tables   →   ✅ Compact page tables
❌ 2× slowdown        →   ✅ ~1-5% overhead
```

> **💡 Insight**
>
> Paging demonstrates a fundamental OS pattern:
>
> **Step 1:** Solve hard problem (fragmentation) with simple mechanism (fixed-size pages)
> **Step 2:** Simple mechanism creates new problems (space/time overhead)
> **Step 3:** Add optimizations to fix new problems (TLB, multi-level tables)
>
> This incremental refinement appears throughout OS design. Start simple, measure, optimize. Real systems are layers of clever optimizations over simple core abstractions.

**The bigger picture:** 🌍

Paging is the **foundation of modern memory virtualization**. It enables:
- Process isolation (security) 🔒
- Virtual memory (usability) 💾
- Memory protection (reliability) 🛡️
- Efficient memory use (performance) ⚡

Every modern OS uses paging (Linux, Windows, macOS, BSD, etc.). Understanding it deeply gives you insight into:
- Why memory bugs cause segfaults
- How virtual memory works
- Why SSDs improved computer responsiveness (faster swapping)
- How containers/VMs provide isolation
- What kernel exploits target (often page tables!)

**Next up:** We'll make paging fast with the TLB! 🚀

---

**Previous:** [Chapter 12: Segmentation](chapter12-segmentation.md) | **Next:** [Chapter 14: Translation Lookaside Buffers](chapter14-tlb.md)
