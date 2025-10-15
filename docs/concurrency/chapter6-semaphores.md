# Chapter 6: Semaphores

**In plain English:** Think of a semaphore as a nightclub bouncer with a clicker counter. The bouncer tracks how many people can still enter (capacity) and either lets you in immediately or makes you wait in line until someone leaves.

**In technical terms:** A semaphore is a synchronization primitive with an integer value that can be atomically incremented or decremented, automatically blocking threads when the value would go negative.

**Why it matters:** Semaphores are the Swiss Army knife of concurrency—they can act as locks, coordinate thread ordering, and solve complex synchronization problems with elegant simplicity.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Semaphores: A Definition](#2-semaphores-a-definition)
   - 2.1. [Basic Operations](#21-basic-operations)
   - 2.2. [Key Properties](#22-key-properties)
3. [Binary Semaphores (Locks)](#3-binary-semaphores-locks)
   - 3.1. [Single Thread Usage](#31-single-thread-usage)
   - 3.2. [Multiple Thread Contention](#32-multiple-thread-contention)
4. [Semaphores For Ordering](#4-semaphores-for-ordering)
   - 4.1. [Parent-Child Synchronization](#41-parent-child-synchronization)
   - 4.2. [Execution Scenarios](#42-execution-scenarios)
5. [The Producer/Consumer Problem](#5-the-producerconsumer-problem)
   - 5.1. [First Attempt](#51-first-attempt)
   - 5.2. [Adding Mutual Exclusion (Incorrectly)](#52-adding-mutual-exclusion-incorrectly)
   - 5.3. [Avoiding Deadlock](#53-avoiding-deadlock)
   - 5.4. [The Working Solution](#54-the-working-solution)
6. [Reader-Writer Locks](#6-reader-writer-locks)
   - 6.1. [Implementation](#61-implementation)
   - 6.2. [Fairness Considerations](#62-fairness-considerations)
7. [The Dining Philosophers](#7-the-dining-philosophers)
   - 7.1. [Problem Setup](#71-problem-setup)
   - 7.2. [Broken Solution](#72-broken-solution)
   - 7.3. [Breaking The Dependency](#73-breaking-the-dependency)
8. [Implementing Semaphores](#8-implementing-semaphores)
   - 8.1. [Zemaphores: Building With Locks and CVs](#81-zemaphores-building-with-locks-and-cvs)
   - 8.2. [Why Building CVs From Semaphores Is Hard](#82-why-building-cvs-from-semaphores-is-hard)
9. [Summary](#9-summary)

---

## 1. Introduction

In previous chapters, we learned that solving concurrency problems requires **both locks and condition variables**. But what if there was a single primitive that could handle both roles?

Enter the **semaphore**, invented by the legendary computer scientist Edsger Dijkstra (yes, the same person behind Dijkstra's shortest path algorithm and the famous essay "Goto Statements Considered Harmful"). Dijkstra introduced semaphores as a unified synchronization primitive that can serve as both locks and condition variables.

> **💡 Insight**
>
> Semaphores represent the power of generalization in computer science. Instead of having separate primitives for mutual exclusion and signaling, semaphores provide one elegant abstraction that handles both. This demonstrates a key principle: sometimes the most powerful tools are those that capture the essence of a problem at the right level of abstraction.

### 🎯 The Core Challenge

**How can we use semaphores instead of locks and condition variables?**

This chapter answers:
- What is a semaphore and how does it work?
- What is a binary semaphore and how does it differ from general semaphores?
- How can we build semaphores from locks and condition variables?
- Can we build locks and condition variables from semaphores?

---

## 2. Semaphores: A Definition

### 2.1. Basic Operations

**In plain English:** A semaphore is like a parking lot with a digital sign showing available spaces. Cars can take a space (decrement) or free up a space (increment). If no spaces are available, cars must wait until one opens up.

**In technical terms:** A semaphore is an object with an integer value manipulated through two atomic operations: `sem_wait()` and `sem_post()`.

#### 🔧 Initialization

Before using a semaphore, you must initialize it:

```c
#include <semaphore.h>
sem_t s;
sem_init(&s, 0, 1);  // Initialize to value 1
```

**Parameters:**
- `&s`: Pointer to the semaphore
- `0`: Indicates the semaphore is shared between threads in the same process
- `1`: Initial value of the semaphore

> **📝 Note**
>
> The second parameter determines sharing scope. A value of `0` means the semaphore is shared between threads in the same process. Other values enable sharing across different processes (see the man page for details).

#### 💻 Core Operations

```c
int sem_wait(sem_t *s) {
    // 1. Decrement the value of semaphore s by one
    // 2. Wait if value of semaphore s is negative
}

int sem_post(sem_t *s) {
    // 1. Increment the value of semaphore s by one
    // 2. If there are waiting threads, wake one
}
```

**How they work:**

**`sem_wait()` - The "Take" Operation:**
1. Decrements the semaphore value
2. If the result is negative, the calling thread blocks
3. If the result is >= 0, the thread continues immediately

**`sem_post()` - The "Give" Operation:**
1. Increments the semaphore value
2. If threads are waiting, wakes one of them
3. Never blocks the caller

> **💡 Insight**
>
> The asymmetry between `sem_wait()` and `sem_post()` is crucial. `sem_wait()` checks a condition and potentially blocks, while `sem_post()` always completes immediately and just signals availability. This mirrors the real world: getting a resource might require waiting, but releasing one is always instant.

#### 🔍 Historical Note: P() and V()

Dijkstra originally named these operations **P()** and **V()**:
- **P()** comes from "prolaag" (Dutch: "try to decrease")
- **V()** comes from "verhoog" (Dutch: "increase")

You might also see them called **down** and **up**. Use the Dutch versions to impress (or confuse) your colleagues!

### 2.2. Key Properties

**Property 1: Atomicity**
All operations on the semaphore value happen atomically. You don't need to worry about race conditions within `sem_wait()` or `sem_post()` themselves—they're guaranteed to be thread-safe.

**Property 2: Negative Values Indicate Waiters**
When the semaphore value is negative, the absolute value equals the number of waiting threads. Though users typically don't see this value directly, it helps understand how semaphores function internally.

**Property 3: Non-Deterministic Wakeup**
When multiple threads are waiting and `sem_post()` is called, **any one** of the waiting threads may be woken. There's no guarantee about ordering.

**Visual Model:**

```
Semaphore Value: 2              Semaphore Value: -1

Available: ██                   Available: (none)
Waiting: (none)                 Waiting: T1 → T2

State: Resources available      State: 1 thread waiting
Action: Threads pass through    Action: Threads block
```

---

## 3. Binary Semaphores (Locks)

Our first practical use of semaphores: **implementing a lock**.

**In plain English:** A binary semaphore is like a single-occupancy bathroom. The lock on the door can only be in two states: vacant (1) or occupied (0). If it's occupied, you wait outside until the current occupant leaves.

### 3.1. Single Thread Usage

```c
sem_t m;
sem_init(&m, 0, 1);  // Initialize to 1 - what does this mean?

sem_wait(&m);
// critical section here
sem_post(&m);
```

**Critical Question:** What should the initial value be? Think before reading on...

**Answer:** The value must be **1**.

#### 🧠 Understanding Why

Let's trace through execution with a single thread:

```
Initial State:
Semaphore m = 1

Thread 0:
1. Calls sem_wait(&m)
   → Decrements: m = 1 - 1 = 0
   → Check: 0 >= 0? YES
   → Action: Continue (enter critical section)

2. Executes critical section
   (no other thread interfering)

3. Calls sem_post(&m)
   → Increments: m = 0 + 1 = 1
   → Check: Any waiters? NO
   → Action: Return (lock released)

Final State:
Semaphore m = 1 (back to initial state)
```

**Visual Trace:**

| Value | Thread 0 Action           |
|-------|---------------------------|
| 1     | Initial state             |
| 1     | Call `sem_wait()`         |
| 0     | `sem_wait()` returns      |
| 0     | (critical section)        |
| 0     | Call `sem_post()`         |
| 1     | `sem_post()` returns      |

### 3.2. Multiple Thread Contention

Now the interesting case: Thread 0 holds the lock, and Thread 1 tries to acquire it.

```
Initial State:
Semaphore m = 1

Thread 0:
1. Calls sem_wait(&m)
   → Decrements: m = 0
   → Enters critical section

[Thread 1 runs]

Thread 1:
1. Calls sem_wait(&m)
   → Decrements: m = 0 - 1 = -1
   → Check: -1 < 0? YES
   → Action: BLOCK (go to sleep, wait for signal)

[Thread 0 runs again]

Thread 0:
2. Finishes critical section
3. Calls sem_post(&m)
   → Increments: m = -1 + 1 = 0
   → Check: Waiters exist? YES (Thread 1)
   → Action: Wake Thread 1

[Thread 1 wakes up]

Thread 1:
2. sem_wait() returns
3. Enters critical section
4. Calls sem_post(&m)
   → Increments: m = 1
   → Back to initial state
```

**Detailed State Trace:**

| Value | Thread 0 State | Thread 0 Action      | Thread 1 State | Thread 1 Action        |
|-------|----------------|----------------------|----------------|------------------------|
| 1     | Running        | Call `sem_wait()`    | Ready          |                        |
| 0     | Running        | Enter critical sect  | Ready          |                        |
| 0     | Running        | (working...)         | Running        | Call `sem_wait()`      |
| -1    | Running        | (working...)         | Sleeping       | Blocked (sem < 0)      |
| -1    | Running        | Exit critical sect   | Sleeping       | (waiting...)           |
| -1    | Running        | Call `sem_post()`    | Sleeping       | (waiting...)           |
| 0     | Running        | Increment sem        | Ready          | Woken by Thread 0      |
| 0     | Ready          |                      | Running        | `sem_wait()` returns   |
| 0     | Ready          |                      | Running        | (critical section)     |
| 0     | Ready          |                      | Running        | Call `sem_post()`      |
| 1     | Ready          |                      | Running        | Done                   |

> **💡 Insight**
>
> The semaphore value of -1 when Thread 1 blocks is not just arbitrary—it encodes information. The negative value tells us "one thread is waiting." If two threads were waiting, it would be -2. The semaphore effectively maintains a count of blocked threads, making the wake-up logic straightforward.

### ✅ Exercise: Multiple Waiters

Try tracing what happens when **three threads** all try to acquire the lock held by Thread 0:
- What will the semaphore value be when all three are blocked?
- In what order might they be woken?
- Is the wakeup order guaranteed?

<details>
<summary>Answer (click to reveal)</summary>

- The semaphore value will be **-3** (indicating 3 waiting threads)
- They will be woken **one at a time** as each releases the lock
- The order is **not guaranteed**—any waiting thread might be woken next
</details>

### 🎓 Binary Semaphore Definition

Because a lock has only two states (held and not held), we call a semaphore used this way a **binary semaphore**.

> **📝 Note**
>
> Binary semaphores can be implemented more efficiently than general semaphores since they only need to track two states. However, the generalized semaphore implementation we discuss here works perfectly fine for this use case.

---

## 4. Semaphores For Ordering

Beyond mutual exclusion, semaphores excel at **ordering events** between threads.

**In plain English:** Imagine you're coordinating a relay race. Runner A must pass the baton to Runner B before Runner B can start. A semaphore is like the baton itself—Runner B waits until Runner A signals "I'm done, here's the baton!"

**Common pattern:**
- Thread A performs some work
- Thread B needs to wait until Thread A completes
- Thread A signals completion
- Thread B proceeds

This is similar to condition variables, but often simpler to implement.

### 4.1. Parent-Child Synchronization

Here's a classic example: a parent thread creates a child thread and wants to wait for it to complete.

**Desired output:**
```
parent: begin
child
parent: end
```

**Implementation:**

```c
sem_t s;

void *child(void *arg) {
    printf("child\n");
    sem_post(&s);  // Signal: child is done
    return NULL;
}

int main(int argc, char *argv[]) {
    sem_init(&s, 0, X);  // What should X be?
    printf("parent: begin\n");
    pthread_t c;
    pthread_create(&c, NULL, child, NULL);
    sem_wait(&s);  // Wait here for child
    printf("parent: end\n");
    return 0;
}
```

**Critical Question:** What should the initial value `X` be?

Think about it before continuing...

**Answer:** The value should be **0**.

#### 🧠 Why Zero?

There are two possible execution scenarios. Let's analyze both:

### 4.2. Execution Scenarios

#### Scenario 1: Parent Runs First

```
Initial State:
Semaphore s = 0

Parent Thread:
1. Creates child thread
2. Calls sem_wait(&s)
   → Decrements: s = 0 - 1 = -1
   → Check: -1 < 0? YES
   → Action: BLOCK (wait for signal)

[Child thread runs]

Child Thread:
1. Prints "child"
2. Calls sem_post(&s)
   → Increments: s = -1 + 1 = 0
   → Check: Waiters? YES (parent)
   → Action: Wake parent

[Parent wakes up]

Parent Thread:
3. sem_wait() returns
4. Prints "parent: end"
```

**State Trace:**

| Value | Parent State | Parent Action         | Child State | Child Action          |
|-------|--------------|----------------------|-------------|-----------------------|
| 0     | Running      | Create child         | Ready       |                       |
| 0     | Running      | Call `sem_wait()`    | Ready       |                       |
| -1    | Sleeping     | Blocked (s < 0)      | Running     | Print "child"         |
| -1    | Sleeping     | (waiting...)         | Running     | Call `sem_post()`     |
| 0     | Ready        | Woken by child       | Running     | Done                  |
| 0     | Running      | `sem_wait()` returns | Done        |                       |
| 0     | Running      | Print "parent: end"  | Done        |                       |

#### Scenario 2: Child Runs First

```
Initial State:
Semaphore s = 0

[Child runs to completion before parent waits]

Child Thread:
1. Prints "child"
2. Calls sem_post(&s)
   → Increments: s = 0 + 1 = 1
   → Check: Waiters? NO
   → Action: Return

[Parent runs]

Parent Thread:
1. Calls sem_wait(&s)
   → Decrements: s = 1 - 1 = 0
   → Check: 0 >= 0? YES
   → Action: Continue (no blocking needed)
2. Prints "parent: end"
```

**State Trace:**

| Value | Parent State | Parent Action         | Child State | Child Action          |
|-------|--------------|----------------------|-------------|-----------------------|
| 0     | Running      | Create child         | Ready       |                       |
| 0     | Ready        | (interrupted)        | Running     | Print "child"         |
| 0     | Ready        | (waiting...)         | Running     | Call `sem_post()`     |
| 1     | Ready        | (waiting...)         | Done        | Exit                  |
| 1     | Running      | Call `sem_wait()`    | Done        |                       |
| 0     | Running      | `sem_wait()` returns | Done        |                       |
| 0     | Running      | Print "parent: end"  | Done        |                       |

> **💡 Insight**
>
> Notice the elegance: the semaphore "remembers" whether the child has completed. If the child runs first, the semaphore value becomes 1, encoding the fact that the signal has already occurred. When the parent later calls `sem_wait()`, it doesn't block because the value is positive. This is fundamentally different from condition variables, which don't have memory—if you signal a condition variable with no one waiting, the signal is lost.

#### 🎨 Visual Model

```
Case 1: Parent Fast          Case 2: Child Fast
─────────────────           ─────────────────

Parent creates child        Parent creates child
      ↓                           ↓
Parent waits (s=0→-1)       Child completes
      ↓                           ↓
Parent BLOCKS               Child signals (s=0→1)
      ↓                           ↓
Child completes             Parent waits (s=1→0)
      ↓                           ↓
Child signals               Parent continues
      ↓                    (no blocking needed!)
Parent wakes & continues
```

**Key Difference from Condition Variables:**
- With CVs: Signal is lost if no one is waiting
- With Semaphores: Signal is "stored" in the counter

---

## 5. The Producer/Consumer Problem

Now we tackle a classic concurrency problem: the **bounded buffer** (also called the **producer/consumer problem**).

**In plain English:** Imagine a bakery where bakers (producers) make bread and place it on a shelf with limited space, while customers (consumers) take bread from the shelf. If the shelf is full, bakers must wait. If it's empty, customers must wait. We need to coordinate this carefully to avoid chaos.

**Technical challenge:**
- Multiple producers adding items to a shared buffer
- Multiple consumers removing items from the buffer
- Buffer has limited capacity
- Need to prevent overflow and underflow
- Need to prevent data races

### 🔧 Setup Code

First, the shared buffer and basic operations:

```c
int buffer[MAX];
int fill = 0;   // Next position to fill
int use = 0;    // Next position to use

void put(int value) {
    buffer[fill] = value;       // Line F1
    fill = (fill + 1) % MAX;    // Line F2
}

int get() {
    int tmp = buffer[use];      // Line G1
    use = (use + 1) % MAX;      // Line G2
    return tmp;
}
```

Note the circular buffer logic: `(fill + 1) % MAX` wraps around when reaching the end.

### 5.1. First Attempt

Let's introduce two semaphores to track empty and full buffer slots:

```c
sem_t empty;
sem_t full;

void *producer(void *arg) {
    int i;
    for (i = 0; i < loops; i++) {
        sem_wait(&empty);  // Line P1: Wait for empty slot
        put(i);            // Line P2: Put data
        sem_post(&full);   // Line P3: Signal data available
    }
}

void *consumer(void *arg) {
    int tmp = 0;
    while (tmp != -1) {
        sem_wait(&full);    // Line C1: Wait for data
        tmp = get();        // Line C2: Get data
        sem_post(&empty);   // Line C3: Signal slot available
        printf("%d\n", tmp);
    }
}

int main(int argc, char *argv[]) {
    // ...
    sem_init(&empty, 0, MAX);  // MAX buffers are empty to begin
    sem_init(&full, 0, 0);     // ... and 0 are full
    // ...
}
```

**How it works (initially):**
- `empty` starts at `MAX` (all slots available)
- `full` starts at `0` (no data available)
- Producer waits for `empty` to be > 0, then decrements it
- Producer puts data, then increments `full`
- Consumer waits for `full` to be > 0, then decrements it
- Consumer gets data, then increments `empty`

#### 📊 Trace: Single Buffer (MAX=1)

Let's trace with one producer, one consumer, and `MAX=1`:

```
Initial: empty=1, full=0

Consumer runs first:
├─ sem_wait(&full)
│  └─ full: 0 → -1
└─ BLOCKS (waits for data)

Producer runs:
├─ sem_wait(&empty)
│  └─ empty: 1 → 0 (continues)
├─ put(data)
├─ sem_post(&full)
│  └─ full: -1 → 0 (wakes consumer)
└─ Loops to sem_wait(&empty)
   └─ empty: 0 → -1 (BLOCKS)

Consumer wakes:
├─ sem_wait() returns
├─ get(data)
├─ sem_post(&empty)
│  └─ empty: -1 → 0 (wakes producer)
└─ Prints data

Producer wakes and continues...
```

This works perfectly! The semaphores coordinate the handoff.

#### ⚠️ The Problem: Race Condition with MAX > 1

Now let's set `MAX=10` and run **multiple producers** and **multiple consumers**.

**The race condition:**

```
Buffer state: fill=0
Producer Pa and Pb both ready to add data

Producer Pa:
├─ sem_wait(&empty) ✓ (empty: 10 → 9)
├─ put(i):
│  ├─ buffer[0] = valueA  ← Line F1
│  └─ [INTERRUPTED before F2]
└─ (fill still = 0!)

Producer Pb:
├─ sem_wait(&empty) ✓ (empty: 9 → 8)
├─ put(i):
│  ├─ buffer[0] = valueB  ← OVERWRITES valueA!
│  └─ fill = 1
└─ sem_post(&full) ✓

Producer Pa resumes:
└─ fill = 1  ← Same as Pb! Next write will collide again!
```

**What went wrong:** The `put()` and `get()` operations are **not atomic**. Two producers can interleave their writes, causing:
- Lost data (valueA overwritten)
- Index corruption (fill not incremented correctly)

> **🐛 Problem**
>
> We protected the **buffer availability** with semaphores, but we didn't protect the **buffer operations themselves**. The `put()` and `get()` functions are critical sections that need mutual exclusion!

### 5.2. Adding Mutual Exclusion (Incorrectly)

Let's add a lock (binary semaphore) to protect `put()` and `get()`:

```c
sem_t empty;
sem_t full;
sem_t mutex;  // NEW: Lock for put/get

void *producer(void *arg) {
    int i;
    for (i = 0; i < loops; i++) {
        sem_wait(&mutex);   // Line P0 (NEW)
        sem_wait(&empty);   // Line P1
        put(i);             // Line P2
        sem_post(&full);    // Line P3
        sem_post(&mutex);   // Line P4 (NEW)
    }
}

void *consumer(void *arg) {
    int i;
    for (i = 0; i < loops; i++) {
        sem_wait(&mutex);   // Line C0 (NEW)
        sem_wait(&full);    // Line C1
        int tmp = get();    // Line C2
        sem_post(&empty);   // Line C3
        sem_post(&mutex);   // Line C4 (NEW)
        printf("%d\n", tmp);
    }
}

int main(int argc, char *argv[]) {
    // ...
    sem_init(&empty, 0, MAX);
    sem_init(&full, 0, 0);
    sem_init(&mutex, 0, 1);  // Binary semaphore (lock)
    // ...
}
```

**Seems reasonable, right?** We wrap everything in a lock. But there's a fatal flaw...

### 5.3. Avoiding Deadlock

This code **deadlocks**. Let's see why:

```
Initial: empty=MAX, full=0, mutex=1

Consumer runs first:
├─ sem_wait(&mutex)  ← Acquires lock
│  └─ mutex: 1 → 0
├─ sem_wait(&full)   ← No data available
│  └─ full: 0 → -1
└─ BLOCKS (but still holds mutex!)

Producer runs:
├─ sem_wait(&mutex)  ← Tries to acquire lock
│  └─ mutex: 0 → -1
└─ BLOCKS (waiting for mutex)

DEADLOCK:
- Consumer holds mutex, waits for full
- Producer waits for mutex, can't signal full
- Neither can proceed!
```

**Circular dependency diagram:**

```
Consumer               Producer
   │                      │
   ├─ Holds: mutex        ├─ Wants: mutex
   │                      │
   └─ Waits: full ←───────┼─ Could signal: full
                          │
                          └─ But blocked on mutex!

CYCLE: Consumer needs Producer to signal,
       Producer needs Consumer to release lock
```

> **💡 Insight**
>
> This is a classic deadlock pattern: **lock ordering combined with condition waiting**. The consumer acquires a lock, then waits for a condition that can only be signaled by another thread that needs the same lock. The fundamental problem is that the lock scope is too broad—it encompasses the condition wait.

### 5.4. The Working Solution

**The fix:** Narrow the lock scope to protect **only** the critical section (the buffer operations), not the signaling:

```c
sem_t empty;
sem_t full;
sem_t mutex;

void *producer(void *arg) {
    int i;
    for (i = 0; i < loops; i++) {
        sem_wait(&empty);       // Line P1: Wait for space (outside lock)
        sem_wait(&mutex);       // Line P1.5: Acquire lock
        put(i);                 // Line P2: Critical section
        sem_post(&mutex);       // Line P2.5: Release lock
        sem_post(&full);        // Line P3: Signal data (outside lock)
    }
}

void *consumer(void *arg) {
    int i;
    for (i = 0; i < loops; i++) {
        sem_wait(&full);        // Line C1: Wait for data (outside lock)
        sem_wait(&mutex);       // Line C1.5: Acquire lock
        int tmp = get();        // Line C2: Critical section
        sem_post(&mutex);       // Line C2.5: Release lock
        sem_post(&empty);       // Line C3: Signal space (outside lock)
        printf("%d\n", tmp);
    }
}

int main(int argc, char *argv[]) {
    // ...
    sem_init(&empty, 0, MAX);
    sem_init(&full, 0, 0);
    sem_init(&mutex, 0, 1);
    // ...
}
```

**Why this works:**

```
Lock Scope Before (WRONG):     Lock Scope After (CORRECT):
─────────────────────          ─────────────────────

[Lock acquired]                sem_wait(&full)     ← Outside lock
│                              [Lock acquired]
├─ Wait for condition          │
│  └─ DEADLOCK!                ├─ put/get()        ← Critical section
│                              │
├─ put/get()                   [Lock released]
│                              sem_post(&empty)    ← Outside lock
[Lock released]
```

**Key principles:**
1. **Wait for availability** before acquiring the lock
2. **Acquire lock** only for buffer manipulation
3. **Release lock** before signaling
4. **Signal availability** after releasing the lock

#### 🧠 Understanding the Flow

Let's trace a complete producer-consumer interaction:

```
Producer:                      Consumer:

1. sem_wait(&empty)           1. sem_wait(&full)
   ├─ Check if space             ├─ Check if data
   └─ May block here             └─ May block here

2. sem_wait(&mutex)           2. sem_wait(&mutex)
   └─ Acquire lock               └─ Acquire lock

3. put(data)                  3. get(data)
   └─ Buffer operation           └─ Buffer operation

4. sem_post(&mutex)           4. sem_post(&mutex)
   └─ Release lock               └─ Release lock

5. sem_post(&full)            5. sem_post(&empty)
   └─ Signal consumer            └─ Signal producer
```

**Why the order matters:**

| Step | Why This Order? |
|------|-----------------|
| Wait for availability **first** | Don't hold lock while waiting—prevents deadlock |
| Acquire lock **second** | Now safe to manipulate buffer |
| Release lock **third** | Minimize lock hold time |
| Signal **last** | Don't hold lock while signaling—allows next thread to proceed |

> **🎓 Pattern: Bounded Buffer**
>
> This solution is a **fundamental concurrency pattern**. Memorize it. You'll use it throughout your career for:
> - Thread pools
> - Message queues
> - Pipeline architectures
> - Event processing systems
>
> The pattern: **Wait → Lock → Work → Unlock → Signal**

---

## 6. Reader-Writer Locks

Some data structures need **different locking strategies** for different operations.

**In plain English:** A library allows many people to read the same book simultaneously (no one's modifying it), but when someone wants to write in the catalog (modify state), everyone else must wait. Reading is parallelizable, writing requires exclusive access.

**The insight:** Operations that **only read** don't need mutual exclusion from each other—only from writers.

### 6.1. Implementation

```c
typedef struct _rwlock_t {
    sem_t lock;       // Protects readers counter
    sem_t writelock;  // Ensures ONE writer or MANY readers
    int readers;      // Count of active readers
} rwlock_t;

void rwlock_init(rwlock_t *rw) {
    rw->readers = 0;
    sem_init(&rw->lock, 0, 1);        // Binary semaphore
    sem_init(&rw->writelock, 0, 1);   // Binary semaphore
}

void rwlock_acquire_writelock(rwlock_t *rw) {
    sem_wait(&rw->writelock);  // Acquire exclusive access
}

void rwlock_release_writelock(rwlock_t *rw) {
    sem_post(&rw->writelock);  // Release exclusive access
}

void rwlock_acquire_readlock(rwlock_t *rw) {
    sem_wait(&rw->lock);         // Protect readers count
    rw->readers++;
    if (rw->readers == 1)        // First reader?
        sem_wait(&rw->writelock); // Then acquire writelock
    sem_post(&rw->lock);         // Release readers count lock
}

void rwlock_release_readlock(rwlock_t *rw) {
    sem_wait(&rw->lock);         // Protect readers count
    rw->readers--;
    if (rw->readers == 0)        // Last reader?
        sem_post(&rw->writelock); // Then release writelock
    sem_post(&rw->lock);         // Release readers count lock
}
```

#### 🧠 How It Works

**Two semaphores with different roles:**

1. **`lock`**: Protects the `readers` counter (short-lived, fast)
2. **`writelock`**: Ensures mutual exclusion between readers and writers (long-lived)

**Writer behavior:**
- Simple: acquire `writelock`, do work, release `writelock`
- Blocks if any readers or another writer is active

**Reader behavior:**
- Increment `readers` count (protected by `lock`)
- **First reader** acquires `writelock` (blocks writers)
- Subsequent readers just increment the count
- **Last reader** releases `writelock` (allows writers)

#### 📊 State Transitions

```
State: No activity              State: Readers active
───────────────                ───────────────

writelock: 1 (available)       writelock: 0 (held by readers)
readers: 0                     readers: 3

Writers: Can acquire           Writers: BLOCKED
Readers: Can acquire           Readers: Can acquire


State: Writer active           State: Transitioning
───────────────                ───────────────

writelock: 0 (held by writer)  writelock: 0
readers: 0                     readers: 1 → 0 (last reader leaving)

Writers: BLOCKED               Writers: Will soon unblock
Readers: BLOCKED               Readers: BLOCKED
```

#### 🎨 Execution Trace Example

```
Initial: readers=0, writelock=1

Reader 1:
├─ Acquire lock
├─ readers: 0 → 1
├─ First reader! Acquire writelock
│  └─ writelock: 1 → 0
└─ Release lock

Reader 2:
├─ Acquire lock
├─ readers: 1 → 2
├─ Not first reader, skip writelock
└─ Release lock

Writer W:
├─ Try to acquire writelock
└─ BLOCKED (writelock held by readers)

Reader 1 finishes:
├─ Acquire lock
├─ readers: 2 → 1
├─ Not last reader, skip writelock release
└─ Release lock

Reader 2 finishes:
├─ Acquire lock
├─ readers: 1 → 0
├─ Last reader! Release writelock
│  └─ writelock: 0 → 1 (Writer W wakes up)
└─ Release lock

Writer W:
└─ Acquires writelock, proceeds
```

### 6.2. Fairness Considerations

**Problem: Reader starvation of writers**

If readers keep arriving, writers can be **starved**:

```
Time:  0    1    2    3    4    5
       │    │    │    │    │    │
R1 ────┼────┼────┴────┘    │    │
R2         ─┴────┴─────┘   │    │
R3              ─┴─────┴───┘    │
W              [WAITING FOREVER...]
```

Each departing reader is replaced by a new arriving reader, so `readers` never reaches 0, and the writer never gets its turn.

**Potential solutions:**
- Limit consecutive reader acquisitions
- Priority queuing for writers
- "Intention to write" flag that blocks new readers
- Time-based fairness

> **⚠️ Warning: Complexity Trap**
>
> While reader-writer locks sound elegant, they come with costs:
> - More complex implementation = more bugs
> - Additional overhead from managing reader counts
> - Potential for writer starvation
> - In practice, often **slower** than simple locks
>
> Always benchmark! Sometimes a simple, fast lock outperforms a "clever" optimization.

### 💪 Hill's Law: Big and Dumb is Better

Computer architecture researcher Mark Hill found that simple direct-mapped caches often outperformed fancy set-associative designs. The lesson: **simplicity enables speed**.

In locking:
- Simple spin locks: Fast, easy to verify
- Reader-writer locks: Complex, potential performance pitfalls

**Advice:** Start with simple locks. Only add complexity when profiling proves you need it.

---

## 7. The Dining Philosophers

A famous concurrency puzzle that's more intellectually interesting than practically useful—but it might come up in interviews!

**In plain English:** Five philosophers sit at a round table, alternating between thinking and eating. To eat, a philosopher needs two forks (one on their left, one on their right). With only five forks total, how do we prevent deadlock and starvation?

### 7.1. Problem Setup

**The scenario:**

```
        f2
        ││
    P1      P2
   /  \    /  \
  f1  ╲  ╱  f3
       ╲╱╱
       P0
      ╱  ╲
     f0    f4
    │      │
   P4 ──── P3
```

- 5 philosophers: P0, P1, P2, P3, P4
- 5 forks: f0, f1, f2, f3, f4
- Fork fN is between philosopher PN and P(N+1)%5

**Each philosopher's behavior:**

```c
while (1) {
    think();      // No forks needed
    getforks();   // Acquire left and right fork
    eat();        // Requires both forks
    putforks();   // Release both forks
}
```

**The challenge:**
- ✅ No deadlock
- ✅ No starvation (every philosopher eventually eats)
- ✅ High concurrency (multiple philosophers eating simultaneously)

#### 🔧 Helper Functions

```c
int left(int p) {
    return p;  // Philosopher p's left fork is fork p
}

int right(int p) {
    return (p + 1) % 5;  // Philosopher p's right fork is fork (p+1)%5
}
```

Example: Philosopher 4's right fork is `(4+1)%5 = 0`.

**Semaphore array:**

```c
sem_t forks[5];  // One semaphore per fork
// Each initialized to 1 (fork available)
for (int i = 0; i < 5; i++) {
    sem_init(&forks[i], 0, 1);
}
```

### 7.2. Broken Solution

**Naive approach:**

```c
void getforks() {
    sem_wait(forks[left(p)]);   // Grab left fork
    sem_wait(forks[right(p)]);  // Grab right fork
}

void putforks() {
    sem_post(forks[left(p)]);   // Release left fork
    sem_post(forks[right(p)]);  // Release right fork
}
```

**Why it breaks:**

```
Time: 0         1         2         3
      │         │         │         │
P0:   grab f0 ─ grab f1? ┐
P1:   grab f1 ─ grab f2? ┤
P2:   grab f2 ─ grab f3? ┼─ ALL DEADLOCKED!
P3:   grab f3 ─ grab f4? ┤
P4:   grab f4 ─ grab f0? ┘
                  │
                  └─ Everyone waiting for their right fork,
                     which is held as the left fork of their neighbor
```

**Deadlock scenario:**
1. P0 grabs f0 (waiting for f1)
2. P1 grabs f1 (waiting for f2)
3. P2 grabs f2 (waiting for f3)
4. P3 grabs f3 (waiting for f4)
5. P4 grabs f4 (waiting for f0) ← Circular wait!

**Circular dependency:**

```
P0 ──holds── f0 ──needs── P4
│                         │
needs                   holds
│                         │
f1 ──holds── P1 ──needs── f4
             │
           holds
             │
             f2 ──holds── P2
                  │
                needs
                  │
                  f3 ──holds── P3
```

> **🐛 Deadlock Condition: Circular Wait**
>
> Everyone holds one resource and waits for the next resource in a circle. No one can proceed, and no one can release what they hold without acquiring what they need.

### 7.3. Breaking The Dependency

**Dijkstra's solution:** Change the acquisition order for **one philosopher** to break the cycle.

```c
void getforks() {
    if (p == 4) {  // Philosopher 4 is special
        sem_wait(forks[right(p)]);  // Grab RIGHT first
        sem_wait(forks[left(p)]);   // Then LEFT
    } else {
        sem_wait(forks[left(p)]);   // Grab LEFT first
        sem_wait(forks[right(p)]);  // Then RIGHT
    }
}
```

**Why this works:**

```
Normal philosophers (P0-P3):   Last philosopher (P4):
───────────────────────        ───────────────────

1. Grab left fork (fP)         1. Grab RIGHT fork (f0)
2. Grab right fork (f(P+1))    2. Grab LEFT fork (f4)
```

**Breaking the cycle:**

```
Worst case scenario:
P0: grabs f0, waits for f1
P1: grabs f1, waits for f2
P2: grabs f2, waits for f3
P3: grabs f3, waits for f4
P4: tries to grab f0... BLOCKED!
    (because P0 holds it)

But P4 hasn't grabbed f4 yet!

So P3 can proceed:
P3: already has f3, grabs f4, EATS, releases both

Now P4 can grab f4, then f0 (when P0 releases)...
The cycle is broken!
```

**Visual proof:**

```
Before (Deadlock possible):       After (No deadlock):
─────────────────                ─────────────────

P0 → f0 → P4 → f4 → P3           P0 → f0 → P4
     │         │                      │         ╲
     └─────────┘                      │          f4 → P3
   (circular!)                        │               │
                                      └───────────────┘
                                      (P4 needs f0, but hasn't
                                       locked f4, so P3 can proceed)
```

> **💡 Insight**
>
> This is a classic deadlock-breaking technique: **break resource ordering**. If everyone tries to acquire resources in the same order, circular wait is possible. By having one entity use a different order, you ensure that at least one resource remains available for someone to make progress.

#### 🎨 Extended Solutions

Other approaches to consider:
- **Maximum N-1 diners**: Only allow 4 philosophers to attempt dining at once
- **Waiter/arbitrator**: Centralized control over fork allocation
- **Timeout and retry**: If can't get both forks in time, release and retry

---

## 8. Implementing Semaphores

We've used semaphores as primitives. Now let's **build them** from locks and condition variables!

### 8.1. Zemaphores: Building With Locks and CVs

**Our implementation: "Zemaphores"**

```c
typedef struct __Zem_t {
    int value;              // The semaphore value
    pthread_cond_t cond;    // For waiting/signaling
    pthread_mutex_t lock;   // For protecting value
} Zem_t;

// Initialize a Zemaphore
void Zem_init(Zem_t *s, int value) {
    s->value = value;
    Cond_init(&s->cond);
    Mutex_init(&s->lock);
}

// Wait (decrement, potentially block)
void Zem_wait(Zem_t *s) {
    Mutex_lock(&s->lock);
    while (s->value <= 0)           // Wait while value is 0 or less
        Cond_wait(&s->cond, &s->lock);
    s->value--;                      // Decrement value
    Mutex_unlock(&s->lock);
}

// Post (increment, potentially wake)
void Zem_post(Zem_t *s) {
    Mutex_lock(&s->lock);
    s->value++;                      // Increment value
    Cond_signal(&s->cond);           // Wake one waiter (if any)
    Mutex_unlock(&s->lock);
}
```

#### 🧠 How It Works

**Components:**
1. **`value`**: The semaphore counter (protected by lock)
2. **`lock`**: Ensures atomic updates to `value`
3. **`cond`**: For blocking and waking threads

**Key operations:**

**Zem_wait():**
```
1. Acquire lock
2. While value <= 0:
   └─ Wait on condition variable
      (atomically releases lock and sleeps)
3. Decrement value
4. Release lock
```

**Zem_post():**
```
1. Acquire lock
2. Increment value
3. Signal condition variable (wake one waiter)
4. Release lock
```

#### 📊 Trace Example

```
Initial: value=1

Thread 1: Zem_wait()
├─ Lock acquired
├─ value = 1 (> 0, skip while loop)
├─ value: 1 → 0
└─ Unlock

Thread 2: Zem_wait()
├─ Lock acquired
├─ value = 0 (<= 0, enter while loop)
├─ Cond_wait() [releases lock, sleeps]
└─ (blocked)

Thread 1: Zem_post()
├─ Lock acquired
├─ value: 0 → 1
├─ Cond_signal() [wakes Thread 2]
└─ Unlock

Thread 2: (wakes up)
├─ Re-acquires lock
├─ Re-checks while condition
├─ value = 1 (> 0, exit while loop)
├─ value: 1 → 0
└─ Unlock
```

> **💡 Insight: Why While Loop?**
>
> We use `while (s->value <= 0)` instead of `if` to handle **spurious wakeups**—the thread might wake up even though no one signaled it. Always re-check the condition after waking from `Cond_wait()`.

#### 🔍 Difference from Dijkstra's Semaphores

**Original Dijkstra semaphore:** Negative value indicates number of waiters
```
value = -3  means 3 threads waiting
value = 0   means available but not waiting threads
value = 5   means 5 resources available
```

**Our Zemaphore:** Value never goes negative
```
value = 0  means no resources (threads may be waiting, but value stays 0)
value = 5  means 5 resources available
```

This is **simpler to implement** and matches the **Linux kernel** implementation.

### 8.2. Why Building CVs From Semaphores Is Hard

Can we go the **other direction**—build condition variables from semaphores?

**Surprisingly difficult!** Even experienced concurrent programmers got this wrong when implementing condition variables on Windows (which only provided semaphores initially).

**The challenge:**

```c
// Naive attempt
void Cond_wait(Cond_t *c, Mutex_t *m) {
    Mutex_unlock(m);      // Release lock
    Sem_wait(&c->sem);    // Wait on semaphore
    Mutex_lock(m);        // Re-acquire lock
}

void Cond_signal(Cond_t *c) {
    Sem_post(&c->sem);    // Signal semaphore
}
```

**Problems:**
1. **Lost wakeup race:** What if `Cond_signal()` is called between `Mutex_unlock()` and `Sem_wait()`?
2. **Spurious wakeup handling:** Hard to re-check condition atomically
3. **Broadcast semantics:** How do you wake all waiters with a semaphore?

> **⚠️ Warning**
>
> Building condition variables from semaphores is a **non-trivial research problem**. Multiple published attempts had subtle bugs. Don't try this at home unless you're writing a PhD thesis!

---

## 9. Summary

Semaphores are a **powerful and flexible** synchronization primitive that can serve as both locks and condition variables.

### 🎯 Key Takeaways

**Core Concepts:**
- Semaphores maintain an integer value manipulated atomically
- `sem_wait()`: Decrement and potentially block
- `sem_post()`: Increment and potentially wake waiters
- Negative values (conceptually) represent waiting threads

**Three Main Uses:**

1. **Binary Semaphores (Locks)**
   - Initialize to 1
   - Provides mutual exclusion
   - Simple and effective

2. **Ordering/Signaling**
   - Initialize to 0
   - One thread waits, another signals
   - "Remembers" the signal (unlike CVs)

3. **Counting/Resource Management**
   - Initialize to N (available resources)
   - Automatically tracks availability
   - Perfect for bounded buffers

**Classic Patterns:**

| Pattern | Semaphores | Initial Values | Use Case |
|---------|-----------|----------------|----------|
| Lock | 1 semaphore | 1 | Mutual exclusion |
| Ordering | 1 semaphore | 0 | Thread coordination |
| Bounded Buffer | 3 semaphores | empty=N, full=0, mutex=1 | Producer-consumer |
| Reader-Writer | 2 semaphores + counter | Both 1 | Concurrent reads, exclusive writes |

**Critical Lessons:**

> **Lock scope matters**
>
> Always acquire locks **after** waiting for availability, and release locks **before** signaling. Incorrect ordering causes deadlock.

> **Deadlock from circular wait**
>
> If all threads acquire resources in the same order, circular dependencies can form. Break the cycle by having at least one thread use a different order.

> **Simplicity often wins**
>
> Reader-writer locks and other "clever" optimizations are often slower than simple locks due to added complexity. Always benchmark!

### 🎓 Going Further

To master concurrency:
- Solve more puzzles (see Allen Downey's "Little Book of Semaphores")
- Study classic problems: cigarette smokers, sleeping barber
- Read research papers on lock-free data structures
- Practice, practice, practice

Becoming an expert takes **years**. This chapter is just the beginning.

---

**Previous:** [Chapter 5: Condition Variables](chapter5-condition-variables.md) | **Next:** [Chapter 7: Common Concurrency Problems](chapter7-common-problems.md)