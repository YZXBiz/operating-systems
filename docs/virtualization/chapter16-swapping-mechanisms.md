# Chapter 16: Beyond Physical Memory - Swapping Mechanisms

## Table of Contents

1. [Introduction - The Memory Illusion](#1-introduction---the-memory-illusion)
   - 1.1. [The Core Challenge](#11-the-core-challenge)
   - 1.2. [Why Support Large Address Spaces?](#12-why-support-large-address-spaces)
   - 1.3. [The Role of Multiprogramming](#13-the-role-of-multiprogramming)
2. [Swap Space - Your Memory Safety Net](#2-swap-space---your-memory-safety-net)
   - 2.1. [What is Swap Space?](#21-what-is-swap-space)
   - 2.2. [How Swap Space Works](#22-how-swap-space-works)
   - 2.3. [Beyond Swap - Code Pages](#23-beyond-swap---code-pages)
3. [The Present Bit - Memory's Truth Detector](#3-the-present-bit---memorys-truth-detector)
   - 3.1. [Normal Memory Access Flow](#31-normal-memory-access-flow)
   - 3.2. [Adding Swap Support](#32-adding-swap-support)
   - 3.3. [Understanding Page Faults](#33-understanding-page-faults)
4. [The Page Fault Handler - Crisis Management](#4-the-page-fault-handler---crisis-management)
   - 4.1. [Hardware vs Software Responsibilities](#41-hardware-vs-software-responsibilities)
   - 4.2. [Servicing a Page Fault](#42-servicing-a-page-fault)
   - 4.3. [The Complete Flow](#43-the-complete-flow)
5. [When Memory is Full - The Replacement Problem](#5-when-memory-is-full---the-replacement-problem)
   - 5.1. [The Performance Stakes](#51-the-performance-stakes)
   - 5.2. [Page Replacement Policies](#52-page-replacement-policies)
6. [Page Fault Control Flow - The Complete Picture](#6-page-fault-control-flow---the-complete-picture)
   - 6.1. [Hardware Control Flow](#61-hardware-control-flow)
   - 6.2. [Software Control Flow](#62-software-control-flow)
   - 6.3. [Three Critical Cases](#63-three-critical-cases)
7. [When Replacements Really Occur - Proactive Memory Management](#7-when-replacements-really-occur---proactive-memory-management)
   - 7.1. [The Watermark Strategy](#71-the-watermark-strategy)
   - 7.2. [The Swap Daemon](#72-the-swap-daemon)
   - 7.3. [Performance Optimizations](#73-performance-optimizations)
8. [Summary](#8-summary)

---

## 1. Introduction - The Memory Illusion

**In plain English:** Imagine your desk (physical memory) is small, but you have a huge filing cabinet (disk) nearby. When you need a document that doesn't fit on your desk, you temporarily store it in the cabinet and swap it back when needed. The OS does this with memory and disk, creating the illusion that you have unlimited desk space.

**In technical terms:** Modern operating systems create the illusion of large virtual address spaces even when physical memory is limited. They achieve this by using disk storage as an extension of RAM, transparently swapping pages between memory and disk.

**Why it matters:** This mechanism allows you to run multiple large programs simultaneously without worrying whether they'll fit in RAM. It's a fundamental building block that makes modern computing practical and convenient.

### 1.1. The Core Challenge

Up until now, we've made unrealistic assumptions:
- Address spaces are small
- All address spaces fit entirely in physical memory
- All pages of every running process reside in RAM

These assumptions don't hold in real systems. We need to support:
- **Large address spaces** (gigabytes per process)
- **Multiple concurrent processes** (dozens or hundreds)
- **Limited physical memory** (less than the sum of all address spaces)

> **💡 Insight**
>
> The memory hierarchy is built on a fundamental tradeoff: capacity vs. speed. Slower storage (disk) provides more capacity at lower cost, while faster storage (RAM) provides less capacity at higher cost. The OS's job is to hide this tradeoff and make it appear as if you have infinite fast memory.

### 1.2. Why Support Large Address Spaces?

**Convenience and ease of use.** With a large virtual address space, programmers can:
- Write programs naturally without worrying about memory limits
- Allocate memory as needed without manual management
- Focus on algorithms instead of memory constraints

**The alternative - Memory Overlays:** Before virtual memory, programmers had to manually manage what was in memory:

```
Old way (manual overlays):
1. Need to call function foo()
2. Check if foo() code is in memory
3. If not, manually swap it in from disk
4. Finally call foo()
5. Later, manually swap it out to make room
```

This was incredibly tedious and error-prone. Virtual memory eliminates this burden entirely.

### 1.3. The Role of Multiprogramming

**In plain English:** Running multiple programs at once (multiprogramming) means their combined memory needs often exceed physical RAM. Swapping is essential to make this work.

**Historical context:** Early machines with multiprogramming couldn't possibly hold all pages of all processes simultaneously. Swapping was invented out of necessity, not luxury.

**The combination:** Multiprogramming + ease-of-use = need for using more memory than physically available. This is what all modern VM systems do.

---

## 2. Swap Space - Your Memory Safety Net

### 2.1. What is Swap Space?

**In plain English:** Swap space is a reserved area on your disk where the OS stores memory pages that aren't currently needed. Think of it as overflow storage for RAM.

**In technical terms:** Swap space is disk storage reserved for moving pages back and forth between memory and disk. The OS can read from and write to swap space in page-sized units.

**Key characteristics:**
- **Larger than memory** - Otherwise, what's the point?
- **Slower than memory** - That's the tradeoff for extra capacity
- **Page-sized operations** - Reads and writes happen in 4KB chunks (typically)
- **Determines max memory** - Swap size limits total virtual memory available

### 2.2. How Swap Space Works

Let's visualize a simple example:

```
Physical Memory (4 pages)          Swap Space (8 blocks)
┌─────────────────────┐            ┌─────────────────────┐
│ PFN 0: Proc 0[VPN 0]│            │ Block 0: Proc 0[VPN 1]│
├─────────────────────┤            ├─────────────────────┤
│ PFN 1: Proc 1[VPN 2]│            │ Block 1: Proc 0[VPN 2]│
├─────────────────────┤            ├─────────────────────┤
│ PFN 2: Proc 1[VPN 3]│            │ Block 2: [Free]      │
├─────────────────────┤            ├─────────────────────┤
│ PFN 3: Proc 2[VPN 0]│            │ Block 3: Proc 1[VPN 0]│
└─────────────────────┘            ├─────────────────────┤
                                   │ Block 4: Proc 1[VPN 1]│
                                   ├─────────────────────┤
                                   │ Block 5: Proc 3[VPN 0]│
                                   ├─────────────────────┤
                                   │ Block 6: Proc 2[VPN 1]│
                                   ├─────────────────────┤
                                   │ Block 7: Proc 3[VPN 1]│
                                   └─────────────────────┘
```

**What this shows:**
- Three processes (Proc 0, 1, 2) are actively sharing physical memory
- Each process only has **some** pages in memory, rest are on disk
- Process 3 is completely swapped out - not currently running
- One swap block remains free for future use

**The key insight:** The system can pretend memory is 12 pages (4 physical + 8 swap) even though only 4 pages of actual RAM exist.

### 2.3. Beyond Swap - Code Pages

**In plain English:** Program code (like the `ls` command) lives on disk permanently. When you run a program, its code pages are loaded into memory. If memory gets tight, the OS can safely discard these pages because it can reload them from the original binary file later.

**Why this matters:** Not all disk I/O is to swap space. Code pages use the original executable as their backing store, which is more efficient than duplicating them to swap.

**The flow:**
```
Program binary on disk
         ↓
   Load into memory (when program runs)
         ↓
   Execute code from RAM (fast)
         ↓
   If memory needed, discard code pages
         ↓
   Reload from binary when needed again
```

> **💡 Insight**
>
> This is why code pages are called "clean" - they never change, so they can always be safely discarded and reloaded. Data pages are "dirty" because they can be modified, requiring them to be written to swap before eviction.

---

## 3. The Present Bit - Memory's Truth Detector

### 3.1. Normal Memory Access Flow

Before introducing swapping, here's the normal hardware-managed TLB flow:

```
Virtual Address Generated
         ↓
Extract VPN (Virtual Page Number)
         ↓
Check TLB for VPN
         ↓
    ┌────┴────┐
    ↓         ↓
  TLB Hit   TLB Miss
    ↓         ↓
  Use PFN   Look up Page Table
    ↓         ↓
            Extract PFN from PTE
            Install in TLB
            Retry (→ TLB Hit)
            ↓
        Access Physical Memory
```

**This works perfectly** when all pages are in physical memory. But what if they're not?

### 3.2. Adding Swap Support

To support swapping, we add a new piece of information to each Page Table Entry (PTE):

**The Present Bit:**
- **Present = 1:** Page is in physical memory (proceed normally)
- **Present = 0:** Page is on disk (trigger page fault)

**Page Table Entry structure:**
```
┌─────────┬─────────┬────────┬─────────┬─────┐
│   PFN   │ Valid   │Present │ Protect │ ... │
│(or Disk)│         │  Bit   │  Bits   │     │
└─────────┴─────────┴────────┴─────────┴─────┘

If Present = 1: PFN field contains physical frame number
If Present = 0: PFN field contains disk address
```

> **💡 Insight**
>
> The same field in the PTE serves dual purposes: when present=1, it holds the physical frame number; when present=0, it holds the disk block address. This elegant design reuses existing bits for different purposes depending on context.

### 3.3. Understanding Page Faults

**Terminology confusion:** A "page fault" sounds like an error, but it's actually a normal operation:

**What people mean by "page fault":**
- Most commonly: A legal memory access to a page that's currently on disk
- Sometimes: Any exception related to page tables (including illegal accesses)
- Technically: Should be called a "page miss" (like cache miss)

**Why it's called a fault:** The hardware doesn't know how to handle it, so it raises an exception and transfers control to the OS. The mechanism is identical to handling illegal operations, hence the name "fault."

**Real-world usage:** When someone says a program is "page faulting," they mean it's accessing parts of its virtual address space that are currently swapped to disk.

---

## 4. The Page Fault Handler - Crisis Management

### 4.1. Hardware vs Software Responsibilities

**Why doesn't hardware handle page faults?**

Two key reasons:

1. **Performance:** Page faults involve slow disk I/O (milliseconds). Even if the OS takes thousands of instructions to handle it, that's negligible compared to disk latency.

2. **Simplicity:** Hardware would need to understand:
   - Swap space organization
   - Disk I/O protocols
   - File systems
   - Replacement policies

   This is too complex and variable across systems.

**The division of labor:**
```
Hardware:                    Software (OS):
- Detects present bit = 0    - Finds disk address
- Raises page fault          - Issues disk I/O
- Transfers to OS            - Waits for completion
- Retries instruction        - Updates page table
                            - Chooses replacement victim
```

### 4.2. Servicing a Page Fault

**Step-by-step process:**

**1. Page fault occurs (present = 0)**
   - Hardware detects page not in memory
   - Transfers control to OS page-fault handler

**2. OS finds the page on disk**
   - Examines PTE to get disk address
   - The same bits that normally hold PFN now hold disk block number

**3. OS issues disk I/O**
   - Requests disk controller to read page into memory
   - This takes milliseconds (eternity in CPU time)

**4. Process blocks**
   - Process enters blocked state
   - OS can schedule other ready processes
   - Overlap I/O of one process with execution of another

**5. Disk I/O completes**
   - Disk controller interrupts CPU
   - OS regains control

**6. OS updates page table**
   - Sets present bit = 1
   - Updates PFN field with physical frame number
   - Page is now valid and present

**7. OS retries instruction**
   - Process becomes ready again
   - Instruction that caused fault executes again
   - This time it succeeds (probably via TLB miss → TLB hit → access)

### 4.3. The Complete Flow

```
Instruction: Load from address 0x4000
         ↓
VPN 4 not in TLB
         ↓
Check Page Table: PTE[4]
         ↓
Present bit = 0 → PAGE FAULT!
         ↓
OS Page Fault Handler Runs
         ↓
Read disk address from PTE[4]
         ↓
Issue I/O: Read disk block 23 into PFN 7
         ↓
Process blocks, other processes run
         ↓
... milliseconds pass ...
         ↓
Disk interrupt: I/O complete
         ↓
Update PTE[4]: present=1, PFN=7
         ↓
Retry instruction
         ↓
TLB miss, look up PTE[4]
         ↓
Install VPN 4 → PFN 7 in TLB
         ↓
Retry again
         ↓
TLB hit! Access PFN 7
         ↓
Success!
```

> **💡 Insight**
>
> The retry mechanism is crucial. The instruction that faulted is restarted from the beginning, as if the fault never happened. This makes page faults completely transparent to the process - it never knows the page was temporarily unavailable.

---

## 5. When Memory is Full - The Replacement Problem

### 5.1. The Performance Stakes

**In plain English:** Choosing the wrong page to evict can make your program run 10,000 to 100,000 times slower. That's the difference between a program finishing in 1 second vs. 28 hours.

**Why replacement matters:**

**Best case scenario:**
- Evict pages that won't be needed soon
- Most accesses hit pages in memory
- Rare page faults
- Program runs at memory speed

**Worst case scenario:**
- Evict pages that will be needed immediately
- Constant page faults (called "thrashing")
- Every access waits for disk I/O
- Program runs at disk speed

**The speed difference:**
```
Memory access:  ~100 nanoseconds
Disk access:    ~10 milliseconds

Ratio: 10,000,000 ns / 100 ns = 100,000x slower!
```

### 5.2. Page Replacement Policies

**In plain English:** When memory is full and we need to bring in a new page, which existing page should we kick out? This is the page replacement problem.

**Key considerations:**
- **Frequency:** How often is the page accessed?
- **Recency:** When was it last accessed?
- **Modification:** Has the page been modified (dirty)?
- **Future use:** Will it be needed soon?

**The challenge:** We can't predict the future perfectly, so policies use heuristics based on past behavior.

**Preview:** Chapter 17 will dive deep into specific replacement policies (LRU, FIFO, optimal, etc.). For now, just understand that such a policy exists and is critical for performance.

---

## 6. Page Fault Control Flow - The Complete Picture

### 6.1. Hardware Control Flow

Here's what the hardware does during address translation with swap support:

```c
// Hardware control flow algorithm
VPN = (VirtualAddress & VPN_MASK) >> SHIFT
(Success, TlbEntry) = TLB_Lookup(VPN)

if (Success == True) {                    // TLB Hit
    if (CanAccess(TlbEntry.ProtectBits) == True) {
        Offset = VirtualAddress & OFFSET_MASK
        PhysAddr = (TlbEntry.PFN << SHIFT) | Offset
        Register = AccessMemory(PhysAddr)
    } else {
        RaiseException(PROTECTION_FAULT)
    }
} else {                                  // TLB Miss
    PTEAddr = PTBR + (VPN * sizeof(PTE))
    PTE = AccessMemory(PTEAddr)

    if (PTE.Valid == False) {
        RaiseException(SEGMENTATION_FAULT)  // Invalid page
    } else if (CanAccess(PTE.ProtectBits) == False) {
        RaiseException(PROTECTION_FAULT)     // Permission denied
    } else if (PTE.Present == True) {
        // Page is valid and in memory - install in TLB
        TLB_Insert(VPN, PTE.PFN, PTE.ProtectBits)
        RetryInstruction()
    } else if (PTE.Present == False) {
        RaiseException(PAGE_FAULT)           // Valid but on disk
    }
}
```

### 6.2. Software Control Flow

Here's what the OS does when handling a page fault:

```c
// OS page fault handler algorithm
PFN = FindFreePhysicalPage()

if (PFN == -1) {                          // No free page found
    PFN = EvictPage()                     // Run replacement algorithm
}

DiskRead(PTE.DiskAddr, PFN)               // Issue I/O to disk
                                          // (Process sleeps here)

// When I/O completes:
PTE.present = True                        // Update page table
PTE.PFN = PFN
RetryInstruction()                        // Try again
```

### 6.3. Three Critical Cases

When a TLB miss occurs, three scenarios are possible:

**Case 1: Page is valid and present (Lines 18-21)**
```
PTE.Valid = True, PTE.Present = True
         ↓
   Normal TLB miss
         ↓
Install PFN in TLB, retry
         ↓
   TLB hit, success
```

**Case 2: Page is valid but not present (Lines 22-23)**
```
PTE.Valid = True, PTE.Present = False
         ↓
     Page fault!
         ↓
OS brings page from disk
         ↓
  Update PTE, retry
         ↓
  Eventually succeeds
```

**Case 3: Page is invalid (Lines 13-14)**
```
PTE.Valid = False
         ↓
   Segmentation fault
         ↓
OS terminates process
         ↓
    Program crash
```

> **💡 Insight**
>
> The distinction between invalid and not-present is crucial. Invalid means the access is illegal (bug in the program). Not-present means the access is legal but the page happens to be on disk temporarily. The first kills the process, the second transparently fixes the situation.

**Visual summary:**
```
TLB Miss Handling
         ↓
┌────────┴────────────────────────┐
↓                ↓                ↓
Valid=0      Valid=1          Valid=1
             Present=0        Present=1
↓                ↓                ↓
Kill Process   Page Fault    Normal TLB Miss
(Bug!)         (Fix It)      (Fast Path)
```

---

## 7. When Replacements Really Occur - Proactive Memory Management

### 7.1. The Watermark Strategy

**In plain English:** Instead of waiting until memory is completely full, the OS maintains a small buffer of free pages. Think of it like keeping some cash in your wallet rather than going to the ATM every time you need to pay for something.

**The watermark approach:**
- **High Watermark (HW):** Target number of free pages (e.g., 20 pages)
- **Low Watermark (LW):** Minimum acceptable free pages (e.g., 5 pages)

**How it works:**
```
Free pages drops below LW (5)
         ↓
Background thread wakes up
         ↓
Evicts pages until HW (20) free
         ↓
Thread sleeps
         ↓
Ready for future allocations
```

### 7.2. The Swap Daemon

**In plain English:** The swap daemon (or page daemon) is a background thread that quietly maintains a pool of free memory pages. It's like a janitor who cleans up before the mess becomes a problem.

**Key characteristics:**
- **Runs in background:** Doesn't block foreground processes
- **Triggered by LW:** Wakes when free pages drop below threshold
- **Batch operation:** Frees multiple pages at once
- **Sleeps after HW:** Goes dormant when enough pages are free

**Why "daemon"?** The term comes from Multics (an early OS). It means a background process that does useful work without direct user interaction. Pronounced "demon" (not "day-mon").

### 7.3. Performance Optimizations

**Clustering writes:** Instead of writing one page at a time to disk, batch multiple pages together:

```
Without clustering:
Page 1 → Seek → Write → Seek → Page 2 → Seek → Write...
(Multiple slow seek operations)

With clustering:
Pages 1-8 → Single Seek → Write all together
(One seek, sequential write - much faster!)
```

**Benefits of background work:**
- **Increased disk efficiency:** Better I/O scheduling with batched operations
- **Improved latency:** Pages ready when needed, no waiting
- **Work reduction:** Some pages might never need to be written (if deleted)
- **Better idle utilization:** Use idle CPU/disk time productively

> **💡 Insight**
>
> Background work is a powerful systems optimization pattern. By anticipating future needs and preparing in advance during idle time, you can dramatically improve responsiveness when actual demand arrives. This principle applies beyond operating systems - to databases, web servers, and many other systems.

**Modified control flow:** With background paging, the page fault handler changes slightly:

```c
// Modified page fault handler
if (FreePagesAvailable()) {
    PFN = GetFreePage()
} else {
    // Don't block - notify background thread
    NotifySwapDaemon()
    WaitForFreePage()      // Sleep until daemon frees some pages
    PFN = GetFreePage()
}

// Rest of handler continues normally
DiskRead(PTE.DiskAddr, PFN)
// ...
```

---

## 8. Summary

**The big picture:** This chapter introduced the mechanisms that allow operating systems to provide the illusion of large virtual memory even when physical memory is limited.

**Key mechanisms covered:**

1. **Swap space:** Disk storage that extends physical memory capacity
2. **Present bit:** Page table flag indicating if page is in memory or on disk
3. **Page faults:** Hardware exceptions that trigger OS intervention
4. **Page fault handler:** OS code that brings pages from disk into memory
5. **Page replacement:** Choosing which page to evict when memory is full
6. **Swap daemon:** Background thread that proactively frees memory
7. **Watermark strategy:** Maintaining a buffer of free pages for efficiency

**The transparency principle:**
```
Process View                    Reality
───────────────                ─────────────────
Contiguous virtual memory   →  Pages scattered in RAM
Always accessible           →  Sometimes on disk
Infinite space             →  Limited physical memory
Simple memory model        →  Complex swapping machinery
```

**Performance implications:**
- **Best case:** Page in memory → nanosecond access
- **Worst case:** Page on disk → millisecond access (100,000x slower!)
- **Critical insight:** Page replacement policy makes the difference between these extremes

**What we haven't covered yet:**
- **Replacement policies:** Which page to evict? (Next chapter!)
- **Thrashing:** When the system spends all time swapping
- **Working sets:** The set of pages a process actively uses
- **Advanced optimizations:** Prefetching, compression, etc.

**The amazing achievement:** All of this complexity is completely transparent to processes. As far as a program knows, it's just accessing its own private, contiguous virtual memory. Behind the scenes, pages are scattered across physical memory and disk, with the OS orchestrating a complex dance to maintain the illusion.

This is one of the great abstractions in computer science - providing simplicity and convenience to programmers while managing incredible complexity underneath.

---

**Previous:** [Chapter 15 - Smaller Page Tables](chapter15-smaller-page-tables.md) | **Next:** Chapter 17 - Page Replacement Policies
