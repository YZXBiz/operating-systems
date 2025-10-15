# 🧵 Chapter 1: Concurrency Introduction

_Understanding threads, race conditions, and the foundations of concurrent programming_

---

## Table of Contents

1. [Introduction: Beyond Single Execution](#1-introduction-beyond-single-execution)
2. [What is a Thread?](#2-what-is-a-thread)
   - 2.1. [Threads vs Processes](#21-threads-vs-processes)
   - 2.2. [Thread State and Context Switching](#22-thread-state-and-context-switching)
   - 2.3. [Multi-Threaded Address Spaces](#23-multi-threaded-address-spaces)
3. [Why Use Threads?](#3-why-use-threads)
   - 3.1. [Reason 1: Parallelism](#31-reason-1-parallelism)
   - 3.2. [Reason 2: Avoiding I/O Blocking](#32-reason-2-avoiding-io-blocking)
   - 3.3. [Threads vs Processes: When to Use Each](#33-threads-vs-processes-when-to-use-each)
4. [Thread Creation in Practice](#4-thread-creation-in-practice)
   - 4.1. [A Simple Example](#41-a-simple-example)
   - 4.2. [Understanding Thread Execution Order](#42-understanding-thread-execution-order)
   - 4.3. [Non-Deterministic Behavior](#43-non-deterministic-behavior)
5. [The Danger: Shared Data](#5-the-danger-shared-data)
   - 5.1. [A Counter Gone Wrong](#51-a-counter-gone-wrong)
   - 5.2. [The Heart of the Problem: Uncontrolled Scheduling](#52-the-heart-of-the-problem-uncontrolled-scheduling)
   - 5.3. [Race Conditions and Critical Sections](#53-race-conditions-and-critical-sections)
6. [The Solution: Atomicity](#6-the-solution-atomicity)
   - 6.1. [What Does Atomic Mean?](#61-what-does-atomic-mean)
   - 6.2. [Building Synchronization Primitives](#62-building-synchronization-primitives)
7. [Beyond Mutual Exclusion](#7-beyond-mutual-exclusion)
8. [Why Study This in OS?](#8-why-study-this-in-os)
9. [Key Terminology](#9-key-terminology)
10. [Summary](#10-summary)

---

## 1. Introduction: Beyond Single Execution

**In plain English:** Up until now, we've thought of programs as having a single "finger" pointing at one instruction at a time. Threads let a program have multiple "fingers" pointing at different instructions simultaneously, all working on the same data.

**In technical terms:** We've seen how the OS creates the illusion of multiple CPUs through virtualization, and how it creates the illusion of large private memory through address spaces. Now we introduce **threads** - a new abstraction that allows multiple points of execution within a single process.

**Why it matters:** Threads are fundamental to modern computing. They power everything from web servers handling thousands of requests simultaneously to your phone running multiple apps smoothly. Understanding threads is essential for writing high-performance, responsive software.

> **💡 Insight**
>
> The operating system has been performing virtualization all along: virtualizing the CPU to create the illusion of many CPUs, and virtualizing memory to create the illusion of private address spaces. Threads are yet another form of virtualization - creating multiple virtual "program counters" within a single program.

---

## 2. What is a Thread?

### 2.1. Threads vs Processes

**In plain English:** Think of a process as a house, and threads as people living in that house. Each person (thread) can be in a different room doing different things, but they all share the same house, kitchen, and furniture (memory). In contrast, separate processes are like separate houses - completely independent with no shared spaces.

**In technical terms:** A thread is similar to a separate process, with one crucial difference: **threads share the same address space** and can access the same data. This makes data sharing trivial compared to inter-process communication.

| Feature | Process | Thread |
|---------|---------|--------|
| **Address Space** | Private, isolated | Shared with other threads |
| **Data Sharing** | Difficult (IPC required) | Easy (shared memory) |
| **Context Switch** | Expensive (page table switch) | Cheaper (same address space) |
| **Use Case** | Logically separate tasks | Cooperative work on shared data |

### 2.2. Thread State and Context Switching

Each thread maintains its own execution context:

- **Program Counter (PC)** - tracks where in the code this thread is executing
- **Private Registers** - each thread has its own set of registers for computation
- **Thread Control Block (TCB)** - stores thread state (similar to PCB for processes)

**Context switching between threads:**

```
Thread 1 Running              Context Switch              Thread 2 Running
─────────────────             ──────────────              ─────────────────
PC = 0x1000                   Save T1 state               PC = 0x2000
Registers = {...}      →      to TCB          →           Registers = {...}
Address Space A               Load T2 state                Address Space A
                              from TCB                     (NO PAGE TABLE SWITCH!)
```

> **💡 Insight**
>
> The key optimization: when switching between threads in the same process, the **address space remains the same**. This means no expensive page table switching, making thread context switches significantly faster than process context switches.

### 2.3. Multi-Threaded Address Spaces

**Single-Threaded Process:**
```
┌─────────────────┐  0KB
│  Program Code   │
├─────────────────┤  1KB
│                 │
│      Heap       │
│   (grows ↓)     │
│                 │
├─────────────────┤
│     (free)      │
├─────────────────┤
│      Stack      │
│   (grows ↑)     │
└─────────────────┘  16KB
```

**Multi-Threaded Process (2 threads):**
```
┌─────────────────┐  0KB
│  Program Code   │
├─────────────────┤  1KB
│                 │
│      Heap       │
│   (grows ↓)     │
│                 │
├─────────────────┤
│     (free)      │
├─────────────────┤
│   Stack (T2)    │  ← Thread 2's stack
├─────────────────┤
│     (free)      │
├─────────────────┤
│   Stack (T1)    │  ← Thread 1's stack
└─────────────────┘  16KB
```

**Key observations:**

1. **Each thread gets its own stack** - for local variables, function parameters, return addresses
2. **Thread-local storage** - stack variables are private to each thread
3. **Shared heap** - dynamically allocated memory is accessible by all threads
4. **Trade-off** - the elegant "stack grows down, heap grows up" layout is sacrificed, but typically okay since stacks don't need to be huge

> **⚠️ Warning**
>
> Unlike the single-threaded model where stack and heap can grow toward each other safely, multi-threaded stacks have fixed sizes. Deep recursion in a multi-threaded program can overflow a thread's stack even if plenty of address space remains.

---

## 3. Why Use Threads?

### 3.1. Reason 1: Parallelism

**In plain English:** Imagine you need to add up numbers in a massive spreadsheet with a million rows. Instead of one person doing all the work, you could split it: one person handles rows 1-500K, another handles 500K-1M, and they work simultaneously. Threads do exactly this for computation.

**In technical terms:** When you have multiple CPU cores, threads enable **parallel execution** of work. This is called **parallelization** - transforming a sequential program into one that exploits multiple CPUs simultaneously.

**Example scenario:**
```
Task: Add two arrays with 1 million elements

Single-threaded:
───────────────────────────────────────► 10 seconds
One thread processes all 1M elements

Multi-threaded (4 cores):
Thread 1: ─────────►                     2.5 seconds
Thread 2: ─────────►
Thread 3: ─────────►
Thread 4: ─────────►
Each processes 250K elements in parallel
```

### 3.2. Reason 2: Avoiding I/O Blocking

**In plain English:** Imagine a restaurant with one waiter. If the waiter takes an order to the kitchen and then just stands there waiting for it to be ready, they're wasting time they could spend taking other orders. Threads let your program stay productive while waiting for slow operations.

**In technical terms:** Disk I/O, network operations, and page faults can take milliseconds to seconds - an eternity in CPU time. Instead of blocking and wasting CPU cycles, **threads enable overlapping I/O with computation**. While one thread blocks on I/O, other threads can execute.

**Example: Web server handling requests**
```
Traditional (blocking):
Request 1 arrives → Read disk (100ms wait) → Response → Next request
Total time for 10 requests: 1000ms

Threaded (overlapping):
Thread 1: Request 1 → Read disk (100ms wait) → Response
Thread 2:   Request 2 → Read disk (100ms wait) → Response
Thread 3:     Request 3 → Read disk (100ms wait) → Response
...
Total time for 10 requests: ~100ms (all overlap!)
```

> **💡 Insight**
>
> Threading enables **I/O concurrency** within a single program, much like multiprogramming enabled I/O concurrency across multiple programs. This is why web servers, databases, and other I/O-intensive applications heavily rely on threads.

### 3.3. Threads vs Processes: When to Use Each

**Use threads when:**
- ✅ Tasks need to share data frequently
- ✅ You need lightweight, fast context switching
- ✅ Working on different parts of the same problem (e.g., parallel array processing)

**Use processes when:**
- ✅ Tasks are logically independent
- ✅ You need strong isolation for security or stability
- ✅ Minimal data sharing required

---

## 4. Thread Creation in Practice

### 4.1. A Simple Example

Let's examine a minimal thread creation program using POSIX threads (pthreads):

**Context:** We'll create two threads that each print a letter ("A" or "B"), then wait for them to complete.

```c
#include <stdio.h>
#include <assert.h>
#include <pthread.h>

void *mythread(void *arg) {
    printf("%s\n", (char *) arg);
    return NULL;
}

int main(int argc, char *argv[]) {
    pthread_t p1, p2;
    printf("main: begin\n");

    // Create two threads
    Pthread_create(&p1, NULL, mythread, "A");
    Pthread_create(&p2, NULL, mythread, "B");

    // Wait for both threads to finish
    Pthread_join(p1, NULL);
    Pthread_join(p2, NULL);

    printf("main: end\n");
    return 0;
}
```

**How it works:**

1. **Pthread_create()** - Creates a new thread that runs `mythread()` with argument "A" or "B"
2. **Thread starts** - The new thread may start immediately or be scheduled later
3. **Pthread_join()** - Main thread waits for each worker thread to complete
4. **Total threads** - Three threads exist: main, T1 (prints "A"), and T2 (prints "B")

> **🎓 Learning Point**
>
> `Pthread_create()` is like making a function call, but instead of executing immediately and returning, it creates a **new independent execution stream** that runs concurrently with the caller. This is fundamentally different from traditional function calls!

### 4.2. Understanding Thread Execution Order

**Important:** Threads don't execute in a guaranteed order. The OS scheduler decides when each thread runs, leading to different possible execution sequences.

**Execution Trace 1: Sequential after creation**
```
Main Thread         Thread 1            Thread 2
───────────         ────────            ────────
prints "begin"
creates T1
creates T2
waits for T1
                    runs
                    prints "A"
                    returns
waits for T2
                                        runs
                                        prints "B"
                                        returns
prints "end"

Output:
main: begin
A
B
main: end
```

**Execution Trace 2: Immediate execution**
```
Main Thread         Thread 1            Thread 2
───────────         ────────            ────────
prints "begin"
creates T1
                    runs immediately!
                    prints "A"
                    returns
creates T2
                                        runs immediately!
                                        prints "B"
                                        returns
waits for T1 (already done)
waits for T2 (already done)
prints "end"

Output:
main: begin
A
B
main: end
```

**Execution Trace 3: T2 before T1**
```
Main Thread         Thread 1            Thread 2
───────────         ────────            ────────
prints "begin"
creates T1
creates T2
                                        runs first!
                                        prints "B"
                                        returns
waits for T1
                    runs
                    prints "A"
                    returns
waits for T2 (already done)
prints "end"

Output:
main: begin
B
A
main: end
```

### 4.3. Non-Deterministic Behavior

> **⚠️ Key Concept**
>
> **Creation order ≠ Execution order**. Just because Thread 1 was created before Thread 2 doesn't mean it will run first. The OS scheduler makes these decisions based on complex heuristics, resource availability, and timing.

**What this means for you:**
- Don't assume any particular execution order
- Programs must work correctly regardless of scheduling
- Use synchronization primitives (locks, condition variables) when order matters

---

## 5. The Danger: Shared Data

### 5.1. A Counter Gone Wrong

Now let's see where threads get dangerous. Consider this program where two threads each increment a shared counter 10 million times:

```c
#include <stdio.h>
#include <pthread.h>

static volatile int counter = 0;

void *mythread(void *arg) {
    printf("%s: begin\n", (char *) arg);
    int i;
    for (i = 0; i < 1e7; i++) {
        counter = counter + 1;  // ← THE PROBLEM IS HERE
    }
    printf("%s: done\n", (char *) arg);
    return NULL;
}

int main(int argc, char *argv[]) {
    pthread_t p1, p2;
    printf("main: begin (counter = %d)\n", counter);

    Pthread_create(&p1, NULL, mythread, "A");
    Pthread_create(&p2, NULL, mythread, "B");

    Pthread_join(p1, NULL);
    Pthread_join(p2, NULL);

    printf("main: done with both (counter = %d)\n", counter);
    return 0;
}
```

**Expected result:** `counter = 20,000,000` (10M + 10M)

**Actual results:**
```bash
prompt> ./main
main: begin (counter = 0)
A: begin
B: begin
A: done
B: done
main: done with both (counter = 20000000)  # ✓ Correct (sometimes!)

prompt> ./main
main: done with both (counter = 19345221)  # ✗ Wrong!

prompt> ./main
main: done with both (counter = 19221041)  # ✗ Wrong and different!
```

**What's happening?** The results are **non-deterministic** - different every time! This violates our expectation that computers produce consistent results.

> **🐛 The Bug**
>
> This is a **race condition** - the outcome depends on the precise timing of thread execution. Sometimes we get lucky and it works; other times threads interfere with each other in subtle, invisible ways.

### 5.2. The Heart of the Problem: Uncontrolled Scheduling

**The innocent-looking line:**
```c
counter = counter + 1;
```

**What the compiler actually generates (x86 assembly):**
```assembly
mov 0x8049a1c, %eax    # Load counter into register
add $0x1, %eax          # Increment register
mov %eax, 0x8049a1c     # Store register back to counter
```

**The problem:** This is **three separate instructions**, and a thread can be interrupted between any of them!

**Detailed execution trace showing the bug:**

```
Time  OS Action       Thread 1              Thread 2         PC    %eax   counter
────  ────────────    ─────────────────     ─────────────   ───   ─────  ───────
1                     mov 0x..., %eax                       100    0      50
2                     add $0x1, %eax                        105    50     50
3                     ← about to store      ← INTERRUPTED   108    51     50

4     INTERRUPT!
5     Save T1 state
6     Load T2 state                                                        50

7                                           mov 0x..., %eax  100    0      50
8                                           add $0x1, %eax   105    50     50
9                                           mov %eax, 0x...  108    51     51
10                                          ← DONE           113    51     51

11    INTERRUPT!
12    Save T2 state
13    Load T1 state   ← resume                              108    51     51

14                    mov %eax, 0x...                       113    51     51
15                    ← DONE                                              51

RESULT: Both threads ran, but counter = 51 instead of 52!
```

**What went wrong:**
1. Thread 1 loads counter (50), increments to 51 in register
2. **INTERRUPT** - before T1 writes back!
3. Thread 2 loads counter (still 50!), increments to 51, writes 51
4. Thread 1 resumes, writes its old value (51) again
5. Result: Two increments but counter only increased once

> **💡 Insight**
>
> The problem isn't the threads themselves - it's that a seemingly atomic operation (`counter++`) is actually multiple instructions at the hardware level. When threads interleave execution at the instruction level, chaos ensues.

### 5.3. Race Conditions and Critical Sections

**Race condition:** When the outcome depends on timing/ordering of thread execution. Results are **indeterminate** - different each time the program runs.

**Critical section:** Code that accesses a shared resource and must not be executed by multiple threads concurrently. In our example:

```c
counter = counter + 1;  // ← This is a CRITICAL SECTION
```

**Mutual exclusion:** The property that if one thread is in a critical section, others are prevented from entering. This is what we need to solve the race condition!

> **🎓 Historical Note**
>
> These terms - critical section, race condition, mutual exclusion - were coined by Edsger Dijkstra, a pioneer in computer science who won the Turing Award for this and related work. His 1968 paper "Cooperating Sequential Processes" provided an amazingly clear description of these problems.

---

## 6. The Solution: Atomicity

### 6.1. What Does Atomic Mean?

**In plain English:** "Atomic" means "as a unit" or "all-or-nothing." Like atoms were once thought to be indivisible, an atomic operation cannot be broken into smaller pieces. Either it happens completely or not at all - no in-between state is visible.

**In technical terms:** An **atomic operation** executes as if it were a single indivisible instruction. Even if interrupted, the interrupt either happens before the operation starts or after it completes - never in the middle.

**Ideal solution - a hypothetical atomic instruction:**
```assembly
memory-add 0x8049a1c, $0x1  # Atomically increment memory location
```

If such an instruction existed and was guaranteed atomic by hardware, our problem would be solved! An interrupt could only occur before or after this instruction, never during it.

**The reality:** We won't have such specific instructions for every operation (imagine "atomic-update-B-tree"!). Instead, we get a few fundamental hardware primitives we can use to **build** higher-level synchronization primitives.

> **💡 Insight: Atomicity Everywhere**
>
> Atomicity isn't just for concurrent programming. It's a fundamental technique used throughout computer systems:
> - **File systems** - Journaling and copy-on-write for crash consistency
> - **Databases** - Transactions (ACID properties)
> - **Distributed systems** - Consensus protocols
> - **Hardware** - Atomic CPU instructions
>
> The idea is the same everywhere: group multiple operations so they appear to happen instantaneously as one indivisible unit.

### 6.2. Building Synchronization Primitives

**The approach:**

1. Hardware provides basic atomic instructions (e.g., test-and-set, compare-and-swap)
2. OS provides system call support
3. We build **synchronization primitives** on top:
   - **Locks** - for mutual exclusion
   - **Condition variables** - for waiting/signaling
   - **Semaphores** - general-purpose synchronization

**Using a lock to fix our counter:**
```c
lock_t mutex;  // Declare a lock

void *mythread(void *arg) {
    for (i = 0; i < 1e7; i++) {
        lock(&mutex);           // ← Acquire lock
        counter = counter + 1;  // ← Critical section (now protected!)
        unlock(&mutex);         // ← Release lock
    }
    return NULL;
}
```

**How locks ensure correctness:**
```
Thread 1                Thread 2                Counter
────────                ────────                ───────
lock(&mutex)   ✓                                50
counter++               lock(&mutex)  ✗ WAITS  51
unlock(&mutex)                                  51
                        ← now acquires lock     51
                        counter++               52
                        unlock(&mutex)          52

Result: counter = 52 (correct!)
```

> **🎉 Success**
>
> With proper synchronization, our program produces **deterministic** results regardless of how threads are scheduled. This is the power of synchronization primitives!

---

## 7. Beyond Mutual Exclusion

**The broader picture:** Mutual exclusion (locks) solves one concurrency problem, but not all. Another common pattern:

**Coordination problem:** One thread needs to wait for another thread to complete some action before continuing.

**Examples:**
- Parent thread waits for child thread to finish (join operation)
- Thread waits for I/O completion
- Producer waits for consumer to process data

**Solution:** We'll study **condition variables** in upcoming chapters - primitives for this sleeping/waking interaction pattern.

> **📝 Preview**
>
> The two fundamental concurrency patterns:
> 1. **Mutual exclusion** - preventing concurrent access (solved by locks)
> 2. **Coordination** - waiting for events/conditions (solved by condition variables)
>
> Together, locks and condition variables form the foundation for building correct concurrent programs.

---

## 8. Why Study This in OS?

**Historical perspective:** The operating system was the **first concurrent program**. Before multi-threaded applications existed, OS designers faced these exact problems.

**Example: File system operations**

Two processes both call `write()` to append data to a file:

**Operations required:**
1. Allocate a new disk block
2. Update file's inode to record block location
3. Update file size
4. Update free block bitmap

**The problem:** An interrupt between any of these steps could leave the file system in an inconsistent state!

```
Process 1                   File System                 Process 2
─────────                   ───────────                 ─────────
write(fd, data)  →          Allocate block 723
                            Update inode...
                            ← INTERRUPT →               write(fd, data)
                                                        Allocate block 723  ← SAME BLOCK!
                                                        Data corruption!
```

**The solution:** OS designers had to make virtually every kernel data structure thread-safe:
- Page tables
- Process lists
- File system structures (inodes, bitmaps)
- Device driver queues
- Memory allocators

> **💡 Insight**
>
> Concurrency isn't an "application problem" - it's fundamental to OS design. The techniques we'll learn were invented by OS developers and later adopted by application programmers as multi-threaded applications became common.

---

## 9. Key Terminology

These four terms are absolutely central to concurrent programming:

**🔑 Critical Section**
- A piece of code that accesses a shared resource (usually a variable or data structure)
- Must not be executed concurrently by multiple threads

**🔑 Race Condition (Data Race)**
- Occurs when multiple threads enter a critical section at roughly the same time
- Both attempt to update shared data, leading to unexpected outcomes
- Results depend on timing of execution

**🔑 Indeterminate Program**
- Contains one or more race conditions
- Output varies from run to run depending on thread scheduling
- Violates our expectation of deterministic computation

**🔑 Mutual Exclusion**
- A property ensuring only a single thread can enter a critical section at a time
- Achieved through synchronization primitives (locks, semaphores, etc.)
- Prevents races and ensures deterministic program behavior

> **📖 Reference**
>
> These terms were formalized by Edsger Dijkstra in his seminal papers [D65, D68]. If you're serious about concurrent programming, these papers are worth reading for their clarity and insight.

---

## 10. Summary

**What we've learned:**

1. **Threads** provide multiple points of execution within a single address space
2. **Why threads matter:**
   - Parallelism: exploit multiple CPUs for faster execution
   - Avoiding I/O blocking: overlap computation with I/O waits

3. **The challenge:** Shared data creates race conditions when threads execute without synchronization

4. **The core problems:**
   - Race conditions lead to indeterminate, incorrect results
   - Simple operations like `counter++` aren't atomic at the hardware level
   - Uncontrolled thread scheduling causes critical sections to interleave

5. **The path forward:** Build synchronization primitives (locks, condition variables) using:
   - Hardware support (atomic instructions)
   - OS support (system calls)
   - Careful design patterns

**Next steps:** We'll dive deep into **locks** - how to build them, how to use them, and how to avoid common pitfalls like deadlock.

`★ Insight ─────────────────────────────────────`
**The fundamental tradeoff of concurrency:**
- **Benefit:** Performance through parallelism and I/O overlap
- **Cost:** Complexity in reasoning about correctness
- **Solution:** Disciplined use of synchronization primitives

Concurrency is hard, but unavoidable in modern systems. The goal isn't to avoid it, but to master it through understanding and proper tools.
`─────────────────────────────────────────────────`

---

**Next:** [Chapter 2: Thread API →](chapter2-thread-api.md)
