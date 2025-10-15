# Chapter 7: Common Concurrency Problems

**In plain English:** When multiple threads work together, things can go wrong in predictable patterns - like forgetting to lock doors (atomicity bugs), arriving in the wrong order (order violations), or creating gridlock situations (deadlock).

**In technical terms:** Concurrency bugs typically fall into two categories: non-deadlock bugs (atomicity and order violations) and deadlock bugs (circular waiting patterns).

**Why it matters:** Understanding these common bug patterns helps you write more robust concurrent code and debug issues faster when they arise in production systems.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Types of Concurrency Bugs](#2-types-of-concurrency-bugs)
3. [Non-Deadlock Bugs](#3-non-deadlock-bugs)
   - 3.1. [Atomicity Violations](#31-atomicity-violations)
   - 3.2. [Order Violations](#32-order-violations)
   - 3.3. [Summary of Non-Deadlock Bugs](#33-summary-of-non-deadlock-bugs)
4. [Deadlock Bugs](#4-deadlock-bugs)
   - 4.1. [Understanding Deadlock](#41-understanding-deadlock)
   - 4.2. [Why Deadlocks Occur](#42-why-deadlocks-occur)
   - 4.3. [Four Conditions for Deadlock](#43-four-conditions-for-deadlock)
   - 4.4. [Deadlock Prevention](#44-deadlock-prevention)
   - 4.5. [Deadlock Avoidance via Scheduling](#45-deadlock-avoidance-via-scheduling)
   - 4.6. [Detect and Recover](#46-detect-and-recover)
5. [Summary](#5-summary)

---

## 1. Introduction

Researchers have spent decades studying concurrency bugs in real-world software. Early work focused primarily on deadlock, while more recent research examines other common patterns. This chapter explores actual concurrency bugs found in production code to help you understand what problems to watch for.

> **💡 Insight**
>
> Concurrency bugs aren't random - they follow patterns. Learning these patterns is like learning to recognize common chess mistakes: once you know them, you can avoid them.

### 1.1. The Research Foundation

A landmark study by Lu et al. analyzed concurrency bugs in four major open-source applications:

- **MySQL** - Popular database management system
- **Apache** - Well-known web server
- **Mozilla** - Famous web browser
- **OpenOffice** - Free office suite

The researchers examined bugs that had been found and fixed, turning developer work into quantitative analysis.

### 1.2. Bug Distribution

| Application | Non-Deadlock Bugs | Deadlock Bugs | Total |
|------------|------------------|---------------|-------|
| MySQL | 14 | 9 | 23 |
| Apache | 13 | 4 | 17 |
| Mozilla | 41 | 16 | 57 |
| OpenOffice | 6 | 2 | 8 |
| **Total** | **74** | **31** | **105** |

**Key observation:** 70% of concurrency bugs (74 out of 105) were non-deadlock bugs. This tells us where to focus our attention.

---

## 2. Types of Concurrency Bugs

**In plain English:** Think of concurrency bugs like traffic accidents - some happen when drivers don't follow the rules correctly (atomicity/order violations), others happen when everyone gets stuck at an intersection with no way out (deadlock).

Concurrency bugs broadly fall into two categories:

1. **🐛 Non-Deadlock Bugs** (70% of bugs)
   - Atomicity violations: Operations that should happen together get interrupted
   - Order violations: Operations happen in the wrong sequence

2. **🔒 Deadlock Bugs** (30% of bugs)
   - Circular dependencies where threads wait for each other indefinitely

> **📝 Note**
>
> The distribution of bug types varies by application. Mozilla had the most bugs (57 total), while OpenOffice had the fewest (8 total). This reflects both codebase size and complexity.

---

## 3. Non-Deadlock Bugs

Non-deadlock bugs make up the majority of concurrency issues. They're often easier to fix than deadlocks, but they're also easier to introduce accidentally. Let's examine the two main types.

### 3.1. Atomicity Violations

**In plain English:** Imagine checking your bank balance, seeing $100, then withdrawing $50. But between the check and withdrawal, someone else already withdrew $60. Your account is now overdrawn because the "check-then-withdraw" operation wasn't atomic.

**In technical terms:** An atomicity violation occurs when multiple memory accesses should execute atomically (as one uninterruptible unit) but don't.

#### 3.1.1. Real Example from MySQL

Let's examine an actual bug found in MySQL:

```c
Thread 1::
if (thd->proc_info) {
    ...
    fputs(thd->proc_info, ...);
    ...
}

Thread 2::
thd->proc_info = NULL;
```

**What's the bug?** 🐛

Let's trace the execution:

1. Thread 1 checks: `thd->proc_info` is not NULL ✅
2. **Context switch to Thread 2**
3. Thread 2 sets: `thd->proc_info = NULL`
4. **Context switch back to Thread 1**
5. Thread 1 calls: `fputs(thd->proc_info, ...)` 💥 **CRASH!**

Thread 1 dereferences a NULL pointer because Thread 2 changed the value between the check and use.

#### 3.1.2. Visual Flow of the Bug

```
Time  Thread 1                  Thread 2
────  ─────────────────         ──────────────────
t1    if (thd->proc_info)
      └─> TRUE ✓
t2                               thd->proc_info = NULL
t3    fputs(thd->proc_info)
      └─> NULL pointer! 💥
```

#### 3.1.3. Formal Definition

> **The desired serializability among multiple memory accesses is violated (i.e., a code region is intended to be atomic, but the atomicity is not enforced during execution).**

In simpler terms: The code assumes the check and use happen together, but that assumption isn't enforced.

#### 3.1.4. The Fix: Add Locks

The solution is to protect the shared variable with a lock:

```c
pthread_mutex_t proc_info_lock = PTHREAD_MUTEX_INITIALIZER;

Thread 1::
pthread_mutex_lock(&proc_info_lock);
if (thd->proc_info) {
    ...
    fputs(thd->proc_info, ...);
    ...
}
pthread_mutex_unlock(&proc_info_lock);

Thread 2::
pthread_mutex_lock(&proc_info_lock);
thd->proc_info = NULL;
pthread_mutex_unlock(&proc_info_lock);
```

**Why this works:**
- Both threads must acquire the lock before accessing `proc_info`
- Only one thread can hold the lock at a time
- The check-and-use in Thread 1 now happens atomically

> **⚠️ Warning**
>
> Any code that accesses `thd->proc_info` must also acquire this lock. Missing even one access point can reintroduce the bug.

### 3.2. Order Violations

**In plain English:** Imagine a restaurant where the waiter serves food before the chef finishes cooking. The order matters! In concurrent programs, sometimes Thread B assumes Thread A has already completed some initialization, but Thread B runs first.

**In technical terms:** An order violation occurs when the desired execution order between two memory accesses is not enforced, causing them to execute in the wrong sequence.

#### 3.2.1. Real Example from Mozilla

Here's an actual bug found in Mozilla's codebase:

```c
Thread 1::
void init() {
    ...
    mThread = PR_CreateThread(mMain, ...);
    ...
}

Thread 2::
void mMain(...) {
    ...
    mState = mThread->State;
    ...
}
```

**What's the bug?** 🐛

Thread 2's `mMain()` function assumes `mThread` has already been initialized by Thread 1. But if Thread 2 runs immediately after being created, `mThread` might still be NULL.

#### 3.2.2. Visual Flow of the Bug

```
Expected Order          Actual Order (Bug)
──────────────          ──────────────────
Thread 1: init()        Thread 2: mMain()
  mThread = ...         mState = mThread->State 💥
                        └─> mThread is NULL!
Thread 2: mMain()
  mState = ...          Thread 1: init()
                          mThread = ...
```

#### 3.2.3. Formal Definition

> **The desired order between two groups of memory accesses is flipped (i.e., A should always execute before B, but the order is not enforced during execution).**

#### 3.2.4. The Fix: Use Condition Variables

Condition variables are perfect for enforcing ordering:

```c
pthread_mutex_t mtLock = PTHREAD_MUTEX_INITIALIZER;
pthread_cond_t mtCond = PTHREAD_COND_INITIALIZER;
int mtInit = 0;

Thread 1::
void init() {
    ...
    mThread = PR_CreateThread(mMain, ...);

    // Signal that the thread has been created
    pthread_mutex_lock(&mtLock);
    mtInit = 1;
    pthread_cond_signal(&mtCond);
    pthread_mutex_unlock(&mtLock);
    ...
}

Thread 2::
void mMain(...) {
    ...
    // Wait for the thread to be initialized
    pthread_mutex_lock(&mtLock);
    while (mtInit == 0)
        pthread_cond_wait(&mtCond, &mtLock);
    pthread_mutex_unlock(&mtLock);

    mState = mThread->State;
    ...
}
```

**How this works:**

1. **Thread 2 starts first (worst case):**
   - Checks `mtInit` → it's 0
   - Calls `pthread_cond_wait()` → goes to sleep
   - Releases `mtLock` while sleeping

2. **Thread 1 initializes:**
   - Sets `mThread = ...`
   - Sets `mtInit = 1`
   - Calls `pthread_cond_signal()` → wakes up Thread 2

3. **Thread 2 wakes up:**
   - Re-checks `mtInit` → it's 1 now
   - Continues safely with initialized `mThread`

4. **Thread 2 starts second (best case):**
   - Checks `mtInit` → it's already 1
   - Skips the wait
   - Continues immediately

> **💡 Insight**
>
> The while loop checking `mtInit` is crucial. Always use while loops with condition variables, not if statements. This protects against spurious wakeups where the thread wakes up even though no signal was sent.

#### 3.2.5. Progressive Complexity

Let's see how this pattern scales:

**Simple:** Two threads, one dependency
```
Thread A initializes → Thread B uses
```

**Intermediate:** Multiple threads, chain of dependencies
```
Thread A initializes X → Thread B uses X, initializes Y → Thread C uses Y
```

**Advanced:** Complex initialization graphs
```
Multiple threads with multiple dependencies, each tracked by its own condition variable and state flag
```

### 3.3. Summary of Non-Deadlock Bugs

**Key statistics from the research:**
- **97%** of non-deadlock bugs are either atomicity or order violations
- **Atomicity violations** are more common than order violations
- Both types are usually fixable with careful locking or synchronization

**Pattern recognition:**

| Bug Type | Recognition Pattern | Fix |
|----------|-------------------|-----|
| **Atomicity Violation** | Check-then-use, read-modify-write sequences | Add locks around the entire operation |
| **Order Violation** | One thread assumes another has run first | Add condition variables to enforce ordering |

> **🎓 Learning Point**
>
> The best defense against these bugs is awareness. During code review, ask:
> - "Can these operations be interrupted mid-sequence?" (atomicity)
> - "Are we assuming something is already initialized?" (order)

**⚠️ Important:** Not all bugs are this simple to fix. Some require:
- Deep understanding of program logic
- Larger code restructuring
- Data structure reorganization

Read the original Lu et al. paper for more complex examples and detailed analysis.

---

## 4. Deadlock Bugs

While non-deadlock bugs are more common, deadlock bugs are often more dramatic and harder to debug. When a deadlock occurs, threads freeze completely, making the entire program unresponsive.

### 4.1. Understanding Deadlock

**In plain English:** Deadlock is like two cars meeting on a narrow one-lane bridge from opposite directions. Each car is waiting for the other to back up, but neither can move forward or backward. Both are stuck forever.

**In technical terms:** Deadlock occurs when threads are waiting for each other in a circular pattern, where each thread holds resources that the next thread needs.

#### 4.1.1. Classic Deadlock Example

```c
Thread 1:                  Thread 2:
pthread_mutex_lock(L1);    pthread_mutex_lock(L2);
pthread_mutex_lock(L2);    pthread_mutex_lock(L1);
```

**How deadlock happens:**

```
Time  Thread 1              Thread 2              Result
────  ─────────────────     ─────────────────     ──────
t1    Lock L1 ✓             -                     Thread 1 holds L1
t2    -                     Lock L2 ✓             Thread 2 holds L2
t3    Try lock L2...        -                     Thread 1 waits (L2 held by T2)
      └─> BLOCKED
t4    -                     Try lock L1...        Thread 2 waits (L1 held by T1)
                            └─> BLOCKED
t5    💀 DEADLOCK - Both threads wait forever 💀
```

#### 4.1.2. Deadlock Dependency Graph

```
      Holds
   Thread 1 ───────> Lock L1
      ↑                 │
      │                 │ Wanted by
      │                 ↓
   Wanted by        Thread 2
      │                 │
      │                 │ Holds
      └─────────────> Lock L2

   🔄 Cycle detected = DEADLOCK
```

> **💡 Insight**
>
> The presence of a cycle in the resource dependency graph is the hallmark of deadlock. No cycle = no deadlock.

### 4.2. Why Deadlocks Occur

If deadlocks are so obviously bad, why do they happen in real systems?

#### 4.2.1. Complex Dependencies in Large Systems

**In plain English:** Imagine a city where the water department needs permission from the power department to fix pipes, but the power department needs permission from the water department to fix power lines. These circular dependencies are hard to spot in large systems.

**Real example:** In an operating system:
1. Virtual memory system needs to page in data from disk
2. To read from disk, it calls the file system
3. File system needs memory to buffer the data
4. To get memory, it calls the virtual memory system
5. 🔄 **Circular dependency!**

#### 4.2.2. Encapsulation Hides Lock Ordering

Encapsulation is great for software design but terrible for lock visibility.

**Example: Java's Vector class**

```java
Vector v1, v2;
v1.AddAll(v2);  // Internally locks v1 then v2
```

Meanwhile, another thread does:

```java
v2.AddAll(v1);  // Internally locks v2 then v1
```

**The problem:** The locking order is hidden inside the `AddAll()` method. Callers can't see that they're creating potential deadlock by calling the methods in different orders.

```
Thread 1: v1.AddAll(v2)          Thread 2: v2.AddAll(v1)
          └─> locks v1, v2                  └─> locks v2, v1

If they run simultaneously:
Thread 1 holds v1, wants v2
Thread 2 holds v2, wants v1
💀 DEADLOCK
```

> **⚠️ Warning**
>
> Encapsulation and concurrency are fundamentally at odds. Hidden locking implementations can create deadlocks that are invisible to the calling code.

### 4.3. Four Conditions for Deadlock

**In plain English:** Deadlock requires four specific conditions to occur simultaneously. If any one condition is prevented, deadlock cannot happen. Think of them as four ingredients needed for a recipe - remove any ingredient and the recipe fails.

All four conditions must hold for deadlock:

1. **🔒 Mutual Exclusion**
   - Threads claim exclusive control of resources
   - Example: Only one thread can hold a lock at a time

2. **✋ Hold-and-Wait**
   - Threads hold resources while waiting for others
   - Example: Thread holds Lock 1 while waiting for Lock 2

3. **🚫 No Preemption**
   - Resources cannot be forcibly taken away
   - Example: You can't steal a lock from a thread that holds it

4. **🔄 Circular Wait**
   - A circular chain exists where each thread waits for the next
   - Example: T1 waits for T2, T2 waits for T3, T3 waits for T1

```
Deadlock Conditions Diagram

    Mutual           Hold-and-        No              Circular
    Exclusion        Wait             Preemption      Wait
    ─────────        ────────         ──────────      ────────
    T1: Lock L1      T1: Holds L1     Can't take      T1→L2→T2
        ⚠️ Only 1    T1: Wants L2     L1 from T1      T2→L1→T1
                     T2: Holds L2     Can't take      🔄 CYCLE
                     T2: Wants L1     L2 from T2
```

> **💡 Insight**
>
> These four conditions give us four different strategies to prevent deadlock: break any one condition, and deadlock becomes impossible.

### 4.4. Deadlock Prevention

Prevention means structuring your code so that deadlock cannot occur. Each prevention technique targets one of the four conditions.

#### 4.4.1. Prevent Circular Wait: Lock Ordering

**Strategy:** Acquire locks in a consistent global order.

**In plain English:** Everyone must always acquire locks in the same order - like always entering a building through the front door, never the back. This prevents circular waiting patterns.

**Simple example:**

```c
// BAD: Inconsistent order causes deadlock
Thread 1:           Thread 2:
lock(L1)            lock(L2)
lock(L2)            lock(L1)

// GOOD: Consistent order prevents deadlock
Thread 1:           Thread 2:
lock(L1)            lock(L1)
lock(L2)            lock(L2)
```

**Why it works:**
- Thread 1 acquires L1 first
- Thread 2 tries to acquire L1 but blocks (L1 held by Thread 1)
- Thread 1 acquires L2 (no competition)
- Thread 1 releases both locks
- Thread 2 now acquires L1, then L2
- No circular wait possible ✅

#### 4.4.2. Real-World Example: Linux Memory Mapping

Linux kernel uses partial lock ordering in memory mapping code. From the source comments:

```
Lock ordering rules:
1. i_mutex before i_mmap_mutex
2. i_mmap_mutex before private_lock
3. private_lock before swap_lock
4. swap_lock before mapping->tree_lock
```

This creates a hierarchy:

```
Lock Hierarchy
──────────────
i_mutex
  └─> i_mmap_mutex
        └─> private_lock
              └─> swap_lock
                    └─> tree_lock

Rule: Always acquire locks top-to-bottom
Never go bottom-to-top
```

#### 4.4.3. Advanced Technique: Lock Address Ordering

**Problem:** What if a function receives two locks as parameters?

```c
void do_something(mutex_t *m1, mutex_t *m2) {
    pthread_mutex_lock(m1);
    pthread_mutex_lock(m2);
    // ... critical section ...
    pthread_mutex_unlock(m2);
    pthread_mutex_unlock(m1);
}

// Calling code
Thread 1: do_something(L1, L2);  // Locks in order: L1, L2
Thread 2: do_something(L2, L1);  // Locks in order: L2, L1
// 💀 DEADLOCK possible!
```

**Solution:** Use memory addresses to determine lock order:

```c
void do_something(mutex_t *m1, mutex_t *m2) {
    if (m1 > m2) {  // Compare memory addresses
        pthread_mutex_lock(m1);
        pthread_mutex_lock(m2);
    } else {
        pthread_mutex_lock(m2);
        pthread_mutex_lock(m1);
    }

    // ... critical section ...

    // Unlock in reverse order
    if (m1 > m2) {
        pthread_mutex_unlock(m2);
        pthread_mutex_unlock(m1);
    } else {
        pthread_mutex_unlock(m1);
        pthread_mutex_unlock(m2);
    }
}
```

**Why this works:**
- Memory addresses provide a consistent global ordering
- Both threads will acquire locks in the same order regardless of parameter order
- Example: If L1 is at address 0x1000 and L2 at 0x2000:
  - `do_something(L1, L2)` → acquires L1 then L2
  - `do_something(L2, L1)` → still acquires L1 then L2 (lower address first)

> **📝 Note**
>
> This assumes m1 != m2. If they could be the same lock, add a check: `if (m1 == m2) { lock once; return; }`

#### 4.4.4. Prevent Hold-and-Wait: Atomic Lock Acquisition

**Strategy:** Acquire all locks at once, atomically.

```c
pthread_mutex_t prevention = PTHREAD_MUTEX_INITIALIZER;

Thread 1:
pthread_mutex_lock(&prevention);  // Meta-lock: lock to acquire locks
pthread_mutex_lock(L1);
pthread_mutex_lock(L2);
pthread_mutex_unlock(&prevention);

// ... use L1 and L2 ...

pthread_mutex_unlock(L2);
pthread_mutex_unlock(L1);
```

**How it prevents hold-and-wait:**
- All lock acquisition happens while holding the `prevention` lock
- No thread can be interrupted mid-acquisition
- Either a thread gets all locks or none

**Visualization:**

```
Thread 1                Thread 2
────────                ────────
Lock prevention ✓       Try lock prevention...
Lock L1 ✓               └─> BLOCKED (waits)
Lock L2 ✓
Unlock prevention       Lock prevention ✓
                        Lock L1 ✓
Use L1, L2              Lock L2 ✓
                        Unlock prevention
Unlock L2, L1
                        Use L1, L2
                        Unlock L2, L1
```

**Problems with this approach:**

1. **⚠️ Encapsulation breaks:** You must know all locks needed upfront
2. **⚡ Reduced concurrency:** All locks acquired early, even if not needed yet
3. **🐌 Performance impact:** Serial lock acquisition can slow things down

> **💡 Insight**
>
> This technique trades deadlock safety for concurrency. It's useful when you have a small, well-defined set of locks and can't risk deadlock.

#### 4.4.5. Prevent No Preemption: Trylock

**Strategy:** Use trylock to back out gracefully when a lock isn't available.

**In plain English:** Instead of waiting indefinitely for a lock, try to get it. If it's not available, release your other locks and try again from the beginning.

```c
top:
    pthread_mutex_lock(L1);
    if (pthread_mutex_trylock(L2) != 0) {
        // L2 not available - back out
        pthread_mutex_unlock(L1);
        goto top;  // Try again
    }

    // Got both locks!
    // ... critical section ...

    pthread_mutex_unlock(L2);
    pthread_mutex_unlock(L1);
```

**How it works:**

```
Successful Scenario:
─────────────────────
Thread 1:
  Lock L1 ✓
  Trylock L2 ✓
  Use both locks
  Done

Failed Scenario (with recovery):
─────────────────────────────────
Thread 1:                    Thread 2:
  Lock L1 ✓                    Lock L2 ✓
  Trylock L2...
  └─> FAILS (T2 holds it)
  Unlock L1                    Trylock L1 ✓
                               Use both locks
  ← Try again ←              Done
  Lock L1 ✓
  Trylock L2 ✓
  Use both locks
  Done
```

**Ordering doesn't matter:**

```c
// Thread 1
top:
    pthread_mutex_lock(L1);
    if (pthread_mutex_trylock(L2) != 0) {
        pthread_mutex_unlock(L1);
        goto top;
    }

// Thread 2 - different order, still safe!
top:
    pthread_mutex_lock(L2);
    if (pthread_mutex_trylock(L1) != 0) {
        pthread_mutex_unlock(L2);
        goto top;
    }
```

**New problem: Livelock** 🔄

**In plain English:** Imagine two people approaching each other in a narrow hallway. They both step to the left, realize they're still blocking, both step right, still blocking, both step left again... They're moving but making no progress.

```
Livelock scenario:
─────────────────
Time  Thread 1           Thread 2
t1    Lock L1            Lock L2
t2    Trylock L2 fails   Trylock L1 fails
t3    Unlock L1          Unlock L2
t4    Lock L1            Lock L2
t5    Trylock L2 fails   Trylock L1 fails
t6    Unlock L1          Unlock L2
...   (repeats forever)  (repeats forever)
```

**Solution to livelock:** Add random delay

```c
#include <stdlib.h>
#include <unistd.h>

top:
    pthread_mutex_lock(L1);
    if (pthread_mutex_trylock(L2) != 0) {
        pthread_mutex_unlock(L1);
        usleep(rand() % 100);  // Random 0-99 microsecond delay
        goto top;
    }
```

The random delay breaks synchronization between competing threads.

> **⚠️ Warning**
>
> Trylock approaches have complexity costs:
> - Must carefully release all acquired resources on failure
> - Works poorly with encapsulation
> - Can introduce livelock if not implemented carefully

#### 4.4.6. Prevent Mutual Exclusion: Lock-Free Data Structures

**Strategy:** Don't use locks at all! Use atomic hardware instructions instead.

**In plain English:** Instead of putting a lock on a door, use a revolving door that only lets one person through at a time automatically. The hardware enforces atomicity, not software locks.

**Hardware primitive: Compare-And-Swap (CAS)**

```c
int CompareAndSwap(int *address, int expected, int new) {
    if (*address == expected) {
        *address = new;
        return 1;  // Success
    }
    return 0;  // Failure - value changed
}
```

**Example 1: Atomic increment (without locks)**

```c
void AtomicIncrement(int *value, int amount) {
    do {
        int old = *value;
    } while (CompareAndSwap(value, old, old + amount) == 0);
}
```

**How it works:**

```
Scenario: Two threads incrementing counter from 0

Thread 1                       Thread 2
────────                       ────────
old = *value (0)               old = *value (0)
CAS(value, 0, 0+5)             CAS(value, 0, 0+3)
  └─> SUCCESS ✓                  └─> FAILS (value is now 5, not 0)
  value = 5                    old = *value (5)
                               CAS(value, 5, 5+3)
                                 └─> SUCCESS ✓
                               value = 8

Final result: 8 (correct!)
```

**Example 2: Lock-free list insertion**

Traditional approach (with locks):

```c
void insert(int value) {
    node_t *n = malloc(sizeof(node_t));
    assert(n != NULL);
    n->value = value;

    pthread_mutex_lock(listlock);  // Lock required
    n->next = head;
    head = n;
    pthread_mutex_unlock(listlock);
}
```

Lock-free approach (using CAS):

```c
void insert(int value) {
    node_t *n = malloc(sizeof(node_t));
    assert(n != NULL);
    n->value = value;

    do {
        n->next = head;  // Point to current head
    } while (CompareAndSwap(&head, n->next, n) == 0);
    // If head changed since we read it, retry
}
```

**Visual explanation:**

```
Initial state: head → A → B → NULL

Thread 1 wants to insert X:
  n->next = head (points to A)

Thread 2 wants to insert Y:
  n->next = head (points to A)

Thread 2 executes CAS first:
  CAS(&head, A, Y) → SUCCESS
  head → Y → A → B → NULL

Thread 1 executes CAS:
  CAS(&head, A, X) → FAILS (head is now Y, not A)
  Retry: n->next = head (points to Y now)
  CAS(&head, Y, X) → SUCCESS
  head → X → Y → A → B → NULL

Final: head → X → Y → A → B → NULL ✓
```

> **💡 Insight**
>
> Lock-free data structures are like optimistic transactions: assume success, verify at commit time, retry if someone else modified the data. This eliminates deadlock entirely because there are no locks to deadlock on!

**⚠️ Important considerations:**

- Lock-free programming is **hard** - easy to get wrong
- Only works for certain data structures
- Full implementation (with delete, lookup) is complex
- Still possible to have livelock
- Read research papers before implementing in production

**Progressive complexity:**

```
Simple:     Lock-free counter
            └─> Single CAS operation

Intermediate: Lock-free stack
              └─> Push/pop with retry logic

Advanced:   Lock-free queue
            └─> Multiple pointers, ABA problem handling

Expert:     Lock-free skip list
            └─> Complex multi-level operations
```

### 4.5. Deadlock Avoidance via Scheduling

**Strategy:** If you know ahead of time which locks each thread needs, schedule threads so deadlock cannot occur.

**In plain English:** It's like a traffic controller who knows which cars need which roads. By controlling who goes when, you can prevent gridlock before it happens.

#### 4.5.1. Simple Example

**Setup:**
- 2 CPUs
- 4 threads (T1, T2, T3, T4)
- 2 locks (L1, L2)

**Lock requirements:**

| Thread | Needs L1? | Needs L2? |
|--------|-----------|-----------|
| T1 | Yes | Yes |
| T2 | Yes | Yes |
| T3 | No | Yes |
| T4 | No | No |

**Observation:** T1 and T2 both need L1 and L2. If they run simultaneously, deadlock is possible.

**Safe schedule:**

```
CPU 1:  T1 ─────────> T2 ─────────>
CPU 2:       T3 ─────>     T4 ────>

Time: ───────────────────────────────>
```

**Why this works:**
- T1 and T2 never run concurrently (scheduled on same CPU)
- T3 can run with T1 or T2 (only needs L2, no conflict)
- T4 can run anytime (needs no locks)
- No circular wait possible ✅

#### 4.5.2. Complex Example

**New lock requirements:**

| Thread | Needs L1? | Needs L2? |
|--------|-----------|-----------|
| T1 | Yes | Yes |
| T2 | Yes | Yes |
| T3 | Yes | Yes |
| T4 | No | No |

**Problem:** T1, T2, and T3 all need both locks!

**Conservative safe schedule:**

```
CPU 1:  T1 ─────> T2 ─────> T3 ───────>
CPU 2:                T4 ──────────────>

Time: ───────────────────────────────────>
```

**Cost of safety:**
- CPU 2 is mostly idle
- T1, T2, T3 run sequentially (slow!)
- Could have run T1+T4 or T2+T4 concurrently
- Performance sacrificed for deadlock safety

#### 4.5.3. Banker's Algorithm

Dijkstra's famous **Banker's Algorithm** is a classic example of deadlock avoidance through scheduling.

**Analogy:** A banker knows:
- How much money each customer might need (max demand)
- How much each customer currently has (current allocation)
- How much is available in the bank (available resources)

The banker only grants loans if it can guarantee all customers can eventually complete their transactions.

**Algorithm concept:**

```
For each resource request:
1. Simulate granting the request
2. Check if system remains in "safe state"
   └─> Safe state: There exists an execution order
       where all threads can complete
3. If safe → Grant request
   If unsafe → Deny request (thread waits)
```

**Limitations:**

1. **🎯 Requires knowing max needs:** Must declare upfront which locks you'll need
2. **🔒 Limited environments:** Only practical in embedded systems with fixed task sets
3. **⚡ Reduces concurrency:** Conservative scheduling limits parallelism
4. **🌐 Not general-purpose:** Rarely used in general-purpose systems

> **💡 Insight**
>
> Avoidance is theoretically elegant but practically limited. It trades maximum safety for minimum performance and flexibility. Prevention techniques are more commonly used in practice.

### 4.6. Detect and Recover

**Strategy:** Let deadlocks happen occasionally, detect them, and recover.

**In plain English:** Instead of installing complex traffic systems to prevent gridlock, hire a traffic officer who watches for gridlock and guides cars to back up when it happens. Sometimes the simple solution is best.

#### 4.6.1. When This Makes Sense

```
Cost-Benefit Analysis
─────────────────────

Deadlock Prevention Cost:  ████████████  High
Deadlock Frequency:        █             Very Rare

→ Detection may be cheaper than prevention!
```

**Practical scenario:** If your OS freezes once a year due to deadlock, just reboot it. The cost of preventing that rare deadlock might be higher than accepting it.

> **Tom West's Law**
>
> "Not everything worth doing is worth doing well."
>
> If a bad thing happens rarely and the consequences are minor, don't spend enormous effort preventing it.

**⚠️ Exception:** Safety-critical systems (space shuttles, medical devices, aircraft) should ignore this advice!

#### 4.6.2. Detection Algorithm

**Technique:** Periodically build a resource graph and check for cycles.

```
Resource Graph Example
──────────────────────

Thread 1 ──holds──> Lock L1
    ↑                   │
    │                   │ wanted by
    │                   ↓
wanted by           Thread 2
    │                   │
    │                   │ holds
    └────────────────> Lock L2

Cycle detector: Found cycle! → DEADLOCK DETECTED
```

**Detection process:**

1. **Run periodically** (e.g., every minute)
2. **Build dependency graph:**
   - Nodes: threads and resources
   - Edges: "holds" and "wants" relationships
3. **Check for cycles** using graph algorithms (DFS, etc.)
4. **If cycle found** → Take recovery action

#### 4.6.3. Recovery Strategies

Once deadlock is detected, you need to break the cycle:

**Option 1: Kill a thread** 💀
```
Terminate one thread in the cycle
→ Releases its locks
→ Other threads can proceed
```

**Option 2: Restart system** 🔄
```
Reboot the entire system
→ All threads restart fresh
→ Works if deadlocks are rare
```

**Option 3: Rollback** ⏪
```
Roll back one thread's transactions
→ Release its locks
→ Thread re-executes from savepoint
```

**Option 4: Human intervention** 👤
```
Alert administrator
→ Human analyzes situation
→ Manual recovery based on context
```

#### 4.6.4. Database Systems

**Real-world use:** Many database systems use detect-and-recover.

```
Database Deadlock Handling
──────────────────────────

1. Transaction 1: UPDATE accounts SET balance=100 WHERE id=1;
   Transaction 2: UPDATE accounts SET balance=200 WHERE id=2;

2. Transaction 1: UPDATE accounts SET balance=300 WHERE id=2;
   Transaction 2: UPDATE accounts SET balance=400 WHERE id=1;

3. Deadlock detector runs
   └─> Detects cycle

4. Database chooses victim (usually newer/cheaper transaction)
   └─> Rolls back Transaction 2

5. Transaction 1 completes
   Transaction 2 retries automatically

6. Transaction 2 completes on retry
```

**Why databases use this approach:**
- Transactions have natural rollback mechanisms
- Can track which locks each transaction holds
- Cost of detection is low compared to prevention
- Deadlocks are relatively rare in well-designed applications

> **📝 Note**
>
> Database concurrency control is a rich topic. Take a databases course or read specialized literature (e.g., Bernstein et al., Kung) to learn more.

---

## 5. Summary

We've explored the landscape of common concurrency bugs found in real production systems. Understanding these patterns is the first step toward writing robust concurrent code.

### 5.1. Key Takeaways

**🐛 Non-Deadlock Bugs (70% of issues):**

1. **Atomicity Violations**
   - Problem: Operations that should be atomic get interrupted
   - Symptom: Check-then-use, read-modify-write races
   - Solution: Add locks around entire operation
   - Example: Check pointer for NULL, then use it

2. **Order Violations**
   - Problem: Thread B assumes Thread A already ran
   - Symptom: Using uninitialized data
   - Solution: Condition variables to enforce ordering
   - Example: Using variable before initialization completes

**Insight:** 97% of non-deadlock bugs are these two types!

**🔒 Deadlock Bugs (30% of issues):**

| Approach | Strategy | Pros | Cons |
|----------|----------|------|------|
| **Prevention** | Break one of four conditions | Guaranteed deadlock-free | Requires careful design |
| - Circular Wait | Lock ordering | Practical, widely used | Must know all locks, fragile |
| - Hold-and-Wait | Atomic acquisition | Simple concept | Reduces concurrency |
| - No Preemption | Trylock with backoff | Order-independent | Complex, possible livelock |
| - Mutual Exclusion | Lock-free structures | Best performance | Very difficult, limited scope |
| **Avoidance** | Schedule based on needs | Theoretically optimal | Impractical for most systems |
| **Detection** | Find and break cycles | Low overhead when rare | Only works if deadlocks acceptable |

### 5.2. Best Practices

**For preventing atomicity violations:**
```
✅ Lock entire check-then-use sequences
✅ Lock entire read-modify-write sequences
✅ Document atomicity assumptions
❌ Don't assume thread switches won't happen
```

**For preventing order violations:**
```
✅ Use condition variables for ordering
✅ Initialize shared data before threads access it
✅ Document initialization dependencies
❌ Don't assume threads run in expected order
```

**For preventing deadlock:**
```
✅ Establish and document lock ordering
✅ Acquire locks in consistent order
✅ Keep critical sections short
✅ Consider lock-free algorithms for hot paths
❌ Don't grab locks in arbitrary order
❌ Don't hide lock ordering in APIs
```

### 5.3. The Bigger Picture

> **💡 Final Insight**
>
> The best concurrency bug is the one you never write. Consider:
> - Can this be single-threaded?
> - Can I use higher-level abstractions (MapReduce, actors, etc.)?
> - Is the complexity worth the performance gain?

**Modern approaches avoid locks entirely:**

- **Message passing:** Threads communicate via messages, not shared memory
- **Actor model:** Each actor has private state, communicates via messages
- **MapReduce:** Framework handles parallelism, you write sequential code
- **Software Transactional Memory:** Optimistic concurrency like database transactions

**The future:** As concurrent programming models improve, traditional locks may become a low-level detail, hidden from most programmers.

---

**Previous:** [Chapter 6: Semaphores](chapter6-semaphores.md) | **Next:** [Chapter 8: Event-Based Concurrency](chapter8-event-based.md)