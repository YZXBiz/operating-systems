# 🧵 Concurrency

_Master concurrent programming: threads, locks, synchronization, and beyond_

---

## 📖 About This Section

Concurrency is one of the most challenging and important topics in operating systems and systems programming. These chapters transform complex concurrent programming concepts into understandable, practical knowledge through:

- **Progressive learning** - Each chapter builds naturally on previous concepts
- **Visual execution traces** - See exactly how race conditions and synchronization work
- **Real-world examples** - Learn from actual bugs in MySQL, Apache, Mozilla, and OpenOffice
- **Practical API reference** - Complete pthread API coverage with working examples

> **💡 Why Concurrency Matters**
>
> Modern systems are fundamentally concurrent: multi-core CPUs, web servers handling thousands of requests, mobile apps running background tasks, databases managing simultaneous transactions. Understanding concurrency isn't optional - it's essential for building correct, performant software.

---

## 🗺️ Learning Path

### **Foundations** (Chapters 1-2)

**[Chapter 1: Concurrency Introduction](chapter1-concurrency-introduction.md)** (27K)
- What are threads and why do we need them?
- Understanding race conditions and shared data
- The fundamental challenge: non-deterministic execution
- Introduction to atomicity and mutual exclusion
- **Key concepts**: threads, race conditions, critical sections, mutual exclusion

**[Chapter 2: Thread API](chapter2-thread-api.md)** (35K)
- Complete pthread API reference
- Thread creation and joining
- Argument passing and return values
- Lock basics (mutex operations)
- Condition variable introduction
- **Use case**: Essential reference for writing threaded code

---

### **Synchronization Primitives** (Chapters 3-6)

**[Chapter 3: Locks](chapter3-locks.md)** (40K)
- Building locks from first principles
- Hardware support: test-and-set, compare-and-swap, fetch-and-add
- Spin locks vs blocking locks
- Performance optimization techniques
- **Key insight**: Understanding how synchronization primitives are built

**[Chapter 4: Concurrent Data Structures](chapter4-concurrent-data-structures.md)** (31K)
- Applying locks to real data structures
- Concurrent counters (simple vs scalable)
- Concurrent linked lists and queues
- Concurrent hash tables
- Fine-grained vs coarse-grained locking
- **Key tradeoff**: Correctness vs performance

**[Chapter 5: Condition Variables](chapter5-condition-variables.md)** (23K)
- Coordination between threads
- Parent/child waiting patterns
- Producer/consumer problem
- Why "while" not "if" (critical!)
- Covering conditions
- **Key pattern**: Waiting for state changes

**[Chapter 6: Semaphores](chapter6-semaphores.md)** (43K)
- Dijkstra's semaphore abstraction
- Binary semaphores as locks
- Semaphores for ordering
- Producer/consumer with semaphores
- Reader-writer locks
- Dining philosophers problem
- **Alternative approach**: Unified primitive for synchronization

---

### **Practical Wisdom** (Chapters 7-8)

**[Chapter 7: Common Concurrency Problems](chapter7-common-problems.md)** (36K)
- Real-world bug analysis (Lu et al. study)
- Atomicity violations
- Order violations
- Deadlock: causes, prevention, avoidance, detection
- **War stories**: Learn from production bugs

**[Chapter 8: Event-Based Concurrency](chapter8-event-based.md)** (37K)
- Alternative to thread-based concurrency
- Event loops and non-blocking I/O
- select() and poll() system calls
- Asynchronous I/O patterns
- When to use events vs threads
- **Different paradigm**: Single-threaded concurrency

---

## 🎯 Quick Navigation

### By Topic

