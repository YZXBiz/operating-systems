# Chapter 5: Condition Variables

## Table of Contents

1. [Introduction: The Waiting Problem](#1-introduction-the-waiting-problem)
2. [What Are Condition Variables?](#2-what-are-condition-variables)
   - 2.1. [Definition and Core Operations](#21-definition-and-core-operations)
   - 2.2. [Why We Need Both Locks AND Condition Variables](#22-why-we-need-both-locks-and-condition-variables)
3. [Parent Waiting for Child: A Simple Example](#3-parent-waiting-for-child-a-simple-example)
   - 3.1. [The Naive Spinning Approach](#31-the-naive-spinning-approach)
   - 3.2. [The Correct Solution with Condition Variables](#32-the-correct-solution-with-condition-variables)
   - 3.3. [Common Mistakes and Why They Fail](#33-common-mistakes-and-why-they-fail)
4. [The Producer/Consumer Problem](#4-the-producerconsumer-problem)
   - 4.1. [Problem Setup and Real-World Examples](#41-problem-setup-and-real-world-examples)
   - 4.2. [Broken Solution #1: Single CV with If Statement](#42-broken-solution-1-single-cv-with-if-statement)
   - 4.3. [Broken Solution #2: Single CV with While Loop](#43-broken-solution-2-single-cv-with-while-loop)
   - 4.4. [The Correct Solution: Two CVs and While Loops](#44-the-correct-solution-two-cvs-and-while-loops)
   - 4.5. [Scaling to Multiple Buffers](#45-scaling-to-multiple-buffers)
5. [Covering Conditions](#5-covering-conditions)
6. [Summary](#6-summary)

---

## 1. Introduction: The Waiting Problem

**In plain English:** Sometimes one thread needs to wait for another thread to finish something before it can continue. Spinning in a loop checking "are you done yet?" wastes CPU cycles.

**In technical terms:** Locks provide mutual exclusion, but they don't provide a mechanism for threads to efficiently wait for a condition to become true. We need a synchronization primitive that puts threads to sleep while waiting and wakes them when the condition changes.

**Why it matters:** Without condition variables, threads would waste CPU time spinning, or we'd need complex polling mechanisms that are both inefficient and hard to get right.

### 🎯 The Core Challenge

**The Crux:** How can a thread efficiently wait for a condition to become true without wasting CPU cycles spinning?

Consider this common scenario: a parent thread creates a child thread and wants to wait for it to complete before continuing. How should this waiting be implemented?

```c
void *child(void *arg) {
    printf("child\n");
    // XXX how to indicate we are done?
    return NULL;
}

int main(int argc, char *argv[]) {
    printf("parent: begin\n");
    pthread_t c;
    Pthread_create(&c, NULL, child, NULL);
    // XXX how to wait for child?
    printf("parent: end\n");
    return 0;
}
```

**Desired output:**
```
parent: begin
child
parent: end
```

> **💡 Insight**
>
> Locks solve the "mutual exclusion" problem (only one thread in critical section), but they don't solve the "waiting for a condition" problem. You need both primitives for complete synchronization.

---

## 2. What Are Condition Variables?

**In plain English:** A condition variable is like a waiting room where threads can sleep until they're notified that something they care about has changed.

**In technical terms:** A condition variable is an explicit queue that threads can put themselves on when some state condition is not as desired. Other threads can then wake one or more waiting threads when they change that state.

**Why it matters:** This allows threads to sleep efficiently instead of spinning, and enables elegant solutions to complex synchronization problems.

### 2.1. Definition and Core Operations

A condition variable has two primary operations:

**wait()** - Put yourself to sleep and release the lock (atomically)
```c
pthread_cond_wait(pthread_cond_t *c, pthread_mutex_t *m);
```

**signal()** - Wake up one sleeping thread
```c
pthread_cond_signal(pthread_cond_t *c);
```

**broadcast()** - Wake up all sleeping threads
```c
pthread_cond_broadcast(pthread_cond_t *c);
```

### 2.2. Why We Need Both Locks AND Condition Variables

**The pattern you'll see everywhere:**

```
Lock the mutex
Check condition with while loop
If condition not met: wait (releases lock, sleeps, reacquires lock on wake)
Do the work
Signal others who might be waiting
Unlock the mutex
```

**Visual Flow:**

```
Thread A (Waiting)              Thread B (Signaling)
─────────────────              ────────────────────
1. Lock mutex           →
2. Check condition
3. Condition false
4. Call wait()
   - Release lock       →      5. Lock mutex (gets it!)
   - Go to sleep               6. Change state
                               7. Signal condition
   - Wake up            ←      8. Unlock mutex
   - Reacquire lock
5. Re-check condition
6. Condition now true
7. Do work
8. Unlock mutex
```

> **⚠️ Critical Rule**
>
> The wait() function **atomically** releases the lock and puts the thread to sleep. This prevents race conditions where the state changes between checking the condition and going to sleep.

---

## 3. Parent Waiting for Child: A Simple Example

Let's solve the parent-child waiting problem step by step, learning from mistakes along the way.

### 3.1. The Naive Spinning Approach

**First attempt: Use a shared variable and spin**

```c
volatile int done = 0;

void *child(void *arg) {
    printf("child\n");
    done = 1;
    return NULL;
}

int main(int argc, char *argv[]) {
    printf("parent: begin\n");
    pthread_t c;
    Pthread_create(&c, NULL, child, NULL);
    while (done == 0)
        ; // spin - wasteful!
    printf("parent: end\n");
    return 0;
}
```

**Why this fails:**
- ❌ Parent wastes CPU cycles spinning
- ❌ Inefficient - parent does nothing useful while waiting
- ❌ On single CPU, child can't even run while parent spins

### 3.2. The Correct Solution with Condition Variables

```c
int done = 0;
pthread_mutex_t m = PTHREAD_MUTEX_INITIALIZER;
pthread_cond_t c = PTHREAD_COND_INITIALIZER;

void thr_exit() {
    Pthread_mutex_lock(&m);
    done = 1;
    Pthread_cond_signal(&c);
    Pthread_mutex_unlock(&m);
}

void *child(void *arg) {
    printf("child\n");
    thr_exit();
    return NULL;
}

void thr_join() {
    Pthread_mutex_lock(&m);
    while (done == 0)
        Pthread_cond_wait(&c, &m);
    Pthread_mutex_unlock(&m);
}

int main(int argc, char *argv[]) {
    printf("parent: begin\n");
    pthread_t p;
    Pthread_create(&p, NULL, child, NULL);
    thr_join();
    printf("parent: end\n");
    return 0;
}
```

**How this works - Two scenarios:**

**Scenario 1: Parent runs first**
1. Parent calls `thr_join()`, acquires lock
2. Checks `done == 0` (true), calls `wait()`
3. `wait()` releases lock and puts parent to sleep
4. Child runs, acquires lock, sets `done = 1`, signals, unlocks
5. Parent wakes, reacquires lock, rechecks condition, continues

**Scenario 2: Child runs first**
1. Child calls `thr_exit()`, acquires lock
2. Sets `done = 1`, signals (no one waiting), unlocks
3. Parent runs, calls `thr_join()`, acquires lock
4. Checks `done == 0` (false!), skips wait, continues

> **💡 Insight**
>
> The state variable (`done`) is crucial. It records what happened even if no one was waiting. Without it, signals are lost if sent when no one is sleeping.

### 3.3. Common Mistakes and Why They Fail

**Mistake #1: No state variable**

```c
void thr_exit() {
    Pthread_mutex_lock(&m);
    Pthread_cond_signal(&c);  // Signal what?
    Pthread_mutex_unlock(&m);
}

void thr_join() {
    Pthread_mutex_lock(&m);
    Pthread_cond_wait(&c, &m);  // Wait for what?
    Pthread_mutex_unlock(&m);
}
```

**Why this fails:**
- If child runs first and signals, no one is waiting
- Parent then waits forever - the signal was lost
- No memory of what happened

**Mistake #2: No lock around signal/wait**

```c
void thr_exit() {
    done = 1;
    Pthread_cond_signal(&c);  // No lock!
}

void thr_join() {
    if (done == 0)
        Pthread_cond_wait(&c);  // No lock!
}
```

**Why this fails - Race condition:**
1. Parent checks `done == 0` (true)
2. Parent about to call `wait()` but gets interrupted
3. Child sets `done = 1` and signals
4. Parent resumes and calls `wait()` - sleeps forever!

**The problem:** Between checking the condition and waiting, the state changed and the signal was lost.

> **🔒 Rule: Always Hold the Lock**
>
> Always hold the lock when calling `signal()` or `wait()`. The `wait()` function requires it (and releases it atomically). For `signal()`, it's technically not always required, but it's simpler and safer to always do it.

---

## 4. The Producer/Consumer Problem

### 4.1. Problem Setup and Real-World Examples

**In plain English:** Some threads produce data and put it in a buffer. Other threads consume data from the buffer. How do we coordinate them so producers don't overflow the buffer and consumers don't try to consume from an empty buffer?

**In technical terms:** The bounded-buffer problem requires synchronization between producer and consumer threads accessing a shared, fixed-size buffer. This is one of the classic synchronization problems in computer science.

**Real-world examples:**

🌐 **Web server:** Producer threads accept HTTP requests and put them in a work queue. Consumer threads pull requests from the queue and process them.

🔄 **Unix pipes:** When you run `grep foo file.txt | wc -l`, grep is the producer writing to a pipe buffer, and wc is the consumer reading from it.

📊 **Data processing:** Log aggregation systems where producers collect logs and consumers process them.

**Basic buffer structure (single slot):**

```c
int buffer;
int count = 0;  // 0 = empty, 1 = full

void put(int value) {
    assert(count == 0);  // Must be empty
    count = 1;
    buffer = value;
}

int get() {
    assert(count == 1);  // Must be full
    count = 0;
    return buffer;
}
```

**Basic producer/consumer threads:**

```c
void *producer(void *arg) {
    int i;
    for (i = 0; i < loops; i++) {
        put(i);
    }
}

void *consumer(void *arg) {
    int i;
    while (1) {
        int tmp = get();
        printf("%d\n", tmp);
    }
}
```

**The challenge:** `put()` and `get()` have critical sections. We need synchronization so:
- Producers only put when buffer is empty
- Consumers only get when buffer is full
- No race conditions

### 4.2. Broken Solution #1: Single CV with If Statement

**First attempt:**

```c
cond_t cond;
mutex_t mutex;

void *producer(void *arg) {
    int i;
    for (i = 0; i < loops; i++) {
        Pthread_mutex_lock(&mutex);
        if (count == 1)                      // If full, wait
            Pthread_cond_wait(&cond, &mutex);
        put(i);
        Pthread_cond_signal(&cond);
        Pthread_mutex_unlock(&mutex);
    }
}

void *consumer(void *arg) {
    int i;
    for (i = 0; i < loops; i++) {
        Pthread_mutex_lock(&mutex);
        if (count == 0)                      // If empty, wait
            Pthread_cond_wait(&cond, &mutex);
        int tmp = get();
        Pthread_cond_signal(&cond);
        Pthread_mutex_unlock(&mutex);
        printf("%d\n", tmp);
    }
}
```

**This works with 1 producer + 1 consumer, but breaks with multiple threads!**

**The fatal race with 2 consumers + 1 producer:**

```
Time  Tc1           Tc2           Tp            Count  State
─────────────────────────────────────────────────────────────
1     Lock
      count==0
      Wait(sleep)                              0      Tc1 sleeping
2                                Lock
                                  count==0
                                  put()
                                  signal()      1      Tc1 woken (ready)
                                  unlock
                                  Lock
                                  count==1
                                  Wait(sleep)   1      Tp sleeping, Tc1 ready
3                   Lock
                    count==1 (!)
                    get()
                    unlock         0             Tc2 consumed it!
4     Wake up
      get()                       0             CRASH! Buffer empty!
      assert fails
```

**What went wrong:**
1. Tc1 was woken when buffer had data
2. But before Tc1 ran, Tc2 snuck in and consumed it
3. Tc1 woke up to an empty buffer

> **⚠️ Mesa Semantics**
>
> Signaling a thread is just a **hint** that the state has changed. By the time the woken thread runs, the state might have changed again. This is called "Mesa semantics" and is used by virtually every real system.

### 4.3. Broken Solution #2: Single CV with While Loop

**Second attempt: Change if to while**

```c
void *producer(void *arg) {
    int i;
    for (i = 0; i < loops; i++) {
        Pthread_mutex_lock(&mutex);
        while (count == 1)                    // While, not if!
            Pthread_cond_wait(&cond, &mutex);
        put(i);
        Pthread_cond_signal(&cond);
        Pthread_mutex_unlock(&mutex);
    }
}

void *consumer(void *arg) {
    int i;
    for (i = 0; i < loops; i++) {
        Pthread_mutex_lock(&mutex);
        while (count == 0)                    // While, not if!
            Pthread_cond_wait(&cond, &mutex);
        int tmp = get();
        Pthread_cond_signal(&cond);
        Pthread_mutex_unlock(&mutex);
        printf("%d\n", tmp);
    }
}
```

**Progress! The while loop fixes the first race:**
- When Tc1 wakes up, it rechecks the condition
- If buffer is empty (because Tc2 took it), Tc1 goes back to sleep
- ✅ No more crashes

**But there's a second problem - deadlock with 2 consumers + 1 producer:**

```
Time  Tc1           Tc2           Tp            Count  State
─────────────────────────────────────────────────────────────
1     Lock
      count==0
      Wait(sleep)                              0      Tc1 sleeping
2                   Lock
                    count==0
                    Wait(sleep)                0      Tc1, Tc2 sleeping
3                                Lock
                                  count==0
                                  put()
                                  signal()      1      Wakes Tc1
                                  unlock
                                  Lock
                                  count==1
                                  Wait(sleep)   1      All sleeping!
4     Wake
      Recheck
      count==1
      get()
      signal()      0                          Wakes... Tc2 (oops!)
5                   Wake
                    Recheck
                    count==0
                    Wait(sleep)   0             All asleep forever!
```

**What went wrong:**
1. Consumer Tc1 consumed the data
2. Tc1 signaled, but woke **another consumer** (Tc2)
3. Tc2 found buffer empty, went back to sleep
4. Producer Tp has data to put but is sleeping
5. **All three threads sleeping forever - deadlock!**

> **💡 Insight**
>
> The problem is directional: a consumer should wake **producers**, not other consumers. A producer should wake **consumers**, not other producers. With a single condition variable, we can't control who gets woken.

### 4.4. The Correct Solution: Two CVs and While Loops

**Use two condition variables for directional signaling:**

```c
cond_t empty, fill;  // Two CVs!
mutex_t mutex;

void *producer(void *arg) {
    int i;
    for (i = 0; i < loops; i++) {
        Pthread_mutex_lock(&mutex);
        while (count == 1)
            Pthread_cond_wait(&empty, &mutex);  // Wait on 'empty'
        put(i);
        Pthread_cond_signal(&fill);              // Signal 'fill'
        Pthread_mutex_unlock(&mutex);
    }
}

void *consumer(void *arg) {
    int i;
    for (i = 0; i < loops; i++) {
        Pthread_mutex_lock(&mutex);
        while (count == 0)
            Pthread_cond_wait(&fill, &mutex);   // Wait on 'fill'
        int tmp = get();
        Pthread_cond_signal(&empty);            // Signal 'empty'
        Pthread_mutex_unlock(&mutex);
        printf("%d\n", tmp);
    }
}
```

**How the two CVs solve the problem:**

```
Condition Variable      Who Waits           Who Signals
──────────────────────────────────────────────────────
empty                   Producers           Consumers
                        (waiting for        (signaling that
                         buffer to          buffer is now
                         be empty)          empty)

fill                    Consumers           Producers
                        (waiting for        (signaling that
                         buffer to          buffer is now
                         be full)           full)
```

**Now the scenario from before:**

```
Time  Tc1           Tc2           Tp
─────────────────────────────────────────────────
1     Lock
      count==0
      Wait(fill)                               Tc1 sleeps on 'fill'
2                   Lock
                    count==0
                    Wait(fill)                 Tc2 sleeps on 'fill'
3                                Lock
                                  put()
                                  Signal(fill)  Wakes Tc1 or Tc2
                                  unlock
                                  Lock
                                  count==1
                                  Wait(empty)   Tp sleeps on 'empty'
4     Wake
      get()
      Signal(empty) ✅                         Wakes Tp (correct!)
```

✅ Consumer can only wake producers (via `empty`)
✅ Producer can only wake consumers (via `fill`)
✅ No more deadlock!

> **🎓 Critical Pattern**
>
> **Always use while loops, not if statements, for condition checks.** Even when it seems unnecessary, it's always correct and protects against:
> 1. Multiple threads racing for the same resource
> 2. Spurious wakeups (implementation artifacts where threads wake without signal)
> 3. Future code changes

### 4.5. Scaling to Multiple Buffers

The single-buffer solution works but is inefficient. With multiple buffer slots:
- Producers can produce multiple items before sleeping
- Consumers can consume multiple items before sleeping
- Multiple producers/consumers can work concurrently

**Updated buffer structure (circular queue):**

```c
int buffer[MAX];
int fill_ptr = 0;
int use_ptr = 0;
int count = 0;

void put(int value) {
    buffer[fill_ptr] = value;
    fill_ptr = (fill_ptr + 1) % MAX;  // Circular wrap
    count++;
}

int get() {
    int tmp = buffer[use_ptr];
    use_ptr = (use_ptr + 1) % MAX;    // Circular wrap
    count--;
    return tmp;
}
```

**Updated synchronization (only conditions change):**

```c
cond_t empty, fill;
mutex_t mutex;

void *producer(void *arg) {
    int i;
    for (i = 0; i < loops; i++) {
        Pthread_mutex_lock(&mutex);
        while (count == MAX)                  // Changed: check if full
            Pthread_cond_wait(&empty, &mutex);
        put(i);
        Pthread_cond_signal(&fill);
        Pthread_mutex_unlock(&mutex);
    }
}

void *consumer(void *arg) {
    int i;
    for (i = 0; i < loops; i++) {
        Pthread_mutex_lock(&mutex);
        while (count == 0)                    // Still check if empty
            Pthread_cond_wait(&fill, &mutex);
        int tmp = get();
        Pthread_cond_signal(&empty);
        Pthread_mutex_unlock(&mutex);
        printf("%d\n", tmp);
    }
}
```

**Benefits:**
- 🚀 Fewer context switches (threads don't sleep as often)
- ⚡ True concurrency (multiple producers/consumers working in parallel)
- 📊 Better throughput (buffer acts as elastic cushion between fast/slow threads)

---

## 5. Covering Conditions

**In plain English:** Sometimes you don't know which specific waiting thread should be woken up, so you need to wake them all and let them figure it out.

**In technical terms:** A covering condition uses broadcast instead of signal to wake all waiting threads. This conservatively covers all cases where a thread might need to wake, at the cost of extra wakeups.

**Example: Memory allocation**

```c
int bytesLeft = MAX_HEAP_SIZE;
cond_t c;
mutex_t m;

void *allocate(int size) {
    Pthread_mutex_lock(&m);
    while (bytesLeft < size)
        Pthread_cond_wait(&c, &m);
    void *ptr = ...; // get memory from heap
    bytesLeft -= size;
    Pthread_mutex_unlock(&m);
    return ptr;
}

void free(void *ptr, int size) {
    Pthread_mutex_lock(&m);
    bytesLeft += size;
    Pthread_cond_signal(&c);  // ⚠️ Problem: whom to signal?
    Pthread_mutex_unlock(&m);
}
```

**The problem scenario:**

```
Thread A: allocate(100) - waiting
Thread B: allocate(10)  - waiting
Thread C: free(50)      - signals one thread

If C wakes A: A still can't run (only 50 bytes free, needs 100)
             A goes back to sleep
             B never wakes up - but B could run!
```

**Solution: Use broadcast**

```c
void free(void *ptr, int size) {
    Pthread_mutex_lock(&m);
    bytesLeft += size;
    Pthread_cond_broadcast(&c);  // ✅ Wake everyone!
    Pthread_mutex_unlock(&m);
}
```

**How broadcast works:**
1. Wakes all waiting threads
2. Each thread reacquires lock (one at a time)
3. Each thread rechecks condition
4. Threads that can proceed do so
5. Threads that can't go back to sleep

**Trade-offs:**

✅ **Pros:**
- Correct: guaranteed to wake any thread that should wake
- Simple: don't need to track which thread needs what

❌ **Cons:**
- Performance: may wake many threads unnecessarily
- Thundering herd: all threads wake, compete for lock, most go back to sleep

> **⚠️ Design Warning**
>
> If you find yourself needing broadcast where signal should work, you probably have a bug. Broadcast is for cases like memory allocation where you genuinely don't know which thread to wake. Don't use it to paper over synchronization bugs!

---

## 6. Summary

**Key concepts mastered:**

🎯 **Condition Variables** - Explicit queues for threads to wait on conditions, enabling efficient sleeping instead of spinning

🔒 **The Essential Pattern:**
```
Lock mutex
while (condition not met)
    wait(cv, mutex)
Do work
signal or broadcast
Unlock mutex
```

⚡ **Critical Rules:**
1. **Always use while loops, never if** - protects against races and spurious wakeups
2. **Always hold lock when calling wait/signal** - prevents race conditions
3. **Always use state variables with CVs** - records what happened for late arrivals
4. **Use signal for one, broadcast for all** - choose based on your needs

📊 **Common Patterns:**
- **Parent/child waiting** - One CV, state variable tracks completion
- **Producer/consumer** - Two CVs for directional signaling (empty/fill)
- **Covering conditions** - Broadcast when you can't predict who to wake

> **💡 Final Insight**
>
> Condition variables complement locks: locks provide mutual exclusion, condition variables provide efficient waiting. Together, they form the foundation for solving complex synchronization problems. Master these patterns, always use while loops, and you'll write correct concurrent code.

---

**Previous:** [Chapter 4: Concurrent Data Structures](chapter4-concurrent-data-structures.md) | **Next:** [Chapter 6: Semaphores](chapter6-semaphores.md)
