# Chapter 3: Locks 🔒

**Transform chaos into control: Building the fundamental synchronization primitive**

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Locks: The Basic Idea](#2-locks-the-basic-idea)
   - 2.1. [Lock Semantics](#21-lock-semantics)
   - 2.2. [Pthread Locks](#22-pthread-locks)
3. [Building a Lock](#3-building-a-lock)
   - 3.1. [Evaluating Locks](#31-evaluating-locks)
4. [Lock Implementation Approaches](#4-lock-implementation-approaches)
   - 4.1. [Controlling Interrupts](#41-controlling-interrupts)
   - 4.2. [Failed Attempt: Just Using Loads/Stores](#42-failed-attempt-just-using-loadsstores)
   - 4.3. [Building Working Spin Locks with Test-And-Set](#43-building-working-spin-locks-with-test-and-set)
   - 4.4. [Evaluating Spin Locks](#44-evaluating-spin-locks)
   - 4.5. [Compare-And-Swap](#45-compare-and-swap)
   - 4.6. [Load-Linked and Store-Conditional](#46-load-linked-and-store-conditional)
   - 4.7. [Fetch-And-Add](#47-fetch-and-add)
5. [Beyond Spinning: OS Support](#5-beyond-spinning-os-support)
   - 5.1. [The Problem with Spinning](#51-the-problem-with-spinning)
   - 5.2. [A Simple Approach: Just Yield](#52-a-simple-approach-just-yield)
   - 5.3. [Using Queues: Sleeping Instead of Spinning](#53-using-queues-sleeping-instead-of-spinning)
   - 5.4. [Different OS, Different Support](#54-different-os-different-support)
   - 5.5. [Two-Phase Locks](#55-two-phase-locks)
6. [Summary](#6-summary)

---

## 1. Introduction

**In plain English:** Imagine you're editing a shared Google Doc with your team. Without any coordination, two people might try to edit the same sentence simultaneously, creating a garbled mess. A lock is like saying "I'm editing this part—everyone else wait your turn."

**In technical terms:** In concurrent programming, we need to execute a series of instructions atomically, but interrupts on a single processor (or multiple threads on multiple processors) can break this atomicity. Locks solve this fundamental problem.

**Why it matters:** Without locks, concurrent programs would produce unpredictable, incorrect results. Every time you use a database, web application, or operating system, locks are working behind the scenes to keep your data consistent.

### 🎯 The Core Challenge

From our introduction to concurrency, we saw that we can't execute multiple instructions atomically due to:
- **Single processor:** Interrupts can occur at any time
- **Multiple processors:** True parallel execution creates race conditions

Locks provide the solution: programmers annotate source code with locks around **critical sections**, ensuring that any such section executes as if it were a single atomic instruction.

### Example: The Canonical Update

```c
balance = balance + 1;
```

Without protection, this simple operation can go wrong with concurrent access. Other critical sections include:
- Adding an element to a linked list
- Updating shared data structures
- Modifying files or databases

---

## 2. Locks: The Basic Idea

### 🔧 Using a Lock

Here's how we protect our critical section:

```c
lock_t mutex; // some globally-allocated lock 'mutex'
...
lock(&mutex);
balance = balance + 1;
unlock(&mutex);
```

> **💡 Insight**
>
> A lock is just a variable that holds state. This simple abstraction—a variable that can be "free" or "held"—is powerful enough to coordinate any number of threads accessing shared resources.

### 2.1. Lock Semantics

**Lock State:**
- **Available** (unlocked/free): No thread holds the lock
- **Acquired** (locked/held): Exactly one thread holds the lock (the "owner")

The lock variable can store additional information:
- Which thread holds the lock
- A queue for ordering lock acquisition
- But this is hidden from the user

**Lock Operations:**

1. **`lock()`** - Try to acquire the lock
   - If free → Acquire it and enter critical section (become the owner)
   - If held → Wait until it becomes free (do not return)

2. **`unlock()`** - Release the lock
   - If no waiting threads → Mark as free
   - If waiting threads → One will acquire the lock

### 🧠 Control Over Scheduling

**In plain English:** Locks are like traffic lights for your code. Instead of the OS randomly deciding which threads run, you control who can enter critical sections.

**The transformation:**
```
Without locks: OS schedules threads randomly → Chaos
With locks: Programmers control critical sections → Controlled activity
```

**Why it matters:** You guarantee that no more than a single thread can ever be active within protected code, transforming unpredictable OS scheduling into deterministic behavior.

### 2.2. Pthread Locks

The POSIX library calls locks **mutexes** (mutual exclusion). Here's the real-world code:

```c
pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;

Pthread_mutex_lock(&lock);   // wrapper; exits on failure
balance = balance + 1;
Pthread_mutex_unlock(&lock);
```

### 🚀 Fine-Grained vs Coarse-Grained Locking

**In plain English:** You can have one big lock for everything (like a single key for your entire house) or many small locks for different things (like separate keys for each room).

**Two strategies:**

1. **Coarse-grained:** One big lock for all critical sections
   - Simple to implement
   - Low concurrency (only one thread active at a time)

2. **Fine-grained:** Different locks for different data structures
   - More complex
   - High concurrency (multiple threads in different critical sections)

**Example:**
```c
pthread_mutex_t balance_lock = PTHREAD_MUTEX_INITIALIZER;
pthread_mutex_t list_lock = PTHREAD_MUTEX_INITIALIZER;

// Thread 1 can update balance
Pthread_mutex_lock(&balance_lock);
balance = balance + 1;
Pthread_mutex_unlock(&balance_lock);

// While Thread 2 updates list (simultaneously!)
Pthread_mutex_lock(&list_lock);
list_add(list, item);
Pthread_mutex_unlock(&list_lock);
```

---

## 3. Building a Lock

### 🎯 The Crux: How to Build a Lock

**How can we build an efficient lock?** Efficient locks provide mutual exclusion at low cost, and might attain other desirable properties. **What hardware support is needed? What OS support?**

### The Requirements

To build a working lock, we need help from:
1. **Hardware:** Special atomic instructions
2. **Operating System:** Primitives for sleeping/waking threads

Over the years, various hardware primitives have been added to instruction sets. We'll study:
- How to use them to build mutual exclusion primitives
- How the OS completes the picture

### 3.1. Evaluating Locks

Before building locks, we need criteria to evaluate them. Three key questions:

#### ✅ 1. Correctness (Mutual Exclusion)

**Does the lock work?** Does it prevent multiple threads from entering a critical section?

This is the most basic requirement—without it, the lock is useless.

#### ⚖️ 2. Fairness

**Does each thread get a fair shot?** More extreme: does any thread starve (never obtaining the lock)?

**Example of unfairness:**
```
Time →
Thread A: [Acquire] [Release] [Acquire] [Release] [Acquire] [Release]
Thread B: [Wait]    [Wait]    [Wait]    [Wait]    [Wait]    [Wait]...
```

#### ⚡ 3. Performance

**What are the time overheads?** Consider multiple cases:

1. **No contention:** Single thread acquiring/releasing
   - What's the overhead with no competition?

2. **Single CPU with contention:** Multiple threads competing
   - How much CPU time is wasted?

3. **Multiple CPUs with contention:** Threads across processors
   - How does it scale?

By comparing these scenarios, we understand the performance impact of different locking techniques.

---

## 4. Lock Implementation Approaches

### 4.1. Controlling Interrupts

**In plain English:** Turn off interrupts before entering a critical section, turn them back on when done. It's like putting a "Do Not Disturb" sign on your door.

#### The Implementation

```c
void lock() {
    DisableInterrupts();
}

void unlock() {
    EnableInterrupts();
}
```

#### How It Works (Single Processor)

By turning off interrupts, we ensure the critical section code won't be interrupted, and thus executes atomically.

**Simple flow:**
```
1. Disable interrupts
2. Execute critical section (no interruption possible)
3. Enable interrupts
4. Continue normally
```

#### ✅ Positives

- **Simplicity:** Easy to understand and implement
- **Guaranteed atomicity:** On single processor, nothing can interrupt

#### ❌ Negatives

**1. Requires too much trust**

```
Greedy program: lock() → monopolize processor forever
Malicious program: lock() → infinite loop → system freeze
```

Only recourse: Restart the system!

**2. Does not work on multiprocessors**

**In plain English:** Turning off interrupts on CPU 1 doesn't affect CPU 2. Other threads on other CPUs can still enter the critical section.

```
CPU 1: [Interrupts OFF] [Critical Section]
CPU 2: [Running normally] → Can enter same critical section!
```

Since multiprocessors are now commonplace, this is a fatal flaw.

**3. Lost interrupts**

**Example scenario:**
```
1. Disable interrupts
2. Disk completes read request → interrupt signal lost
3. OS never knows to wake waiting process
4. Process hangs forever
```

**4. Inefficient**

Modern CPUs execute interrupt masking/unmasking instructions slowly compared to normal operations.

> **💡 Insight**
>
> Interrupt disabling is only used in limited contexts today, primarily inside the OS itself. The OS trusts itself to perform privileged operations. For example, the OS might disable interrupts when accessing its own data structures to guarantee atomicity.

### 4.2. Failed Attempt: Just Using Loads/Stores

**In plain English:** Let's try using a simple flag variable. If the flag is up, someone's using the lock. If it's down, the lock is free. Seems simple, right?

#### The Implementation

```c
typedef struct __lock_t {
    int flag;
} lock_t;

void init(lock_t *mutex) {
    // 0 -> lock is available, 1 -> held
    mutex->flag = 0;
}

void lock(lock_t *mutex) {
    while (mutex->flag == 1)  // TEST the flag
        ;                      // spin-wait (do nothing)
    mutex->flag = 1;           // now SET it!
}

void unlock(lock_t *mutex) {
    mutex->flag = 0;
}
```

#### How It's Supposed to Work

1. First thread calls `lock()`, sees `flag == 0`
2. Sets `flag = 1` and enters critical section
3. Second thread calls `lock()`, sees `flag == 1`
4. Second thread spins in while loop
5. First thread calls `unlock()`, sets `flag = 0`
6. Second thread exits loop, sets `flag = 1`, enters critical section

#### ❌ Problem 1: Correctness Failure

**The race condition:**

```
Thread 1                          Thread 2
--------------------              --------------------
call lock()
while (flag == 1)  // flag is 0
  [INTERRUPT] ─────────────────→  call lock()
                                  while (flag == 1)  // flag is 0
                                  flag = 1;
  [INTERRUPT] ←─────────────────
flag = 1;  // Oops! Both set it!
```

**Result:** Both threads are now in the critical section simultaneously. This is what professionals call "bad" 😄

> **⚠️ Warning: Think Like a Malicious Scheduler**
>
> When analyzing concurrent code, pretend you're an evil scheduler that interrupts threads at the worst possible moments. Although the exact sequence may be improbable, if it's possible, it will eventually happen in production.

#### ❌ Problem 2: Performance Failure

**Spin-waiting** is the problem: the thread endlessly checks the flag value.

**In plain English:** Imagine standing at a locked door, checking the handle every millisecond. You're wasting energy doing nothing useful.

**Why it's especially bad on single CPU:**
```
Thread A: [Holds lock, interrupted]
Thread B: [Spins entire time slice checking flag] ← Complete waste!
Thread A: [Finally runs again, releases lock]
```

The waiting thread can't possibly acquire the lock until a context switch occurs, yet it burns an entire time slice doing nothing.

### 4.3. Building Working Spin Locks with Test-And-Set

**In plain English:** We need hardware that can "test the old value" and "set a new value" in a single atomic operation. Like checking if a parking spot is empty and parking your car in one indivisible action.

#### 🔧 The Test-And-Set Instruction

Hardware provides an atomic instruction (names vary by architecture):
- **SPARC:** `ldstub` (load/store unsigned byte)
- **x86:** `xchg` (atomic exchange)

**C pseudocode (this executes atomically in hardware):**

```c
int TestAndSet(int *old_ptr, int new) {
    int old = *old_ptr;      // fetch old value at old_ptr
    *old_ptr = new;          // store 'new' into old_ptr
    return old;              // return the old value
}
```

**Key insight:** These three operations happen atomically—no interrupt can occur between them.

#### The Lock Implementation

```c
typedef struct __lock_t {
    int flag;
} lock_t;

void init(lock_t *lock) {
    // 0: lock is available, 1: lock is held
    lock->flag = 0;
}

void lock(lock_t *lock) {
    while (TestAndSet(&lock->flag, 1) == 1)
        ;  // spin-wait (do nothing)
}

void unlock(lock_t *lock) {
    lock->flag = 0;
}
```

#### 🎓 Understanding Why This Works

**Case 1: Lock is free (flag = 0)**

```
Thread calls lock()
  ↓
TestAndSet(&flag, 1) executes atomically:
  - Returns old value: 0
  - Sets flag: 1
  ↓
While loop condition: (0 == 1) → false
  ↓
Exit loop, enter critical section ✓
```

**Case 2: Lock is held (flag = 1)**

```
Thread calls lock()
  ↓
TestAndSet(&flag, 1) executes atomically:
  - Returns old value: 1
  - Sets flag: 1 (no change)
  ↓
While loop condition: (1 == 1) → true
  ↓
Spin and repeat until flag becomes 0
```

**Visual diagram:**

```
Initial State       Thread A Acquires       Thread B Tries
─────────────       ─────────────────       ──────────────
flag: 0             flag: 1 (by A)          flag: 1
                    A in critical section   B spins...
                                           (keeps returning 1)

Thread A Releases   Thread B Succeeds
─────────────────   ─────────────────
flag: 0 (by A)      flag: 1 (by B)
A exits             B enters critical section
```

> **💡 Insight**
>
> By making both the "test" (of the old lock value) and "set" (of the new value) a single atomic operation, we ensure that only one thread acquires the lock. This is the key to building correct mutual exclusion primitives.

#### 🔄 Why It's Called a "Spin Lock"

```
Waiting Thread: [Check] → [Check] → [Check] → [Check] → ...
                 ↓         ↓         ↓         ↓
                 Busy      Busy      Busy      Busy
```

The thread literally **spins**, using CPU cycles, until the lock becomes available.

**Requirement on single CPU:** Needs a preemptive scheduler (one that uses timer interrupts to switch threads). Without preemption, a thread spinning would never give up the CPU, and the lock holder could never run to release the lock!

### 4.4. Evaluating Spin Locks

Let's evaluate our spin lock against our three criteria:

#### ✅ 1. Correctness: YES

The spin lock provides mutual exclusion. Only one thread can enter the critical section at a time.

**Proof:** The atomic test-and-set ensures that only one thread will see the old value as 0 and successfully acquire the lock.

#### ⚖️ 2. Fairness: POOR

> **⚠️ Warning: Starvation Risk**
>
> Spin locks provide **no fairness guarantees**. A thread may spin forever under contention, while other threads repeatedly acquire and release the lock.

**Starvation scenario:**

```
Time →
Thread A: [Acquire] [Release] [Acquire] [Release] [Acquire] [Release]
Thread B: [Spin]    [Bad luck] [Spin]    [Bad luck] [Spin forever]...
Thread C: [Acquire] [Release] [Acquire] [Release]...
```

Thread B might never get scheduled at the right moment to acquire the lock.

#### ⚡ 3. Performance: DEPENDS

**Case 1: Single CPU with contention → TERRIBLE**

```
Scenario:
- Thread 0 holds lock, gets preempted in critical section
- N-1 other threads try to acquire lock
- Each spins for entire time slice
- Scheduler eventually returns to Thread 0
- Thread 0 releases lock
```

**Cost:** (N-1) × (time slice duration) of wasted CPU cycles

**In plain English:** Imagine 100 threads. The lock holder gets interrupted. The other 99 threads each waste an entire time slice just spinning before the lock holder gets to run again.

**Case 2: Multiple CPUs, threads ≈ CPUs → REASONABLE**

```
CPU 1: Thread A [Acquires lock] [Critical section] [Releases]
CPU 2: Thread B [Spins briefly] ───────────────────→ [Acquires]
```

**Why it works:**
- Thread B spins on CPU 2 while Thread A works on CPU 1
- Critical sections are typically short
- Minimal cycles wasted
- Lock becomes available quickly

> **💡 Insight**
>
> Spin locks work well when:
> 1. Number of threads ≈ number of CPUs
> 2. Critical sections are short
> 3. Lock contention is low
>
> They work poorly when threads exceed CPUs or critical sections are long.

### 4.5. Compare-And-Swap

**In plain English:** This is like test-and-set's smarter sibling. Instead of always setting a new value, it says "I expect this value; if it's there, change it; otherwise, do nothing."

#### 🔧 The Compare-And-Swap Instruction

Hardware names:
- **SPARC:** compare-and-swap
- **x86:** compare-and-exchange (`cmpxchg`)

**C pseudocode (executes atomically):**

```c
int CompareAndSwap(int *ptr, int expected, int new) {
    int actual = *ptr;
    if (actual == expected)
        *ptr = new;
    return actual;
}
```

**The key difference from test-and-set:**
- **Test-and-set:** Always writes the new value
- **Compare-and-swap:** Only writes if the current value matches expected

#### The Lock Implementation

```c
void lock(lock_t *lock) {
    while (CompareAndSwap(&lock->flag, 0, 1) == 1)
        ;  // spin
}
```

The rest is the same as test-and-set.

#### 🎓 How It Works

**Step-by-step execution:**

```
1. Call CompareAndSwap(&lock->flag, 0, 1)
2. Check: Is flag == 0? (expected value)
3. If YES:
     - Set flag = 1 (atomically)
     - Return 0
     - While condition: (0 == 1) → false
     - Exit loop, acquired lock ✓
4. If NO (flag == 1):
     - Don't change flag
     - Return 1
     - While condition: (1 == 1) → true
     - Keep spinning
```

**Visual comparison:**

```
Test-And-Set                   Compare-And-Swap
────────────                   ────────────────
Always sets new value          Only sets if expected value matches
Simpler                        More powerful
                              Better for lock-free algorithms
```

> **💡 Insight**
>
> Compare-and-swap is more powerful than test-and-set. We can use this extra power for lock-free synchronization and wait-free algorithms. However, for simple spin locks, the behavior is identical to test-and-set.

### 4.6. Load-Linked and Store-Conditional

**In plain English:** Instead of one atomic instruction, some architectures provide two instructions that work together. Think of it like checking out a library book—you load (check out) the value, and your store (return) only succeeds if nobody else modified it in the meantime.

#### 🔧 The Load-Linked and Store-Conditional Instructions

**Architectures:** MIPS, Alpha, PowerPC, ARM

**C pseudocode:**

```c
int LoadLinked(int *ptr) {
    return *ptr;
}

int StoreConditional(int *ptr, int value) {
    if (no update to *ptr since LoadLinked to this address) {
        *ptr = value;
        return 1;  // success!
    } else {
        return 0;  // failed to update
    }
}
```

#### How They Work Together

**Load-Linked:** Fetches a value and marks the address for monitoring

**Store-Conditional:** Succeeds only if:
- No intervening store to the address has occurred
- If successful → writes value, returns 1
- If failed → doesn't write, returns 0

#### The Lock Implementation

```c
void lock(lock_t *lock) {
    while (1) {
        while (LoadLinked(&lock->flag) == 1)
            ;  // spin until it's zero
        if (StoreConditional(&lock->flag, 1) == 1)
            return;  // if set-it-to-1 was a success: all done
        // otherwise: try it all over again
    }
}

void unlock(lock_t *lock) {
    lock->flag = 0;
}
```

#### 🎓 Understanding the Flow

**Successful acquisition (no contention):**

```
1. LoadLinked(&flag) → returns 0 (lock free)
2. Exit inner while loop
3. StoreConditional(&flag, 1) → returns 1 (success!)
4. Return (lock acquired) ✓
```

**Failed acquisition (race condition):**

```
Thread A                          Thread B
────────                          ────────
LoadLinked(&flag) → 0
  [INTERRUPT] ─────────────────→  LoadLinked(&flag) → 0
                                  StoreConditional(&flag, 1) → 1 ✓
                                  (Thread B acquired lock)
  [RESUME] ←───────────────────
StoreConditional(&flag, 1) → 0 ✗
(Fails! Flag was updated)
Go back to outer while loop
Try again...
```

**Why store-conditional fails:**
- Thread A executed load-linked
- Thread B modified flag between A's load-linked and store-conditional
- A's store-conditional detects the intervening write
- A must retry

> **💡 Insight**
>
> The load-linked/store-conditional pair provides a different approach to atomicity. Instead of one instruction doing everything atomically, the hardware monitors for intervening writes and allows software to retry when conflicts are detected.

#### 🎨 Concise Version (Advanced)

A clever student suggested this more concise version using short-circuit evaluation:

```c
void lock(lock_t *lock) {
    while (LoadLinked(&lock->flag) ||
           !StoreConditional(&lock->flag, 1))
        ;  // spin
}
```

**How it works:**
- `LoadLinked(&flag)` returns 1 (true) if flag is 1 → keep spinning
- `LoadLinked(&flag)` returns 0 (false) if flag is 0 → try store-conditional
- `!StoreConditional(&flag, 1)` is true if store failed → keep spinning
- `!StoreConditional(&flag, 1)` is false if store succeeded → exit loop

### 4.7. Fetch-And-Add

**In plain English:** This instruction atomically adds 1 to a value and returns the old value. Like taking a number at the deli counter—you get the current number, and the counter automatically increments for the next person.

#### 🔧 The Fetch-And-Add Instruction

**C pseudocode (executes atomically):**

```c
int FetchAndAdd(int *ptr) {
    int old = *ptr;
    *ptr = old + 1;
    return old;
}
```

#### 🎫 Building a Ticket Lock

Using fetch-and-add, we can build a fairer lock called a **ticket lock** (like the deli counter system):

```c
typedef struct __lock_t {
    int ticket;
    int turn;
} lock_t;

void lock_init(lock_t *lock) {
    lock->ticket = 0;
    lock->turn = 0;
}

void lock(lock_t *lock) {
    int myturn = FetchAndAdd(&lock->ticket);
    while (lock->turn != myturn)
        ;  // spin
}

void unlock(lock_t *lock) {
    lock->turn = lock->turn + 1;
}
```

#### 🎓 How Ticket Locks Work

**The deli counter analogy:**

```
Initial State:
  Ticket dispenser: 0
  Now serving: 0

Customer A arrives:
  Takes ticket: 0 (FetchAndAdd returns 0, increments to 1)
  Waits for: turn == 0 ✓ (immediately served)

Customer B arrives:
  Takes ticket: 1 (FetchAndAdd returns 1, increments to 2)
  Waits for: turn == 1 (must wait)

Customer C arrives:
  Takes ticket: 2 (FetchAndAdd returns 2, increments to 3)
  Waits for: turn == 2 (must wait)

Customer A leaves:
  turn = 1 (Customer B is now served)

Customer B leaves:
  turn = 2 (Customer C is now served)
```

**Visual timeline:**

```
Time →
Thread A: [myturn=0] [Acquire immediately] [Work] [Release, turn=1]
Thread B: [myturn=1] [Wait for turn==1] ──────────→ [Acquire] [Work] [Release, turn=2]
Thread C: [myturn=2] [Wait for turn==2] ───────────────────────────→ [Acquire]
```

#### ✅ The Key Improvement: Fairness

> **💡 Insight**
>
> **Ticket locks ensure progress for all threads.** Once a thread is assigned its ticket value, it will eventually be scheduled. In previous spin lock attempts, a thread could spin forever even as other threads repeatedly acquire and release the lock.

**Comparison:**

```
Test-And-Set Lock              Ticket Lock
─────────────────              ───────────
No fairness guarantee          Guarantees fairness
Possible starvation            No starvation
Random acquisition order       FIFO acquisition order
```

---

## 5. Beyond Spinning: OS Support

### 5.1. The Problem with Spinning

**In plain English:** Our hardware-based locks work correctly, but they waste CPU cycles. It's like revving your car engine while waiting at a red light—it works, but it's inefficient.

#### 🔄 The Crux: How to Avoid Spinning

**How can we develop a lock that doesn't needlessly waste time spinning on the CPU?**

#### The Inefficiency Scenario

```
Single CPU, Two Threads:

Thread 0: [Holds lock] [PREEMPTED mid-critical-section]
Thread 1: [Tries lock] [Spins entire time slice] ← WASTE!
Thread 0: [Resumes] [Releases lock]
Thread 1: [Next time slice] [Finally acquires lock]
```

**Cost:** One complete time slice of spinning (typically 10-100ms)

#### Multiple Threads Makes It Worse

```
Single CPU, N threads:

Thread 0: [Holds lock] [PREEMPTED]
Thread 1: [Spins entire time slice]     ← WASTE!
Thread 2: [Spins entire time slice]     ← WASTE!
Thread 3: [Spins entire time slice]     ← WASTE!
...
Thread N-1: [Spins entire time slice]   ← WASTE!
Thread 0: [Finally resumes] [Releases lock]
```

**Cost:** (N-1) × time slice duration of pure waste

> **⚠️ Warning**
>
> Hardware support alone cannot solve the spinning problem. We'll need OS support to put threads to sleep instead of wasting CPU cycles.

### 5.2. A Simple Approach: Just Yield

**In plain English:** Instead of spinning like crazy, politely give up the CPU when you find the lock is held. "After you, I insist!"

#### The Implementation

```c
void init() {
    flag = 0;
}

void lock() {
    while (TestAndSet(&flag, 1) == 1)
        yield();  // give up the CPU
}

void unlock() {
    flag = 0;
}
```

#### 🔄 How Yield Works

**OS support:** `yield()` is a system call that:
1. Moves caller from **running** state to **ready** state
2. Allows another thread to run
3. Eventually, scheduler will run the yielding thread again

**Thread states:**
- **Running:** Currently executing on CPU
- **Ready:** Runnable, waiting for CPU
- **Blocked:** Waiting for something (I/O, lock, etc.)

#### ✅ Two Threads, One CPU: GOOD

```
Thread A: [Acquires lock]
Thread B: [Tries lock, finds it held] → yield()
          [Deschedules itself]
Thread A: [Resumes, finishes, releases lock]
Thread B: [Scheduled again, acquires lock] ✓
```

**Benefit:** Thread B doesn't waste its time slice spinning. Thread A gets to finish quickly.

#### ❌ Many Threads: STILL PROBLEMATIC

```
100 threads competing for lock:

Thread 1: [Acquires lock] [PREEMPTED]
Thread 2: [Tries, yields] → Context switch
Thread 3: [Tries, yields] → Context switch
Thread 4: [Tries, yields] → Context switch
...
Thread 100: [Tries, yields] → Context switch
Thread 1: [Finally runs again, releases lock]
```

**Problems:**

1. **99 context switches before lock holder runs**
   - Each context switch has overhead (saving/restoring registers, switching page tables, etc.)
   - Better than spinning, but still costly

2. **No guarantee against starvation**
   - A thread may get caught in an endless yield loop
   - Other threads repeatedly enter and exit critical section
   - Unlucky thread never acquires lock

> **💡 Insight**
>
> Yielding is better than spinning (no wasted CPU cycles), but it still leaves too much to chance. The scheduler determines which thread runs next, and it might make bad choices that lead to many context switches or starvation.

### 5.3. Using Queues: Sleeping Instead of Spinning

**In plain English:** Instead of repeatedly checking if the lock is free, go to sleep and ask to be woken up when it's your turn. Like waiting in a virtual line—you don't need to keep checking; someone will call your number.

#### 🎯 The Better Approach

We need to:
1. **Explicitly control** which thread acquires the lock next
2. **Track waiting threads** in a queue
3. Use OS primitives to **sleep** and **wake** threads

#### OS Primitives: Solaris park() and unpark()

**Solaris provides two system calls:**

- **`park()`** - Put calling thread to sleep
- **`unpark(threadID)`** - Wake specific thread

These can be used together to build efficient locks.

#### 🔧 The Implementation

```c
typedef struct __lock_t {
    int flag;
    int guard;
    queue_t *q;
} lock_t;

void lock_init(lock_t *m) {
    m->flag = 0;
    m->guard = 0;
    queue_init(m->q);
}

void lock(lock_t *m) {
    while (TestAndSet(&m->guard, 1) == 1)
        ;  // acquire guard lock by spinning

    if (m->flag == 0) {
        m->flag = 1;      // lock is acquired
        m->guard = 0;
    } else {
        queue_add(m->q, gettid());
        m->guard = 0;
        park();
    }
}

void unlock(lock_t *m) {
    while (TestAndSet(&m->guard, 1) == 1)
        ;  // acquire guard lock by spinning

    if (queue_empty(m->q))
        m->flag = 0;  // let go of lock; no one wants it
    else
        unpark(queue_remove(m->q));  // hold lock (for next thread!)

    m->guard = 0;
}
```

#### 🎓 Understanding the Design

**Two interesting aspects:**

**1. The guard lock protects the lock state**

**In plain English:** We use a spin lock (guard) to protect the lock's internal state. But we only spin for a few instructions, not for the entire critical section.

```
guard: Protects manipulation of flag and queue
  ↓
flag: Indicates whether lock is held
  ↓
queue: Tracks waiting threads
```

**Spinning time:**
- **Without queue:** Spin for entire user critical section (long!)
- **With guard:** Spin only during lock/unlock operations (short!)

**2. Direct lock pass-off**

Notice that when unlocking with waiting threads:
- We don't set `flag = 0`
- We directly wake the next thread
- That thread becomes the new owner

**Why?** The woken thread returns from `park()` but doesn't hold the guard, so it can't set `flag = 1` itself. The lock is passed directly from releaser to acquirer.

#### 🌊 Flow Diagrams

**Successful acquisition (no contention):**

```
lock():
  Acquire guard (spin briefly)
    ↓
  Check flag == 0? YES
    ↓
  Set flag = 1
    ↓
  Release guard
    ↓
  Enter critical section ✓
```

**Failed acquisition (lock held):**

```
lock():
  Acquire guard (spin briefly)
    ↓
  Check flag == 0? NO (lock held)
    ↓
  Add self to queue
    ↓
  Release guard
    ↓
  park() [GO TO SLEEP] 😴
    ↓
  [Eventually woken by unpark()]
    ↓
  Return from park()
    ↓
  Lock is now mine! ✓
```

**Release with waiters:**

```
unlock():
  Acquire guard (spin briefly)
    ↓
  Check queue empty? NO
    ↓
  Remove thread from queue
    ↓
  unpark(thread) [WAKE IT UP]
    ↓
  Keep flag = 1 (lock passed to woken thread)
    ↓
  Release guard
```

#### ⚠️ The Wakeup/Waiting Race

**A subtle problem:** What if a thread is about to park, but gets interrupted and another thread releases the lock?

```
Thread A (trying to lock):       Thread B (holds lock):
─────────────────────────        ──────────────────────
queue_add(q, A)
guard = 0
[About to park...] ──────────→   unlock()
                                 unpark(A)  ← Oops! A hasn't parked yet!
park()  ← Sleeps forever?
```

**Solution 1: Solaris setpark()**

```c
queue_add(m->q, gettid());
setpark();        // NEW: Indicate we're about to park
m->guard = 0;
park();          // If unpark() was called, return immediately
```

`setpark()` tells the OS: "I'm about to park. If someone calls unpark() on me before I actually park, make park() return immediately instead of sleeping."

**Solution 2: Pass guard into kernel**

The kernel could take precautions to atomically release the guard and park the thread.

> **💡 Insight**
>
> Combining hardware primitives (test-and-set) with OS support (park/unpark) creates an efficient lock:
> - **Correctness:** Mutual exclusion guaranteed
> - **Fairness:** Queue ensures threads eventually acquire lock
> - **Performance:** No spinning during critical sections, only brief spinning to protect lock state

### 5.4. Different OS, Different Support

Operating systems provide different primitives for efficient locking. The details vary, but the concepts are similar.

#### 🐧 Linux: futex (Fast Userspace muTEX)

**Key differences from Solaris:**
- Each futex is associated with a physical memory location
- In-kernel queue per futex
- More functionality in-kernel

**Two main calls:**

```c
futex_wait(address, expected)
  // Put calling thread to sleep
  // ONLY if value at address == expected
  // If not equal, return immediately

futex_wake(address)
  // Wake one thread waiting on queue
```

#### 🔧 Linux Futex Lock Implementation

```c
void mutex_lock(int *mutex) {
    int v;

    /* Bit 31 was clear, we got the mutex (the fastpath) */
    if (atomic_bit_test_set(mutex, 31) == 0)
        return;

    atomic_increment(mutex);

    while (1) {
        if (atomic_bit_test_set(mutex, 31) == 0) {
            atomic_decrement(mutex);
            return;
        }

        /* We have to wait. First make sure the futex value
           we are monitoring is truly negative (locked). */
        v = *mutex;
        if (v >= 0)
            continue;

        futex_wait(mutex, v);
    }
}

void mutex_unlock(int *mutex) {
    /* Adding 0x80000000 to counter results in 0 if and
       only if there are not other interested threads */
    if (atomic_add_zero(mutex, 0x80000000))
        return;

    /* There are other threads waiting for this mutex,
       wake one of them up. */
    futex_wake(mutex);
}
```

#### 🎓 Clever Design Features

**1. Single integer stores two things:**

```
Bit 31 (high bit):     Is lock held?
  1 = held
  0 = free

Bits 0-30:            Number of waiters
```

**In plain English:** The sign of the integer tells you if the lock is held (negative = held), and the magnitude tells you how many threads are waiting.

**2. Fast path optimization:**

```
No contention path (common case):
  lock:   atomic_bit_test_set → return     [FAST!]
  unlock: atomic_add_zero → return         [FAST!]

Contention path (less common):
  lock:   Multiple operations + futex_wait  [Slower, but fair]
  unlock: futex_wake                        [Wakes waiting thread]
```

> **💡 Insight**
>
> The Linux futex optimizes for the common case: when there's no contention, very little work is done (just an atomic bit test-and-set to lock, and an atomic add to unlock). The complex queue and sleep/wake logic only kicks in when needed.

### 5.5. Two-Phase Locks

**In plain English:** Sometimes spinning a little bit is faster than immediately going to sleep. Two-phase locks spin briefly (hoping to get lucky), then sleep if that doesn't work.

#### 🎯 The Idea

**Phases:**
1. **Phase 1:** Spin for a while (hoping lock is released soon)
2. **Phase 2:** Give up, use OS support to sleep

#### 🧠 Why Spin First?

**Scenario where spinning is better:**

```
Thread A: [Holds lock] [About to release...]
Thread B: [Tries lock] [Spins 10 cycles] → Lock released! ✓
```

**Cost:** 10 CPU cycles

**If we went to sleep immediately:**

```
Thread A: [Holds lock] [About to release...]
Thread B: [Tries lock] [park()] → Context switch overhead
          [Lock released, woken up] → Context switch overhead
```

**Cost:** 2 context switches (~1000s of cycles each)

> **💡 Insight**
>
> If the critical section is very short, spinning a bit can be faster than the overhead of sleeping and waking up. Two-phase locks combine the best of both worlds.

#### 🔧 Generalized Two-Phase Lock

```
Phase 1: Spin for N iterations
  ↓
Lock acquired? → YES → Enter critical section ✓
  ↓ NO
Phase 2: Use futex/park to sleep
  ↓
Wait until woken
  ↓
Try again...
```

**The Linux lock shown earlier is a simple two-phase lock:**
- It spins once
- If that fails, it uses futex support

**A generalized version could:**
- Spin for a fixed number of iterations (e.g., 100)
- Then sleep using OS support

#### ⚖️ Trade-offs

**Benefits:**
- Avoid context switch overhead for short critical sections
- Better performance in low-contention scenarios

**Drawbacks:**
- Still wastes some CPU cycles spinning
- Tuning the spin count is workload-dependent

> **💡 Insight**
>
> Two-phase locks are a hybrid approach: combining two good ideas (spinning + sleeping) may yield a better one. However, whether it does depends strongly on:
> - Hardware environment
> - Number of threads
> - Workload details
>
> Making a single general-purpose lock good for all use cases is quite a challenge!

---

## 6. Summary

### 🎯 How Real Locks Are Built

Modern locks combine:
1. **Hardware support:** Powerful atomic instructions
   - Test-and-set
   - Compare-and-swap
   - Load-linked/store-conditional
   - Fetch-and-add

2. **OS support:** Sleep/wake primitives
   - Solaris: `park()` and `unpark()`
   - Linux: `futex_wait()` and `futex_wake()`

### 🏗️ Evolution of Lock Designs

```
Simple (Incorrect)           Hardware-Based              OS-Enhanced
──────────────              ──────────────              ───────────
Disable interrupts          Test-and-set spinlock       Queue-based locks
Load/store flag             Compare-and-swap            Futex
                           Load-linked/store-cond      Two-phase locks
                           Fetch-and-add (ticket)
  ↓                           ↓                           ↓
Single CPU only             Correct but spins           Efficient + fair
```

### ✅ Key Lessons

**1. Correctness requires atomic operations**

You cannot build a correct lock with just loads and stores. You need hardware support for atomic read-modify-write operations.

**2. Fairness requires explicit control**

Simple spin locks can starve threads. Ticket locks and queue-based locks provide fairness guarantees.

**3. Performance requires OS support**

Spinning wastes CPU cycles. Efficient locks use OS primitives to sleep instead of spin, especially under high contention.

**4. Real-world locks are tuned**

Actual implementations (Solaris, Linux) are highly optimized:
- Fast path for no contention
- Slow path with queues for contention
- Sometimes hybrid (two-phase) approaches

### 📊 Lock Comparison

| Lock Type | Correct? | Fair? | Performance |
|-----------|----------|-------|-------------|
| Interrupt disable | ✅ (single CPU) | ✅ | ❌ (doesn't work on multi-CPU) |
| Load/store flag | ❌ | N/A | N/A |
| Test-and-set | ✅ | ❌ | ❌ (single CPU), ✅ (multi-CPU) |
| Ticket lock | ✅ | ✅ | ❌ (spins) |
| Queue + yield | ✅ | ~✅ | ~ (many context switches) |
| Queue + park/futex | ✅ | ✅ | ✅ |
| Two-phase | ✅ | ✅ | ✅✅ (optimized) |

### 🔍 Going Deeper

Want to see real implementations?
- **Solaris:** Check out the kernel source
- **Linux:** Read `lowlevellock.h` in the nptl library (part of glibc)
- **Research:** David et al.'s comparison of locking strategies on modern multiprocessors

The code is fascinating and highly tuned for performance!

### 🎓 Final Insight

> **💡 Insight**
>
> Building locks is a perfect example of systems design:
> - **Hardware** provides atomic primitives
> - **OS** provides sleep/wake mechanisms
> - **Libraries** combine them cleverly
> - **Optimization** focuses on the common case (no contention)
>
> From simple ideas (protect shared data) to complex implementations (two-phase futex locks), locks demonstrate how multiple layers of the system stack work together to provide efficient, correct, and fair synchronization.

---

**Previous:** [Chapter 2: Thread API](chapter2-thread-api.md) | **Next:** [Chapter 4: Concurrent Data Structures](chapter4-concurrent-data-structures.md)
