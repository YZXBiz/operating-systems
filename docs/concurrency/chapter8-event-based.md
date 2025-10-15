# 8. Event-based Concurrency (Advanced)

**In plain English:** Event-based concurrency is like a single chef handling multiple orders by constantly checking what's ready to cook next, instead of hiring multiple chefs who might bump into each other in the kitchen.

**In technical terms:** Event-based concurrency is a programming model that handles concurrent operations using a single-threaded event loop that processes events as they arrive, rather than using multiple threads.

**Why it matters:** This approach gives you complete control over scheduling, eliminates race conditions and deadlocks, and is the foundation of modern server frameworks like Node.js and GUI applications.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [The Basic Idea: An Event Loop](#2-the-basic-idea-an-event-loop)
   - 2.1. [The Event Loop Structure](#21-the-event-loop-structure)
   - 2.2. [How Event Handling Works](#22-how-event-handling-works)
3. [Important APIs: select() and poll()](#3-important-apis-select-and-poll)
   - 3.1. [Understanding select()](#31-understanding-select)
   - 3.2. [Practical Example Using select()](#32-practical-example-using-select)
4. [Why Simpler? No Locks Needed](#4-why-simpler-no-locks-needed)
5. [The Blocking Problem](#5-the-blocking-problem)
   - 5.1. [Why Blocking Kills Event-Based Servers](#51-why-blocking-kills-event-based-servers)
   - 5.2. [Blocking vs Non-Blocking Interfaces](#52-blocking-vs-non-blocking-interfaces)
6. [The Solution: Asynchronous I/O](#6-the-solution-asynchronous-io)
   - 6.1. [How Asynchronous I/O Works](#61-how-asynchronous-io-works)
   - 6.2. [Using the AIO API](#62-using-the-aio-api)
   - 6.3. [Checking I/O Completion](#63-checking-io-completion)
   - 6.4. [Signals: An Interrupt-Based Alternative](#64-signals-an-interrupt-based-alternative)
7. [State Management Challenge](#7-state-management-challenge)
   - 7.1. [The Problem: Manual Stack Management](#71-the-problem-manual-stack-management)
   - 7.2. [The Solution: Continuations](#72-the-solution-continuations)
8. [Remaining Difficulties](#8-remaining-difficulties)
   - 8.1. [Multicore Systems](#81-multicore-systems)
   - 8.2. [Page Faults](#82-page-faults)
   - 8.3. [Code Evolution](#83-code-evolution)
   - 8.4. [API Integration](#84-api-integration)
9. [Summary](#9-summary)

---

## 1. Introduction

Throughout our discussion of concurrency, we've focused almost entirely on threads as the primary mechanism for building concurrent applications. But like many aspects of computing, there's an alternative approach that offers different trade-offs.

🔄 **Event-based concurrency** represents a fundamentally different way of thinking about concurrent programming. Instead of creating multiple threads that the OS schedules, you write a single-threaded program that explicitly decides what to do next based on incoming events.

**Where it's used:**
- **GUI applications:** Button clicks, mouse movements, keyboard input
- **Web servers:** Node.js, nginx's event-driven architecture
- **Network applications:** High-performance servers handling thousands of connections

### 1.1. The Problems Event-Based Concurrency Solves

**Problem 1: Threading Complexity**

Managing multi-threaded applications is challenging:
- Missing locks lead to race conditions
- Too many locks lead to deadlock
- Debugging concurrent bugs is difficult
- The complexity grows with the number of threads

**Problem 2: Loss of Control**

In multi-threaded programs:
- The OS scheduler decides which thread runs when
- You have little control over the ordering of operations
- General-purpose schedulers can't optimize for every workload
- Sometimes the OS schedules work sub-optimally

> **💡 Insight**
>
> Event-based concurrency trades parallelism for simplicity and control. You give up the ability to run code on multiple cores simultaneously, but you gain explicit control over scheduling and eliminate entire classes of concurrency bugs.

### 1.2. The Core Question

**THE CRUX: How to Build Concurrent Servers Without Threads**

How can we build a concurrent server without using threads, and thus retain control over concurrency as well as avoid the problems that plague multi-threaded applications?

---

## 2. The Basic Idea: An Event Loop

🔄 The fundamental concept in event-based concurrency is deceptively simple: **wait for events, then handle them one at a time**.

### 2.1. The Event Loop Structure

Here's the canonical event loop in pseudocode:

```c
while (1) {
    events = getEvents();
    for (e in events)
        processEvent(e);
}
```

**Breaking it down:**

```
Step 1: Wait           →    getEvents() blocks until something happens
Step 2: Retrieve       →    Get all pending events as a collection
Step 3: Process        →    Handle each event sequentially
Step 4: Repeat         →    Loop forever
```

> **💡 Insight**
>
> The event loop is essentially a scheduler running in user space. When you decide which event to handle next, you're making a scheduling decision—but you're making it explicitly in your code, not delegating it to the OS.

### 2.2. How Event Handling Works

**Event Handler:** The code that processes a specific event

**Critical Properties:**
1. **Single-threaded:** Only one handler runs at a time
2. **Run to completion:** A handler processes an event completely before the next one starts
3. **Explicit scheduling:** Choosing which event to handle next is equivalent to scheduling

**Visual flow:**

```
Event Queue          Handler Execution        Result
───────────         ─────────────────        ───────
[Event A]
[Event B]      →    Handle Event A      →    Complete
[Event C]

[Event B]
[Event C]      →    Handle Event B      →    Complete

[Event C]      →    Handle Event C      →    Complete
```

**Advantages of this model:**
- No race conditions (only one thing happens at a time)
- No need for locks (no shared data being modified concurrently)
- Explicit control over what runs when
- Predictable execution order

---

## 3. Important APIs: select() and poll()

The event loop concept is elegant, but how does the server actually detect events? How does it know when a network packet arrives or when data is ready to read?

🔧 Two fundamental system calls provide this capability: **select()** and **poll()**.

### 3.1. Understanding select()

The `select()` system call allows a program to monitor multiple file descriptors, waiting until one or more become "ready" for some operation.

**Function signature:**

```c
int select(int nfds,
           fd_set *restrict readfds,
           fd_set *restrict writefds,
           fd_set *restrict errorfds,
           struct timeval *restrict timeout);
```

**Parameters explained:**

| Parameter | Purpose | Example Use |
|-----------|---------|-------------|
| `nfds` | Number of descriptors to check | Check descriptors 0 through nfds-1 |
| `readfds` | Set of descriptors to check for reading | "Has data arrived on this socket?" |
| `writefds` | Set of descriptors to check for writing | "Can I send data without blocking?" |
| `errorfds` | Set of descriptors to check for errors | "Has this connection encountered an error?" |
| `timeout` | How long to wait | NULL = block forever, 0 = return immediately |

**What it does:**

1. **Input:** You give it sets of file descriptors you're interested in
2. **Wait:** It blocks until at least one descriptor is ready
3. **Output:** It modifies the sets to contain only the ready descriptors
4. **Return:** It returns the total count of ready descriptors

**The timeout parameter is crucial:**

```c
// Block indefinitely until something is ready
select(maxFD+1, &readFDs, NULL, NULL, NULL);

// Check immediately and return (non-blocking)
struct timeval timeout = {0, 0};
select(maxFD+1, &readFDs, NULL, NULL, &timeout);

// Wait up to 5 seconds
struct timeval timeout = {5, 0};
select(maxFD+1, &readFDs, NULL, NULL, &timeout);
```

> **💡 Insight**
>
> `select()` is the bridge between the abstract event loop concept and concrete I/O operations. It transforms "wait for events" into "wait for I/O to become ready on these specific descriptors."

### 3.2. Practical Example Using select()

Let's see a realistic example of using `select()` to monitor network sockets:

```c
#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>
#include <sys/types.h>
#include <unistd.h>

int main(void) {
    // open and set up a bunch of sockets (not shown)

    // main loop
    while (1) {
        // initialize the fd_set to all zero
        fd_set readFDs;
        FD_ZERO(&readFDs);

        // now set the bits for the descriptors
        // this server is interested in
        // (for simplicity, all of them from min to max)
        int fd;
        for (fd = minFD; fd < maxFD; fd++)
            FD_SET(fd, &readFDs);

        // do the select
        int rc = select(maxFD+1, &readFDs, NULL, NULL, NULL);

        // check which actually have data using FD_ISSET()
        int fd;
        for (fd = minFD; fd < maxFD; fd++)
            if (FD_ISSET(fd, &readFDs))
                processFD(fd);
    }
}
```

**Code walkthrough:**

```
Step 1: Clear the set       →    FD_ZERO() resets all bits to 0
Step 2: Mark descriptors    →    FD_SET() marks each descriptor we care about
Step 3: Call select()       →    Blocks until at least one descriptor is ready
Step 4: Check results       →    FD_ISSET() tells us which descriptors are ready
Step 5: Process data        →    processFD() handles the actual I/O
Step 6: Loop                →    Repeat forever
```

**Key macros:**

| Macro | Purpose |
|-------|---------|
| `FD_ZERO(&set)` | Clear all bits in the set |
| `FD_SET(fd, &set)` | Add a file descriptor to the set |
| `FD_ISSET(fd, &set)` | Check if a file descriptor is in the set |
| `FD_CLR(fd, &set)` | Remove a file descriptor from the set |

> **📝 Note**
>
> Real servers are more complex and need additional logic for:
> - Accepting new connections
> - Sending messages (using `writefds`)
> - Handling errors and disconnections
> - Managing disk I/O
> - Graceful shutdown

**poll() alternative:**

The `poll()` system call provides similar functionality with a slightly different API. Many developers find `poll()` easier to use because it uses an array of structures instead of bit sets. Consult the manual page (`man poll`) for details.

---

## 4. Why Simpler? No Locks Needed

One of the most compelling advantages of event-based programming becomes clear when you consider synchronization:

✅ **With a single CPU and event-based design, traditional concurrency problems simply vanish.**

### 4.1. Why Locks Aren't Needed

**In multi-threaded programs:**
- Multiple threads can access shared data simultaneously
- You must use locks to protect critical sections
- Forgetting a lock causes race conditions
- Using locks incorrectly causes deadlock

**In event-based programs:**
- Only one event handler runs at a time
- No interruption by another thread is possible
- The handler runs to completion before the next starts
- No shared data is being accessed concurrently

**Comparison:**

```
Multi-threaded Server              Event-based Server
─────────────────────             ──────────────────

Thread 1: lock(m)                 Event Handler
Thread 1: counter++               counter++
Thread 1: unlock(m)               (no lock needed!)

Thread 2: lock(m)                 Next Event Handler
Thread 2: counter++               counter++
Thread 2: unlock(m)               (no lock needed!)
```

> **💡 Insight**
>
> Event-based concurrency eliminates concurrency bugs not by solving them, but by structurally preventing them from occurring. If only one thing runs at a time, race conditions are impossible by definition.

### 4.2. The Fundamental Trade-off

**What you gain:**
- No locks, no deadlock, no race conditions
- Simpler reasoning about program behavior
- Explicit control over scheduling

**What you give up:**
- Can't utilize multiple CPUs (in the basic model)
- No automatic parallelism
- Must carefully avoid blocking operations

---

## 5. The Blocking Problem

⚠️ Event-based programming sounds perfect so far: simple event loops, no locks, full control. But there's a critical issue that threatens the entire model.

### 5.1. Why Blocking Kills Event-Based Servers

**The scenario:**

Imagine a client requests a file from your web server:

```
1. Client sends HTTP request for "document.pdf"
2. Your event handler receives the request
3. Handler calls open("document.pdf")      ← May block!
4. Handler calls read(fd, buffer, size)    ← May block!
5. Handler sends response to client
```

**The problem:**

If `open()` or `read()` needs to go to disk (and the data isn't cached), the call will **block**—potentially for milliseconds or more. During this time:

```
Event-based Server State
────────────────────────

Thread 1 (only thread):  BLOCKED waiting for I/O
Event loop:              BLOCKED (can't run)
Other pending events:    WAITING (can't be processed)
Server:                  EFFECTIVELY DEAD
```

**Contrast with multi-threaded servers:**

```
Multi-threaded Server               Event-based Server
─────────────────────              ──────────────────

Thread 1: read() → blocks          Main thread: read() → blocks
Thread 2: Still running            No other threads!
Thread 3: Still running            Entire server blocked!
Thread 4: Still running            No progress possible!
```

> **⚠️ Critical Rule**
>
> **No blocking calls are allowed in event-based systems.** A single blocking call stops the entire server, wasting resources and frustrating clients.

### 5.2. Blocking vs Non-Blocking Interfaces

🔍 Understanding the distinction between blocking and non-blocking interfaces is crucial for event-based programming.

**Blocking (Synchronous) Interfaces:**

```c
// This call doesn't return until ALL work is done
int bytes = read(fd, buffer, size);
// Only reaches here after disk I/O completes
printf("Read %d bytes\n", bytes);
```

**Characteristics:**
- Do all work before returning
- Easy to understand and use
- Natural control flow
- **Fatal for event-based servers**

**Non-blocking (Asynchronous) Interfaces:**

```c
// This call returns immediately, even if I/O isn't done
int rc = aio_read(&aiocb);
// Reaches here immediately!
// I/O happens in background

// Later, check if it's done
while (aio_error(&aiocb) == EINPROGRESS) {
    // Not done yet, do other work
}
// Now it's complete
```

**Characteristics:**
- Begin work but return immediately
- Work continues in the background
- More complex to use
- **Essential for event-based servers**

**Visual comparison:**

```
Blocking Call                    Non-blocking Call
─────────────                   ─────────────────

Call read()                     Call aio_read()
    ↓                              ↓
Wait for disk ──────            Return immediately
    ↓                              ↓
    ↓ (milliseconds)            Do other work
    ↓                              ↓
Return with data                Check if done later
```

> **💡 Insight**
>
> The blocking vs. non-blocking distinction appears throughout systems: disk I/O, network I/O, even memory access (page faults). Event-based systems must navigate all these carefully to maintain responsiveness.

---

## 6. The Solution: Asynchronous I/O

Modern operating systems provide APIs specifically designed for event-based programming: **asynchronous I/O** (AIO).

### 6.1. How Asynchronous I/O Works

🌊 Asynchronous I/O transforms the problematic blocking pattern into a flow that works with event loops:

**Traditional blocking I/O:**
```
Issue read() → Wait → Get data → Continue
```

**Asynchronous I/O:**
```
Issue aio_read() → Continue immediately → Check later if done → Get data
```

**The key difference:**
- Blocking I/O: "Do this and don't return until it's done"
- Asynchronous I/O: "Start doing this, and let me know when it's done"

### 6.2. Using the AIO API

The POSIX asynchronous I/O API centers around a control structure:

```c
struct aiocb {
    int aio_fildes;         /* File descriptor */
    off_t aio_offset;       /* File offset */
    volatile void *aio_buf; /* Location of buffer */
    size_t aio_nbytes;      /* Length of transfer */
};
```

**Step-by-step usage:**

**Step 1: Fill in the control block**

```c
struct aiocb cb;
memset(&cb, 0, sizeof(struct aiocb));

cb.aio_fildes = fd;              // Which file to read from
cb.aio_offset = 0;               // Start at beginning
cb.aio_buf = buffer;             // Where to put the data
cb.aio_nbytes = sizeof(buffer);  // How much to read
```

**Step 2: Issue the asynchronous read**

```c
int rc = aio_read(&cb);
if (rc < 0) {
    perror("aio_read failed");
    return;
}
// Function returns immediately!
// I/O is happening in background
```

**Step 3: Continue with other work**

```c
// The event loop continues processing other events
// while the I/O happens in the background
processOtherEvents();
handleNetworkTraffic();
respondToClients();
```

### 6.3. Checking I/O Completion

Eventually, you need to know when the I/O finishes. The `aio_error()` function provides this:

```c
int aio_error(const struct aiocb *aiocbp);
```

**Return values:**
- `0`: I/O completed successfully
- `EINPROGRESS`: I/O still in progress
- Other: An error occurred

**Polling approach:**

```c
// In your event loop, check periodically
while (aio_error(&cb) == EINPROGRESS) {
    // Not done yet, process other events
    processOtherEvents();
}

// I/O is complete, handle the result
handleCompletedRead(&cb);
```

**The challenge:**

If you have many outstanding I/Os, checking each one repeatedly is inefficient:

```c
// Inefficient for many I/Os!
for (int i = 0; i < num_ios; i++) {
    if (aio_error(&ios[i]) == 0) {
        handleCompletion(&ios[i]);
    }
}
```

### 6.4. Signals: An Interrupt-Based Alternative

🔔 To avoid constant polling, you can use **UNIX signals** to be notified when I/O completes.

**How it works:**

```
1. Register signal handler  →    Handle SIGUSR1 with my_handler()
2. Configure aiocb         →    Request signal on completion
3. Issue aio_read()        →    I/O starts in background
4. Process other events    →    Event loop continues normally
5. I/O completes           →    OS sends SIGUSR1
6. Handler runs            →    my_handler() processes completion
7. Resume event loop       →    Continue normal processing
```

**UNIX Signals: A Brief Overview**

📝 Signals are a fundamental UNIX mechanism for process communication and interruption.

**Common signals:**

| Signal | Name | Meaning |
|--------|------|---------|
| SIGHUP | Hang up | Terminal disconnected |
| SIGINT | Interrupt | Ctrl+C pressed |
| SIGTERM | Terminate | Polite shutdown request |
| SIGKILL | Kill | Forced termination (can't catch) |
| SIGSEGV | Segmentation violation | Invalid memory access |
| SIGUSR1 | User signal 1 | Application-defined |

**Simple signal handler example:**

```c
#include <stdio.h>
#include <signal.h>

void handle(int arg) {
    printf("Caught signal %d\n", arg);
}

int main(int argc, char *argv[]) {
    // Register handler for SIGHUP
    signal(SIGHUP, handle);

    while (1)
        ; // Infinite loop, waiting for signals

    return 0;
}
```

**Using it:**

```bash
$ ./signal_demo &
[1] 36705

$ kill -HUP 36705
Caught signal 1

$ kill -HUP 36705
Caught signal 1
```

**Signals vs. Polling:**

| Approach | Advantages | Disadvantages |
|----------|-----------|---------------|
| Polling | Simple, explicit control | CPU overhead, latency |
| Signals | Efficient, immediate notification | Complex, harder to debug |

> **💡 Insight**
>
> The polling vs. interrupts debate appears throughout systems: device drivers, I/O completion, network packets. It's a fundamental trade-off between simplicity and efficiency.

**Hybrid approaches:**

Many real systems use a combination:
- Network I/O: `select()` or `poll()` (naturally event-driven)
- Disk I/O: Thread pool (if async I/O unavailable)
- Memory allocation: Synchronous (usually fast enough)

---

## 7. State Management Challenge

🧠 Event-based programming introduces a subtle but important complexity: **manual stack management**.

### 7.1. The Problem: Manual Stack Management

**In thread-based programming:**

The thread's stack automatically maintains state between operations:

```c
// Thread-based code (simple!)
int rc = read(fd, buffer, size);
rc = write(sd, buffer, size);
```

**What's on the stack:**
```
─────────────
| sd (socket descriptor)  |  ← Automatically preserved
| buffer                  |  ← Automatically preserved
| size                    |  ← Automatically preserved
| fd (file descriptor)    |  ← Automatically preserved
─────────────
```

When `read()` blocks, the thread sleeps, but all variables remain on its stack. When the thread wakes up, it continues right where it left off—`sd` is still there, ready to use.

**In event-based programming:**

```c
// Event-based code (complex!)

// Event handler 1: Initiate read
struct aiocb cb;
cb.aio_fildes = fd;
cb.aio_buf = buffer;
cb.aio_nbytes = size;
aio_read(&cb);
// Function returns immediately!

// ... time passes, other events are handled ...

// Event handler 2: Read completed
// Problem: How do we know which socket (sd) to write to?
// The stack is gone! We're in a different function call!
```

**Visual comparison:**

```
Thread-based Flow               Event-based Flow
─────────────────              ────────────────

read(fd) → blocks              aio_read(fd) → returns immediately
    ↓                               ↓
Thread sleeps                  Handle other events
Stack preserved                Stack destroyed
    ↓                               ↓
Disk I/O completes             Disk I/O completes
    ↓                               ↓
Thread wakes                   Completion handler called
Stack still there!             New stack!
    ↓                               ↓
write(sd)                      write(sd) ← Where is 'sd'?
```

> **⚠️ The Challenge**
>
> When an asynchronous operation completes, you're in a completely different function call with a different stack. You must manually save and restore any state needed to complete the operation.

### 7.2. The Solution: Continuations

The solution is to use a programming language construct called a **continuation**—though the name sounds fancy, the idea is simple.

**Continuation:** A data structure that captures the state needed to continue processing when an asynchronous operation completes.

**Implementation approach:**

**Step 1: Define a continuation structure**

```c
struct continuation {
    int socket_descriptor;  // Where to send the result
    char *buffer;          // Data buffer
    int buffer_size;       // Buffer size
    void *callback;        // Function to call when done
};
```

**Step 2: Create continuation when starting async I/O**

```c
// Event handler: Client requests file
void handleRequest(int socket_fd, char *filename) {
    // Set up the async read
    struct aiocb *cb = malloc(sizeof(struct aiocb));
    char *buffer = malloc(BUFFER_SIZE);

    cb->aio_fildes = open(filename, O_RDONLY);
    cb->aio_buf = buffer;
    cb->aio_nbytes = BUFFER_SIZE;

    // Create continuation with state we'll need later
    struct continuation *cont = malloc(sizeof(struct continuation));
    cont->socket_descriptor = socket_fd;  // Save for later!
    cont->buffer = buffer;
    cont->buffer_size = BUFFER_SIZE;

    // Store continuation in a hash table indexed by fd
    storeContination(cb->aio_fildes, cont);

    // Issue async read
    aio_read(cb);
    // Returns immediately, state preserved in 'cont'
}
```

**Step 3: Retrieve continuation when I/O completes**

```c
// Event handler: Async I/O completed
void handleIOComplete(int fd) {
    // Look up the continuation
    struct continuation *cont = getContination(fd);

    // Now we have all the state we need!
    int sd = cont->socket_descriptor;
    char *buffer = cont->buffer;
    int size = cont->buffer_size;

    // Complete the operation
    write(sd, buffer, size);

    // Clean up
    free(cont);
}
```

**Data structure for tracking continuations:**

```c
// Hash table mapping file descriptors to continuations
struct {
    int fd;
    struct continuation *cont;
} continuation_table[MAX_FDS];
```

**Visual flow:**

```
Start Request              Store State                Complete Request
─────────────             ────────────               ────────────────

Receive request           Create continuation        I/O completes
    ↓                         ↓                           ↓
Extract socket fd         cont->socket_fd = sd       Look up fd
    ↓                         ↓                           ↓
Open file                 Store in hash table        Retrieve continuation
    ↓                         ↓                           ↓
Start aio_read()          Return to event loop       Extract socket_fd
    ↓                                                     ↓
Return immediately                                   write(socket_fd, ...)
```

> **💡 Insight**
>
> Continuations are essentially "manual stack frames." You're doing explicitly what the OS does implicitly for threads: saving and restoring execution context. This is why event-based code is harder to write—you're implementing part of the runtime system yourself.

**Real-world example: JavaScript Promises**

Modern JavaScript uses this exact pattern with Promises and async/await:

```javascript
// The continuation is captured automatically
async function handleRequest(socket, filename) {
    // Start async read (returns a Promise)
    const data = await readFile(filename);

    // When this line executes, the continuation (socket variable)
    // has been preserved by the JavaScript runtime
    socket.write(data);
}
```

The JavaScript engine maintains the continuation for you—but it's the same concept!

---

## 8. Remaining Difficulties

Despite the elegance of event-based concurrency, several practical challenges remain unsolved or only partially addressed.

### 8.1. Multicore Systems

⚡ **The Parallelism Problem**

The beautiful simplicity of event-based programming—no locks needed!—breaks down on multi-core systems.

**On a single CPU:**
```
Core 0: Event handler A → Event handler B → Event handler C
        (Only one thing at a time, no races!)
```

**On multiple CPUs:**
```
Core 0: Event handler A ─────┐
                             ├─→  Race condition!
Core 1: Event handler B ─────┘
```

**To utilize multiple cores, you must:**

1. **Run multiple event handlers in parallel** (one per core)
2. **Synchronize access to shared data** (locks are back!)
3. **Manage cross-core communication** (added complexity)

**Example scenario:**

```c
// Global counter shared across event handlers
int connection_count = 0;

// Handler on Core 0
void handleNewConnection() {
    connection_count++;  // ← Race condition!
}

// Handler on Core 1
void handleDisconnection() {
    connection_count--;  // ← Race condition!
}
```

**Solution: Locks are back**

```c
pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;

void handleNewConnection() {
    pthread_mutex_lock(&lock);
    connection_count++;
    pthread_mutex_unlock(&lock);
}
```

> **💡 Insight**
>
> The multicore problem reveals a fundamental truth: parallelism introduces complexity. Event-based programming eliminated concurrency bugs by eliminating parallelism—but modern hardware demands parallelism for performance.

**Hybrid approaches:**

Many systems use multiple event loops:
```
Core 0: Event loop A → handles connections 0-999
Core 1: Event loop B → handles connections 1000-1999
Core 2: Event loop C → handles connections 2000-2999
```

Each loop is single-threaded (no locks within a loop), but data shared between loops needs synchronization.

### 8.2. Page Faults

💾 **The Implicit Blocking Problem**

Even if you carefully avoid all blocking system calls, your program can still block implicitly due to **page faults**.

**What's a page fault?**

When your program accesses memory that's not currently in RAM (it's been paged out to disk), the OS must:
1. Pause your program
2. Read the page from disk
3. Resume your program

**Why it's problematic:**

```c
void handleEvent(Event *e) {
    // Looks innocent, but...
    char *data = e->data;  // ← Might cause page fault!

    // If this page is on disk, the ENTIRE event loop blocks
    // while the OS reads it back into memory
}
```

**Visual impact:**

```
Event Handler Execution           What Actually Happens
───────────────────────          ─────────────────────

Access e->data                   Access e->data
    ↓                                ↓
Process event                    Page fault!
    ↓                                ↓
Handle next event                Block waiting for disk ───┐
                                     ↓                     │
                                 (milliseconds)            │
                                     ↓                     │
                                 Page read complete    ────┘
                                     ↓
                                 Resume execution
```

**Why you can't prevent it:**

- You don't control which pages are in memory
- The OS makes paging decisions independently
- Accessing any data structure might cause a page fault
- Even reading code can cause instruction page faults

> **⚠️ Warning**
>
> Page faults represent a form of blocking you cannot avoid with current APIs. This is a fundamental limitation of event-based systems—they can suffer from blocking they didn't explicitly request.

**Mitigation strategies:**

1. **Memory locking** (`mlock()`): Pin critical pages in RAM (requires privileges)
2. **Working set management**: Keep frequently accessed data "hot"
3. **Overprovisioning RAM**: Reduce paging through hardware
4. **Accept the limitation**: Understand that some blocking is unavoidable

### 8.3. Code Evolution

🔧 **The API Change Problem**

Event-based systems are fragile with respect to API changes.

**The scenario:**

You have an event handler that calls a library function:

```c
// Version 1.0 of library
void handleEvent() {
    // process_data() is non-blocking
    process_data();
    send_response();
}
```

**Then the library is updated:**

```c
// Version 2.0 of library - process_data() now blocks!
void handleEvent() {
    // This now BLOCKS, killing your event loop
    process_data();
    send_response();
}
```

**The problem:**

In thread-based code, this change is usually fine—one thread blocks, others continue. In event-based code, this change is **catastrophic**—the entire server blocks.

**Required refactoring:**

```c
// Must split into two handlers
void handleEventPart1() {
    // Start async version
    async_process_data(callback);
}

void handleEventPart2() {
    // Called when async operation completes
    send_response();
}
```

> **⚠️ Critical Issue**
>
> You must constantly monitor the blocking behavior of every function you call. A library update that changes a function from non-blocking to blocking can break your entire application.

**Real-world impact:**

- Difficult to maintain over time
- Library updates require careful review
- Third-party code is risky
- Defensive programming essential

### 8.4. API Integration

🌐 **The Unified Interface Problem**

Different I/O types use different APIs, making event-based programming more complex.

**The ideal world:**

```c
// Wouldn't it be nice if this worked?
while (1) {
    events = getEvents();  // ALL events: network, disk, timers
    for (e in events)
        processEvent(e);
}
```

**The real world:**

```c
// Actually need multiple APIs
while (1) {
    // Network I/O
    select(maxfd, &readfds, &writefds, NULL, &timeout);

    // Disk I/O
    for (int i = 0; i < num_ios; i++) {
        if (aio_error(&ios[i]) == 0) {
            handleDiskIO(&ios[i]);
        }
    }

    // Timers
    checkTimers();

    // Signals
    // (handled via signal handlers)
}
```

**Problems:**

1. **Multiple blocking points**: Each API can block independently
2. **Timeout complexity**: Coordinating timeouts across APIs is tricky
3. **Priority inversion**: Disk I/O checks might starve network I/O
4. **Code complexity**: More APIs mean more code and more bugs

**Historical context:**

Asynchronous I/O for disk operations came **much later** than `select()` for network I/O. Many systems had mature event-based network code before async disk I/O was available, leading to hybrid approaches:

```c
// Common pattern: network events + thread pool for disk
while (1) {
    select(maxfd, &readfds, ...);  // Network events

    if (need_disk_io) {
        submit_to_thread_pool(disk_io_task);  // Threads for disk
    }
}
```

> **💡 Insight**
>
> The API fragmentation problem reflects the historical evolution of operating systems. Each I/O subsystem was developed independently, and true unified asynchronous I/O remains an ongoing challenge even in modern systems.

**Modern solutions:**

- **Linux io_uring**: Unified async interface for all I/O types
- **Windows I/O Completion Ports**: Unified event notification
- **libuv**: Cross-platform library abstracting differences (used by Node.js)

---

## 9. Summary

We've explored an alternative model for concurrent programming that offers different trade-offs from traditional threading.

### 9.1. Event-Based Concurrency Recap

**Core concept:**
- Single-threaded event loop
- Wait for events, process them one at a time
- Explicit control over scheduling

**Key components:**
- **Event loop**: The main control structure
- **select()/poll()**: APIs for detecting I/O readiness
- **Asynchronous I/O**: Non-blocking operations
- **Continuations**: Manual state management

### 9.2. Advantages

✅ **No concurrency bugs (on single core):**
- No race conditions
- No deadlocks
- No need for locks

✅ **Explicit scheduling control:**
- You decide what runs next
- Predictable behavior
- Can optimize for specific workloads

✅ **Lower overhead:**
- No thread context switches
- No synchronization overhead
- Simpler memory model

### 9.3. Challenges

⚠️ **Blocking operations:**
- Must avoid all blocking calls
- Requires async versions of everything
- Difficult to enforce

⚠️ **State management:**
- Manual stack management
- Continuation tracking
- More complex code

⚠️ **Multicore systems:**
- Basic model doesn't scale to multiple CPUs
- Must add parallelism (and locks) to utilize all cores
- Loses some simplicity

⚠️ **Page faults:**
- Implicit blocking you can't control
- Performance unpredictability
- Difficult to mitigate

⚠️ **API fragmentation:**
- Different interfaces for network vs disk I/O
- Evolving library semantics
- Integration complexity

### 9.4. When to Use Each Model

**Use event-based concurrency when:**
- Building I/O-intensive servers (web servers, proxies)
- Need precise control over scheduling
- Want to minimize overhead
- Single-core is sufficient or you can partition work

**Use thread-based concurrency when:**
- Need true parallelism across multiple cores
- Have CPU-intensive workloads
- Want simpler code structure
- Can tolerate synchronization overhead

> **💡 Final Insight**
>
> Neither threads nor events are universally superior. Threads offer parallelism and simplicity at the cost of synchronization complexity. Events offer control and efficiency at the cost of programming complexity. Modern systems often use both: event loops for I/O and thread pools for computation.

### 9.5. Where Event-Based Concurrency Thrives

**Modern frameworks using this model:**
- **Node.js**: JavaScript runtime for servers
- **nginx**: High-performance web server
- **Redis**: In-memory data store
- **Twisted/Tornado**: Python async frameworks
- **libuv**: Cross-platform async I/O library

### 9.6. Further Learning

To deepen your understanding:

1. **Read research papers:**
   - "SEDA: An Architecture for Well-Conditioned, Scalable Internet Services" (Welsh et al.)
   - "Capriccio: Scalable Threads for Internet Services" (von Behren et al.)
   - "Cooperative Task Management Without Manual Stack Management" (Adya et al.)

2. **Write event-based code:**
   - Build a simple echo server using `select()`
   - Implement an async file reader using AIO
   - Create a multi-client chat server

3. **Study production systems:**
   - Read nginx source code
   - Explore libuv documentation
   - Examine Node.js event loop implementation

Event-based concurrency represents decades of innovation in building high-performance servers. While it introduces new challenges, it remains a powerful tool for specific problem domains—particularly I/O-intensive applications where explicit scheduling control outweighs the complexity of manual state management.

---

**Previous:** [Chapter 7 - Common Concurrency Problems](chapter7-common-problems.md)
