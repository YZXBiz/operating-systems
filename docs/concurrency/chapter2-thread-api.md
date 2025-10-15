# 🔧 Chapter 2: Thread API

_Mastering the POSIX thread interface for thread creation, synchronization, and control_

---

## Table of Contents

1. [Introduction: Your Threading Toolkit](#1-introduction-your-threading-toolkit)
2. [Thread Creation](#2-thread-creation)
   - 2.1. [The pthread_create Function](#21-the-pthread_create-function)
   - 2.2. [Understanding Function Pointers](#22-understanding-function-pointers)
   - 2.3. [Passing Arguments with void Pointers](#23-passing-arguments-with-void-pointers)
   - 2.4. [Creating a Thread - Complete Example](#24-creating-a-thread---complete-example)
3. [Thread Completion](#3-thread-completion)
   - 3.1. [The pthread_join Function](#31-the-pthread_join-function)
   - 3.2. [Returning Values from Threads](#32-returning-values-from-threads)
   - 3.3. [Simplified Argument Passing](#33-simplified-argument-passing)
   - 3.4. [The Stack Allocation Trap](#34-the-stack-allocation-trap)
   - 3.5. [When to Use Join](#35-when-to-use-join)
4. [Locks for Mutual Exclusion](#4-locks-for-mutual-exclusion)
   - 4.1. [The Lock/Unlock Primitives](#41-the-lockunlock-primitives)
   - 4.2. [Proper Lock Initialization](#42-proper-lock-initialization)
   - 4.3. [Error Handling with Locks](#43-error-handling-with-locks)
   - 4.4. [Additional Lock Functions](#44-additional-lock-functions)
5. [Condition Variables](#5-condition-variables)
   - 5.1. [The Wait and Signal Operations](#51-the-wait-and-signal-operations)
   - 5.2. [Using Condition Variables Correctly](#52-using-condition-variables-correctly)
   - 5.3. [Why Not Use Simple Flags?](#53-why-not-use-simple-flags)
6. [Compiling and Running](#6-compiling-and-running)
7. [Thread API Best Practices](#7-thread-api-best-practices)
8. [Summary](#8-summary)

---

## 1. Introduction: Your Threading Toolkit

**In plain English:** Think of the thread API as your toolbox for concurrent programming. Just like a carpenter needs to know how to use a hammer, saw, and drill, you need to master thread creation, joining, locks, and condition variables. This chapter is your quick reference guide.

**In technical terms:** The POSIX thread library (pthreads) provides a standardized API for multi-threaded programming. While subsequent chapters will explore the concepts in depth with examples, this chapter serves as a **practical reference** for the core API functions.

**Why it matters:** These few API functions form the foundation of all multi-threaded programming in C. Master these, and you can build sophisticated concurrent systems. The API is intentionally minimal - you don't need hundreds of functions, just a handful used correctly.

> **🎯 Chapter Goal**
>
> **THE CRUX: HOW TO CREATE AND CONTROL THREADS**
>
> What interfaces should the OS present for thread creation and control? How should these interfaces be designed to enable ease of use as well as utility?

> **💡 Insight**
>
> This chapter is **reference-oriented** rather than tutorial-oriented. Think of it as the API documentation you'll refer back to repeatedly. The following chapters will provide deeper conceptual understanding with extensive examples - this chapter gives you the essential mechanics first.

---

## 2. Thread Creation

### 2.1. The pthread_create Function

**The essential API for creating new threads:**

```c
#include <pthread.h>

int pthread_create(
    pthread_t             *thread,
    const pthread_attr_t  *attr,
    void                  *(*start_routine)(void*),
    void                  *arg
);
```

**Parameter breakdown:**

| Parameter | Type | Purpose |
|-----------|------|---------|
| **thread** | `pthread_t *` | Pointer to thread structure - initialized by this call |
| **attr** | `const pthread_attr_t *` | Thread attributes (stack size, priority) - use `NULL` for defaults |
| **start_routine** | `void *(*)(void*)` | Function pointer - which function should the thread run? |
| **arg** | `void *` | Argument passed to start_routine |

**In plain English:** You're telling the OS: "Create a new execution stream, configure it with these attributes, start it running at this function, and pass this data to it."

### 2.2. Understanding Function Pointers

**The confusing syntax demystified:**

```c
void *(*start_routine)(void*)
```

**Reading it step by step:**
1. `start_routine` - the name of the function pointer
2. `(*start_routine)` - it's a pointer to a function
3. `void *` (before) - the function returns a `void*` (generic pointer)
4. `(void*)` (after) - the function takes a `void*` as argument

**Example variations:**

```c
// If the thread function takes an int instead:
int pthread_create(...,
    void *(*start_routine)(int),
    int arg);

// If it returns an int instead:
int pthread_create(...,
    int (*start_routine)(void*),
    void *arg);
```

> **🎓 Learning Point**
>
> Function pointers let you pass "executable code" as a parameter. This is how pthread_create knows what code to run in the new thread - you're literally passing it a pointer to a function!

### 2.3. Passing Arguments with void Pointers

**Why `void*` everywhere?**

**In plain English:** `void*` is C's way of saying "a pointer to anything." Think of it as a universal adapter - it can hold the address of any type of data, but you have to remember what type it actually is.

**In technical terms:** Using `void*` for both arguments and return values provides **type flexibility**:
- **Pass any type** - int, struct, array, anything
- **Return any type** - same flexibility on output
- **Your responsibility** - you must cast it back to the correct type

**The pattern:**
```
You → Package data as void* → pthread_create → Thread receives void*
                                                         ↓
Thread → Cast back to original type → Use the data
```

### 2.4. Creating a Thread - Complete Example

**Context:** We'll create a thread that prints two integers, demonstrating how to package multiple arguments.

```c
#include <pthread.h>
#include <stdio.h>

// Define a structure to hold multiple arguments
typedef struct {
    int a;
    int b;
} myarg_t;

void *mythread(void *arg) {
    myarg_t *args = (myarg_t *) arg;  // Cast back to original type
    printf("%d %d\n", args->a, args->b);
    return NULL;
}

int main(int argc, char *argv[]) {
    pthread_t p;

    // Package arguments into structure
    myarg_t args;
    args.a = 10;
    args.b = 20;

    // Create thread with packaged arguments
    int rc = pthread_create(&p, NULL, mythread, &args);
    // ... (rest of program)
}
```

**How the data flows:**

```
main()                          mythread()
──────                          ──────────
args (struct)
  a = 10
  b = 20
    ↓
&args cast to void*  ─────→     void *arg
                                    ↓
                                Cast to myarg_t*
                                    ↓
                                Access: args->a, args->b
```

**Expected output:**
```
10 20
```

> **✅ Key Takeaway**
>
> Once `pthread_create()` returns successfully, you have a **new live executing entity** with its own call stack, running within the same address space as all other threads. The thread may start immediately or be scheduled later - you don't control when!

---

## 3. Thread Completion

### 3.1. The pthread_join Function

**Waiting for a thread to finish:**

```c
int pthread_join(pthread_t thread, void **value_ptr);
```

**Parameters:**

| Parameter | Type | Purpose |
|-----------|------|---------|
| **thread** | `pthread_t` | Which thread to wait for (from pthread_create) |
| **value_ptr** | `void **` | Pointer to location where return value will be stored |

**In plain English:** "Stop and wait here until the specified thread finishes running, then give me whatever value it returned."

**In technical terms:** `pthread_join()` provides **synchronization** - the calling thread blocks until the target thread terminates. This is essential for ensuring work completes before proceeding.

**Why `void**` instead of `void*`?**

```
The thread returns:      void*
You need to modify:      void* (your variable)
To modify a pointer:     You need a pointer to that pointer → void**
```

### 3.2. Returning Values from Threads

**Complete example showing argument passing AND return values:**

```c
#include <stdio.h>
#include <pthread.h>
#include <stdlib.h>

typedef struct {
    int a;
    int b;
} myarg_t;

typedef struct {
    int x;
    int y;
} myret_t;

void *mythread(void *arg) {
    myarg_t *args = (myarg_t *) arg;
    printf("%d %d\n", args->a, args->b);

    // Allocate return value on HEAP (not stack!)
    myret_t *rvals = malloc(sizeof(myret_t));
    rvals->x = 1;
    rvals->y = 2;

    return (void *) rvals;
}

int main(int argc, char *argv[]) {
    pthread_t p;
    myret_t *rvals;

    myarg_t args = {10, 20};
    pthread_create(&p, NULL, mythread, &args);

    // Wait for thread and get return value
    pthread_join(p, (void **) &rvals);

    printf("returned %d %d\n", rvals->x, rvals->y);
    free(rvals);  // Clean up heap allocation

    return 0;
}
```

**Expected output:**
```
10 20
returned 1 2
```

**Data flow visualization:**

```
main()                  mythread()                  Return Path
──────                  ──────────                  ───────────
                        malloc(myret_t)
                        rvals->x = 1
                        rvals->y = 2
                        return (void*)rvals ─────→  pthread_join receives
                                                           ↓
rvals pointer  ←───────────────────────────────────  stores in value_ptr
    ↓
Access rvals->x, rvals->y
    ↓
free(rvals)
```

### 3.3. Simplified Argument Passing

**When you only need to pass a single integer:**

```c
void *mythread(void *arg) {
    int value = (int) arg;  // Cast void* directly to int
    printf("%d\n", value);
    return (void *) (value + 1);  // Return int as void*
}

int main(int argc, char *argv[]) {
    pthread_t p;
    int result;

    // Pass 100 directly as void*
    pthread_create(&p, NULL, mythread, (void *) 100);
    pthread_join(p, (void **) &result);

    printf("returned %d\n", result);
    return 0;
}
```

**Expected output:**
```
100
returned 101
```

**When to skip the complexity:**

✅ **Use NULL for arguments** - When thread needs no input:
```c
pthread_create(&p, NULL, mythread, NULL);
```

✅ **Use NULL for return values** - When you don't care about the result:
```c
pthread_join(p, NULL);
```

> **💡 Insight**
>
> The wrapper functions like `Pthread_create()` and `Pthread_join()` you see in examples are just thin wrappers that call the lowercase versions and assert success. They make code cleaner but aren't part of the official API.

### 3.4. The Stack Allocation Trap

**⚠️ DANGER: Never return pointers to stack-allocated data!**

**The broken code:**

```c
void *mythread(void *arg) {
    myarg_t *args = (myarg_t *) arg;
    printf("%d %d\n", args->a, args->b);

    myret_t rvals;  // ← ALLOCATED ON STACK: BAD!
    rvals.x = 1;
    rvals.y = 2;

    return (void *) &rvals;  // ← RETURNING POINTER TO STACK: DISASTER!
}
```

**Why this is catastrophic:**

```
mythread() execution:
┌──────────────────┐
│   Stack Frame    │
│   ────────────   │
│   myret_t rvals  │  ← Allocated here
│   x = 1          │
│   y = 2          │
└──────────────────┘
        ↓
   return &rvals  ────────→  Pointer to stack memory
        ↓
   Thread ends
        ↓
   Stack frame DEALLOCATED  ← Memory is now invalid!
        ↓
   Pointer now points to garbage or reused memory
```

**What happens when main() tries to use this pointer:**
- **Sometimes:** Appears to work (memory hasn't been reused yet)
- **Often:** Garbage data
- **Worst case:** Segmentation fault or silent corruption

> **⚠️ Critical Rule**
>
> **Stack memory is automatically deallocated when the function returns.** Returning a pointer to stack memory is like giving someone directions to a house that's about to be demolished - they'll find nothing or worse!

**The correct approach:**

```c
✅ Use heap allocation:
myret_t *rvals = malloc(sizeof(myret_t));  // Heap allocation persists!

✅ Use global/static variables:
static myret_t rvals;  // Lives in data segment, not stack

❌ Never use stack allocation for return values:
myret_t rvals;  // Stack - deallocated when function returns!
```

> **🔍 Compiler Warning**
>
> Modern compilers (especially gcc with warnings enabled) will catch this mistake:
> ```
> warning: function returns address of local variable
> ```
> **Always pay attention to compiler warnings!** This is one of many reasons why.

### 3.5. When to Use Join

**Pattern 1: Create-and-wait (unusual):**

```c
pthread_create(&p, NULL, mythread, arg);
pthread_join(p, NULL);  // Immediate wait
```

**In plain English:** This is basically a complicated function call! If you're creating one thread and immediately waiting, you're not really exploiting concurrency. There's an easier way: just call the function directly.

**Pattern 2: Parallel work (common):**

```c
// Create multiple threads
for (int i = 0; i < 10; i++) {
    pthread_create(&threads[i], NULL, worker, &data[i]);
}

// Wait for all to complete
for (int i = 0; i < 10; i++) {
    pthread_join(threads[i], NULL);
}
```

**Use case:** Parallel computation - divide work among threads, wait for all to finish before proceeding.

**Pattern 3: Long-lived servers (no join):**

```c
// Web server example
while (1) {
    connection = accept_request();
    pthread_create(&worker, NULL, handle_request, connection);
    // No join - threads run indefinitely!
}
```

**Use case:** Server processes where threads handle ongoing work. The main thread keeps accepting requests while workers process them.

> **📝 When to Join**
>
> **Use pthread_join when:**
> - ✅ You need results from the thread
> - ✅ You must ensure work completes before proceeding
> - ✅ Building parallel algorithms (e.g., parallel sort, parallel matrix multiply)
>
> **Skip pthread_join when:**
> - ✅ Running long-lived worker threads
> - ✅ Implementing server/daemon processes
> - ✅ Background tasks that run indefinitely

---

## 4. Locks for Mutual Exclusion

### 4.1. The Lock/Unlock Primitives

**The fundamental mutual exclusion API:**

```c
int pthread_mutex_lock(pthread_mutex_t *mutex);
int pthread_mutex_unlock(pthread_mutex_t *mutex);
```

**In plain English:** A lock is like a bathroom occupancy indicator. Before entering the critical section (bathroom), you check if it's locked. If free, you lock it and enter. If occupied, you wait. When done, you unlock it so others can enter.

**In technical terms:** These functions provide **mutual exclusion** for critical sections. The lock ensures that only one thread executes the protected code at a time.

**Basic usage pattern:**

```c
pthread_mutex_t lock;

pthread_mutex_lock(&lock);
// Critical section - only one thread at a time
x = x + 1;
pthread_mutex_unlock(&lock);
```

**How it works:**

```
Thread 1                    Thread 2                Lock State
────────                    ────────                ──────────
pthread_mutex_lock(&lock)                           ACQUIRED by T1
  ↓ Lock acquired
x = x + 1                   pthread_mutex_lock()    LOCKED
  ↓                           ↓ Blocks, waits       T2 WAITING
pthread_mutex_unlock()        ↓                     RELEASED
                              ↓ Wakes up
                            Lock acquired           ACQUIRED by T2
                            x = x + 1               LOCKED
                            pthread_mutex_unlock()  RELEASED
```

> **💡 Insight**
>
> When `pthread_mutex_lock()` is called:
> - If lock is **available** → thread acquires it and continues immediately
> - If lock is **held** → thread blocks (sleeps) until the lock is released
> - **Multiple threads** may wait; only the lock holder can unlock

### 4.2. Proper Lock Initialization

**⚠️ Problem: The code above is BROKEN!**

The lock must be initialized before use. There are two ways:

**Method 1: Static initialization (compile-time):**

```c
pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
```

**Method 2: Dynamic initialization (run-time):**

```c
pthread_mutex_t lock;

int rc = pthread_mutex_init(&lock, NULL);
assert(rc == 0);  // Always check success!

// ... use lock ...

pthread_mutex_destroy(&lock);  // Clean up when done
```

**Parameters for pthread_mutex_init:**
- First argument: Address of the lock
- Second argument: Optional attributes (use `NULL` for defaults)

**Complete correct example:**

```c
pthread_mutex_t lock;

void init_lock(void) {
    int rc = pthread_mutex_init(&lock, NULL);
    assert(rc == 0);
}

void use_lock(void) {
    pthread_mutex_lock(&lock);
    counter = counter + 1;
    pthread_mutex_unlock(&lock);
}

void cleanup(void) {
    pthread_mutex_destroy(&lock);
}
```

> **✅ Best Practice**
>
> **Dynamic initialization is recommended** because:
> - More flexible (can initialize at runtime)
> - Allows checking for initialization errors
> - Pairs with destroy for proper resource management
> - Works for locks in heap-allocated structures

### 4.3. Error Handling with Locks

**The second problem: No error checking!**

**Bad code (silently fails):**

```c
pthread_mutex_lock(&lock);    // What if this fails?
counter++;
pthread_mutex_unlock(&lock);  // What if this fails?
```

**Correct code (checks errors):**

```c
int rc;

rc = pthread_mutex_lock(&lock);
if (rc != 0) {
    // Handle error - lock acquisition failed!
    fprintf(stderr, "Lock error: %d\n", rc);
    exit(1);
}

counter++;

rc = pthread_mutex_unlock(&lock);
if (rc != 0) {
    // Handle error - unlock failed!
    fprintf(stderr, "Unlock error: %d\n", rc);
    exit(1);
}
```

**Using wrapper functions (cleaner):**

```c
void Pthread_mutex_lock(pthread_mutex_t *mutex) {
    int rc = pthread_mutex_lock(mutex);
    assert(rc == 0);  // Program exits if lock fails
}

void Pthread_mutex_unlock(pthread_mutex_t *mutex) {
    int rc = pthread_mutex_unlock(mutex);
    assert(rc == 0);
}

// Usage (much cleaner):
Pthread_mutex_lock(&lock);
counter++;
Pthread_mutex_unlock(&lock);
```

> **⚠️ Critical Warning**
>
> **Without error checking:**
> - Lock failures go unnoticed
> - Multiple threads may enter critical section simultaneously
> - Silent data corruption occurs
> - Bugs are nearly impossible to debug
>
> **For production code:** Don't just exit on error - implement proper error recovery!

### 4.4. Additional Lock Functions

**Beyond basic lock/unlock:**

```c
int pthread_mutex_trylock(pthread_mutex_t *mutex);

int pthread_mutex_timedlock(pthread_mutex_t *mutex,
                            struct timespec *abs_timeout);
```

**pthread_mutex_trylock:**
- **Behavior:** Attempts to acquire lock, returns immediately whether successful or not
- **Returns:** 0 if lock acquired, error code if already locked
- **Use case:** Non-blocking lock acquisition

```c
int rc = pthread_mutex_trylock(&lock);
if (rc == 0) {
    // Got the lock!
    counter++;
    pthread_mutex_unlock(&lock);
} else {
    // Lock was busy, do something else
    printf("Lock busy, trying later\n");
}
```

**pthread_mutex_timedlock:**
- **Behavior:** Waits for lock up to specified timeout
- **Returns:** 0 if acquired within timeout, error otherwise
- **Use case:** Bounded waiting

```c
struct timespec timeout;
clock_gettime(CLOCK_REALTIME, &timeout);
timeout.tv_sec += 5;  // Wait up to 5 seconds

int rc = pthread_mutex_timedlock(&lock, &timeout);
if (rc == 0) {
    // Got lock within 5 seconds
    counter++;
    pthread_mutex_unlock(&lock);
} else {
    // Timeout or error
    printf("Couldn't acquire lock in 5 seconds\n");
}
```

> **📝 Usage Note**
>
> **Special case:** `pthread_mutex_timedlock` with timeout of zero is equivalent to `pthread_mutex_trylock`.

> **⚠️ When to Use These**
>
> **Generally avoid** trylock and timedlock:
> - Add complexity without much benefit in most cases
> - Can hide design problems (why can't you wait for the lock?)
>
> **Legitimate uses:**
> - Deadlock avoidance strategies (covered in future chapters)
> - Real-time systems with hard timing constraints
> - Optional optimizations (try lock, fall back to non-critical path)

---

## 5. Condition Variables

### 5.1. The Wait and Signal Operations

**For coordination between threads:**

```c
int pthread_cond_wait(pthread_cond_t *cond, pthread_mutex_t *mutex);
int pthread_cond_signal(pthread_cond_t *cond);
```

**In plain English:** Locks prevent concurrent access, but what if one thread needs to wait for another thread to do something? Condition variables provide a way for threads to sleep until signaled that "something changed."

**In technical terms:** Condition variables enable **signaling between threads**. One thread waits for a condition to become true; another signals when that condition changes.

**Key insight:** You always use a condition variable **paired with a lock**.

### 5.2. Using Condition Variables Correctly

**Initialization:**

```c
pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
pthread_cond_t cond = PTHREAD_COND_INITIALIZER;
```

Or dynamically:
```c
pthread_mutex_init(&lock, NULL);
pthread_cond_init(&cond, NULL);  // Don't forget to destroy later!
```

**Waiting side (thread that needs to wait):**

```c
pthread_mutex_lock(&lock);

while (ready == 0) {
    pthread_cond_wait(&cond, &lock);
}

pthread_mutex_unlock(&lock);
```

**Signaling side (thread that changes the condition):**

```c
pthread_mutex_lock(&lock);

ready = 1;
pthread_cond_signal(&cond);

pthread_mutex_unlock(&lock);
```

**How pthread_cond_wait works (this is subtle!):**

```
Before wait:
1. Thread holds the lock
2. Checks condition (ready == 0)
3. Calls pthread_cond_wait(&cond, &lock)

During wait:
4. Atomically: releases lock AND puts thread to sleep
5. Other threads can now acquire the lock
6. Thread sleeps until signaled

After signal:
7. Thread wakes up
8. Re-acquires the lock (before returning!)
9. Returns from pthread_cond_wait
10. Re-checks condition in while loop
```

> **💡 Critical Understanding**
>
> **Why pthread_cond_wait takes a lock parameter:**
>
> The waiting thread must release the lock while sleeping (otherwise no other thread could acquire it to signal!). But it needs to hold the lock when checking the condition. pthread_cond_wait handles this atomically:
> - **Releases lock** when putting thread to sleep
> - **Re-acquires lock** before returning
>
> This prevents race conditions between checking the condition and sleeping.

**Complete example:**

```c
// Shared state
pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
pthread_cond_t cond = PTHREAD_COND_INITIALIZER;
int ready = 0;

// Thread 1: Waiter
void *wait_for_signal(void *arg) {
    pthread_mutex_lock(&lock);

    while (ready == 0) {
        printf("Waiting...\n");
        pthread_cond_wait(&cond, &lock);  // Sleep until signaled
    }

    printf("Condition met! Proceeding.\n");
    pthread_mutex_unlock(&lock);
    return NULL;
}

// Thread 2: Signaler
void *send_signal(void *arg) {
    sleep(2);  // Simulate some work

    pthread_mutex_lock(&lock);
    ready = 1;
    pthread_cond_signal(&cond);  // Wake up waiter
    pthread_mutex_unlock(&lock);

    return NULL;
}
```

**Execution timeline:**

```
Time  Thread 1 (Waiter)           Thread 2 (Signaler)       ready  Lock
────  ─────────────────           ────────────────────       ─────  ────
0     lock()                                                 0      T1
1     check: ready == 0
2     wait() - release lock                                  0      FREE
3     ← sleeping                                             0
4                                 sleep(2 seconds)           0
5                                 lock()                     0      T2
6                                 ready = 1                  1      T2
7                                 signal()                   1      T2
8     ← wakes up
9     ← tries to acquire lock     unlock()                   1      FREE
10    ← acquires lock                                        1      T1
11    check: ready == 1 (loop)
12    proceeds
13    unlock()                                               1      FREE
```

**Why use a while loop instead of if?**

```c
// WRONG - susceptible to spurious wakeups:
if (ready == 0) {
    pthread_cond_wait(&cond, &lock);
}

// CORRECT - handles spurious wakeups:
while (ready == 0) {
    pthread_cond_wait(&cond, &lock);
}
```

> **⚠️ Spurious Wakeups**
>
> Some pthread implementations can wake up a waiting thread **even when no signal occurred**. This is called a **spurious wakeup**. By using a while loop, you re-check the actual condition after waking up, ensuring correctness regardless of spurious wakeups.
>
> **Always use while, never if** - it's safer and the overhead is negligible.

### 5.3. Why Not Use Simple Flags?

**Tempting but wrong approach:**

```c
// Waiting thread
while (ready == 0) {
    ;  // Busy-wait (spin)
}

// Signaling thread
ready = 1;
```

**Why this is terrible:**

**Problem 1: Wastes CPU cycles**
```
CPU Usage while waiting:
With condition variable: ~0% (thread is sleeping)
With busy-wait:         100% (constantly checking flag)
```

**Problem 2: Error-prone**

Research by Xiong et al. [X+10] found that approximately **50% of ad-hoc flag-based synchronizations contained bugs**!

**Common bugs with flags:**
- Missing memory barriers (compiler/CPU reordering)
- Race conditions in check-then-act sequences
- Subtle ordering issues
- Deadlocks from incorrect logic

**The correct approach:**

```c
✅ Use condition variables
❌ Don't use busy-waiting on flags
```

> **📊 Research Finding**
>
> Study: "Ad Hoc Synchronization Considered Harmful" [Xiong et al., 2010]
>
> **Finding:** Analyzed real-world concurrent programs and found that:
> - 50% of hand-rolled synchronizations using flags had bugs
> - Bugs were subtle and difficult to detect
> - Proper primitives (condition variables) had near-zero defect rate
>
> **Lesson:** Don't be clever. Use the well-tested primitives!

> **💡 Insight**
>
> Condition variables may seem confusing at first, but they're solving a genuinely hard problem. The complexity is necessary - the primitive encapsulates subtle race-condition-free signaling logic that's extremely difficult to implement correctly yourself.

---

## 6. Compiling and Running

**Required header:**

```c
#include <pthread.h>
```

**Compilation command:**

```bash
gcc -o program program.c -Wall -pthread
```

**Flag breakdown:**

| Flag | Purpose |
|------|---------|
| `-o program` | Output executable name |
| `-Wall` | Enable all warnings (always use this!) |
| **`-pthread`** | Link with pthread library |

**Complete example workflow:**

```bash
# Write your code
$ cat > mythread.c
#include <stdio.h>
#include <pthread.h>

void *mythread(void *arg) {
    printf("Hello from thread!\n");
    return NULL;
}

int main() {
    pthread_t p;
    pthread_create(&p, NULL, mythread, NULL);
    pthread_join(p, NULL);
    return 0;
}

# Compile with pthread support
$ gcc -o mythread mythread.c -Wall -pthread

# Run
$ ./mythread
Hello from thread!
```

> **⚠️ Common Mistake**
>
> **Forgetting `-pthread` causes cryptic linker errors:**
> ```
> undefined reference to `pthread_create'
> undefined reference to `pthread_join'
> ```
>
> **Solution:** Always include `-pthread` when compiling threaded programs!

**Platform notes:**

```bash
# Linux
gcc -o program program.c -pthread

# macOS (same command)
gcc -o program program.c -pthread

# Older systems might use:
gcc -o program program.c -lpthread  # Explicitly link library
```

> **💻 Modern Build Systems**
>
> For larger projects, use build systems that handle flags automatically:
>
> **CMake:**
> ```cmake
> find_package(Threads REQUIRED)
> target_link_libraries(myprogram Threads::Threads)
> ```
>
> **Makefile:**
> ```make
> CFLAGS = -Wall -pthread
> program: program.c
>     $(CC) $(CFLAGS) -o program program.c
> ```

---

## 7. Thread API Best Practices

**Guidelines for writing robust multi-threaded code:**

### 🎯 Keep It Simple

**Rule:** Any locking or signaling code should be as simple as possible.

**Why:** Tricky thread interactions → bugs. Complex synchronization is extremely difficult to reason about and test.

**Example:**
```c
✅ Simple:
lock(&mutex);
counter++;
unlock(&mutex);

❌ Complex (avoid):
if (trylock(&mutex1)) {
    if (trylock(&mutex2)) {
        complex_operation();
        unlock(&mutex2);
    }
    unlock(&mutex1);
}
```

### 🔗 Minimize Thread Interactions

**Rule:** Limit the number of ways threads interact with each other.

**Why:** Each interaction point is a potential source of race conditions or deadlocks.

**Approach:**
- Use well-tested patterns (producer-consumer, reader-writer, etc.)
- Document synchronization invariants clearly
- Prefer message-passing over shared memory when feasible

### ✅ Initialize Everything

**Rule:** Always initialize locks and condition variables.

**Why:** Failure to initialize leads to code that **sometimes works, sometimes fails** - the worst kind of bug.

```c
✅ Correct:
pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
pthread_cond_t cond = PTHREAD_COND_INITIALIZER;

✅ Also correct:
pthread_mutex_init(&lock, NULL);
pthread_cond_init(&cond, NULL);

❌ Broken:
pthread_mutex_t lock;  // Uninitialized - undefined behavior!
```

### 🔍 Check Return Codes

**Rule:** Check **every** return code from pthread functions.

**Why:** Silent failures lead to bizarre, hard-to-debug behavior.

**The problem:**
```c
pthread_mutex_lock(&lock);  // What if this fails?
counter++;                   // Multiple threads might be here!
pthread_mutex_unlock(&lock);
```

**Solutions:**

```c
// Option 1: Wrapper functions (for simple programs)
void Pthread_mutex_lock(pthread_mutex_t *m) {
    int rc = pthread_mutex_lock(m);
    assert(rc == 0);
}

// Option 2: Proper error handling (for production)
int rc = pthread_mutex_lock(&lock);
if (rc != 0) {
    fprintf(stderr, "Lock failed: %s\n", strerror(rc));
    // Recover or fail gracefully
    return ERROR_CODE;
}
```

### 🗂️ Stack vs Heap Awareness

**Rule:** Never return pointers to stack-allocated data from threads.

**Why:** Stack memory is deallocated when function returns!

```c
❌ Broken:
void *mythread(void *arg) {
    int result = 42;
    return &result;  // DISASTER - pointing to deallocated stack!
}

✅ Correct:
void *mythread(void *arg) {
    int *result = malloc(sizeof(int));
    *result = 42;
    return result;  // Heap allocation persists
}
```

**Key concept:** Each thread has its own stack. Local variables are **private** to that thread. To share data, use:
- Heap allocation (`malloc`)
- Global variables
- Static variables
- Data passed via thread arguments

### 📊 Always Use Condition Variables for Signaling

**Rule:** Use condition variables, not ad-hoc flags.

**Why:** 50% of ad-hoc synchronizations contain bugs [Xiong et al., 2010].

```c
❌ Tempting but wrong:
while (flag == 0) {
    ;  // Busy-wait - wastes CPU, error-prone
}

✅ Correct:
pthread_mutex_lock(&lock);
while (condition == 0) {
    pthread_cond_wait(&cond, &lock);
}
pthread_mutex_unlock(&lock);
```

### 📖 Use the Manual Pages

**Rule:** Read `man pthread_*` for detailed documentation.

**Why:** Man pages contain crucial details about:
- Error codes and their meanings
- Platform-specific behaviors
- Subtle corner cases
- Performance characteristics

```bash
# Essential man pages:
man pthread_create
man pthread_join
man pthread_mutex_init
man pthread_cond_wait
man pthread_attr_init

# List all pthread functions:
man -k pthread
```

> **💡 Summary of Guidelines**
>
> 1. **Simplicity** - Keep synchronization logic simple
> 2. **Minimal interaction** - Limit how threads communicate
> 3. **Initialize** - Always initialize locks/condition variables
> 4. **Check errors** - Every return code, every time
> 5. **Stack awareness** - Don't return pointers to stack data
> 6. **Each thread has its own stack** - Local variables are private
> 7. **Use proper primitives** - Condition variables, not flags
> 8. **Read the manual** - Man pages are your friend

---

## 8. Summary

**What we've covered:**

### 🔧 Thread Creation

```c
pthread_create(&thread, NULL, start_function, arg);
```

- Create new execution streams with their own stacks
- Pass arguments via `void*` for flexibility
- Function pointers specify where thread starts executing

### 🔗 Thread Completion

```c
pthread_join(thread, &return_value);
```

- Wait for thread to finish
- Retrieve return values
- ⚠️ Never return pointers to stack-allocated data!
- Use join for parallel algorithms, skip for long-lived servers

### 🔒 Locks (Mutual Exclusion)

```c
pthread_mutex_lock(&mutex);
// Critical section
pthread_mutex_unlock(&mutex);
```

- Prevent concurrent access to shared data
- Always initialize: `PTHREAD_MUTEX_INITIALIZER` or `pthread_mutex_init()`
- Always check return codes!
- Trylock/timedlock exist but should generally be avoided

### 📡 Condition Variables (Coordination)

```c
// Waiter:
while (condition == 0) {
    pthread_cond_wait(&cond, &lock);
}

// Signaler:
condition = 1;
pthread_cond_signal(&cond);
```

- Enable threads to wait for events
- Always paired with a lock
- Always use `while` loop, never `if`
- Handles spurious wakeups correctly
- Never use busy-waiting on flags instead!

### 💻 Compilation

```bash
gcc -o program program.c -Wall -pthread
```

**Key insights:**

> **🎯 The Essential Toolkit**
>
> You don't need hundreds of functions to write robust concurrent programs. Just master:
> - Thread creation/joining
> - Locks for mutual exclusion
> - Condition variables for coordination
> - Careful attention to initialization and error handling
>
> The hard part isn't the API - it's the **logic** of designing correct concurrent algorithms!

> **📚 Looking Ahead**
>
> This chapter provided the **mechanics** - how to call the functions. The following chapters provide the **understanding**:
> - How locks work internally
> - When and why to use condition variables
> - Common patterns and idioms
> - Pitfalls like deadlock and how to avoid them
>
> Think of this chapter as your reference card while you learn the deeper concepts.

**Final wisdom:**

```
┌─────────────────────────────────────────────────┐
│  "The pthread API is simple.                    │
│   Concurrent programming is hard.               │
│   The API is just the beginning."               │
└─────────────────────────────────────────────────┘
```

**The real journey:**
- Understanding race conditions
- Reasoning about thread interleavings
- Designing deadlock-free systems
- Building efficient concurrent data structures

The API is your toolbox. The next chapters teach you how to use it wisely.

---

**Previous:** [Chapter 1: Concurrency Introduction](chapter1-concurrency-introduction.md) | **Next:** [Chapter 3: Locks](chapter3-locks.md)