**Getting Started**
- [What are threads?](chapter1-concurrency-introduction.md#2-what-is-a-thread)
- [Why use threads?](chapter1-concurrency-introduction.md#3-why-use-threads)
- [Creating threads](chapter2-thread-api.md#2-thread-creation)

**Synchronization**
- [Understanding locks](chapter3-locks.md#1-locks-the-basic-idea)
- [Using condition variables](chapter5-condition-variables.md#2-definition-and-routines)
- [Working with semaphores](chapter6-semaphores.md#2-semaphores-a-definition)

**Common Patterns**
- [Producer/Consumer](chapter5-condition-variables.md#3-the-producerconsumer-problem)
- [Reader/Writer](chapter6-semaphores.md#5-reader-writer-locks)
- [Dining Philosophers](chapter6-semaphores.md#6-the-dining-philosophers)

**Debugging & Problems**
- [Race conditions explained](chapter1-concurrency-introduction.md#5-the-danger-shared-data)
- [Deadlock prevention](chapter7-common-problems.md#32-deadlock-prevention)
- [Common bug patterns](chapter7-common-problems.md#2-non-deadlock-bugs)

### By Skill Level

**Beginner** (Start here if new to concurrency)
1. [Chapter 1: Introduction](chapter1-concurrency-introduction.md)
2. [Chapter 2: Thread API](chapter2-thread-api.md) - Sections 1-3
3. [Chapter 3: Locks](chapter3-locks.md) - Sections 1-2
4. [Chapter 5: Condition Variables](chapter5-condition-variables.md) - Section 1

**Intermediate** (Building real concurrent systems)
1. [Chapter 4: Concurrent Data Structures](chapter4-concurrent-data-structures.md)
2. [Chapter 5: Condition Variables](chapter5-condition-variables.md) - Complete
3. [Chapter 7: Common Problems](chapter7-common-problems.md)

**Advanced** (Deep understanding and alternatives)
1. [Chapter 3: Locks](chapter3-locks.md) - Complete implementation details
2. [Chapter 6: Semaphores](chapter6-semaphores.md) - Complete
3. [Chapter 8: Event-Based Concurrency](chapter8-event-based.md)

---

## 💡 Key Insights

### The Fundamental Challenge
Concurrency introduces **non-determinism** - the same program can produce different results on different runs. This violates our expectation that computers are deterministic machines.

### Two Core Problems
1. **Mutual Exclusion** - Preventing concurrent access to shared resources (solved by locks/semaphores)
2. **Coordination** - Waiting for conditions to become true (solved by condition variables/semaphores)

### Three Critical Rules
1. **Always hold a lock** when accessing shared data
2. **Always use while loops** (not if statements) with condition variables
3. **Avoid deadlock** through consistent lock ordering or other strategies

### The Tradeoff
- **Coarse-grained locking**: Simple, correct, but poor parallelism
- **Fine-grained locking**: Maximum parallelism, but complex and error-prone
- **Lock-free**: Ultimate performance, ultimate complexity

---

## 🔧 Practical Resources

### Essential APIs (POSIX Threads)

**Thread Management**
```c
pthread_create()   // Create new thread
pthread_join()     // Wait for thread completion
```

**Mutual Exclusion**
```c
pthread_mutex_init()      // Initialize lock
pthread_mutex_lock()      // Acquire lock
pthread_mutex_unlock()    // Release lock
pthread_mutex_destroy()   // Clean up lock
```

**Coordination**
```c
pthread_cond_init()       // Initialize condition variable
pthread_cond_wait()       // Wait for condition
pthread_cond_signal()     // Wake one waiter
pthread_cond_broadcast()  // Wake all waiters
pthread_cond_destroy()    // Clean up condition variable
```

**Semaphores**
```c
sem_init()     // Initialize semaphore
sem_wait()     // Decrement (P operation)
sem_post()     // Increment (V operation)
sem_destroy()  // Clean up semaphore
```

### Compilation
```bash
gcc -o program program.c -Wall -pthread
```

### Debugging Tools
- **gdb** - Debugger with thread support
- **valgrind --tool=helgrind** - Race condition detector
- **valgrind --tool=drd** - Thread error detector
- **ThreadSanitizer** - Dynamic race detector

---

## 📚 Chapter Details

| Chapter | Title | Size | Focus | Key Takeaway |
|---------|-------|------|-------|--------------|
| 1 | [Concurrency Introduction](chapter1-concurrency-introduction.md) | 27K | Foundations | Why concurrency is hard |
| 2 | [Thread API](chapter2-thread-api.md) | 35K | Reference | How to use pthread |
| 3 | [Locks](chapter3-locks.md) | 40K | Implementation | Building synchronization |
| 4 | [Concurrent Data Structures](chapter4-concurrent-data-structures.md) | 31K | Application | Using locks correctly |
| 5 | [Condition Variables](chapter5-condition-variables.md) | 23K | Coordination | Waiting and signaling |
| 6 | [Semaphores](chapter6-semaphores.md) | 43K | Alternative | Unified primitive |
| 7 | [Common Problems](chapter7-common-problems.md) | 36K | Pitfalls | Learning from bugs |
| 8 | [Event-Based Concurrency](chapter8-event-based.md) | 37K | Alternative | Different paradigm |

**Total: 272 KB of learnable content**

---

## 🎓 Learning Outcomes

After completing this section, you will:

✅ **Understand** how threads work and why they're needed
✅ **Recognize** race conditions and other concurrency bugs
✅ **Use** locks, condition variables, and semaphores correctly
✅ **Design** thread-safe data structures
✅ **Debug** concurrent programs systematically
✅ **Avoid** common pitfalls like deadlock
✅ **Choose** between threading models (threads vs events)
✅ **Reason** about concurrent execution confidently

---

## ⚠️ Common Pitfalls to Avoid

1. **Using `if` instead of `while` with condition variables** - Always recheck conditions!
2. **Returning pointers to stack variables** from threads - Use heap allocation
3. **Forgetting to initialize locks/condition variables** - Leads to undefined behavior
4. **Inconsistent lock ordering** - Causes deadlock
5. **Spinning instead of blocking** - Wastes CPU cycles
6. **Racing on flag variables** - Use proper synchronization primitives
7. **Not checking return codes** - Errors fail silently
8. **Holding locks too long** - Destroys parallelism

---

## 🚀 Next Steps

**After mastering concurrency, explore:**
- **Persistence** - File systems, storage, crash consistency
- **Virtualization** - Processes, scheduling, memory management
- **Distributed Systems** - Concurrency across machines
- **Lock-Free Programming** - Advanced synchronization techniques

---

## 📖 Historical Context

The foundations of concurrent programming were laid by pioneers like:

- **Edsger Dijkstra** - Semaphores, mutual exclusion, THE operating system
- **Tony Hoare** - Monitors, CSP (Communicating Sequential Processes)
- **Leslie Lamport** - Logical clocks, distributed systems theory
- **Maurice Herlihy** - Transactional memory, lock-free algorithms

Their work in the 1960s-1980s established the principles we still use today.

---

## 🔗 Related Topics

- [Virtualization Section](../virtualization/) - Understanding process scheduling
- Operating System kernel design
- Database transaction processing (ACID properties)
- Distributed consensus algorithms (Paxos, Raft)
- Modern async/await patterns in high-level languages

---

_Concurrency is challenging but essential. Take your time, work through the examples, and remember: understanding these concepts deeply will make you a significantly better systems programmer._

**Start here:** [Chapter 1: Concurrency Introduction →](chapter1-concurrency-introduction.md)
