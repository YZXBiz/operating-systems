# 4. Lock-based Concurrent Data Structures

**In plain English:** Taking normal data structures and making them work when multiple threads try to use them at the same time.

**In technical terms:** Adding synchronization mechanisms (locks) to data structures to ensure thread-safe operations while maintaining performance.

**Why it matters:** Every multi-threaded program needs to share data safely. Learning how to protect data structures correctly while keeping them fast is essential for building scalable applications.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Concurrent Counters](#2-concurrent-counters)
   - 2.1. [Simple Thread-Safe Counter](#21-simple-thread-safe-counter)
   - 2.2. [The Scalability Problem](#22-the-scalability-problem)
   - 2.3. [Approximate Counters: The Scalable Solution](#23-approximate-counters-the-scalable-solution)
   - 2.4. [Understanding the Threshold Tradeoff](#24-understanding-the-threshold-tradeoff)
3. [Concurrent Linked Lists](#3-concurrent-linked-lists)
   - 3.1. [Basic Concurrent List](#31-basic-concurrent-list)
   - 3.2. [Improved Design: Minimizing Lock Scope](#32-improved-design-minimizing-lock-scope)
   - 3.3. [Hand-Over-Hand Locking](#33-hand-over-hand-locking)
4. [Concurrent Queues](#4-concurrent-queues)
   - 4.1. [The Michael-Scott Queue](#41-the-michael-scott-queue)
   - 4.2. [Two Locks for Better Concurrency](#42-two-locks-for-better-concurrency)
5. [Concurrent Hash Tables](#5-concurrent-hash-tables)
   - 5.1. [Per-Bucket Locking](#51-per-bucket-locking)
   - 5.2. [Performance Comparison](#52-performance-comparison)
6. [Design Principles](#6-design-principles)
   - 6.1. [Start Simple](#61-start-simple)
   - 6.2. [Lock Scope and Control Flow](#62-lock-scope-and-control-flow)
   - 6.3. [More Concurrency Isn't Always Better](#63-more-concurrency-isnt-always-better)
7. [Summary](#7-summary)

---

## 1. Introduction

Think about a shared counter in a busy application - like tracking the number of website visitors. Multiple threads are all trying to increment it at once. Without protection, you get race conditions. With a single lock protecting everything, you get correctness but terrible performance.

This chapter explores the art of making common data structures work correctly AND efficiently in multi-threaded environments.

> 💡 **Insight**
>
> The core tension in concurrent data structure design: correctness is mandatory, but performance determines whether your solution is practical. The goal is finding the sweet spot between safety and speed.

### 🎯 The Core Challenge

**How do we add locks to data structures in a way that:**
- Guarantees correctness (no race conditions)
- Enables high performance (many threads accessing concurrently)
- Maintains simplicity (fewer bugs, easier maintenance)

### 📋 What We'll Cover

This chapter examines four fundamental concurrent data structures:
1. **Counters** - The simplest structure, showing basic concepts and scalability techniques
2. **Linked Lists** - Demonstrating lock scope and control flow challenges
3. **Queues** - Illustrating how to enable producer-consumer concurrency
4. **Hash Tables** - Showing how multiple locks can scale beautifully

---

## 2. Concurrent Counters

Let's start with the simplest possible data structure: a counter that can be incremented, decremented, and read.

### 2.1. Simple Thread-Safe Counter

First, here's a non-thread-safe counter:

```c
typedef struct __counter_t {
    int value;
} counter_t;

void init(counter_t *c) {
    c->value = 0;
}

void increment(counter_t *c) {
    c->value++;
}

void decrement(counter_t *c) {
    c->value--;
}

int get(counter_t *c) {
    return c->value;
}
```

**Problem:** If two threads call `increment()` simultaneously, they can both read the same value, increment it, and write back - causing one increment to be lost.

#### The Standard Solution: Add a Lock

```c
typedef struct __counter_t {
    int value;
    pthread_mutex_t lock;
} counter_t;

void init(counter_t *c) {
    c->value = 0;
    pthread_mutex_init(&c->lock, NULL);
}

void increment(counter_t *c) {
    pthread_mutex_lock(&c->lock);
    c->value++;
    pthread_mutex_unlock(&c->lock);
}

void decrement(counter_t *c) {
    pthread_mutex_lock(&c->lock);
    c->value--;
    pthread_mutex_unlock(&c->lock);
}

int get(counter_t *c) {
    pthread_mutex_lock(&c->lock);
    int rc = c->value;
    pthread_mutex_unlock(&c->lock);
    return rc;
}
```

This follows the most basic concurrent data structure pattern:
1. Add a single lock to the structure
2. Acquire the lock at the start of each operation
3. Release the lock before returning

**This is correct.** Every operation is atomic. No race conditions possible.

> 💡 **Insight**
>
> This pattern (one lock protecting the entire structure) is similar to monitors in object-oriented programming - locks are acquired and released automatically when entering and exiting methods. It's the safest starting point for any concurrent data structure.

### 2.2. The Scalability Problem

Correctness isn't enough. We need performance too. Let's test this counter with multiple threads:

**Test setup:** Each thread increments the counter 1 million times.

```
Results (4-core Intel i5 @ 2.7 GHz):

Threads    Time (seconds)
1          0.03
2          5.2
3          7.8
4          9.1
```

**What happened?** Adding more threads made everything slower!

#### Understanding the Breakdown

With 1 thread:
- No contention
- No waiting
- Pure computation speed

With 4 threads:
- All threads fight for the same lock
- Only one can make progress at a time
- Others wait idle
- Lock overhead (acquire/release) dominates

**Visualization:**

```
Single Thread (Fast)          Four Threads (Slow)
────────────────             ────────────────────
Thread 1: ████████          Thread 1: ██░░░░░░
                            Thread 2: ░░██░░░░
                            Thread 3: ░░░░██░░
                            Thread 4: ░░░░░░██

█ = Working                  █ = Working
                            ░ = Blocked waiting
```

> 💡 **Insight**
>
> Perfect scaling means N threads complete N times the work in the same time it takes 1 thread to complete 1x the work. With a single lock protecting a hot data structure, we get the opposite - adding threads makes things slower due to contention.

### 2.3. Approximate Counters: The Scalable Solution

**The key insight:** We don't always need the exact value immediately. We can trade accuracy for performance.

#### The Architecture

```
┌─────────────────────────────────────┐
│         Global Counter              │
│            Value: ???               │
│         Lock: glock                 │
└─────────────────────────────────────┘
                 ▲
                 │ Periodic updates
                 │ (when local >= threshold)
                 │
    ┌────────────┴───────────┬────────────┬────────────┐
    │                        │            │            │
┌───▼────┐              ┌────▼───┐   ┌───▼────┐  ┌────▼───┐
│ CPU 0  │              │ CPU 1  │   │ CPU 2  │  │ CPU 3  │
│Local: 4│              │Local: 3│   │Local: 2│  │Local: 5│
│Lock: L0│              │Lock: L1│   │Lock: L2│  │Lock: L3│
└────────┘              └────────┘   └────────┘  └────────┘
    ▲                        ▲            ▲           ▲
    │                        │            │           │
Threads on CPU 0      Threads on CPU 1  etc...
```

**How it works:**

1. **Each CPU core has its own local counter** with its own lock
2. **Threads increment their CPU's local counter** (no cross-CPU contention)
3. **When local counter reaches threshold S**, transfer value to global counter
4. **Reading the global counter** gives an approximate value (may be off by up to `S * num_CPUs`)

#### Implementation

```c
typedef struct __counter_t {
    int global;                    // global count
    pthread_mutex_t glock;         // global lock
    int local[NUMCPUS];           // local count (per cpu)
    pthread_mutex_t llock[NUMCPUS]; // local locks
    int threshold;                 // update frequency
} counter_t;

// Initialize everything
void init(counter_t *c, int threshold) {
    c->threshold = threshold;
    c->global = 0;
    pthread_mutex_init(&c->glock, NULL);

    for (int i = 0; i < NUMCPUS; i++) {
        c->local[i] = 0;
        pthread_mutex_init(&c->llock[i], NULL);
    }
}

// Update: increment local counter, transfer when threshold reached
void update(counter_t *c, int threadID, int amt) {
    int cpu = threadID % NUMCPUS;

    pthread_mutex_lock(&c->llock[cpu]);
    c->local[cpu] += amt;

    if (c->local[cpu] >= c->threshold) {
        // Transfer to global
        pthread_mutex_lock(&c->glock);
        c->global += c->local[cpu];
        pthread_mutex_unlock(&c->glock);
        c->local[cpu] = 0;
    }

    pthread_mutex_unlock(&c->llock[cpu]);
}

// Get: return global value (approximate)
int get(counter_t *c) {
    pthread_mutex_lock(&c->glock);
    int val = c->global;
    pthread_mutex_unlock(&c->glock);
    return val; // May be off by up to threshold * NUMCPUS
}
```

#### Execution Example

Let's trace an execution with threshold S=5 and 4 CPUs:

```
Time   L1   L2   L3   L4   Global   Event
────   ──   ──   ──   ──   ──────   ─────
0      0    0    0    0    0        Initial state
1      1    0    0    1    0        Thread on CPU 0 and 3 increment
2      2    0    1    1    0        Thread on CPU 0 and 2 increment
3      3    0    2    1    0        Thread on CPU 0 and 2 increment
4      4    0    2    2    0        Thread on CPU 0 and 3 increment
5      5 → 0  1    2    3    5      L1 reaches threshold → transfer to global
6      0    1    3    4    5        Normal increments
7      0    2    4    5 → 0  10     L4 reaches threshold → transfer to global

Actual total count: 10
Global shows: 10
All local shows: 0 + 2 + 4 + 0 = 6
True count if we read everything: 10 + 6 = 16
```

**Performance Results:**

With threshold S=1024 on 4 cores:

```
Threads    Precise Counter    Approximate Counter
1          0.03s              0.03s
2          5.2s               0.04s
4          9.1s               0.04s
```

**Nearly perfect scaling!** Four threads do 4x the work in the same time.

### 2.4. Understanding the Threshold Tradeoff

The threshold value S controls the accuracy-performance balance:

```
Threshold S=1 (Low)              Threshold S=1024 (High)
────────────────────             ────────────────────────
✅ Global always accurate        ⚠️  Global may lag by ~4000
❌ Frequent global updates       ✅ Rare global updates
❌ Lock contention              ✅ Minimal contention
❌ Poor performance             ✅ Excellent performance
```

**Performance vs Threshold:**

```
Time (seconds)
15│
  │                               ●───●───● Precise (S=1)
10│                           ●
  │                       ●
 5│                   ●
  │               ●
 0│●───●───●───●                           Approximate (S≥256)
  └───────────────────────────────────
  1   2   4   8  16  32  64  128  256  512  1024
              Threshold Value (S)
```

> 💡 **Insight**
>
> Approximate counters demonstrate a powerful pattern in concurrent programming: sometimes "good enough and fast" beats "perfectly accurate and slow". The key is understanding when accuracy can be relaxed and by how much.

**Use cases:**

- **S=1 (or precise counter):** Financial transactions, critical counts
- **S=64-256:** System metrics, monitoring dashboards
- **S=1024+:** High-frequency statistics, approximate analytics

---

## 3. Concurrent Linked Lists

Linked lists are more complex than counters - they have structure, multiple nodes, and operations that traverse multiple elements.

### 3.1. Basic Concurrent List

Let's start with a simple insert-only list:

```c
// Node structure
typedef struct __node_t {
    int key;
    struct __node_t *next;
} node_t;

// List structure
typedef struct __list_t {
    node_t *head;
    pthread_mutex_t lock;
} list_t;

void List_Init(list_t *L) {
    L->head = NULL;
    pthread_mutex_init(&L->lock, NULL);
}
```

#### First Attempt: Lock Everything

```c
int List_Insert(list_t *L, int key) {
    pthread_mutex_lock(&L->lock);

    node_t *new = malloc(sizeof(node_t));
    if (new == NULL) {
        perror("malloc");
        pthread_mutex_unlock(&L->lock);  // ⚠️ Must unlock on error!
        return -1;
    }

    new->key = key;
    new->next = L->head;
    L->head = new;

    pthread_mutex_unlock(&L->lock);
    return 0;
}

int List_Lookup(list_t *L, int key) {
    pthread_mutex_lock(&L->lock);
    node_t *curr = L->head;

    while (curr) {
        if (curr->key == key) {
            pthread_mutex_unlock(&L->lock);  // ⚠️ Unlock on success
            return 0;
        }
        curr = curr->next;
    }

    pthread_mutex_unlock(&L->lock);  // ⚠️ Unlock on failure
    return -1;
}
```

**This works, but notice a problem:** Multiple places where we unlock. Each is an opportunity for bugs.

> ⚠️ **Warning: Error Paths Are Bug Magnets**
>
> Research on Linux kernel patches found that nearly 40% of bugs occur in rarely-executed error paths. The malloc failure path above is particularly dangerous - easy to forget the unlock.

### 3.2. Improved Design: Minimizing Lock Scope

We can reduce lock scope and simplify control flow:

```c
void List_Insert(list_t *L, int key) {
    // Allocate BEFORE locking (malloc is thread-safe)
    node_t *new = malloc(sizeof(node_t));
    if (new == NULL) {
        perror("malloc");
        return;  // No lock to release!
    }
    new->key = key;

    // Only lock for the critical section
    pthread_mutex_lock(&L->lock);
    new->next = L->head;
    L->head = new;
    pthread_mutex_unlock(&L->lock);
}

int List_Lookup(list_t *L, int key) {
    int rv = -1;
    pthread_mutex_lock(&L->lock);

    node_t *curr = L->head;
    while (curr) {
        if (curr->key == key) {
            rv = 0;
            break;  // Exit loop, not function
        }
        curr = curr->next;
    }

    pthread_mutex_unlock(&L->lock);  // Single unlock point!
    return rv;
}
```

**Improvements:**

1. **Malloc happens outside the lock** - No wasted time holding lock during allocation
2. **Single return path** - Only one place to unlock
3. **Smaller critical section** - Lock held for less time

**Before and After:**

```
Original Insert                   Improved Insert
─────────────────                ─────────────────
Lock                             Malloc (unlocked)
├─ Malloc                        Lock
├─ Setup node                    ├─ Link node
└─ Unlock                        └─ Unlock

Time locked: 100%                Time locked: 20%
```

> 💡 **Insight**
>
> Minimizing critical sections (code between lock/unlock) has two benefits: better performance (less contention) and fewer bugs (fewer places to manage lock state). Always ask: "What truly needs to be protected?"

### 3.3. Hand-Over-Hand Locking

For even more concurrency, we could use **lock coupling** - each node has its own lock:

```
List: [A] → [B] → [C] → [D] → NULL

Thread 1 traversal:
Time 1: Lock A, read A's data
Time 2: Lock B, unlock A, read B's data
Time 3: Lock C, unlock B, read C's data
Time 4: Lock D, unlock C, read D's data
Time 5: Unlock D

Thread 2 can work on other nodes simultaneously!
```

**Theory:** Multiple threads can traverse different parts of the list concurrently.

**Reality:** Usually slower than single lock!

**Why it fails:**

```
Single Lock Approach             Hand-Over-Hand Approach
────────────────────            ───────────────────────
Lock once                       Lock N times (for N nodes)
Traverse all nodes              Unlock N times
Unlock once
                                Each lock/unlock has overhead!

Time: O(N) + 2 lock ops         Time: O(N) + 2N lock ops
```

Unless your list is very long and you have many concurrent operations, the overhead of locking each node exceeds the benefit of increased concurrency.

> 💡 **Insight**
>
> This illustrates a critical principle: theoretical concurrency doesn't guarantee practical speedup. Lock overhead can dwarf the benefits. Measure before optimizing!

---

## 4. Concurrent Queues

Queues are everywhere in multi-threaded systems: work queues, message passing, producer-consumer patterns. Unlike counters and lists, queues have two distinct access points: head (dequeue) and tail (enqueue).

### 4.1. The Michael-Scott Queue

This classic design by Michael and Scott (1998) enables true concurrency between producers and consumers.

#### The Key Insight: Two Locks

```
Queue Structure:
┌──────────────────────────────────────────────┐
│  Head (dequeue)              Tail (enqueue)  │
│       │                            │         │
│       ▼                            ▼         │
│   ┌──────┐    ┌──────┐    ┌──────┐         │
│   │ Dummy│ -> │  42  │ -> │  17  │ -> NULL │
│   └──────┘    └──────┘    └──────┘         │
│       │                            │         │
│   headLock                    tailLock      │
└──────────────────────────────────────────────┘

Producers only need tailLock
Consumers only need headLock
→ They can work simultaneously!
```

### 4.2. Two Locks for Better Concurrency

```c
typedef struct __node_t {
    int value;
    struct __node_t *next;
} node_t;

typedef struct __queue_t {
    node_t *head;
    node_t *tail;
    pthread_mutex_t headLock;
    pthread_mutex_t tailLock;
} queue_t;

void Queue_Init(queue_t *q) {
    // Dummy node separates head and tail operations
    node_t *tmp = malloc(sizeof(node_t));
    tmp->next = NULL;
    q->head = q->tail = tmp;

    pthread_mutex_init(&q->headLock, NULL);
    pthread_mutex_init(&q->tailLock, NULL);
}
```

#### Enqueue: Only Touch the Tail

```c
void Queue_Enqueue(queue_t *q, int value) {
    // Allocate outside lock
    node_t *tmp = malloc(sizeof(node_t));
    assert(tmp != NULL);
    tmp->value = value;
    tmp->next = NULL;

    // Only lock tail
    pthread_mutex_lock(&q->tailLock);
    q->tail->next = tmp;
    q->tail = tmp;
    pthread_mutex_unlock(&q->tailLock);
}
```

#### Dequeue: Only Touch the Head

```c
int Queue_Dequeue(queue_t *q, int *value) {
    pthread_mutex_lock(&q->headLock);

    node_t *tmp = q->head;
    node_t *newHead = tmp->next;

    if (newHead == NULL) {
        pthread_mutex_unlock(&q->headLock);
        return -1; // Queue empty
    }

    *value = newHead->value;
    q->head = newHead;
    pthread_mutex_unlock(&q->headLock);

    free(tmp);
    return 0;
}
```

#### Why the Dummy Node?

The dummy node is the trick that makes two locks possible:

```
Without Dummy (Single Lock Needed):
──────────────────────────────────
Empty: head = tail = NULL
├─ Enqueue needs to update head AND tail
├─ Dequeue needs to check tail
└─ Must share a lock

With Dummy (Two Locks Possible):
────────────────────────────────
Empty: head = tail = dummy
├─ Enqueue only updates tail
├─ Dequeue only updates head
└─ They never touch the same pointers!
```

**Visualization of Concurrent Operations:**

```
Time   Producer                   Consumer                Queue State
─────  ─────────────              ─────────────          ────────────
T0     Enqueue(42) starts         Dequeue() starts       [Dummy] -> NULL
       Lock tailLock              Lock headLock
                                                         (No contention!)

T1     Adding node               Reading head's next     [Dummy] -> NULL
       [Dummy] -> [42]                                   (Producer working on tail)

T2     Update tail               Queue empty,            [Dummy] -> [42]
       Unlock tailLock           return -1               head=tail=Dummy
                                 Unlock headLock

T3     Done                      Done                    [Dummy] -> [42]
                                                         head=Dummy, tail=42

Both operations happened simultaneously!
```

> 💡 **Insight**
>
> The two-lock queue demonstrates that understanding data structure invariants enables better concurrency. By ensuring head and tail operations are truly independent, we can use separate locks without coordination.

---

## 5. Concurrent Hash Tables

Hash tables are one of the most important data structures in systems programming. Making them concurrent-friendly is crucial for performance.

### 5.1. Per-Bucket Locking

The brilliant insight: hash tables already partition data into buckets. Give each bucket its own lock!

```c
#define BUCKETS (101)

typedef struct __hash_t {
    list_t lists[BUCKETS];  // Each list has its own lock
} hash_t;

void Hash_Init(hash_t *H) {
    for (int i = 0; i < BUCKETS; i++) {
        List_Init(&H->lists[i]);
    }
}

int Hash_Insert(hash_t *H, int key) {
    int bucket = key % BUCKETS;
    return List_Insert(&H->lists[bucket], key);
}

int Hash_Lookup(hash_t *H, int key) {
    int bucket = key % BUCKETS;
    return List_Lookup(&H->lists[bucket], key);
}
```

**Architecture:**

```
Hash Table (101 buckets, each with its own lock)
┌─────────────────────────────────────────────────┐
│ Bucket 0:  [3] -> [104] -> NULL     Lock 0      │
│ Bucket 1:  [1] -> [102] -> [203]    Lock 1      │
│ Bucket 2:  [2] -> NULL              Lock 2      │
│ ...                                              │
│ Bucket 100: [100] -> NULL           Lock 100    │
└─────────────────────────────────────────────────┘

Thread A: Insert(15)  → Hash to bucket 15 → Lock 15 only
Thread B: Insert(42)  → Hash to bucket 42 → Lock 42 only
Thread C: Lookup(7)   → Hash to bucket 7  → Lock 7 only
Thread D: Insert(93)  → Hash to bucket 93 → Lock 93 only

All four threads work simultaneously with zero contention!
```

### 5.2. Performance Comparison

Let's compare hash table vs simple linked list with 4 threads:

```
Inserts (Thousands)
50│                     ╱ Simple List (1 lock)
  │                   ╱
40│                 ╱
  │               ╱
30│             ╱
  │           ╱
20│         ╱
  │       ╱
10│     ╱
  │   ╱
 0│─────────── Hash Table (101 locks)
  └──────────────────────────────
  0   5   10   15   20   25   30
              Time (seconds)

Hash Table: 50K inserts in ~1 second (scales perfectly)
Simple List: 50K inserts in ~30 seconds (no scaling)
```

**Why it works so well:**

1. **Natural partitioning:** Hash function spreads keys across buckets
2. **Independent operations:** Operations on different buckets don't conflict
3. **Low overhead:** Each thread only locks one bucket briefly
4. **Balanced load:** Good hash functions ensure even distribution

> 💡 **Insight**
>
> Hash tables scale beautifully because they combine data structure design (partitioning) with locking strategy (per-partition locks). When your data naturally partitions, use that structure for concurrency too.

**Real-world impact:** This pattern is used everywhere:
- Database indexes (per-page locks)
- Web servers (per-connection state)
- Operating system caches (per-hash-bucket locks)
- Memory allocators (per-CPU heaps)

---

## 6. Design Principles

Let's consolidate the lessons from building concurrent data structures.

### 6.1. Start Simple

> 🎯 **Knuth's Law: "Premature optimization is the root of all evil"**

**The right approach:**

```
Step 1: Add a single big lock
        ├─ Verify correctness
        ├─ Test in production
        └─ Measure performance

Step 2: Is it fast enough?
        ├─ YES → Done! Ship it.
        └─ NO → Continue to Step 3

Step 3: Profile and identify bottlenecks
        ├─ Where is contention?
        ├─ What operations are slow?
        └─ Design targeted optimization

Step 4: Implement refined locking
        ├─ Verify correctness again
        ├─ Measure performance improvement
        └─ Compare complexity cost
```

**Historical examples:**

- **Sun OS:** Started with Big Kernel Lock (BKL) → Later split into fine-grained locks
- **Linux:** Used BKL for years → Eventually replaced with multiple locks
- **Solaris:** Built concurrent from day one → More complex but faster on multi-CPU

> 💡 **Insight**
>
> Both approaches work! Starting simple lets you ship faster and add complexity only when measurements prove it's needed. Starting complex works if you have the resources and know multi-CPU is your target.

### 6.2. Lock Scope and Control Flow

**Anti-pattern: Locks and multiple return paths**

```c
// ❌ BAD: Multiple unlock points
int lookup(list_t *L, int key) {
    pthread_mutex_lock(&L->lock);

    if (special_case) {
        pthread_mutex_unlock(&L->lock);  // Unlock here
        return -1;
    }

    node_t *n = find(L, key);
    if (n == NULL) {
        pthread_mutex_unlock(&L->lock);  // And here
        return -1;
    }

    if (n->valid) {
        pthread_mutex_unlock(&L->lock);  // And here
        return n->value;
    }

    pthread_mutex_unlock(&L->lock);  // And here
    return -1;
}
// Easy to add a return without unlocking!
```

**Pattern: Single unlock point**

```c
// ✅ GOOD: Single unlock point
int lookup(list_t *L, int key) {
    int rv = -1;
    pthread_mutex_lock(&L->lock);

    if (!special_case) {
        node_t *n = find(L, key);
        if (n != NULL && n->valid) {
            rv = n->value;
        }
    }

    pthread_mutex_unlock(&L->lock);  // Only here!
    return rv;
}
```

**Guidelines:**

1. **Lock late, unlock early:** Minimize critical section size
2. **Single entry/exit:** One lock point, one unlock point when possible
3. **No locks held during I/O or allocation:** Keep them for the truly critical parts
4. **Test error paths:** They're where bugs hide

### 6.3. More Concurrency Isn't Always Better

We saw this with hand-over-hand locking in lists. Let's understand when more locks help and when they hurt.

**When more locks help:**

```
✅ Data naturally partitions (hash table buckets)
✅ Operations are long (holding lock for milliseconds)
✅ Operations are independent (readers and writers)
✅ High contention on single lock measured in practice
```

**When more locks hurt:**

```
❌ Lock overhead exceeds contention cost
❌ Operations are fast (microseconds)
❌ Complex lock ordering required (deadlock risk)
❌ Low contention in practice
```

**Decision tree:**

```
Do you have a performance problem?
├─ NO → Use single lock, you're done
└─ YES → Profile to find bottleneck
          │
          Is it lock contention?
          ├─ NO → Optimize something else
          └─ YES → Can you partition the data?
                    ├─ YES → Add per-partition locks (hash table style)
                    └─ NO → Consider different structure or algorithm
```

> ⚡ **Key Performance Principle**
>
> The best optimization is the one you don't make. Complexity is a tax you pay forever. Only add it when measurements prove the benefit exceeds the cost.

---

## 7. Summary

We've explored how to make fundamental data structures thread-safe while maintaining performance:

### 🎯 Key Structures

1. **Counters**
   - Simple: One lock, correct but slow
   - Scalable: Per-CPU counters with periodic aggregation
   - Tradeoff: Accuracy vs performance via threshold

2. **Linked Lists**
   - Standard: Single lock protecting entire list
   - Improved: Minimize critical section, single unlock point
   - Advanced: Hand-over-hand locking (usually not worth it)

3. **Queues**
   - Michael-Scott: Two locks (head and tail)
   - Key trick: Dummy node enables lock separation
   - Benefit: Producers and consumers don't block each other

4. **Hash Tables**
   - Pattern: Per-bucket locking
   - Performance: Nearly perfect scaling
   - Why: Natural data partitioning matches lock partitioning

### 🧠 Design Principles

**Start simple:**
- Begin with single lock
- Measure before optimizing
- Add complexity only when needed

**Minimize critical sections:**
- Lock as late as possible
- Unlock as early as possible
- Keep I/O and allocation outside locks

**Control flow matters:**
- Single unlock point prevents bugs
- Error paths are dangerous
- Simplicity reduces mistakes

**More concurrency ≠ better performance:**
- Lock overhead can exceed benefits
- Measure actual contention
- Consider data structure characteristics

### 🚀 The Big Picture

> 💡 **Insight**
>
> Concurrent data structure design is about finding the balance between three forces: correctness (mandatory), simplicity (reduces bugs), and performance (must be measured, not assumed). Master the simple patterns first, then optimize only when measurements demand it.

**What's next:**

This chapter focused on lock-based structures. But locks have limitations:
- Threads block when waiting
- Priority inversion can occur
- Deadlocks are possible with multiple locks

The next chapter introduces **condition variables** - a mechanism that lets threads efficiently wait for complex conditions, enabling sophisticated patterns like bounded queues and producer-consumer relationships.

### 📚 Further Study

- **Moir and Shavit Survey** [MS04]: Comprehensive overview of concurrent data structures
- **Lock-free structures:** Non-blocking algorithms using atomic operations
- **B-trees and databases:** Complex concurrent structures in database systems
- **Linux and Solaris kernels:** Real-world case studies of scaling from single lock to fine-grained concurrency

---

**Previous:** [Chapter 3: Locks](chapter3-locks.md) | **Next:** [Chapter 5: Condition Variables](chapter5-condition-variables.md)
