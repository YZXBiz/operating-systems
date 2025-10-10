# Chapter 17: Page Replacement Policies

## Table of Contents

1. [Introduction](#1-introduction)
2. [Cache Management](#2-cache-management)
   - 2.1. [Understanding Memory as a Cache](#21-understanding-memory-as-a-cache)
   - 2.2. [Average Memory Access Time (AMAT)](#22-average-memory-access-time-amat)
3. [The Optimal Replacement Policy](#3-the-optimal-replacement-policy)
   - 3.1. [How Optimal Works](#31-how-optimal-works)
   - 3.2. [Types of Cache Misses](#32-types-of-cache-misses)
4. [Simple Policies](#4-simple-policies)
   - 4.1. [FIFO (First-In, First-Out)](#41-fifo-first-in-first-out)
   - 4.2. [Random Replacement](#42-random-replacement)
5. [Using History: LRU](#5-using-history-lru)
   - 5.1. [The Principle of Locality](#51-the-principle-of-locality)
   - 5.2. [How LRU Works](#52-how-lru-works)
6. [Workload Examples](#6-workload-examples)
   - 6.1. [No-Locality Workload](#61-no-locality-workload)
   - 6.2. [80-20 Workload](#62-80-20-workload)
   - 6.3. [Looping-Sequential Workload](#63-looping-sequential-workload)
7. [Implementing Historical Algorithms](#7-implementing-historical-algorithms)
   - 7.1. [The Cost of Perfect LRU](#71-the-cost-of-perfect-lru)
   - 7.2. [Approximating LRU with Clock Algorithm](#72-approximating-lru-with-clock-algorithm)
8. [Considering Dirty Pages](#8-considering-dirty-pages)
9. [Other VM Policies](#9-other-vm-policies)
   - 9.1. [Page Selection Policy](#91-page-selection-policy)
   - 9.2. [Write Clustering](#92-write-clustering)
10. [Thrashing](#10-thrashing)
11. [Summary](#11-summary)

---

## 1. Introduction

**In plain English:** Imagine you're working at a desk with limited space. When your desk gets full and you need a new document, you must decide which old document to put away. Should you remove the oldest one? The one you use least? Or make a random choice?

**In technical terms:** When physical memory is full and a page fault occurs, the operating system must decide which page to evict to make room for the new page. This decision is made by the **replacement policy**.

**Why it matters:** Making smart eviction decisions is crucial for performance. With modern disk access times being roughly 100,000 times slower than memory access, even a small improvement in keeping the right pages in memory can dramatically affect system performance.

### 🎯 The Core Challenge

**How can the OS decide which page (or pages) to evict from memory?**

The replacement policy must balance simplicity (fast decision-making) with intelligence (keeping frequently-used pages in memory). This was especially critical in early systems with limited physical memory, but remains important today with the rise of fast SSDs changing performance characteristics.

> **💡 Insight**
>
> The page replacement problem is fundamentally about predicting the future based on the past. The OS must guess which pages will be needed soon and which won't, using only historical access patterns as a guide.

---

## 2. Cache Management

### 2.1. Understanding Memory as a Cache

**In plain English:** Your physical memory (RAM) doesn't hold every page your programs might need - that would require too much space. Instead, it holds a subset of "hot" pages, acting like a cache for all the virtual pages that live on disk.

**In technical terms:** Main memory serves as a cache for the complete set of virtual memory pages stored on disk. The goal is to maximize **cache hits** (finding the page in memory) and minimize **cache misses** (having to fetch from disk).

```
Complete Virtual Memory (on disk)
        ↓
Physical Memory (cache)
        ↓
    Fast Access!

Miss? → Slow disk fetch → Update cache
```

### 2.2. Average Memory Access Time (AMAT)

The effectiveness of a replacement policy can be measured using **Average Memory Access Time**:

```
AMAT = T_M + (P_Miss × T_D)
```

Where:
- **T_M** = Time to access memory (e.g., 100 nanoseconds)
- **T_D** = Time to access disk (e.g., 10 milliseconds)
- **P_Miss** = Probability of a cache miss (0.0 to 1.0)

#### 📊 Example Calculation

Consider a tiny address space: 4KB with 256-byte pages (16 total virtual pages).

**Reference sequence:**
```
0x000, 0x100, 0x200, 0x300, 0x400, 0x500, 0x600, 0x700, 0x800, 0x900
```

This accesses pages: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9

If all pages except page 3 are in memory:
```
hit, hit, hit, MISS, hit, hit, hit, hit, hit, hit
```

**Hit rate:** 9/10 = 90%
**Miss rate (P_Miss):** 1/10 = 0.1

**AMAT calculation:**
```
AMAT = 100ns + (0.1 × 10ms)
     = 100ns + 1ms
     = 1.0001ms ≈ 1 millisecond
```

Now compare with a 99.9% hit rate (P_Miss = 0.001):
```
AMAT = 100ns + (0.001 × 10ms)
     = 100ns + 10μs
     = 10.1 microseconds
```

**This is ~100 times faster!**

> **💡 Insight**
>
> The enormous gap between memory and disk speeds means that even tiny improvements in hit rate can yield massive performance gains. A policy that improves the hit rate from 90% to 99.9% doesn't just make things 10% better - it makes them 100x better!

---

## 3. The Optimal Replacement Policy

### 3.1. How Optimal Works

**In plain English:** If you could see the future and knew which pages would be needed when, you'd keep the pages you'll need soon and evict the page you won't need for the longest time. This gives the best possible performance.

**In technical terms:** The **optimal replacement policy** (developed by Belady, also called MIN) evicts the page that will be accessed furthest in the future. While impossible to implement in practice (we can't predict the future), it serves as a perfect benchmark for comparing real policies.

#### 🔍 Example Trace

**Reference stream:** 0, 1, 2, 0, 1, 3, 0, 3, 1, 2, 1
**Cache size:** 3 pages

```
Access  | Action      | Cache State      | Hit/Miss
--------|-------------|------------------|----------
0       | Cold start  | [0]              | MISS
1       | Cold start  | [0, 1]           | MISS
2       | Cold start  | [0, 1, 2]        | MISS
0       | In cache    | [0, 1, 2]        | HIT
1       | In cache    | [0, 1, 2]        | HIT
3       | Evict 2*    | [0, 1, 3]        | MISS
0       | In cache    | [0, 1, 3]        | HIT
3       | In cache    | [0, 1, 3]        | HIT
1       | In cache    | [0, 1, 3]        | HIT
2       | Evict 3**   | [0, 1, 2]        | MISS
1       | In cache    | [0, 1, 2]        | HIT

* Why evict 2? Next accesses are 0 (immediate), 1 (soon), 2 (far future)
** Why evict 3? Could also evict 0; both work equally well
```

**Results:**
- 6 hits, 5 misses
- Hit rate: 6/11 = 54.5%
- Hit rate (excluding compulsory misses): 6/8 = 75%

> **⚡ Key Principle**
>
> When comparing replacement policies, always measure against optimal. If optimal achieves 82% and your policy achieves 80%, you're near-perfect! If optimal achieves 82% and your policy achieves 50%, there's room for improvement.

### 3.2. Types of Cache Misses

Understanding why misses occur helps in designing better policies:

**1. Compulsory Miss (Cold-start Miss)**
```
In plain English: First time seeing a page - it can't be in cache yet
Example: The first three misses in any trace
```

**2. Capacity Miss**
```
In plain English: Cache is full, so we must evict something
Example: Accessing page 3 when cache already holds 0, 1, 2
```

**3. Conflict Miss**
```
In plain English: Hardware restriction forces eviction (doesn't apply to OS page caches)
Example: Only occurs in set-associative hardware caches
```

---

## 4. Simple Policies

### 4.1. FIFO (First-In, First-Out)

**In plain English:** Like a queue at a store - the page that's been in memory the longest gets evicted first, regardless of whether it's still being used.

**In technical terms:** Pages are organized in a queue. On eviction, remove the page at the head (first-in). On addition, append to the tail (last-in).

#### 🔄 Example Trace

**Reference stream:** 0, 1, 2, 0, 1, 3, 0, 3, 1, 2, 1
**Cache size:** 3 pages

```
Access  | Action      | Cache State      | Hit/Miss
--------|-------------|------------------|----------
0       | Cold start  | [0] ←first       | MISS
1       | Cold start  | [0, 1] ←first    | MISS
2       | Cold start  | [0, 1, 2] ←first | MISS
0       | In cache    | [0, 1, 2]        | HIT
1       | In cache    | [0, 1, 2]        | HIT
3       | Evict 0     | [1, 2, 3]        | MISS
0       | Evict 1     | [2, 3, 0]        | MISS
3       | In cache    | [2, 3, 0]        | HIT
1       | Evict 2     | [3, 0, 1]        | MISS
2       | Evict 3     | [0, 1, 2]        | MISS
1       | In cache    | [0, 1, 2]        | HIT
```

**Results:**
- 4 hits, 7 misses
- Hit rate: 4/11 = 36.4%
- Hit rate (excluding compulsory): 4/8 = 50%

**Problem:** FIFO evicted page 0 even though it was about to be used again! FIFO has no notion of page importance.

#### ⚠️ Belady's Anomaly

FIFO has a strange property: sometimes giving it MORE memory makes performance WORSE!

**Example reference stream:** 1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5

```
With 3 pages: Hit rate = X%
With 4 pages: Hit rate = Y% (where Y < X!)
```

This happens because FIFO lacks the **stack property** - a cache of size N+1 doesn't naturally contain all pages from a cache of size N.

> **💡 Insight**
>
> Belady's Anomaly reveals a fundamental flaw in FIFO: it doesn't respect the intuition that "more resources = better performance." Policies like LRU have the stack property and avoid this counterintuitive behavior.

### 4.2. Random Replacement

**In plain English:** When memory is full, just pick a random page to evict. Simple, but unpredictable.

**In technical terms:** On eviction, select a page uniformly at random from all pages in memory. No historical information is used.

#### 🎲 Example Trace

**Reference stream:** 0, 1, 2, 0, 1, 3, 0, 3, 1, 2, 1
**Cache size:** 3 pages

```
Access  | Action      | Cache State  | Hit/Miss
--------|-------------|--------------|----------
0       | Cold start  | [0]          | MISS
1       | Cold start  | [0, 1]       | MISS
2       | Cold start  | [0, 1, 2]    | MISS
0       | In cache    | [0, 1, 2]    | HIT
1       | In cache    | [0, 1, 2]    | HIT
3       | Evict 1     | [0, 2, 3]    | MISS (random choice)
0       | In cache    | [0, 2, 3]    | HIT
3       | In cache    | [0, 2, 3]    | HIT
1       | Evict 3     | [0, 2, 1]    | MISS (random choice)
2       | In cache    | [0, 2, 1]    | HIT
1       | In cache    | [0, 2, 1]    | HIT
```

**This particular run:**
- 7 hits, 4 misses
- Hit rate: 7/11 = 63.6%

**But results vary!** Running 10,000 trials shows:
- Best case: 6 hits (54.5%) - matches optimal sometimes
- Worst case: 2 hits (18.2%)
- Average: ~4-5 hits (36-45%)

**Advantage:** No weird corner cases like FIFO's anomaly. Random has nice statistical properties.

---

## 5. Using History: LRU

### 5.1. The Principle of Locality

**In plain English:** Programs tend to use the same code and data repeatedly in short time windows. If you accessed a page recently, you'll probably access it again soon. If you haven't touched a page in a while, you probably won't need it for a while.

**In technical terms:** Programs exhibit two types of locality:

**Temporal Locality**
```
Principle: Pages accessed recently → likely to be accessed again soon
Example: Variables in a loop, frequently-called functions
```

**Spatial Locality**
```
Principle: If page P is accessed → pages near P (P-1, P+1) likely accessed too
Example: Sequential array access, sequential code execution
```

> **💡 Insight**
>
> Locality isn't a law - it's a pattern observed in most real programs. Some programs (like those that scan large datasets randomly) have poor locality. The principle works as a heuristic, not a guarantee.

### 5.2. How LRU Works

**In plain English:** Keep track of when each page was last used. When you need to evict, throw out the page that hasn't been touched for the longest time.

**In technical terms:** **Least-Recently-Used (LRU)** maintains a recency ordering of pages. On each access, move that page to the MRU (most-recently-used) position. On eviction, remove the page at the LRU position.

#### 📈 Example Trace

**Reference stream:** 0, 1, 2, 0, 1, 3, 0, 3, 1, 2, 1
**Cache size:** 3 pages

```
Access  | Action      | Cache State         | Hit/Miss
--------|-------------|---------------------|----------
0       | Cold start  | [0] ←MRU            | MISS
1       | Cold start  | [1, 0] ←MRU         | MISS
2       | Cold start  | [2, 1, 0] ←MRU      | MISS
0       | Move to MRU | [0, 2, 1] ←LRU      | HIT
1       | Move to MRU | [1, 0, 2] ←LRU      | HIT
3       | Evict 2     | [3, 1, 0] ←LRU      | MISS
0       | Move to MRU | [0, 3, 1] ←LRU      | HIT
3       | Move to MRU | [3, 0, 1] ←LRU      | HIT
1       | Move to MRU | [1, 3, 0] ←LRU      | HIT
2       | Evict 0     | [2, 1, 3] ←LRU      | MISS
1       | Move to MRU | [1, 2, 3] ←LRU      | HIT
```

**Results:**
- 6 hits, 5 misses
- Hit rate: 6/11 = 54.5%
- **Matches optimal!** (on this trace)

**Why it works:** At each eviction decision, LRU's historical guess happens to align with what the future holds.

---

## 6. Workload Examples

### 6.1. No-Locality Workload

**Setup:**
- 100 unique pages
- 10,000 total accesses
- Each access is to a random page
- No pattern whatsoever

**Visual Results:**

```
Hit Rate
100% ┤                                  ╭────── All policies
     │                              ╭───╯
 80% ┤                          ╭───╯
     │                      ╭───╯
 60% ┤                  ╭───╯
     │              ╭───╯
 40% ┤          ╭───╯
     │      ╭───╯
 20% ┤  ╭───╯
     │╭─╯
  0% ┼────────────────────────────────────────
     0    20    40    60    80   100
              Cache Size (pages)

Legend: OPT, LRU, FIFO, RAND (all overlap!)
```

**Observations:**

1. **Without locality, all policies perform identically** - FIFO = LRU = Random
2. **Hit rate is purely a function of cache size** - More cache = better hit rate
3. **Optimal still wins** - Peeking at the future helps even with randomness
4. **Full cache = 100% hits** - All policies converge when cache holds everything

> **💡 Insight**
>
> When there's no pattern to exploit, there's no advantage to being smart. This shows that LRU's superiority depends on programs exhibiting locality.

### 6.2. 80-20 Workload

**Setup:**
- 100 unique pages (20 "hot", 80 "cold")
- 80% of accesses → 20% of pages (hot pages)
- 20% of accesses → 80% of pages (cold pages)
- Realistic model of many real applications

**Visual Results:**

```
Hit Rate
100% ┤                              ╭──── OPT
     │                          ╭───╯
 80% ┤                      ╭───╯ ╭────── LRU
     │                  ╭───╯  ╭──╯
 60% ┤              ╭───╯   ╭──╯
     │          ╭───╯    ╭──╯  ╭────────── FIFO
 40% ┤      ╭───╯     ╭──╯  ╭──╯
     │  ╭───╯      ╭──╯  ╭──╯  ╭────────── RAND
 20% ┤╭─╯       ╭──╯  ╭──╯  ╭──╯
     │╯      ╭──╯  ╭──╯  ╭──╯
  0% ┼────────────────────────────────────
     0    20    40    60    80   100
              Cache Size (pages)
```

**Observations:**

1. **LRU outperforms FIFO and Random** - Historical information helps!
2. **LRU keeps hot pages in cache** - Recently-used pages stay, cold pages get evicted
3. **Optimal still better** - History is good, but future is better
4. **Gap shows room for improvement** - Space between LRU and optimal

**Why LRU wins:**
```
Hot page access → Recent access → Stays in cache → Next hot access hits
Cold page access → Recent access → Might stay briefly → Eventually evicted
Result: Hot pages accumulate in cache over time
```

### 6.3. Looping-Sequential Workload

**Setup:**
- 50 unique pages
- Access pattern: 0, 1, 2, ..., 49, 0, 1, 2, ..., 49, (repeat)
- Models database scans, sequential file processing
- **Worst case for LRU and FIFO!**

**Visual Results:**

```
Hit Rate
100% ┤                              ╭──── OPT
     │                          ╭───╯
 80% ┤                      ╭───╯
     │                  ╭───╯
 60% ┤              ╭───╯         ╭─ RAND
     │          ╭───╯         ╭───╯
 40% ┤      ╭───╯         ╭───╯
     │  ╭───╯         ╭───╯
 20% ┤╭─╯         ╭───╯
     │╯       ╭───╯
  0% ┼────────────────────────────────────
     0    20    40    60    80   100
              Cache Size (pages)

     LRU and FIFO = 0% until cache = 50!
```

**The Disaster:**

With cache size = 49 and workload of 50 pages:

```
Iteration 1: Load pages 0-48 into cache
Access 49 → Evict 0 (LRU/FIFO choice)
Cache: [1, 2, 3, ..., 48, 49]

Iteration 2: Access 0 → MISS! (just evicted it)
Evict 1 → Cache: [2, 3, 4, ..., 49, 0]

Access 1 → MISS! (just evicted it)
Evict 2 → Cache: [3, 4, 5, ..., 0, 1]

Result: 0% hit rate! Every access misses!
```

**Why Random does better:**
- Random might keep page 0 when accessing 49
- Random doesn't have systematic "always evict the wrong page" behavior
- No weird corner cases

> **⚠️ Warning**
>
> No policy is perfect for all workloads. LRU's assumption that "recent = important" fails when the working set is slightly larger than cache and accessed sequentially. This is why modern systems often use scan-resistant algorithms.

---

## 7. Implementing Historical Algorithms

### 7.1. The Cost of Perfect LRU

**The Challenge:** Perfect LRU requires updating data structures on EVERY memory access.

**In plain English:** Imagine having to reorganize your entire filing system every single time you touch a document. That's what perfect LRU demands.

**In technical terms:**

```
FIFO cost:
- Update on page eviction: O(1)
- Update on page insertion: O(1)
- Memory accesses between updates: thousands

LRU cost:
- Update on EVERY memory access: O(1) per access
- But "every memory access" = every instruction fetch, load, store
- Overhead becomes prohibitive
```

**Example: Modern System**
```
4GB memory ÷ 4KB pages = 1,048,576 pages
Finding absolute LRU page = scan 1M entries
Even at 1ns per check = 1ms per eviction
Way too slow!
```

**Hardware-Assisted Approach:**

Add a timestamp field to each page:
```
Page Table Entry:
┌──────────┬──────────┬───────────┐
│ PFN      │ Valid    │ Timestamp │
│ (20 bit) │ (1 bit)  │ (64 bit)  │
└──────────┴──────────┴───────────┘

On each access: Hardware sets Timestamp = current_time
On eviction: OS scans all timestamps, finds minimum
```

**Problem:** Scanning millions of timestamps is still too expensive!

### 7.2. Approximating LRU with Clock Algorithm

**In plain English:** Instead of tracking exact access times, just remember "has this page been used recently?" using a single bit. Scan pages looking for one that hasn't been used recently.

**In technical terms:** Use a **use bit** (reference bit) per page. Hardware sets it to 1 on access. OS clears it and uses it to approximate recency.

#### 🔄 Clock Algorithm (Corbato, 1969)

**Setup:**
```
All pages arranged in circular list
Clock hand points to current page
Each page has a use bit (0 or 1)
```

**Algorithm:**
```
When eviction needed:
1. Examine page at clock hand
2. If use bit = 0:
   - Evict this page (hasn't been used recently)
   - Done!
3. If use bit = 1:
   - Clear use bit to 0 (give it another chance)
   - Advance clock hand
   - Go to step 1
```

**Visual Example:**

```
Initial state (need to evict):
     ┌──────┐
     │ P0:1 │ ← Clock hand
     ├──────┤
     │ P1:0 │
     ├──────┤
     │ P2:1 │
     ├──────┤
     │ P3:1 │
     └──────┘

Step 1: Check P0, use=1 → Clear to 0, advance
Step 2: Check P1, use=0 → Evict P1! ✓

Result: P1 evicted (hasn't been used recently)
```

**Worst Case:**
```
All pages have use=1:
- Scan full circle, clearing all bits
- Come back to start, all bits now 0
- Evict first page

Effect: Degrades to FIFO in worst case
```

**Performance:**

On 80-20 workload:
- Optimal: ~85% hit rate
- Perfect LRU: ~82% hit rate
- Clock: ~78% hit rate
- FIFO: ~65% hit rate
- Random: ~60% hit rate

Clock approximates LRU well enough for practical use!

> **💡 Insight**
>
> Perfect is the enemy of good. Clock algorithm gives up on perfect LRU tracking and gains enormous implementation simplicity and speed. The small loss in hit rate is worth the huge gain in overhead reduction.

---

## 8. Considering Dirty Pages

**In plain English:** Some pages have been modified (written to) while in memory. Evicting these "dirty" pages requires writing them back to disk - expensive! Clean pages can just be discarded - cheap! Prefer evicting clean pages when possible.

**In technical terms:** Use a **dirty bit** (modified bit) to track writes. Enhanced Clock algorithm considers both use bit and dirty bit.

### 🔧 Enhanced Clock Algorithm

**Page States:**
```
Use=0, Dirty=0: Best choice (not used recently, clean)
Use=0, Dirty=1: Second choice (not used recently, but dirty)
Use=1, Dirty=0: Third choice (used recently, but clean)
Use=1, Dirty=1: Last choice (used recently and dirty)
```

**Two-Pass Algorithm:**
```
Pass 1: Look for (use=0, dirty=0) - Best case!
        While scanning, clear use bits

Pass 2: Look for (use=0, dirty=1) - Second best
        (Use bits now cleared from pass 1)

If nothing found: Degraded to regular clock
```

**Benefit:**
```
Evicting clean page:
- Just update page table
- Reuse physical frame immediately
- Cost: ~100 nanoseconds

Evicting dirty page:
- Write page to disk (10 milliseconds)
- Update page table
- Reuse physical frame
- Cost: ~10,000,000 nanoseconds

Savings: 100,000x faster!
```

> **⚡ Performance Tip**
>
> Preferring clean pages can dramatically reduce I/O. In workloads with many reads and few writes, most pages stay clean, allowing very fast evictions.

---

## 9. Other VM Policies

### 9.1. Page Selection Policy

**When to bring pages into memory?**

**Demand Paging (Standard Approach)**
```
In plain English: Wait until page is accessed, then load it
Advantage: Never load pages that aren't needed
Disadvantage: Every first access takes a page fault
```

**Prefetching (Optimistic Approach)**
```
In plain English: Guess which pages will be needed, load them early
Example: Load page P+1 when loading code page P
Advantage: Hide latency if guess is right
Disadvantage: Waste memory and I/O if guess is wrong
```

**When to prefetch:**
```
Sequential code: Load P → likely to need P+1 ✓
Sequential data: Access array[i] → likely to access array[i+1] ✓
Random access: Hard to predict ✗
```

### 9.2. Write Clustering

**In plain English:** Instead of writing pages to disk one at a time, collect several dirty pages and write them all at once. Disk drives handle one large write much better than many small writes.

**In technical terms:** Buffer multiple dirty pages and issue a single large I/O operation.

**Example:**
```
Individual writes:
Write page 10: Seek + rotate + write = 10ms
Write page 11: Seek + rotate + write = 10ms
Write page 12: Seek + rotate + write = 10ms
Total: 30ms

Clustered write:
Write pages 10-12: Seek + rotate + write(3x) = 12ms
Total: 12ms (2.5x faster!)
```

> **💡 Insight**
>
> The VM subsystem has many policy decisions beyond just replacement: when to load pages, when to write pages, how many to operate on at once. Each decision offers opportunities for optimization.

---

## 10. Thrashing

**In plain English:** When you have too many programs running and not enough memory, the system spends all its time swapping pages in and out, making no real progress. It's like juggling too many balls - you're constantly catching and throwing, never actually accomplishing anything.

**In technical terms:** **Thrashing** occurs when the combined **working sets** (actively-used pages) of all processes exceed physical memory. The system enters a state of constant paging with minimal useful work.

### 🌊 The Thrashing Cycle

```
Step 1: Too many processes, not enough memory
        ↓
Step 2: Each process constantly faults
        ↓
Step 3: OS constantly evicts pages
        ↓
Step 4: Just-evicted pages immediately needed again
        ↓
Step 5: CPU idle, disk saturated
        ↓
        Go to Step 2 (endless cycle)
```

### 🔧 Solutions

**1. Admission Control**
```
In plain English: Don't start new processes if memory is tight
Principle: Better to do less work well than everything poorly

Algorithm:
- Monitor memory pressure
- If working sets > physical memory:
  - Suspend some processes
  - Let remaining processes run efficiently
  - Resume suspended processes when memory frees
```

**2. Out-of-Memory (OOM) Killer (Linux)**
```
In plain English: Kill a memory-hungry process to free up space
Advantage: Immediate relief from memory pressure
Disadvantage: Might kill important processes

Example: Kills X server → All GUI apps become unusable
```

**3. User Action**
```
In plain English: Close some programs!
Reality: Most effective solution
```

> **⚠️ Warning**
>
> Thrashing represents a catastrophic failure mode of virtual memory. Prevention (not running too many processes) is far better than cure (killing processes or massive slowdown).

---

## 11. Summary

### 🎯 Key Concepts

**The Problem:**
When physical memory is full, the OS must decide which page to evict. This replacement policy dramatically affects performance because disk is ~100,000x slower than memory.

**The Policies:**

| Policy | Strategy | Pros | Cons | Hit Rate |
|--------|----------|------|------|----------|
| **Optimal** | Evict page used furthest in future | Perfect performance | Impossible to implement | Best (benchmark) |
| **FIFO** | Evict oldest page | Simple | No notion of importance, Belady's Anomaly | Poor |
| **Random** | Evict random page | Simple, no corner cases | Unpredictable | Poor to Medium |
| **LRU** | Evict least recently used | Exploits locality | Expensive to implement perfectly | Good |
| **Clock** | Approximate LRU with use bit | Efficient, close to LRU | Not perfect LRU | Good |

**The Principles:**

1. **Locality is key** - Programs that reuse pages perform better
2. **History guides the future** - Recent access patterns predict future needs
3. **Perfect is expensive** - Approximations (Clock) work well enough
4. **Dirty pages cost more** - Prefer evicting clean pages
5. **Measure against optimal** - Know how much room for improvement exists

### 📊 Performance Patterns

```
No Locality Workload:
All policies equal → Cache size determines hit rate

80-20 Workload:
LRU > FIFO ≈ Random → History helps

Looping-Sequential Workload:
LRU = FIFO = 0% (disaster!)
Random > LRU → Corner case exists
```

### 🔄 Modern Developments

**The Renaissance:**
- Flash-based SSDs changing performance ratios
- SSD access: ~100μs (vs HDD ~10ms)
- Makes page replacement optimization relevant again
- New algorithms: ARC (scan-resistant), modern variants

**The Evolution:**
```
1960s: Memory scarce → Replacement critical
1990s-2000s: Memory cheap → "Just buy more RAM"
2010s-present: Fast SSDs → Replacement interesting again
```

> **💡 Final Insight**
>
> Page replacement policies embody a fundamental computer science challenge: predicting the future based on the past. The techniques developed here - using history, approximating optimal, balancing cost and benefit - apply far beyond virtual memory to caching at all levels of computer systems.

**Further Reading:**
- Scan-resistant algorithms: ARC (Adaptive Replacement Cache)
- Modern SSD-optimized policies
- Machine learning approaches to replacement

---

**Previous:** [Chapter 16: Segmentation](chapter16-segmentation.md) | **Next:** [Chapter 18: Complete VM Systems](chapter18-complete-vm-systems.md)
