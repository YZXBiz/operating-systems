# Chapter 7: Multiprocessor Scheduling 🔀

_Mastering the art of scheduling across multiple CPUs_

---

## 📋 Table of Contents

1. [🎯 Introduction](#1-introduction)
2. [🖥️ Background: Multiprocessor Architecture](#2-background-multiprocessor-architecture)
   - 2.1. [Hardware Caches and Memory](#21-hardware-caches-and-memory)
   - 2.2. [Cache Coherence Problem](#22-cache-coherence-problem)
   - 2.3. [Bus Snooping Solution](#23-bus-snooping-solution)
3. [🔒 Synchronization Challenges](#3-synchronization-challenges)
   - 3.1. [Race Conditions on Shared Data](#31-race-conditions-on-shared-data)
   - 3.2. [Locking for Correctness](#32-locking-for-correctness)
4. [📍 Cache Affinity](#4-cache-affinity)
5. [🎯 Single-Queue Multiprocessor Scheduling (SQMS)](#5-single-queue-multiprocessor-scheduling-sqms)
   - 5.1. [The Basic Approach](#51-the-basic-approach)
   - 5.2. [Scalability Problems](#52-scalability-problems)
   - 5.3. [Cache Affinity Issues](#53-cache-affinity-issues)
   - 5.4. [Affinity Mechanisms](#54-affinity-mechanisms)
6. [🔄 Multi-Queue Multiprocessor Scheduling (MQMS)](#6-multi-queue-multiprocessor-scheduling-mqms)
   - 6.1. [The Multi-Queue Approach](#61-the-multi-queue-approach)
   - 6.2. [Advantages of MQMS](#62-advantages-of-mqms)
   - 6.3. [Load Imbalance Problem](#63-load-imbalance-problem)
   - 6.4. [Work Stealing Solution](#64-work-stealing-solution)
7. [🐧 Linux Multiprocessor Schedulers](#7-linux-multiprocessor-schedulers)
   - 7.1. [The Three Approaches](#71-the-three-approaches)
   - 7.2. [Comparing Scheduler Designs](#72-comparing-scheduler-designs)
8. [📝 Summary](#8-summary)

---

## 1. 🎯 Introduction

**In plain English:** Imagine you're managing a restaurant kitchen 🍳 with multiple chefs (CPUs) instead of just one. Suddenly, everything gets more complicated! Do you give each chef their own order queue? Or one shared queue everyone picks from? What if one chef is idle while another is swamped? What if two chefs need the same ingredient at the same time?

**In technical terms:** Multiprocessor scheduling extends single-CPU scheduling to systems with multiple processors. While multicore processors are now ubiquitous—from smartphones 📱 to servers 🖥️—they introduce fundamental new challenges. The primary issue: a typical single-threaded application can't use multiple CPUs. Adding CPUs doesn't make your program faster unless you rewrite it using threads to parallelize the work.

**Why it matters:** Understanding multiprocessor scheduling is critical for modern computing. Single CPUs have hit power and heat limits 🔥, so manufacturers pack multiple cores onto chips instead. But exploiting this parallelism requires both application-level threading and OS-level scheduling intelligence to coordinate work efficiently across CPUs.

> **💡 Insight**
>
> The shift from single-core to multicore represents a **fundamental paradigm change** in computing. For decades, programs got faster automatically as CPUs improved (Moore's Law). Now, **concurrency is mandatory**—you must explicitly parallelize programs to benefit from hardware improvements. This pattern appears everywhere: GPUs, distributed systems, cloud computing. Understanding multiprocessor scheduling teaches you to think about parallel resource management.

### 🎯 The Core Challenge

**THE CRUX:** How should the OS schedule jobs on multiple CPUs? What new problems arise? Do the same old techniques work, or are new ideas required?

The fundamental challenges of multiprocessor scheduling:

```
Single CPU                    Multiple CPUs
─────────────                 ─────────────────
One job at a time       →     N jobs simultaneously
No coordination         →     Cache coherence needed
No shared data issues   →     Synchronization critical
Simple to reason about  →     Complex interactions

New Challenges:
├─ 🔄 Cache coherence (hardware)
├─ 🔒 Synchronization (software)
├─ 📍 Cache affinity (performance)
├─ ⚖️ Load balancing (fairness)
└─ 📈 Scalability (as CPUs grow)
```

> **💡 Insight**
>
> Multiprocessor scheduling reveals a **classic tradeoff pattern**: simplicity vs. performance vs. scalability. Single-queue designs are simple but don't scale. Multi-queue designs scale but introduce load imbalance. Work stealing solves load imbalance but adds complexity and overhead. There's no perfect solution—only careful engineering balancing competing concerns. This tradeoff appears in distributed systems, database design, and network protocols.

---

## 2. 🖥️ Background: Multiprocessor Architecture

### 2.1. 💾 Hardware Caches and Memory

**In plain English:** Caches are like a chef's 🧑‍🍳 mise en place—ingredients prepped and within arm's reach. It's much faster to grab pre-chopped onions from your cutting board than walk to the refrigerator every time. CPUs similarly keep frequently-used data in small, fast caches rather than fetching from large, slow main memory every time.

**In technical terms:** Modern CPUs use a hierarchy of hardware caches to bridge the speed gap between fast processors and slow memory:

```
Single CPU System
─────────────────

   ┌─────────────┐
   │     CPU     │  ← Fast (executes billions of instructions/sec)
   └─────┬───────┘
         │
    ┌────▼─────┐
    │  Cache   │     ← Small & Fast (64KB-8MB, ~1-10 nanoseconds)
    │ (L1/L2/  │        Holds copies of popular data
    │   L3)    │        Based on locality
    └────┬─────┘
         │
   ┌─────▼──────────┐
   │  Main Memory   │  ← Large & Slow (GBs, ~100+ nanoseconds)
   │   (DRAM)       │     Holds all data
   └────────────────┘
```

**How caches exploit locality:**

1. **Temporal Locality** ⏰
   - **Principle:** Data accessed recently will likely be accessed again soon
   - **Example:** Loop variables, function calls in a loop
   ```c
   for (int i = 0; i < 1000000; i++) {
       sum += i;  // 'sum' accessed repeatedly → stays in cache
   }
   ```

2. **Spatial Locality** 📍
   - **Principle:** Data near recently-accessed locations will likely be accessed soon
   - **Example:** Array traversal, sequential instruction execution
   ```c
   int arr[1000];
   for (int i = 0; i < 1000; i++) {
       arr[i] = i;  // arr[0], arr[1], arr[2]... fetched together
   }
   ```

**Cache operation example:**

```
First Access to Variable X           Second Access to Variable X
──────────────────────────           ───────────────────────────
1. CPU needs X                       1. CPU needs X
2. Check cache → MISS ❌              2. Check cache → HIT ✅
3. Fetch from memory (~100ns)        3. Use cached value (~1ns)
4. Store copy in cache               4. 100x faster! ⚡
5. Use the value
```

### 2.2. ⚠️ Cache Coherence Problem

**In plain English:** Imagine two chefs 👨‍🍳👩‍🍳 in different kitchens, both working from photocopies of the same recipe. If one chef updates their copy ("add more salt"), the other chef doesn't see the change and follows the old recipe. Their dishes won't match! This is the cache coherence problem—multiple CPUs with separate caches can have different views of the same memory location.

**In technical terms:** When multiple CPUs each have caches, a single memory location can exist in multiple caches simultaneously. Writes to that location must be coordinated, or caches become inconsistent:

```
Multiprocessor System with Caches
──────────────────────────────────

Step 1: Initial State
─────────────────────
┌──────────┐                    ┌──────────┐
│  CPU 1   │                    │  CPU 2   │
│  Cache:  │                    │  Cache:  │
│  [empty] │                    │  [empty] │
└────┬─────┘                    └────┬─────┘
     └────────┬───────────────────────┘
              │
        ┌─────▼──────┐
        │   Memory   │
        │  A = D     │  ← Original value at address A
        └────────────┘


Step 2: CPU 1 reads A
─────────────────────
┌──────────┐                    ┌──────────┐
│  CPU 1   │                    │  CPU 2   │
│  Cache:  │                    │  Cache:  │
│  A = D   │ ← Cached copy      │  [empty] │
└────┬─────┘                    └────┬─────┘
     └────────┬───────────────────────┘
              │
        ┌─────▼──────┐
        │   Memory   │
        │  A = D     │
        └────────────┘


Step 3: CPU 1 writes A = D' (cached, not written through yet)
──────────────────────────────────────────────────────────────
┌──────────┐                    ┌──────────┐
│  CPU 1   │                    │  CPU 2   │
│  Cache:  │                    │  Cache:  │
│  A = D'  │ ← Modified!        │  [empty] │
└────┬─────┘                    └────┬─────┘
     └────────┬───────────────────────┘
              │
        ┌─────▼──────┐
        │   Memory   │
        │  A = D     │  ← Still old value (write-back delay)
        └────────────┘


Step 4: Process migrates to CPU 2, reads A
───────────────────────────────────────────
┌──────────┐                    ┌──────────┐
│  CPU 1   │                    │  CPU 2   │
│  Cache:  │                    │  Cache:  │
│  A = D'  │                    │  A = D   │ ← Fetched old value! ❌
└────┬─────┘                    └────┬─────┘
     └────────┬───────────────────────┘
              │
        ┌─────▼──────┐
        │   Memory   │
        │  A = D     │  ← Process reads stale data!
        └────────────┘
```

**The problem in code:**

```c
// Running on CPU 1
int x = memory[A];     // x = D (fetches to CPU 1 cache)
memory[A] = x + 1;     // memory[A] = D' (updates CPU 1 cache only)

// OS moves process to CPU 2
int y = memory[A];     // y = D (CPU 2 fetches from memory, gets old value!)
                       // Should be D', but CPU 1 hasn't written back yet
```

### 2.3. 🔧 Bus Snooping Solution

**In plain English:** Imagine all chefs 👨‍🍳 work in an open kitchen where they can overhear each other. When one chef announces "I'm updating the salt measurement in recipe A," the others check if they have recipe A. If they do, they either erase their copy (invalidation) or update it to match (update). This "listening to the bus" is called bus snooping.

**In technical terms:** Hardware provides cache coherence through **bus snooping**—caches monitor (snoop) the shared bus connecting CPUs to memory. When one cache modifies data, it broadcasts the change on the bus, and other caches react:

**Two main coherence protocols:**

1. **Write-Invalidate Protocol** 🗑️ (most common)
   ```
   CPU 1 writes to A
        ↓
   Broadcast "A modified" on bus
        ↓
   Other CPUs snoop the bus
        ↓
   CPU 2 sees "A modified" → invalidates its copy of A
        ↓
   Next time CPU 2 needs A, it fetches fresh value
   ```

2. **Write-Update Protocol** 🔄
   ```
   CPU 1 writes A = D'
        ↓
   Broadcast "A = D'" on bus
        ↓
   Other CPUs snoop the bus
        ↓
   CPU 2 sees update → changes its cached A to D'
   ```

**Complete coherence example:**

```
Step-by-Step with Bus Snooping
──────────────────────────────

1. CPU 1 reads A = D
   ┌──────────┐     ┌──────────┐
   │  CPU 1   │     │  CPU 2   │
   │ Cache: A=D│     │ Cache: - │
   └──────────┘     └──────────┘
           Memory: A=D

2. CPU 1 writes A = D'
   ┌──────────┐     ┌──────────┐
   │  CPU 1   │     │  CPU 2   │
   │Cache: A=D'│     │ Cache: - │
   └──────────┘     └──────────┘
   ↓ Broadcasts "A modified" on bus

3. CPU 2 reads A
   - CPU 2 checks cache → MISS
   - CPU 2 requests A from memory
   - CPU 1 snoops request, sees it has modified A
   - CPU 1 provides D' (or forces write to memory first)
   ┌──────────┐     ┌──────────┐
   │  CPU 1   │     │  CPU 2   │
   │Cache: A=D'│     │Cache: A=D'│ ← Correct value! ✅
   └──────────┘     └──────────┘
           Memory: A=D'
```

> **💡 Insight**
>
> **Cache coherence is hardware's gift to programmers**. Without it, multiprocessor programming would be nightmarishly complex—you'd manually track which CPU last modified each memory location. But coherence only ensures **eventual consistency** of memory views. It doesn't prevent **race conditions** (two CPUs modifying data simultaneously). That requires synchronization primitives like locks—a software responsibility.

---

## 3. 🔒 Synchronization Challenges

### 3.1. ⚠️ Race Conditions on Shared Data

**In plain English:** Imagine two bank tellers 💼 processing withdrawals from the same account simultaneously. Both read "Balance: $100", both approve a $60 withdrawal, both write "Balance: $40". The account should have $0 (or reject one withdrawal), but instead has $40! Money appeared from nowhere because the operations **raced** against each other without coordination.

**In technical terms:** Even with cache coherence ensuring consistent memory views, **concurrent access to shared data structures** can corrupt them. Coherence prevents reading stale values, but doesn't make multi-step operations atomic.

**Classic example: Linked list deletion**

```c
typedef struct __Node_t {
    int value;
    struct __Node_t *next;
} Node_t;

Node_t *head;  // Global shared variable

int List_Pop() {
    Node_t *tmp = head;          // Line 1: Remember current head
    int value = head->value;     // Line 2: Get value
    head = head->next;           // Line 3: Advance head
    free(tmp);                   // Line 4: Free old head
    return value;                // Line 5: Return value
}
```

**Race condition scenario:**

```
Initial State: head → [A|next] → [B|next] → [C|next] → NULL

Thread 1 (CPU 1)                Thread 2 (CPU 2)
────────────────                ────────────────
tmp = head
  (tmp points to A)
                                tmp = head
                                  (tmp points to A) ← Same node!
value = head->value
  (value = A's data)
                                value = head->value
                                  (value = A's data)
head = head->next
  (head now points to B)
                                head = head->next
                                  (head now points to B) ← Redundant
free(tmp)
  (frees node A)
                                free(tmp) ← DOUBLE FREE! 💥
                                  (tries to free A again)
```

**Problems caused:**
1. ❌ **Double free** → crashes or corrupts memory allocator
2. ❌ **Both threads return same value** → lost data
3. ❌ **Node B referenced but A removed** → lost data permanently

> **💡 Insight**
>
> Cache coherence ensures **single memory operations** are atomic (you won't read half-written values). But **multi-step algorithms** like "remove from list" need atomicity across multiple operations. This is why **higher-level synchronization** (locks, transactions) is essential. The pattern repeats: hardware provides low-level guarantees, software builds higher-level abstractions on top.

### 3.2. 🔐 Locking for Correctness

**In plain English:** To fix the race condition, we need a "talking stick" 🎤—only the thread holding it can modify the shared list. Others must wait their turn. This stick is called a **mutex** (mutual exclusion lock).

**In technical terms:** Locks provide **mutual exclusion**—only one thread can hold a lock at a time. While locked, that thread has exclusive access to protected data.

**Corrected code with locking:**

```c
pthread_mutex_t list_lock = PTHREAD_MUTEX_INITIALIZER;  // Global lock
Node_t *head;  // Protected by list_lock

int List_Pop() {
    pthread_mutex_lock(&list_lock);      // Acquire lock (wait if held)

    if (head == NULL) {                  // Check for empty list
        pthread_mutex_unlock(&list_lock);
        return -1;  // Error: empty list
    }

    Node_t *tmp = head;                  // Critical section:
    int value = head->value;             // Only one thread here
    head = head->next;                   // at a time
    free(tmp);

    pthread_mutex_unlock(&list_lock);    // Release lock
    return value;
}
```

**How locks prevent races:**

```
Thread 1                           Thread 2
────────                           ────────
lock(&list_lock)
  ✅ Acquired
                                   lock(&list_lock)
tmp = head                           🔄 Waiting... (blocked)
value = head->value                  🔄 Waiting...
head = head->next                    🔄 Waiting...
free(tmp)                            🔄 Waiting...
unlock(&list_lock)
  ✅ Released                        ✅ Now acquires lock!
                                   tmp = head
                                   value = head->value
                                   head = head->next
                                   free(tmp)
                                   unlock(&list_lock)
```

**Performance implications:**

```
Sequential Operations          With Lock Contention
────────────────────          ────────────────────
Thread 1: Pop (10μs)          Thread 1: Pop (10μs)
Thread 2: Pop (10μs)          Thread 2: Wait (10μs) + Pop (10μs) = 20μs
Thread 3: Pop (10μs)          Thread 3: Wait (20μs) + Pop (10μs) = 30μs
Thread 4: Pop (10μs)          Thread 4: Wait (30μs) + Pop (10μs) = 40μs
─────────────────             ──────────────────────────────────
Total: 40μs                   Total: 100μs (2.5x slower!)

Speedup from 4 CPUs: None! 😞
```

> **💡 Insight**
>
> Locks sacrifice **parallelism for correctness**. With one lock protecting a data structure, only one CPU can access it at a time—you've created a **serialization bottleneck**. As the number of CPUs grows, contention worsens. This is why modern designs use:
> - **Fine-grained locking** (multiple locks for different parts)
> - **Lock-free data structures** (clever atomic operations)
> - **Per-CPU data structures** (eliminate sharing entirely)
>
> The fundamental principle: **shared state is the enemy of scalability**.

---

## 4. 📍 Cache Affinity

**In plain English:** Imagine you've set up your workbench 🔧 with all your tools organized exactly how you like them. If someone makes you switch to a different workbench, you waste time setting up again. Similarly, when a process runs on a CPU, it "warms up" that CPU's cache with its data. Moving to a different CPU means starting over with a cold cache ❄️—everything must be fetched from slow memory again.

**In technical terms:** **Cache affinity** refers to the performance benefit when a process continues running on the same CPU it ran on previously. The CPU's caches (L1, L2, L3) and TLB (translation lookaside buffer) retain the process's:
- Frequently-accessed data
- Recently-executed code
- Virtual-to-physical address translations

**Performance impact example:**

```
Process A's Memory Access Pattern
──────────────────────────────────
Access 1000 array elements repeatedly in a loop

Scenario 1: Always runs on CPU 0 (Good Cache Affinity) ✅
────────────────────────────────────────────────────────
First loop iteration:
  - 1000 cache misses → Load from memory (slow)
  - Populate CPU 0's cache

Subsequent iterations:
  - 1000 cache hits → Read from cache (fast) ⚡
  - 100x faster than first iteration

Total time: 100μs (first) + 1μs × 999 = 1,099μs


Scenario 2: Migrates to different CPU each time (Poor Affinity) ❌
──────────────────────────────────────────────────────────────────
Iteration 1 on CPU 0:
  - 1000 cache misses → Load to CPU 0 cache

Iteration 2 on CPU 1:
  - 1000 cache misses → Load to CPU 1 cache (CPU 0 cache useless)

Iteration 3 on CPU 2:
  - 1000 cache misses → Load to CPU 2 cache

...pattern continues...

Total time: 100μs × 1000 = 100,000μs (100x slower!) 🐌
```

**Affinity in scheduling decisions:**

```
Good Scheduling (Preserves Affinity)        Bad Scheduling (Ignores Affinity)
────────────────────────────────────        ──────────────────────────────────

CPU 0    CPU 1    CPU 2    CPU 3           CPU 0    CPU 1    CPU 2    CPU 3
─────    ─────    ─────    ─────           ─────    ─────    ─────    ─────
  A        B        C        D                A        B        C        D
  A        B        C        D                B        C        D        A
  A        B        C        D                C        D        A        B
  A        B        C        D                D        A        B        C
  A        B        C        D                A        B        C        D

✅ A always on CPU 0                        ❌ A bounces across all CPUs
✅ Cache stays warm                         ❌ Cache always cold
```

**What gets cached:**

| Cache Type | Contents | Size | Affinity Benefit |
|------------|----------|------|------------------|
| **L1 Data** | Recently accessed variables | 32-64 KB | Huge (1-4 cycles vs 200+) |
| **L1 Instruction** | Recently executed code | 32-64 KB | Huge (avoid refetch) |
| **L2 Unified** | Mix of data/instructions | 256 KB-1 MB | Large (10-20 cycles vs 200+) |
| **L3 Shared** | Shared across cores | 4-32 MB | Medium (40-75 cycles vs 200+) |
| **TLB** | Virtual→Physical translations | 64-1024 entries | Critical (avoid page walks) |

> **💡 Insight**
>
> Cache affinity creates a **tension between load balancing and performance**. Moving a process achieves better load balance but hurts performance due to cache loss. The optimal solution depends on:
> - **How long the process will run** (longer = more benefit from affinity)
> - **How severe the imbalance** (extreme imbalance justifies migration cost)
> - **Cache footprint size** (small footprint = faster to warm up again)
>
> This balancing act appears in many domains: database query optimization (change plans mid-flight?), network routing (reroute flows?), cloud resource management (migrate VMs?). The pattern: **stability has value, but so does optimization**.

---

## 5. 🎯 Single-Queue Multiprocessor Scheduling (SQMS)

### 5.1. 📋 The Basic Approach

**In plain English:** Imagine a single waiting line 📏 at a bank with multiple tellers 💼. All customers join one queue, and the next available teller serves the next customer. Simple and fair! Similarly, SQMS uses one shared queue containing all runnable processes. Each CPU picks the next job from this single queue.

**In technical terms:** Single-Queue Multiprocessor Scheduling (SQMS) reuses single-CPU scheduling algorithms by maintaining one global ready queue. When a CPU needs work, it picks the next process according to the scheduling policy (round-robin, priority-based, etc.).

**Basic structure:**

```
SQMS Architecture
─────────────────

                    Global Ready Queue
          ┌─────────────────────────────────────┐
          │  [A] → [B] → [C] → [D] → [E] → NULL │  ← Single shared queue
          └─────────────────────────────────────┘
                     ↑         ↑         ↑
                     │         │         │
           ┌─────────┴───┬─────┴───┬─────┴──────┐
           │             │         │            │
        ┌──▼──┐       ┌──▼──┐   ┌──▼──┐      ┌──▼──┐
        │CPU 0│       │CPU 1│   │CPU 2│      │CPU 3│
        └─────┘       └─────┘   └─────┘      └─────┘
     (running A)   (running B) (running C)  (running D)
```

**Example scheduling trace:**

```
Time Slice Schedule (4 CPUs, 5 Jobs, Round-Robin)
──────────────────────────────────────────────────

Time    CPU 0    CPU 1    CPU 2    CPU 3    Queue
────    ─────    ─────    ─────    ─────    ─────
1       A        B        C        D        [E]
2       E        A        B        C        [D]
3       D        E        A        B        [C]
4       C        D        E        A        [B]
5       B        C        D        E        [A]
6       A        B        C        D        [E]
...     (pattern repeats)
```

**Advantages:** ✅
1. **Simplicity** 🎯
   - Reuse existing single-CPU scheduler
   - Minimal code changes
   - Easy to understand and debug

2. **Automatic Load Balancing** ⚖️
   - Idle CPU automatically picks next job
   - No explicit balancing logic needed

### 5.2. ⚠️ Scalability Problems

**In plain English:** Imagine 100 bank tellers 💼 all reaching for the same customer list 📋. They constantly bump into each other, fight over the clipboard, and spend more time managing the list than serving customers. This is SQMS with many CPUs—lock contention on the shared queue becomes the bottleneck.

**In technical terms:** SQMS requires a lock to protect the shared queue from concurrent access. As the number of CPUs increases, lock contention grows **superlinearly**, causing severe scalability problems.

**Lock contention analysis:**

```
Scaling from 1 to 8 CPUs
────────────────────────

1 CPU:  No contention (only one accessor)
        ┌───┐
        │ Q │ ← CPU 0
        └───┘
        Overhead: 0%

2 CPUs: Occasional contention
        ┌───┐
        │ Q │ ← CPU 0, CPU 1 (sometimes conflict)
        └───┘
        Overhead: ~5%

4 CPUs: Frequent contention
        ┌───┐
        │ Q │ ← CPU 0, CPU 1, CPU 2, CPU 3 (often conflict)
        └───┘
        Overhead: ~20%

8 CPUs: Constant contention
        ┌───┐
        │ Q │ ← CPU 0-7 (always fighting for lock)
        └───┘
        Overhead: ~60% 🔥
```

**Performance degradation:**

```c
// Every schedule() call needs to acquire lock
void schedule() {
    lock(&global_queue_lock);        // Wait for lock...
    struct proc *next = dequeue();   // Quick operation
    unlock(&global_queue_lock);      // Release lock
    context_switch(current, next);   // Actual work
}

// With high CPU count:
// - lock() takes longer (spinning/waiting)
// - dequeue() is tiny compared to lock overhead
// - Most time spent on synchronization, not scheduling!
```

**Measured slowdown example:**

| CPUs | Useful Work | Lock Overhead | Total Time | Efficiency |
|------|-------------|---------------|------------|------------|
| 1 | 100μs | 0μs | 100μs | 100% ✅ |
| 2 | 100μs | 5μs | 105μs | 95% ✅ |
| 4 | 100μs | 25μs | 125μs | 80% ⚠️ |
| 8 | 100μs | 150μs | 250μs | 40% ❌ |
| 16 | 100μs | 600μs | 700μs | 14% 💥 |

> **💡 Insight**
>
> **Amdahl's Law** strikes again! Even if 90% of your scheduler is parallel, the 10% serial portion (lock acquisition) limits scalability. With 16 CPUs, speedup maxes out at 10x, not 16x. This fundamental principle appears everywhere in parallel computing: **serial bottlenecks** destroy scalability. The solution: **eliminate shared state** (as MQMS does) or use lock-free algorithms.

### 5.3. 🔄 Cache Affinity Issues

**In plain English:** With a single queue, it's like musical chairs 🎵—processes keep switching CPUs every time the music stops. Job A runs on CPU 0, then CPU 2, then CPU 1... always starting with a cold cache. Nobody gets to settle down and warm up their workspace.

**In technical terms:** SQMS with simple round-robin scheduling naturally causes processes to migrate across CPUs, destroying cache affinity.

**Cache affinity problem example:**

```
Job Distribution (5 jobs, 4 CPUs, time slices)
───────────────────────────────────────────────

CPU 0    CPU 1    CPU 2    CPU 3    Analysis
─────    ─────    ─────    ─────    ────────
A        B        C        D        Initial placement
E        A        B        C        A: CPU0→CPU1 (cache miss)
D        E        A        B        A: CPU1→CPU2 (cache miss)
C        D        E        A        A: CPU2→CPU3 (cache miss)
B        C        D        E        A: CPU3→   (cache miss)
A        B        C        D        A: →CPU0   (cache miss)

Every job migrates to every CPU! ❌
Every time = cold cache = poor performance 🐌
```

**Cache pollution effect:**

```
Process A's perspective (bouncing between CPUs)
───────────────────────────────────────────────

Run 1 on CPU 0:
  - Load working set to CPU 0 cache (1000 cache misses)
  - Execute (fast)

Run 2 on CPU 1:
  - CPU 0 cache is now useless
  - Load working set to CPU 1 cache (1000 cache misses again!) ❌
  - Execute (fast)

Run 3 on CPU 2:
  - CPU 1 cache is now useless
  - Load working set to CPU 2 cache (1000 cache misses again!) ❌
  - Execute (fast)

Pattern: Constant cache misses, never reuse cached data 🔥
```

### 5.4. 🔧 Affinity Mechanisms

**In plain English:** To fix cache affinity, we give some jobs "reserved seats" 💺—they prefer certain CPUs. It's like having regular customers sit at their favorite table 🪑, where the waiter already knows their order. We only shuffle people when absolutely necessary to balance the load.

**In technical terms:** SQMS implementations add **affinity hints** to the scheduler. Each process has a **preferred CPU**. The scheduler tries to run processes on their preferred CPU, but can migrate them for load balancing.

**Affinity-aware scheduling:**

```c
struct proc {
    int pid;
    int preferred_cpu;      // Affinity hint
    int last_cpu;           // Track migrations
    // ... other fields ...
};

struct proc* pick_next_job(int current_cpu) {
    lock(&global_queue_lock);

    // Strategy 1: Look for jobs with affinity to current CPU
    struct proc *p = find_in_queue_with_affinity(current_cpu);
    if (p) {
        dequeue(p);
        unlock(&global_queue_lock);
        return p;
    }

    // Strategy 2: Take any job, update its affinity
    p = dequeue_next();
    p->preferred_cpu = current_cpu;
    unlock(&global_queue_lock);
    return p;
}
```

**Improved scheduling pattern:**

```
Affinity-Aware Schedule (5 jobs, 4 CPUs)
────────────────────────────────────────

Assignment: A→CPU0, B→CPU1, C→CPU2, D→CPU3, E→floater

CPU 0    CPU 1    CPU 2    CPU 3    Analysis
─────    ─────    ─────    ─────    ────────
A        B        C        D        Initial
A        B        E        D        C done; E floats
A        B        E        C        D done; C returns to CPU2
A        E        B        C        E floats to CPU1; B to CPU2
A        E        B        C        Stable assignments
A        E        B        C        A,B,C stay put ✅

Jobs A, B, C maintain affinity 👍
Only E migrates (load balancing) ⚖️
Cache warmth preserved for A, B, C 🔥
```

**Affinity strategies:**

1. **Strict Affinity** 🔒
   ```
   - Process ONLY runs on preferred CPU
   - May cause imbalance (some CPUs idle while others overloaded)
   - Used for: Real-time systems, NUMA architectures
   ```

2. **Soft Affinity** 🌊 (most common)
   ```
   - Process PREFERS certain CPU, but can migrate
   - Threshold-based: migrate only if imbalance exceeds X%
   - Used for: General-purpose OS (Linux, Windows)
   ```

3. **Affinity Rotation** 🔄
   ```
   - Each process gets affinity to one CPU for N time slices
   - Then reassign affinity to balance load
   - Used for: Fairness-focused schedulers
   ```

**Affinity fairness example:**

```
Round-Robin Affinity Assignment
────────────────────────────────

Round 1 (time slices 1-5):
  A→CPU0, B→CPU1, C→CPU2, D→CPU3, E→CPU0

Round 2 (time slices 6-10):
  A→CPU1, B→CPU2, C→CPU3, D→CPU0, E→CPU1

Round 3 (time slices 11-15):
  A→CPU2, B→CPU3, C→CPU0, D→CPU1, E→CPU2

Ensures:
✅ Each job eventually runs on each CPU
✅ Load balanced across CPUs
✅ Multi-slice affinity windows preserve caching
```

> **💡 Insight**
>
> Affinity mechanisms demonstrate **heuristic-based system design**. There's no perfect algorithm—you're balancing conflicting goals (cache warmth vs. load balance). Real systems use **tunable policies** with parameters like:
> - Migration threshold (how imbalanced before moving jobs?)
> - Affinity strength (how strongly prefer certain CPU?)
> - Time quantum (how long before reconsidering?)
>
> This pattern appears in networking (congestion control), databases (query planning), and compilers (register allocation): **use heuristics, measure, tune**.

**SQMS Summary:**

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Simplicity** | ⭐⭐⭐⭐⭐ | Easy to implement |
| **Load Balancing** | ⭐⭐⭐⭐ | Automatic from shared queue |
| **Scalability** | ⭐⭐ | Lock contention limits scaling |
| **Cache Affinity** | ⭐⭐ | Poor without affinity hints; medium with |

---

## 6. 🔄 Multi-Queue Multiprocessor Scheduling (MQMS)

### 6.1. 🎯 The Multi-Queue Approach

**In plain English:** Instead of one long line at the bank, imagine each teller has their own customer queue 🏦. Customers pick a line when they enter, and generally stay with that teller. No more fighting over one shared list! Each teller (CPU) independently manages their own queue (schedule).

**In technical terms:** Multi-Queue Multiprocessor Scheduling (MQMS) gives each CPU its own scheduling queue. When a job arrives, it's placed on one CPU's queue (via some heuristic—random, shortest queue, etc.) and scheduled independently by that CPU.

**MQMS architecture:**

```
Multi-Queue Structure
─────────────────────

    ┌─────────┐      ┌─────────┐      ┌─────────┐      ┌─────────┐
    │ Queue 0 │      │ Queue 1 │      │ Queue 2 │      │ Queue 3 │
    │         │      │         │      │         │      │         │
    │ [A]→[C] │      │ [B]→[D] │      │ [E]→[G] │      │ [F]→[H] │
    └────┬────┘      └────┬────┘      └────┬────┘      └────┬────┘
         │                │                │                │
      ┌──▼──┐          ┌──▼──┐          ┌──▼──┐          ┌──▼──┐
      │CPU 0│          │CPU 1│          │CPU 2│          │CPU 3│
      └─────┘          └─────┘          └─────┘          └─────┘
   (running A)      (running B)      (running E)      (running F)

Each CPU has:
✅ Private queue (no sharing!)
✅ Independent scheduler
✅ Own lock (minimal contention)
```

**Job placement strategies:**

1. **Random Assignment** 🎲
   ```c
   int assign_cpu = random() % num_cpus;
   enqueue(cpu_queues[assign_cpu], new_job);
   ```
   - Simple, statistically balances load
   - No coordination needed

2. **Round-Robin Assignment** 🔄
   ```c
   static int next_cpu = 0;
   enqueue(cpu_queues[next_cpu], new_job);
   next_cpu = (next_cpu + 1) % num_cpus;
   ```
   - Evenly distributes jobs
   - Requires counter synchronization

3. **Shortest Queue** 📏
   ```c
   int shortest = find_shortest_queue();
   enqueue(cpu_queues[shortest], new_job);
   ```
   - Best load balance at placement time
   - Requires checking all queues (overhead)

**Example scheduling trace:**

```
Initial Assignment (Round-Robin placement)
──────────────────────────────────────────

Job A → Queue 0
Job B → Queue 1
Job C → Queue 0
Job D → Queue 1

Queue 0: [A] → [C]
Queue 1: [B] → [D]
Queue 2: []
Queue 3: []


Execution Timeline (Round-Robin scheduling within each queue)
──────────────────────────────────────────────────────────────

Time    CPU 0 (Q0)    CPU 1 (Q1)    CPU 2 (Q2)    CPU 3 (Q3)
────    ──────────    ──────────    ──────────    ──────────
1       A             B             idle          idle
2       C             D             idle          idle
3       A             B             idle          idle
4       C             D             idle          idle
5       A             B             idle          idle
...
```

### 6.2. ✅ Advantages of MQMS

**In plain English:** Each CPU is like a independent restaurant kitchen 🍳 with its own order queue. Chefs don't interfere with each other, don't fight over the same order tickets, and develop familiarity with their regular dishes (cache affinity). It's the "divide and conquer" approach to scheduling.

**1. Scalability** 📈

```
Lock Contention Comparison
──────────────────────────

SQMS (Single Queue):                    MQMS (Multi Queue):
All CPUs compete for one lock           Each CPU has its own lock

┌─────────────┐                         ┌────┐ ┌────┐ ┌────┐ ┌────┐
│ Global Lock │                         │ L0 │ │ L1 │ │ L2 │ │ L3 │
└──────┬──────┘                         └─┬──┘ └─┬──┘ └─┬──┘ └─┬──┘
       ↓                                  ↓      ↓      ↓      ↓
┌──────┴──────────────┐                ┌──▼─┐ ┌──▼─┐ ┌──▼─┐ ┌──▼─┐
│ CPU0 CPU1 CPU2 CPU3 │                │Q0  │ │Q1  │ │Q2  │ │Q3  │
│  ↑    ↑    ↑    ↑   │                └────┘ └────┘ └────┘ └────┘
│  └────┴────┴────┘   │
│   All competing!    │                 No contention! ✅
└─────────────────────┘
Contention = O(N²)                      Contention = O(1)
```

**Performance scaling:**

| CPUs | SQMS Overhead | MQMS Overhead | MQMS Advantage |
|------|---------------|---------------|----------------|
| 1 | 1x | 1x | 1.0x |
| 2 | 2x | 1x | 2.0x ⭐ |
| 4 | 8x | 1x | 8.0x ⭐⭐ |
| 8 | 32x | 1x | 32.0x ⭐⭐⭐ |
| 16 | 128x | 1x | 128.0x ⭐⭐⭐⭐ |

**2. Cache Affinity** 🔥

```
Natural Affinity (jobs stay on assigned CPU)
────────────────────────────────────────────

CPU 0 runs:  A → C → A → C → A → C ...
             └─────────┬──────────┘
                  Cache stays warm ✅

CPU 1 runs:  B → D → B → D → B → D ...
             └─────────┬──────────┘
                  Cache stays warm ✅

Compare to SQMS:
CPU 0 runs:  A → E → D → C → B → A ...
             └─────────┬──────────┘
                  Always cold ❌
```

**Cache hit rate comparison:**

```
Workload: Each job accesses 1000 data items repeatedly

SQMS (job bouncing):
- Iteration 1: 1000 misses (load to cache)
- Iteration 2: 1000 misses (different CPU, reload)
- Iteration 3: 1000 misses (different CPU, reload)
Hit rate: ~0% 😞

MQMS (job sticky):
- Iteration 1: 1000 misses (load to cache)
- Iteration 2: 1000 hits (same CPU!) ⚡
- Iteration 3: 1000 hits (same CPU!) ⚡
Hit rate: ~99% 🎉
```

**3. Simplicity** 🎯

```c
// Each CPU independently schedules
void schedule_on_this_cpu() {
    int cpu_id = get_current_cpu();

    lock(&queue_locks[cpu_id]);           // Only lock OWN queue
    struct proc *next = dequeue(&queues[cpu_id]);
    unlock(&queue_locks[cpu_id]);

    context_switch(current, next);
    // No coordination with other CPUs! ✅
}
```

### 6.3. ⚠️ Load Imbalance Problem

**In plain English:** Imagine four restaurant kitchens 🍳. Kitchen 1 has 10 orders, kitchens 2-4 have zero. Customers wait 30 minutes in kitchen 1 while chefs in kitchens 2-4 play cards 🃏. The total capacity is fine, but poor distribution means bad service!

**In technical terms:** MQMS can suffer severe **load imbalance**—some CPUs overloaded while others are idle. Unlike SQMS where idle CPUs automatically grab work from the shared queue, MQMS CPUs can't see each other's queues without explicit migration logic.

**Imbalance scenario 1: Job completion**

```
Initial State (balanced)
────────────────────────
Queue 0: [A] → [C]
Queue 1: [B] → [D]

CPU 0    CPU 1
─────    ─────
A        B
C        D
A        B
C        D
...


After C finishes
────────────────
Queue 0: [A]
Queue 1: [B] → [D]

CPU 0    CPU 1          Analysis
─────    ─────          ────────
A        B              CPU 1 has 2x the work
A        D              CPU 0 gets 2x the CPU
A        B              Unfair! ❌
A        D
A        B              Jobs B and D suffer
A        D              Job A gets twice the CPU it deserves
...
```

**Imbalance scenario 2: All jobs finish on one queue**

```
Initial State
─────────────
Queue 0: [A] → [B]
Queue 1: [C] → [D]

After A, B finish; C, D continue
────────────────────────────────
Queue 0: []
Queue 1: [C] → [D]

CPU 0    CPU 1          Analysis
─────    ─────          ────────
idle     C              50% CPU utilization! 💥
idle     D              CPU 0 wasted
idle     C              System running at half capacity
idle     D              Terrible resource usage
...
```

**Severe imbalance example:**

```
Worst Case: All jobs on one queue
──────────────────────────────────

Queue 0: [A] → [B] → [C] → [D] → [E] → [F]
Queue 1: []
Queue 2: []
Queue 3: []

Time Wasted Per Job = 3 × (time if balanced)

Job A's perspective:
- With balance: Runs every 2 time slices (4 CPUs, 4 jobs effective)
- With imbalance: Runs every 6 time slices (sharing 1 CPU with 5 jobs)
- 3x slower response time! 😞
```

**Why SQMS doesn't have this problem:**

```
SQMS (Self-Balancing)              MQMS (Imbalance-Prone)
─────────────────────              ───────────────────────

    [Shared Queue]                 Queue 0: [A] [B] [C]
    [A][B][C][D][E]                Queue 1: []
         ↓                         Queue 2: [D]
    All CPUs see                   Queue 3: [E]
    same queue →                        ↓
    Idle CPU grabs work ✅         Idle CPU doesn't see
                                   other queues' work ❌
```

> **💡 Insight**
>
> **Load imbalance reveals the MQMS tradeoff**: isolation improves scalability and cache affinity but loses **global knowledge**. This is a microcosm of distributed systems—partitioning data reduces coordination overhead but creates imbalance. Solutions: periodic rebalancing (MQMS work stealing) or consistent hashing (distributed systems). The fundamental challenge: **local decisions with global consequences**.

### 6.4. 🔄 Work Stealing Solution

**In plain English:** If you're a chef 👨‍🍳 with nothing to do, peek into other kitchens. If someone's swamped, steal an order from their queue and cook it yourself! But don't peek too often—walking around wastes time. This is **work stealing**: idle CPUs occasionally migrate jobs from busy CPUs.

**In technical terms:** Work stealing is a migration technique where an idle (or underloaded) CPU periodically checks other CPUs' queues. If it finds a queue significantly fuller than its own, it steals one or more jobs.

**Work stealing algorithm:**

```c
// Called when CPU's local queue is empty or low
void work_steal() {
    int my_cpu = get_current_cpu();
    int my_queue_len = queue_length(queues[my_cpu]);

    // Check other CPUs' queues
    for (int target_cpu = 0; target_cpu < num_cpus; target_cpu++) {
        if (target_cpu == my_cpu) continue;

        lock(&queue_locks[target_cpu]);
        int target_queue_len = queue_length(queues[target_cpu]);

        // Steal if target has significantly more work
        if (target_queue_len > my_queue_len + THRESHOLD) {
            struct proc *stolen = dequeue(&queues[target_cpu]);
            unlock(&queue_locks[target_cpu]);

            lock(&queue_locks[my_cpu]);
            enqueue(&queues[my_cpu], stolen);
            unlock(&queue_locks[my_cpu]);

            return;  // Success!
        }
        unlock(&queue_locks[target_cpu]);
    }
}
```

**Work stealing example:**

```
Before Work Stealing
────────────────────
Queue 0: []
Queue 1: [B] → [D]

CPU 0: idle 😴
CPU 1: B (working hard)


Work Stealing Process
─────────────────────
1. CPU 0 notices it's idle
2. CPU 0 checks CPU 1's queue → length 2
3. CPU 0 steals job D
4. D migrates from Queue 1 to Queue 0


After Work Stealing
───────────────────
Queue 0: [D]
Queue 1: [B]

CPU 0: D ⚡
CPU 1: B ⚡

Result: Both CPUs utilized! ✅
```

**Fixing the earlier imbalance:**

```
Scenario: Jobs finish on one queue
───────────────────────────────────

Initial (Imbalanced):
Queue 0: []
Queue 1: [C] → [D]

Step 1: CPU 0 goes idle, checks CPU 1
Step 2: CPU 0 steals D

After First Steal:
Queue 0: [D]
Queue 1: [C]

Result:
CPU 0: D ⚡
CPU 1: C ⚡
Perfect balance achieved! ✅
```

**Work stealing parameters:**

1. **Steal Frequency** ⏰
   ```
   Too Frequent:                      Too Rare:
   - High overhead (checking queues)  - Long imbalance periods
   - Lock contention                  - Wasted CPU cycles
   - Cache disruption                 - Unfairness

   Typical: Check every 10-100ms
   ```

2. **Steal Threshold** 📏
   ```
   Threshold = Difference to trigger steal

   Low Threshold (e.g., 1 job):       High Threshold (e.g., 5 jobs):
   - Aggressive balancing             - Tolerate imbalance
   - More migration (cache misses)    - Less migration (better affinity)
   - Better load balance              - Occasional severe imbalance

   Typical: 2-3 jobs or 20-30% difference
   ```

3. **Steal Amount** 📦
   ```
   Steal One Job:                     Steal Half:
   - Minimal disruption               - Faster rebalancing
   - May require multiple rounds      - Risk over-migration
   - Better for small imbalances      - Better for large imbalances

   Typical: 1 job (simple), or (target_len - my_len)/2 (aggressive)
   ```

**Work stealing visualization:**

```
Timeline: Work Stealing in Action
──────────────────────────────────

Time 0: Job placement
Queue 0: [A] → [C]
Queue 1: [B] → [D]
Queue 2: []
Queue 3: []

Time 1: C finishes
Queue 0: [A]
Queue 1: [B] → [D]
Queue 2: []
Queue 3: []

Time 50: CPU 2 checks for work (threshold = 2)
CPU 2: My queue length = 0
CPU 2: Scanning...
CPU 2: CPU 1 has length 2 → difference = 2 → STEAL!

After Steal:
Queue 0: [A]
Queue 1: [B]
Queue 2: [D]  ← Stolen!
Queue 3: []

Time 100: A finishes
Queue 0: []
Queue 1: [B]
Queue 2: [D]
Queue 3: []

Time 150: CPU 0 steals from CPU 1
Queue 0: [B]  ← Stolen!
Queue 1: []
Queue 2: [D]
Queue 3: []

Result: Work balanced across CPUs! ⚖️
```

**Work stealing overhead analysis:**

```
Best Case (Balanced Load):
- Steal checks find no imbalance
- Overhead: 1 lock acquire per check per CPU
- Acceptable if infrequent (e.g., every 100ms)

Worst Case (Frequent Imbalance):
- Constant stealing
- Overhead: Lock contention + migration + cache misses
- Can approach SQMS overhead if too aggressive!

Sweet Spot:
- Rare imbalances detected and fixed quickly
- Minimal overhead, good balance
- Achieved by tuning frequency and threshold
```

> **💡 Insight**
>
> Work stealing exemplifies **eventual consistency**—systems don't maintain perfect balance continuously, but detect and correct imbalances periodically. This appears throughout distributed systems:
> - **Gossip protocols** (eventually propagate information)
> - **Load balancers** (periodically rebalance)
> - **Garbage collectors** (eventually reclaim memory)
>
> Perfect real-time consistency is expensive. Eventual consistency with bounded convergence time is practical. The art lies in tuning detection frequency vs. correction overhead.

**MQMS Summary:**

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Simplicity** | ⭐⭐⭐ | More complex than SQMS (migration logic) |
| **Load Balancing** | ⭐⭐⭐ | Good with work stealing; poor without |
| **Scalability** | ⭐⭐⭐⭐⭐ | Excellent (no shared queue contention) |
| **Cache Affinity** | ⭐⭐⭐⭐⭐ | Excellent (jobs stay on same CPU) |

---

## 7. 🐧 Linux Multiprocessor Schedulers

### 7.1. 🎯 The Three Approaches

**In plain English:** The Linux community couldn't agree on one "best" scheduler, so three different approaches evolved 🔀. It's like three different restaurants 🍽️ with competing philosophies—one focuses on low overhead (O(1)), one on fairness (CFS), and one on simplicity (BFS). Each has succeeded in production, proving multiple solutions can work!

**In technical terms:** Linux has featured three major multiprocessor schedulers over time. All are production-quality, but optimize for different goals. Understanding them reveals that scheduler design involves fundamental tradeoffs with no single optimal solution.

**The three schedulers:**

```
Linux Scheduler Evolution
─────────────────────────

    O(1) Scheduler              CFS                    BFS
    (2002-2007)           (2007-present)          (2009-present)
    ──────────────        ───────────────         ──────────────

    🎯 Priority-based     ⚖️ Proportional-share    🎯 Simple SQMS
    📊 Multi-Queue        📊 Multi-Queue           📊 Single-Queue
    ⚡ Interactive focus  🔄 Fairness focus        🎯 Simplicity focus

    Used in:              Used in:                 Used in:
    - RHEL 4/5            - Mainline Linux         - BFS/MuQSS patches
    - Older kernels       - All modern distros     - Desktop-focused
```

### 1. 🚀 O(1) Scheduler (2002-2007)

**Core idea:** Constant-time scheduling operations, priority-based with interactivity bonuses.

**Architecture:**

```
O(1) Multi-Queue Structure (per CPU)
────────────────────────────────────

Each CPU has TWO arrays of queues:

Active Array (140 priority levels):        Expired Array (140 priority levels):
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│ Priority 0:   [A] → [B]         │       │ Priority 0:   []                │
│ Priority 1:   [C]               │       │ Priority 1:   []                │
│ Priority 2:   []                │       │ Priority 2:   [D]               │
│ ...                             │       │ ...                             │
│ Priority 139: [E] → [F]         │       │ Priority 139: []                │
└─────────────────────────────────┘       └─────────────────────────────────┘
          ↑                                         ↑
    Schedule from here first              Time slice expired? → Move here
```

**O(1) scheduling algorithm:**

```c
// Constant time: just find highest non-empty priority
struct task_struct* pick_next_task() {
    struct runqueue *rq = this_cpu_runqueue();

    // Bitmap tracks which priorities have jobs (one bit per priority)
    int priority = find_first_set_bit(rq->active_bitmap);  // O(1)

    if (priority >= 0) {
        struct list_head *queue = &rq->active[priority];
        struct task_struct *next = list_first_entry(queue);  // O(1)
        return next;
    }

    // Active array empty? Swap active ↔ expired
    swap(rq->active, rq->expired);  // O(1)
    return pick_next_task();  // Try again
}
```

**Why O(1)?**
- Find priority: O(1) bitmap scan
- Get task: O(1) list head access
- Total: O(1) regardless of number of tasks! ⚡

**Interactivity heuristics:**
```
Bonus/Penalty System
────────────────────
Sleep time ↑ → Interactive (I/O-bound) → Priority ↑ (bonus)
CPU time ↑   → CPU-bound              → Priority ↓ (penalty)

Example:
- Text editor (lots of sleeping, waiting for keystrokes): +5 bonus
- Video encoder (constant CPU): -5 penalty
```

**Why it was replaced:** Complex heuristics were hard to tune. Some workloads gamed the system, getting unfair CPU time.

### 2. ⚖️ Completely Fair Scheduler (CFS) (2007-present)

**Core idea:** Track CPU time precisely, always schedule task with least CPU time. Deterministic fairness.

**Architecture:**

```
CFS Per-CPU Red-Black Tree
───────────────────────────

Each CPU has a red-black tree sorted by vruntime (virtual runtime):

                    ┌────────┐
                    │ Task C │
                    │ vr=50  │
                    └───┬────┘
                   /           \
            ┌─────▼──┐        ┌──▼─────┐
            │ Task A │        │ Task E │
            │ vr=10  │        │ vr=80  │
            └────┬───┘        └────────┘
                /
         ┌─────▼──┐
         │ Task B │
         │ vr=5   │  ← Leftmost = least runtime = next to run!
         └────────┘
```

**CFS scheduling algorithm:**

```c
// Pick task with minimum vruntime (leftmost in tree)
struct task_struct* pick_next_task() {
    struct rbtree *tree = this_cpu_rbtree();

    // Leftmost node = minimum vruntime
    struct rb_node *leftmost = rb_first(tree);  // O(1) cached pointer
    struct task_struct *next = rb_entry(leftmost, struct task_struct);

    return next;  // Always fairest choice!
}

// After task runs, update vruntime and reinsert
void update_after_run(struct task_struct *task, u64 runtime) {
    task->vruntime += runtime * task->weight_inverse;  // Weight for priority

    rb_erase(&task->node, tree);           // Remove: O(log N)
    rb_insert(&task->node, tree);          // Reinsert: O(log N)

    // Tree automatically sorted by vruntime!
}
```

**Fairness example:**

```
Initial State:
─────────────
Task A: vruntime = 0, weight = 1
Task B: vruntime = 0, weight = 1

Time slice 1: Schedule A (vruntime 0 < B's 0, break tie by PID)
After 10ms: A.vruntime = 10

Time slice 2: Schedule B (vruntime 0 < A's 10)
After 10ms: B.vruntime = 10

Time slice 3: Schedule A (vruntime 10 = B's 10, break tie)
After 10ms: A.vruntime = 20

Result: A and B get exactly 50% CPU each ⚖️
Perfect fairness! ✅
```

**Priority via weights:**

```c
// Nice value → weight mapping
// Nice -20 (highest): weight = 88761
// Nice 0 (default): weight = 1024
// Nice 19 (lowest): weight = 15

// Higher weight → vruntime increases slower → more CPU
vruntime += runtime / weight;

Example:
Task A (nice 0, weight 1024): runs 10ms → vruntime += 10/1024 = 0.0097
Task B (nice 5, weight 335):  runs 10ms → vruntime += 10/335  = 0.0298

Task A's vruntime grows slower → scheduled more often ✅
```

**Why it succeeded:** Deterministic fairness, no complex heuristics, good behavior across workloads.

### 3. 🎯 BF Scheduler (BFS) (2009-present)

**Core idea:** Single global queue, simplest possible design, optimized for desktop responsiveness.

**Architecture:**

```
BFS Single-Queue Structure
──────────────────────────

                 Global Queue (EEVDF-sorted)
        ┌─────────────────────────────────────────┐
        │ [Task A] → [Task B] → [Task C] → [Task D] │
        └─────────────────────────────────────────┘
                     ↑         ↑         ↑
                     │         │         │
              ┌──────┴───┬─────┴───┬─────┴──────┐
              │          │         │            │
           ┌──▼──┐    ┌──▼──┐   ┌──▼──┐      ┌──▼──┐
           │CPU 0│    │CPU 1│   │CPU 2│      │CPU 3│
           └─────┘    └─────┘   └─────┘      └─────┘
```

**EEVDF (Earliest Eligible Virtual Deadline First):**

```c
// Each task has a virtual deadline
struct task_struct {
    u64 vruntime;           // Virtual runtime so far
    u64 time_slice;         // Allocated time slice
    u64 virtual_deadline;   // vruntime + time_slice
};

// Schedule task with earliest virtual deadline
struct task_struct* pick_next_task() {
    struct task_struct *earliest = NULL;
    u64 min_deadline = U64_MAX;

    // Scan queue for earliest deadline (could be O(N), but queue is short)
    for_each_task_in_queue(task) {
        if (task->virtual_deadline < min_deadline) {
            min_deadline = task->virtual_deadline;
            earliest = task;
        }
    }
    return earliest;
}
```

**BFS characteristics:**

```
Advantages:                         Disadvantages:
───────────                         ──────────────
✅ Simple code (~1000 lines)        ❌ Lock contention (single queue)
✅ Easy to understand               ❌ Doesn't scale past ~16 CPUs
✅ Excellent desktop responsiveness ❌ Not in mainline kernel
✅ Predictable behavior             ❌ Worse throughput than CFS
```

**Why it exists:** Some users prefer simplicity and low-latency desktop performance over scalability to 100+ CPUs.

### 7.2. 🔍 Comparing Scheduler Designs

**Feature comparison:**

| Feature | O(1) | CFS | BFS |
|---------|------|-----|-----|
| **Queue Type** | Multi-Queue (MQMS) | Multi-Queue (MQMS) | Single-Queue (SQMS) |
| **Time Complexity** | O(1) | O(log N) | O(N) |
| **Fairness** | Heuristic | Deterministic | Deterministic |
| **Scalability** | Good (64+ CPUs) | Excellent (1000+ CPUs) | Poor (16 CPUs max) |
| **Interactivity** | Priority-based | Weight-based | EEVDF-based |
| **Code Complexity** | High | Medium | Low |
| **Use Case** | Legacy servers | General purpose | Desktop/laptop |

**Workload performance:**

```
Throughput (batch processing):
CFS ⭐⭐⭐⭐⭐  (best multi-queue scalability)
O(1) ⭐⭐⭐⭐   (good, but tuning issues)
BFS ⭐⭐      (single queue limits throughput)

Latency (desktop responsiveness):
BFS ⭐⭐⭐⭐⭐  (optimized for low latency)
CFS ⭐⭐⭐⭐   (good fairness helps latency)
O(1) ⭐⭐⭐    (can have latency spikes)

Server (many CPUs):
CFS ⭐⭐⭐⭐⭐  (scales to 1000+ cores)
O(1) ⭐⭐⭐⭐   (scales to 64+ cores)
BFS ⭐        (single lock breaks down)
```

**Real-world usage:**

```
Production Deployments
──────────────────────

CFS:
- All major Linux distributions (RHEL, Ubuntu, Debian)
- Android (mobile devices)
- Cloud providers (AWS, GCP, Azure Linux VMs)
- Supercomputers

BFS/MuQSS:
- Enthusiast desktop distributions
- Low-latency audio workstations
- Gaming-focused Linux distros
- Systems with < 16 cores

O(1):
- Legacy systems (RHEL 4/5)
- Gradually phased out after 2007
```

> **💡 Insight**
>
> **No one scheduler dominates all metrics**. This is a **Pareto frontier**—you can't improve one dimension without sacrificing another:
> - CFS: Great fairness and scalability, but complex
> - BFS: Simple and responsive, but doesn't scale
> - O(1): Fast operations, but heuristic fairness
>
> This pattern appears everywhere in systems design:
> - **CAP theorem** (consistency vs. availability vs. partition tolerance)
> - **Memory allocators** (speed vs. fragmentation vs. simplicity)
> - **Network protocols** (latency vs. throughput vs. reliability)
>
> Great systems engineering means understanding tradeoffs and choosing the right point for your workload.

---

## 8. 📝 Summary

**Key Takeaways:** 🎯

**1. Multiprocessor Scheduling Challenges** 🖥️

New problems beyond single-CPU scheduling:
```
Hardware Layer:              Software Layer:
───────────────              ───────────────
🔄 Cache coherence     →     🔒 Synchronization
📍 Cache affinity      →     ⚖️ Load balancing
🔧 Bus snooping        →     📈 Scalability
```

**2. Single-Queue Multiprocessor Scheduling (SQMS)** 🎯

```
Advantages:                  Disadvantages:
───────────                  ──────────────
✅ Simple (reuse existing)   ❌ Lock contention
✅ Auto load balancing       ❌ Poor scalability
                             ❌ Cache affinity issues

Best for: < 4 CPUs, simplicity priority
```

**3. Multi-Queue Multiprocessor Scheduling (MQMS)** 🔄

```
Advantages:                  Disadvantages:
───────────                  ──────────────
✅ Excellent scalability     ❌ Load imbalance
✅ Great cache affinity      ❌ More complex
✅ No lock contention        ❌ Needs migration logic

Solution: Work stealing
Best for: Many CPUs (8+), performance priority
```

**4. Work Stealing** 🎣

```
Idle CPU periodically checks other queues:
1. Detect imbalance (threshold-based)
2. Steal jobs from busy CPUs
3. Balance load without constant coordination

Key parameters:
- Frequency (how often to check)
- Threshold (how imbalanced before stealing)
- Amount (how many jobs to steal)
```

**5. Linux Schedulers Comparison** 🐧

| Scheduler | Type | Strength | Weakness |
|-----------|------|----------|----------|
| **O(1)** | MQMS, Priority | O(1) operations | Complex heuristics |
| **CFS** | MQMS, Fair-share | Deterministic fairness | O(log N) operations |
| **BFS** | SQMS, EEVDF | Simple, responsive | Poor scalability |

**Core Design Principles:** 🧠

1. **Tradeoff Triangle** 🔺
   ```
          Simplicity
              △
             / \
            /   \
           /     \
          /       \
         /         \
        /           \
   Scalability ────── Cache Affinity

   Pick 2 of 3:
   - SQMS: Simplicity + Auto-balance (sacrifice scalability)
   - MQMS: Scalability + Affinity (sacrifice simplicity)
   ```

2. **Shared State is the Enemy** 💥
   ```
   Shared Queue (SQMS) → Lock contention → Poor scaling
   Per-CPU Queues (MQMS) → No contention → Great scaling

   General principle: Eliminate sharing for performance
   ```

3. **Eventual Consistency** ⏰
   ```
   Perfect balance all the time: Too expensive
   Detect imbalance periodically: Practical

   Pattern: Gossip protocols, load balancers, work stealing
   ```

**What's Next:** 🚀

Multiprocessor scheduling connects to:
- 🔒 **Concurrency** (locks, atomics, lock-free structures)
- 💾 **NUMA** (non-uniform memory access architectures)
- 🌐 **Distributed scheduling** (cluster schedulers like Kubernetes)
- ⚡ **Real-time scheduling** (deadline guarantees on multicore)

> **💡 Final Insight**
>
> Multiprocessor scheduling reveals the **core tension in parallel systems**: **coordination vs. independence**.
> - Too much coordination (SQMS) → bottleneck
> - Too much independence (MQMS without migration) → imbalance
>
> The art lies in **minimal coordination** to achieve balance. This principle guides:
> - **Distributed databases** (eventual consistency)
> - **Microservices** (loose coupling)
> - **Lock-free algorithms** (compare-and-swap instead of locks)
>
> Master this tension, and you've unlocked the key to building scalable parallel systems! ⚡

---

**Previous:** [Chapter 6: Limited Direct Execution](chapter6-limited-direct-execution.md) | **Next:** [Chapter 8: Scheduling: The Multi-Level Feedback Queue](chapter8-mlfq.md)
