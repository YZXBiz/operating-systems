# Chapter 2: The Process API 🔧

_Mastering the fork-exec-wait pattern for process creation and control_

---

## 📋 Table of Contents

1. [🎯 Introduction](#1-introduction)
2. [🍴 The fork() System Call](#2-the-fork-system-call)
   - 2.1. [How fork() Works](#21-how-fork-works)
   - 2.2. [Understanding Return Values](#22-understanding-return-values)
   - 2.3. [Nondeterministic Execution](#23-nondeterministic-execution)
3. [⏳ The wait() System Call](#3-the-wait-system-call)
   - 3.1. [Parent-Child Synchronization](#31-parent-child-synchronization)
   - 3.2. [Deterministic Output](#32-deterministic-output)
4. [🚀 The exec() System Call](#4-the-exec-system-call)
   - 4.1. [Running Different Programs](#41-running-different-programs)
   - 4.2. [The exec() Family](#42-the-exec-family)
   - 4.3. [Process Transformation](#43-process-transformation)
5. [🎨 Why This API? Design Motivation](#5-why-this-api-design-motivation)
   - 5.1. [The UNIX Shell](#51-the-unix-shell)
   - 5.2. [I/O Redirection](#52-io-redirection)
   - 5.3. [Pipes and Command Composition](#53-pipes-and-command-composition)
6. [👥 Process Control and Users](#6-process-control-and-users)
   - 6.1. [The Signal System](#61-the-signal-system)
   - 6.2. [User Permissions](#62-user-permissions)
   - 6.3. [The Superuser](#63-the-superuser)
7. [🛠️ Useful Tools](#7-useful-tools)
   - 7.1. [Command-Line Process Tools](#71-command-line-process-tools)
   - 7.2. [Monitoring and Control](#72-monitoring-and-control)
8. [📝 Summary](#8-summary)

---

## 1. 🎯 Introduction

**In plain English:** Imagine you're a manager 👔 who needs to delegate work. You could just give orders and hope tasks get done. Or you could have a systematic way to: (1) create a clone of yourself to do the work 👯, (2) transform that clone into a specialist for the specific task 🔄, (3) wait for them to report back ⏳, and (4) send them messages while they work 📨. That's exactly what UNIX process APIs give you!

**In technical terms:** The UNIX process API provides three core system calls—`fork()`, `exec()`, and `wait()`—that together form one of the most elegant and powerful abstractions in operating system design. These calls enable process creation, program execution, and synchronization with a surprising degree of flexibility.

**Why it matters:** Understanding these APIs is crucial because:
- 🔑 They're the foundation of how shells work
- ⚡ They enable powerful features like pipes and I/O redirection
- 🌐 Modern frameworks (like web servers spawning workers) use these patterns
- 🧠 They teach fundamental OS design principles: separation of concerns and composition

> **💡 Insight**
>
> The **separation of fork() and exec()** is a masterclass in API design. By splitting "create a process" from "run a program," UNIX enables features that would be impossible with a monolithic `CreateProcess(program)` call. This is Lampson's Law in action: "Get it right. Neither abstraction nor simplicity is a substitute for getting it right."

### 🎯 The Core Challenge

**THE CRUX:** How should an OS provide interfaces for process creation and control? What primitives enable both simplicity and power?

The UNIX answer: Three primitives that compose beautifully 🎼

```
fork()  → 👯 Create identical copy of current process
exec()  → 🔄 Transform process into different program
wait()  → ⏳ Synchronize parent with child completion

Combined:
fork() + exec() + wait() = 🎯 Complete process lifecycle control
```

---

## 2. 🍴 The fork() System Call

### 2.1. How fork() Works

**In plain English:** Calling `fork()` is like looking in a magic mirror 🪞 that creates a living copy of you. Suddenly there are two of you—the original (parent) and the copy (child). Both of you remember everything up to that moment, but from now on, you live separate lives. The weird part? You both remember looking in the mirror, but you each get a different message 📨 about who you are!

**In technical terms:** `fork()` creates a new process by making an almost exact copy of the calling process. The child process gets its own:
- Address space (copy of parent's memory) 💾
- Registers (copy of parent's register state) 🔧
- Program counter (continues from same point) 📍
- File descriptors (shares parent's open files) 📁

Let's see it in action:

```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    printf("hello (pid:%d)\n", (int) getpid());

    int rc = fork();  // 🪞 The magic moment!

    if (rc < 0) {
        // ❌ fork failed
        fprintf(stderr, "fork failed\n");
        exit(1);
    } else if (rc == 0) {
        // 👶 child (new process)
        printf("child (pid:%d)\n", (int) getpid());
    } else {
        // 👨 parent goes down this path (main)
        printf("parent of %d (pid:%d)\n", rc, (int) getpid());
    }

    return 0;
}
```

**Sample output:**
```bash
prompt> ./p1
hello (pid:29146)
parent of 29147 (pid:29146)
child (pid:29147)
prompt>
```

**What happened:**

```
Timeline of Execution
─────────────────────

Time 1:  Parent process running
         ├─ "hello (pid:29146)" ← printed once
         └─ Calls fork()

Time 2:  🪞 OS creates child (exact copy)
         Now TWO processes exist!

Time 3:  Both return from fork()
         Parent: rc = 29147 (child's PID)
         Child:  rc = 0 (special marker)

Time 4:  Parent executes else branch
         └─ "parent of 29147 (pid:29146)"

Time 5:  Child executes else if branch
         └─ "child (pid:29147)"

Time 6:  Both processes exit
```

> **💡 Insight**
>
> The child doesn't start at `main()`! It materializes **as if it had just called fork() itself**. This is why "hello" prints only once—the child comes into existence after that line. Understanding this "fork returns twice" behavior is key to mastering process creation.

### 2.2. 🔍 Understanding Return Values

The genius of `fork()` is in its return values:

```
Return Value    Meaning           Who Gets It?
────────────    ───────────       ────────────
< 0             ❌ Error          Parent (child wasn't created)
= 0             👶 I'm the child  Child process only
> 0             👨 Child's PID    Parent process only
```

**Why this design is brilliant:**

```c
int rc = fork();

if (rc == 0) {
    // 👶 Child-specific code
    printf("I'm the child, I'll do the work\n");
    do_child_task();
} else {
    // 👨 Parent-specific code
    printf("I'm the parent, I'll wait for child: %d\n", rc);
    wait_for_child(rc);  // rc is the child's PID!
}
```

**In plain English:** It's like giving twins 👯 different colored wristbands at birth. Even though they're identical, each knows their role by checking their wristband.

**Progressive Example:**

**Simple:** Identify who you are
```c
if (fork() == 0) {
    printf("Child here!\n");
} else {
    printf("Parent here!\n");
}
```

**Intermediate:** Store PID for later use
```c
int child_pid = fork();
if (child_pid == 0) {
    printf("Child with PID %d\n", getpid());
} else {
    printf("Parent spawned child with PID %d\n", child_pid);
    // Can now send signals to specific child: kill(child_pid, SIGTERM);
}
```

**Advanced:** Multiple children management
```c
#define NUM_CHILDREN 5
int child_pids[NUM_CHILDREN];

for (int i = 0; i < NUM_CHILDREN; i++) {
    int pid = fork();
    if (pid == 0) {
        // Child i does its work
        do_work(i);
        exit(0);  // Important: child exits loop!
    } else {
        child_pids[i] = pid;  // Parent tracks all children
    }
}

// Parent waits for all children
for (int i = 0; i < NUM_CHILDREN; i++) {
    waitpid(child_pids[i], NULL, 0);  // Wait for specific child
}
```

### 2.3. 🎲 Nondeterministic Execution

**In plain English:** After fork(), you have two runners 🏃🏃 standing at the starting line. Who runs first? It's up to the referee (CPU scheduler) to decide. You can't predict or control this—it's **nondeterministic**.

**Different output from same program:**

**Run 1:**
```bash
prompt> ./p1
hello (pid:29146)
parent of 29147 (pid:29146)
child (pid:29147)
prompt>
```

**Run 2:**
```bash
prompt> ./p1
hello (pid:29146)
child (pid:29147)
parent of 29147 (pid:29146)
prompt>
```

**Why the difference?**

```
Scenario A: Parent Runs First        Scenario B: Child Runs First
────────────────────────              ────────────────────────

1. fork() creates child               1. fork() creates child
2. Scheduler picks PARENT             2. Scheduler picks CHILD
   └─ Parent prints its line             └─ Child prints its line
3. Scheduler picks CHILD              3. Scheduler picks PARENT
   └─ Child prints its line              └─ Parent prints its line
```

**In technical terms:** The CPU scheduler (which we'll study deeply in upcoming chapters) makes complex decisions about which process to run based on:
- ⏱️ Time slice allocations
- 🎯 Process priorities
- ⚡ I/O readiness
- 🔄 Fairness considerations

**Key takeaway:** You **cannot** make assumptions about execution order after `fork()`. Write your code to handle any possible interleaving.

> **💡 Insight**
>
> **Nondeterminism is a feature, not a bug!** It allows the OS to maximize CPU utilization. If the parent is waiting for disk I/O, the child can run. This parallelism 🔀 is essential for performance. However, it introduces complexity in multi-process/multi-threaded programs—a topic we'll tackle in the concurrency section of this book.

---

## 3. ⏳ The wait() System Call

### 3.1. Parent-Child Synchronization

**In plain English:** Imagine you sent your kid to the store 🏪. You can either keep doing housework while they're gone (asynchronous) or sit by the door staring at it until they return 🚪👀 (synchronous). The `wait()` system call is like choosing to wait by the door—you pause everything until the child comes back.

**Why wait?**

```
Without wait()              With wait()
───────────────             ───────────

Parent: Do task 1           Parent: Do task 1
Child:  Do task A           Child:  Do task A
Parent: Do task 2           Parent: WAIT for child...
Child:  Do task B           Child:  Do task B
Parent: Exit (oops!)        Child:  Exit
Child:  Orphaned! 😢        Parent: Continue with task 2
                            Parent: Exit
```

**Code example:**

```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>

int main(int argc, char *argv[]) {
    printf("hello (pid:%d)\n", (int) getpid());

    int rc = fork();
    if (rc < 0) {
        fprintf(stderr, "fork failed\n");
        exit(1);
    } else if (rc == 0) {
        // 👶 child (new process)
        printf("child (pid:%d)\n", (int) getpid());
    } else {
        // 👨 parent goes down this path
        int rc_wait = wait(NULL);  // ⏳ Block until child finishes
        printf("parent of %d (rc_wait:%d) (pid:%d)\n",
               rc, rc_wait, (int) getpid());
    }

    return 0;
}
```

**Output (now deterministic!):**
```bash
prompt> ./p2
hello (pid:29266)
child (pid:29267)
parent of 29267 (rc_wait:29267) (pid:29266)
prompt>
```

### 3.2. ✅ Deterministic Output

**Key observation:** The child ALWAYS prints before the parent now. Why?

```
Case 1: Child Scheduled First       Case 2: Parent Scheduled First
──────────────────────────           ──────────────────────────

1. fork() creates child              1. fork() creates child
2. Scheduler picks CHILD             2. Scheduler picks PARENT
   └─ Child prints                      └─ Parent calls wait()
   └─ Child exits                          └─ BLOCKS (sleep until child done)
3. Parent wakes up                   3. Scheduler picks CHILD
   └─ wait() returns                    └─ Child prints
   └─ Parent prints                     └─ Child exits
                                     4. Parent wakes up
                                        └─ wait() returns
                                        └─ Parent prints
```

**In plain English:** Even if the parent runs first, it immediately calls `wait()` and goes to sleep 😴. The child will definitely run and finish before the parent wakes up. Result: deterministic output order! 🎯

**What wait() returns:**

```c
int status;
pid_t child_pid = wait(&status);  // Blocks until ANY child exits

if (child_pid > 0) {
    printf("Child %d finished\n", child_pid);

    if (WIFEXITED(status)) {
        int exit_code = WEXITSTATUS(status);
        printf("Exit code: %d\n", exit_code);

        if (exit_code == 0) {
            printf("✅ Success!\n");
        } else {
            printf("❌ Child failed with code %d\n", exit_code);
        }
    }
}
```

**More precise control with waitpid():**

```c
// Wait for specific child
waitpid(child_pid, &status, 0);  // Block until this specific child exits

// Non-blocking check
pid_t result = waitpid(child_pid, &status, WNOHANG);
if (result == 0) {
    printf("Child still running...\n");
} else if (result > 0) {
    printf("Child finished!\n");
}
```

> **💡 Insight**
>
> The `wait()` system call demonstrates **synchronization primitives** in their simplest form. Parent and child are two concurrent entities, and `wait()` coordinates them. This is fundamentally the same problem as thread synchronization (locks, condition variables) but at the process level. Master this concept here, and you're prepared for concurrency challenges later.

---

## 4. 🚀 The exec() System Call

### 4.1. Running Different Programs

**In plain English:** So far, `fork()` just creates a clone doing the same thing. That's like photocopying yourself 📋 to do the same job. But what if you want your clone to do something completely different? That's where `exec()` comes in—it's like performing brain surgery 🧠🔪 on the clone, replacing their entire personality and skill set!

**The problem fork() alone can't solve:**

```c
int rc = fork();
if (rc == 0) {
    // Child is running... but it's just another copy of parent
    // How do we make it run a DIFFERENT program?
    // Answer: exec()!
}
```

**Example: Running the `wc` (word count) program:**

```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <sys/wait.h>

int main(int argc, char *argv[]) {
    printf("hello (pid:%d)\n", (int) getpid());

    int rc = fork();
    if (rc < 0) {
        fprintf(stderr, "fork failed\n");
        exit(1);
    } else if (rc == 0) {
        // 👶 child (new process)
        printf("child (pid:%d)\n", (int) getpid());

        // 🔄 Transform into 'wc' program
        char *myargs[3];
        myargs[0] = strdup("wc");      // program name
        myargs[1] = strdup("p3.c");    // argument: file to count
        myargs[2] = NULL;              // end-of-array marker

        execvp(myargs[0], myargs);     // 🚀 TRANSFORM!

        printf("this shouldn't print out");  // Never reached!
    } else {
        // 👨 parent
        int rc_wait = wait(NULL);
        printf("parent of %d (rc_wait:%d) (pid:%d)\n",
               rc, rc_wait, (int) getpid());
    }

    return 0;
}
```

**Output:**
```bash
prompt> ./p3
hello (pid:29383)
child (pid:29384)
29 107 1030 p3.c            ← Output from 'wc' program!
parent of 29384 (rc_wait:29384) (pid:29383)
prompt>
```

### 4.2. 🎯 The exec() Family

**In plain English:** `exec()` isn't one function—it's a whole family 👨‍👩‍👧‍👦 of related functions. Each variant handles arguments or environment variables slightly differently, like different ways to pass a message 💌.

**The six variants on Linux:**

```
Function     Args Type    Path Search?   Environment
────────     ─────────    ────────────   ───────────
execl()      List         No             Inherit
execlp()     List         Yes (PATH)     Inherit
execle()     List         No             Specify
execv()      Array        No             Inherit
execvp()     Array        Yes (PATH)     Inherit
execve()     Array        No             Specify
```

**Mnemonic for the letters:**
- `l` = List (separate arguments: `"wc", "p3.c", NULL`)
- `v` = Vector/Array (array of strings: `char *args[]`)
- `p` = Path search (looks in PATH environment variable)
- `e` = Environment (you provide environment variables)

**Examples:**

```c
// execl: arguments as separate parameters
execl("/bin/ls", "ls", "-l", "-a", NULL);

// execlp: searches PATH, no full path needed
execlp("ls", "ls", "-l", "-a", NULL);

// execv: arguments in array
char *args[] = {"ls", "-l", "-a", NULL};
execv("/bin/ls", args);

// execvp: array + PATH search (most common!)
char *args[] = {"ls", "-l", "-a", NULL};
execvp("ls", args);  // Searches PATH for 'ls'

// execle: specify environment
char *envp[] = {"PATH=/bin:/usr/bin", "USER=alice", NULL};
execle("/bin/ls", "ls", "-l", NULL, envp);

// execve: array + environment (most flexible)
char *args[] = {"ls", "-l", NULL};
char *envp[] = {"PATH=/bin", NULL};
execve("/bin/ls", args, envp);
```

**Progressive Example:**

**Simple:** Run a command with no arguments
```c
if (fork() == 0) {
    execlp("date", "date", NULL);  // Shows current date/time
}
```

**Intermediate:** Run a command with arguments
```c
if (fork() == 0) {
    char *args[] = {"grep", "error", "logfile.txt", NULL};
    execvp(args[0], args);
}
```

**Advanced:** Build command from user input
```c
// Simulate shell behavior
char *user_command = read_user_input();  // e.g., "ls -la /tmp"
char **args = parse_command(user_command);  // ["ls", "-la", "/tmp", NULL]

if (fork() == 0) {
    execvp(args[0], args);
    perror("exec failed");  // Only prints if exec fails!
    exit(1);
}
wait(NULL);
```

### 4.3. 🔄 Process Transformation

**In plain English:** When `exec()` succeeds, it's like swapping out the film 🎞️ in a projector while it's running. Same projector (same process, same PID), completely different movie! The old program is **gone**—its code, its data, everything. The new program takes over completely.

**What happens during exec():**

```
Before exec()                    exec() call                After exec()
─────────────                    ──────────                 ────────────

Process 29384                    TRANSFORMATION              Process 29384
┌──────────────┐                ═════════════════           ┌──────────────┐
│ PID: 29384   │                Keeps:                      │ PID: 29384   │
├──────────────┤                • PID                       ├──────────────┤
│ Code:        │                • Open file descriptors     │ Code:        │
│   p3.c       │                • Working directory         │   wc         │
│   program    │                • User/group IDs            │   program    │
├──────────────┤                                            ├──────────────┤
│ Data:        │                Replaces:                   │ Data:        │
│   variables  │                • Code segment              │   wc's data  │
├──────────────┤                • Data segment              ├──────────────┤
│ Stack:       │                • Stack                     │ Stack:       │
│   call stack │                • Heap                      │   fresh      │
├──────────────┤                • Registers                 ├──────────────┤
│ Heap:        │                                            │ Heap:        │
│   malloc'd   │                                            │   empty      │
└──────────────┘                                            └──────────────┘
```

**Critical insight:** Code after `exec()` never runs (if successful)

```c
printf("Before exec\n");
execvp("ls", args);
printf("After exec\n");  // ⚠️ NEVER PRINTS (unless exec failed!)
```

**Why?** Because `exec()` replaces the entire program! It's like asking "What did you do after you died?" 💀 There is no "after" for a successful `exec()`.

**Proper error handling:**

```c
if (fork() == 0) {
    printf("Child: About to exec\n");
    execvp("some-program", args);

    // If we're here, exec() FAILED!
    perror("exec failed");  // Prints descriptive error
    exit(1);                // Exit with error code
}
```

> **💡 Insight**
>
> **Why separate fork() and exec()?** This seems wasteful—why copy the entire process just to throw it away? Two reasons:
> 1. **Simplicity:** Each system call does one thing well. Fork copies, exec transforms.
> 2. **Power:** The gap between fork and exec is where magic happens! The child can modify its environment (file descriptors, working directory) before calling exec. This enables I/O redirection, pipes, and other shell features without special support in exec itself.
>
> This is **separation of mechanism and policy** in action—a fundamental principle of elegant system design.

---

## 5. 🎨 Why This API? Design Motivation

### 5.1. 🐚 The UNIX Shell

**In plain English:** A shell is just a regular program 📝 that runs in a loop: (1) show a prompt, (2) read what you type, (3) run that program, (4) repeat. The fork-exec-wait pattern makes this incredibly simple to implement!

**Simplified shell pseudocode:**

```c
while (1) {
    printf("prompt> ");           // 1️⃣ Show prompt
    char *command = read_line();  // 2️⃣ Read user input

    if (strcmp(command, "exit") == 0) {
        break;  // Built-in command
    }

    char **args = parse_command(command);  // "ls -la" → ["ls", "-la", NULL]

    int rc = fork();              // 3️⃣ Create child
    if (rc == 0) {
        // Child executes the command
        execvp(args[0], args);
        perror("Command not found");
        exit(1);
    } else {
        // Parent waits for completion
        wait(NULL);               // 4️⃣ Wait for command to finish
    }

    // Loop back to prompt
}
```

**What happens when you type:** `ls -la /tmp`

```
Step-by-Step Execution
──────────────────────

1. Shell displays "prompt> "
2. You type "ls -la /tmp" and press Enter
3. Shell parses: args = ["ls", "-la", "/tmp", NULL]
4. Shell calls fork()
   └─ Creates child process (clone of shell)
5. Child calls execvp("ls", args)
   └─ Transforms into 'ls' program
   └─ Runs with arguments "-la /tmp"
6. Parent (shell) calls wait()
   └─ Blocks until 'ls' finishes
7. Child (now 'ls') executes, prints directory listing
8. Child exits
9. Parent wakes up from wait()
10. Shell displays "prompt> " again
```

**In technical terms:** The shell is the **first process** you interact with after logging in. Its job is to:
- 📖 Parse command strings
- 🍴 Fork children to run commands
- 🔄 Exec to transform children into requested programs
- ⏳ Wait for foreground processes (or not, for background `&`)

### 5.2. 🔀 I/O Redirection

**In plain English:** The separation of fork and exec creates a magical window ✨ where the child exists but hasn't transformed yet. During this window, we can mess with its file descriptors—changing where its input comes from or output goes to. This is how `>`, `<`, and `|` work!

**Example: Redirecting output to a file**

```bash
prompt> wc p3.c > newfile.txt
```

**What the shell does:**

```c
int rc = fork();
if (rc == 0) {
    // 🎯 The magic happens HERE (between fork and exec)!

    // Close stdout (file descriptor 1)
    close(STDOUT_FILENO);

    // Open output file (gets lowest available fd, which is 1)
    open("newfile.txt", O_CREAT|O_WRONLY|O_TRUNC, S_IRWXU);

    // Now stdout points to newfile.txt instead of terminal!

    // Execute the command
    char *args[] = {"wc", "p3.c", NULL};
    execvp(args[0], args);
} else {
    wait(NULL);
}
```

**Complete working example:**

```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <fcntl.h>
#include <sys/wait.h>

int main(int argc, char *argv[]) {
    int rc = fork();
    if (rc < 0) {
        fprintf(stderr, "fork failed\n");
        exit(1);
    } else if (rc == 0) {
        // 👶 Child: redirect standard output to a file

        close(STDOUT_FILENO);  // Close fd 1 (stdout)

        // Open file (automatically gets fd 1, the lowest available)
        open("./p4.output", O_CREAT|O_WRONLY|O_TRUNC, S_IRWXU);

        // Now any printf() or write() to stdout goes to file!

        // Execute wc
        char *myargs[3];
        myargs[0] = strdup("wc");
        myargs[1] = strdup("p4.c");
        myargs[2] = NULL;

        execvp(myargs[0], myargs);
    } else {
        // 👨 Parent waits
        int rc_wait = wait(NULL);
    }

    return 0;
}
```

**Output:**
```bash
prompt> ./p4
prompt> cat p4.output
32 109 846 p4.c
prompt>
```

**Why this works:**

```
File Descriptor Table Evolution
────────────────────────────────

Initial State (after fork):      After close(1):           After open():
┌─────────────────┐              ┌─────────────────┐       ┌─────────────────┐
│ 0: stdin        │              │ 0: stdin        │       │ 0: stdin        │
│ 1: stdout (tty) │      →       │ 1: [CLOSED]     │   →   │ 1: p4.output    │
│ 2: stderr       │              │ 2: stderr       │       │ 2: stderr       │
└─────────────────┘              └─────────────────┘       └─────────────────┘

Now printf() writes to p4.output instead of terminal!
```

**Key principle:** File descriptors are inherited across `exec()` ✅

> **💡 Insight**
>
> **The UNIX philosophy: Everything is a file.** Whether it's a text file 📄, a terminal 🖥️, a network socket 🌐, or a hardware device 🖨️, you use the same file operations: `open()`, `read()`, `write()`, `close()`. This powerful abstraction lets shells redirect I/O without knowing anything about the programs they're running. The programs don't need special "redirection support"—it's all handled by manipulating file descriptors before exec.

### 5.3. 🌊 Pipes and Command Composition

**In plain English:** Pipes `|` are like water pipes 🚰 connecting programs. The output of one program flows directly into the input of the next, creating powerful data processing chains 🔗.

**Example:** Count how many times "error" appears in a file

```bash
grep -o "error" file.txt | wc -l
```

**How pipes work:**

```
┌──────────┐      ┌────────┐      ┌──────────┐
│  grep    │──┬──→│ pipe   │──┬──→│    wc    │
│  process │  │   │ buffer │  │   │  process │
└──────────┘  │   └────────┘  │   └──────────┘
              │                │
           stdout            stdin
         (write end)      (read end)
```

**Shell implementation pseudocode:**

```c
// Create pipe
int pipefd[2];
pipe(pipefd);  // pipefd[0] = read end, pipefd[1] = write end

// First command: grep
if (fork() == 0) {
    close(pipefd[0]);              // Close read end (not needed)
    dup2(pipefd[1], STDOUT_FILENO); // Redirect stdout to write end
    close(pipefd[1]);              // Close original fd

    execlp("grep", "grep", "-o", "error", "file.txt", NULL);
}

// Second command: wc
if (fork() == 0) {
    close(pipefd[1]);              // Close write end (not needed)
    dup2(pipefd[0], STDIN_FILENO);  // Redirect stdin to read end
    close(pipefd[0]);              // Close original fd

    execlp("wc", "wc", "-l", NULL);
}

// Parent closes both ends and waits
close(pipefd[0]);
close(pipefd[1]);
wait(NULL);
wait(NULL);
```

**Complete pipe chain example:** `cat file | grep pattern | sort | uniq`

```
Process 1: cat file
    ↓ (pipe)
Process 2: grep pattern
    ↓ (pipe)
Process 3: sort
    ↓ (pipe)
Process 4: uniq
    ↓ (terminal)
```

**Why this is powerful:**

1. **Composability** 🧩: Combine simple tools to solve complex problems
2. **Reusability** ♻️: Each tool doesn't need to know about others
3. **Parallelism** ⚡: All processes run simultaneously (true pipelining!)

**Example of power:**

```bash
# Find the 10 most common words in a book
cat book.txt |
    tr '[:upper:]' '[:lower:]' |    # Convert to lowercase
    tr -cs '[:alpha:]' '\n' |        # One word per line
    sort |                            # Sort words
    uniq -c |                         # Count occurrences
    sort -rn |                        # Sort by count (descending)
    head -10                          # Top 10
```

Six simple programs, combined with pipes, perform sophisticated text analysis! 📊

> **💡 Insight**
>
> **The separation of fork() and exec() enables composition without coordination.** Each program in a pipeline doesn't need special "pipe support"—it just reads from stdin and writes to stdout. The shell handles all the plumbing 🔧. This is **loose coupling** in action, a fundamental principle of software engineering. Programs become Lego blocks 🧱 that snap together in unlimited combinations.

---

## 6. 👥 Process Control and Users

### 6.1. 📡 The Signal System

**In plain English:** Signals are like text messages 📨 you can send to processes. Some are polite requests ("Could you please stop?" 🙏), others are forceful commands ("Stop NOW!" 🛑). Processes can choose how to respond—or whether to respond at all.

**Common signals:**

```
Signal       Number   Meaning                      Default Action
──────       ──────   ───────                      ──────────────
SIGINT       2        Interrupt (Ctrl-C)           ❌ Terminate
SIGTERM      15       Polite termination request   ❌ Terminate
SIGKILL      9        Force kill (can't catch!)    ❌ Terminate
SIGSTOP      17       Stop process (Ctrl-Z)        ⏸️ Stop
SIGCONT      19       Continue stopped process     ▶️ Resume
SIGHUP       1        Hangup (terminal closed)     ❌ Terminate
SIGSEGV      11       Segmentation fault           💥 Crash + core dump
SIGUSR1/2    10/12    User-defined signals         ❌ Terminate
```

**Sending signals from shell:**

```bash
# Send signals by name
kill -INT 1234      # Same as Ctrl-C to process 1234
kill -TERM 1234     # Polite termination
kill -KILL 1234     # Force kill (can't be caught!)
kill -STOP 1234     # Pause process
kill -CONT 1234     # Resume process

# Shortcuts
kill 1234           # Defaults to SIGTERM
kill -9 1234        # SIGKILL (the "nuclear option")
```

**Keyboard shortcuts:**

```
Ctrl-C  →  SIGINT   (interrupt, usually terminates)
Ctrl-Z  →  SIGTSTP  (terminal stop, pauses process)
Ctrl-\  →  SIGQUIT  (quit with core dump)
```

**Catching signals in code:**

```c
#include <signal.h>
#include <stdio.h>
#include <unistd.h>

// Signal handler function
void handle_sigint(int sig) {
    printf("\n🛑 Caught SIGINT (Ctrl-C)! But I'm not stopping!\n");
    // Process can choose to ignore, log, cleanup, etc.
}

void handle_sigterm(int sig) {
    printf("\n🚪 Caught SIGTERM. Cleaning up and exiting...\n");
    // Do cleanup work
    exit(0);
}

int main() {
    // Register signal handlers
    signal(SIGINT, handle_sigint);   // Catch Ctrl-C
    signal(SIGTERM, handle_sigterm); // Catch kill command

    printf("Try pressing Ctrl-C or running 'kill %d' in another terminal!\n",
           getpid());
    printf("I'll catch SIGINT and SIGTERM, but not SIGKILL (kill -9).\n");

    while (1) {
        printf("Running... (PID: %d)\n", getpid());
        sleep(2);
    }

    return 0;
}
```

**Progressive Example:**

**Simple:** Ignore a signal
```c
signal(SIGINT, SIG_IGN);  // Ignore Ctrl-C (can't interrupt now!)
```

**Intermediate:** Custom cleanup
```c
void cleanup(int sig) {
    close_files();
    flush_buffers();
    printf("Goodbye!\n");
    exit(0);
}

signal(SIGTERM, cleanup);
signal(SIGINT, cleanup);
```

**Advanced:** Cooperative multi-process system
```c
// Parent sends work requests via SIGUSR1
// Child sends completion notifications via SIGUSR2

void parent_process() {
    pid_t child = fork();
    if (child == 0) {
        signal(SIGUSR1, handle_work_request);
        while (1) pause();  // Wait for signals
    } else {
        sleep(1);
        kill(child, SIGUSR1);  // Send work request
        pause();               // Wait for SIGUSR2 completion
    }
}
```

> **💡 Insight**
>
> **SIGKILL (signal 9) cannot be caught or ignored.** It's the OS's emergency shutdown button 🚨. Why have an uncatchable signal? Imagine a rogue process that ignores all termination requests—it would be unkillable! SIGKILL is the system administrator's last resort. This demonstrates an important principle: **ultimate control rests with the OS, not the application.**

### 6.2. 🔒 User Permissions

**In plain English:** Imagine a daycare 👶👧👦 where each parent can only pick up their own kids, not others'. Similarly, each user can only send signals to their own processes. This prevents chaos and malicious behavior!

**Permission rules:**

```
User Alice (UID: 1000)        User Bob (UID: 1001)
─────────────────────         ───────────────────

Processes owned:               Processes owned:
- PID 1234 ✅                  - PID 5678 ✅
- PID 1235 ✅                  - PID 5679 ✅

Can signal:                    Can signal:
- 1234, 1235 ✅               - 5678, 5679 ✅
- Bob's processes ❌           - Alice's processes ❌
```

**Example scenarios:**

```bash
# Alice tries to kill her own process
alice$ kill 1234
✅ Success!

# Alice tries to kill Bob's process
alice$ kill 5678
❌ Operation not permitted

# Alice runs a command
alice$ sleep 100 &
[1] 1236

# Bob tries to kill Alice's command
bob$ kill 1236
❌ Operation not permitted
```

**User ID system:**

```c
#include <unistd.h>
#include <stdio.h>

int main() {
    printf("Real UID:      %d\n", getuid());       // Who started this process
    printf("Effective UID: %d\n", geteuid());      // What permissions do we have
    printf("Process ID:    %d\n", getpid());       // Our process ID
    printf("Parent ID:     %d\n", getppid());      // Who forked us

    return 0;
}
```

**Real-world implications:**

```
Security Through Isolation
──────────────────────────

✅ Users can't interfere with each other
✅ Accidental kills are prevented
✅ Malicious users are contained
✅ System processes are protected
```

### 6.3. 👑 The Superuser (root)

**In plain English:** Every kingdom needs a king 👑 who can override the rules. In UNIX, that's the `root` user (UID 0). Root can do anything—kill any process, read any file, access any device. Great power, great responsibility! 🕷️

**Root's superpowers:**

```
Regular User (UID > 0)         Root (UID = 0)
──────────────────────         ──────────────

✅ Own processes               ✅ ALL processes
❌ Other users' processes      ✅ Other users' processes
✅ Own files                   ✅ ALL files
❌ System configuration        ✅ System configuration
❌ Hardware access             ✅ Hardware access
❌ Port < 1024                 ✅ Any port
❌ Install software            ✅ Install software
```

**Example operations:**

```bash
# Regular user
alice$ ps aux           # Can see all processes
alice$ kill 5678        # ❌ Can't kill Bob's process
alice$ rm /etc/passwd   # ❌ Can't modify system files

# Root
root# ps aux            # Can see all processes
root# kill 5678         # ✅ Can kill anyone's process
root# rm /etc/passwd    # ✅ Can delete critical system files (DON'T!)
root# killall chrome    # ✅ Can kill all Chrome processes for all users
```

**Becoming root:**

```bash
# Method 1: Switch user
$ su -           # Switch to root (need root password)
Password: ****
# whoami
root

# Method 2: Run single command as root (more common)
$ sudo kill 5678        # Run one command with root privileges
[sudo] password for alice: ****

# Method 3: Start a root shell
$ sudo -i               # Interactive root shell
root#
```

**Best practices:**

```
❌ DON'T:                      ✅ DO:
─────────                      ─────

Run as root by default  →      Use regular account daily
sudo rm -rf /*          →      Double-check dangerous commands
chmod 777 everything    →      Use minimum necessary permissions
Disable security        →      Use sudo only when needed
Leave root logged in    →      Exit root shell immediately after
```

**Real-world example: Restarting a system service**

```bash
# Regular user can't do this
alice$ systemctl restart nginx
❌ Failed to restart nginx.service: Access denied

# But sudo grants temporary root powers
alice$ sudo systemctl restart nginx
[sudo] password for alice: ****
✅ nginx.service restarted successfully
```

> **💡 Insight**
>
> **The principle of least privilege:** Run with the minimum permissions necessary. Most tasks don't need root—reading files, compiling code, running web browsers all work fine as a regular user. Only escalate to root for administrative tasks. Modern systems enforce this via:
> - 🔒 Default non-root accounts
> - ⚡ `sudo` for temporary elevation
> - 🔐 SELinux/AppArmor for fine-grained control
> - 🐳 Containers running as non-root users
>
> This is a fundamental security principle applicable far beyond operating systems—from database permissions to cloud IAM policies.

---

## 7. 🛠️ Useful Tools

### 7.1. 🖥️ Command-Line Process Tools

**In plain English:** The OS gives you a Swiss Army knife 🔪 of tools for inspecting and managing processes. Let's explore the essential ones!

#### 📊 ps (Process Status)

**Basic usage:**

```bash
# Show your processes
$ ps
  PID TTY          TIME CMD
 1234 pts/0    00:00:00 bash
 5678 pts/0    00:00:00 ps

# Show all processes (detailed)
$ ps aux
USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root         1  0.0  0.1  19856  1564 ?        Ss   08:00   0:01 /sbin/init
alice     1234  0.0  0.2  21532  2984 pts/0    Ss   09:23   0:00 -bash
alice     5678  2.5  1.4 123456 15000 pts/0    R+   10:15   0:03 python script.py
```

**Column meanings:**

```
Column    Meaning
──────    ───────
USER      Who owns this process
PID       Process ID (unique identifier)
%CPU      CPU usage percentage
%MEM      Memory usage percentage
VSZ       Virtual memory size (KB)
RSS       Resident set size (physical RAM in KB)
TTY       Terminal associated with process
STAT      Process state (see below)
START     When process started
TIME      Total CPU time used
COMMAND   Command line that started process
```

**Process states (STAT column):**

```
Code    Meaning
────    ───────
R       Running or runnable (on run queue) 🏃
S       Sleeping (waiting for event) 😴
D       Uninterruptible sleep (usually I/O) 💤
Z       Zombie (finished but not reaped) 🧟
T       Stopped (Ctrl-Z or signal) ⏸️
<       High priority
N       Low priority
+       Foreground process group
l       Multi-threaded
```

**Useful ps variations:**

```bash
# Show process tree (parent-child relationships)
$ ps auxf
# or
$ pstree

# Show processes for specific user
$ ps -u alice

# Show specific process by PID
$ ps -p 1234

# Custom columns
$ ps -eo pid,ppid,cmd,pcpu,pmem
  PID  PPID CMD                         %CPU %MEM
 1234     1 /usr/bin/python server.py    2.5  1.4
```

#### 📈 top (Process Monitor)

**In plain English:** `top` is like a live dashboard 📊 showing which processes are hogging resources. It updates every few seconds.

```bash
$ top

top - 10:23:45 up 5 days,  2:15,  3 users,  load average: 0.45, 0.38, 0.32
Tasks: 247 total,   2 running, 245 sleeping,   0 stopped,   0 zombie
%Cpu(s):  5.2 us,  1.3 sy,  0.0 ni, 93.2 id,  0.3 wa,  0.0 hi,  0.0 si,  0.0 st
MiB Mem :   7872.2 total,   1234.5 free,   3456.7 used,   3181.0 buff/cache
MiB Swap:   2048.0 total,   2048.0 free,      0.0 used.   3987.2 avail Mem

  PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
 5678 alice     20   0 1234567 123456  45678 R  25.0   1.5   0:12.34 python
 1234 bob       20   0  987654  87654  32109 S  10.5   1.1   1:23.45 chrome
```

**Useful keybindings:**

```
Key     Action
───     ──────
M       Sort by memory usage 💾
P       Sort by CPU usage 🔥
k       Kill a process 💀
r       Renice (change priority) ⚖️
u       Filter by user 👤
1       Show individual CPU cores 🖥️
q       Quit ❌
```

**Modern alternative: htop**

```bash
$ htop  # More colorful, user-friendly, interactive
```

#### 💀 kill / killall (Send Signals)

```bash
# Send SIGTERM (polite request to terminate)
$ kill 1234

# Send SIGKILL (force kill, no cleanup)
$ kill -9 1234
$ kill -KILL 1234

# Send other signals
$ kill -STOP 1234    # Pause process
$ kill -CONT 1234    # Resume process
$ kill -HUP 1234     # Reload configuration (common for servers)

# Kill all processes by name
$ killall firefox    # Kills all firefox processes

# Kill all processes matching pattern
$ pkill python       # Kills all processes with 'python' in command
```

### 7.2. 🔍 Monitoring and Control

**Advanced process management:**

#### jobs, fg, bg (Shell Job Control)

```bash
# Start long-running process in background
$ sleep 100 &
[1] 5678

# List background jobs
$ jobs
[1]+  Running                 sleep 100 &

# Bring to foreground
$ fg %1
sleep 100
^Z                  # Press Ctrl-Z to stop
[1]+  Stopped                 sleep 100

# Resume in background
$ bg %1
[1]+ sleep 100 &

# Kill background job
$ kill %1
```

#### systemctl (Service Management)

```bash
# Check service status
$ systemctl status nginx
● nginx.service - A high performance web server
     Loaded: loaded (/lib/systemd/system/nginx.service)
     Active: active (running) since Mon 2025-01-06 08:00:00 PST

# Start/stop/restart services
$ sudo systemctl start nginx
$ sudo systemctl stop nginx
$ sudo systemctl restart nginx

# Enable/disable auto-start
$ sudo systemctl enable nginx   # Start on boot
$ sudo systemctl disable nginx  # Don't start on boot
```

#### lsof (List Open Files)

```bash
# See what files a process has open
$ lsof -p 1234

# See which process has a file open
$ lsof /var/log/syslog

# See network connections
$ lsof -i        # All network connections
$ lsof -i :80    # What's using port 80?
```

#### strace (System Call Tracer)

```bash
# See every system call a program makes
$ strace ls
execve("/bin/ls", ["ls"], [/* 27 vars */]) = 0
brk(NULL)                               = 0x55a4b0e9c000
access("/etc/ld.so.preload", R_OK)      = -1 ENOENT (No such file)
openat(AT_FDCWD, "/etc/ld.so.cache", O_RDONLY|O_CLOEXEC) = 3
...

# Trace specific system calls
$ strace -e open,read,write cat file.txt

# Attach to running process
$ strace -p 1234
```

> **💡 Insight**
>
> **Process monitoring tools are essential for debugging production issues.** When a system is slow 🐌, these tools help you answer:
> - 🔍 Which process is using all the CPU?
> - 💾 Is memory exhausted?
> - 💤 Is a process stuck in I/O?
> - 🔌 What network connections exist?
> - 🚨 Are processes crashing and respawning?
>
> Master these tools, and you'll be the hero 🦸 who can debug that mysterious production outage at 3 AM.

---

## 8. 📝 Summary

**Key Takeaways:** 🎯

### **1. The Three Musketeers of Process Management** ⚔️

```
fork()  → 👯 Create a copy of the current process
exec()  → 🔄 Transform process into a different program
wait()  → ⏳ Synchronize parent with child completion
```

**Together they form:** The most elegant process creation API in computing history! 🏆

### **2. fork() Magic** 🪞

- Creates identical copy of calling process
- Returns twice: once in parent (child's PID), once in child (0)
- Child inherits: memory, file descriptors, register state
- Execution order is nondeterministic (scheduler decides)

```c
int pid = fork();
if (pid == 0) {
    // Child code
} else {
    // Parent code (pid = child's PID)
}
```

### **3. wait() Synchronization** ⏳

- Blocks parent until child exits
- Returns child's PID and exit status
- Makes output deterministic
- Prevents zombie accumulation 🧟

```c
int status;
pid_t child = wait(&status);
if (WIFEXITED(status)) {
    printf("Child exited with code %d\n", WEXITSTATUS(status));
}
```

### **4. exec() Transformation** 🔄

- Replaces current process with new program
- Keeps: PID, file descriptors, working directory
- Replaces: code, data, stack, heap
- Never returns on success!

```c
execvp("ls", args);  // This process is now 'ls'
// Never reaches here (unless exec failed)
```

### **5. Separation Powers the Shell** 🐚

**The gap between fork() and exec() enables:**

```
fork()
  ↓
  🎯 Magic happens here!
  • Modify file descriptors (I/O redirection)
  • Set up pipes (command composition)
  • Change working directory
  • Drop privileges
  ↓
exec()
```

**Result:** Shells can implement powerful features without modifying programs!

### **6. I/O Redirection** 🔀

```bash
command < input.txt > output.txt 2> errors.txt

Translates to:
fork() → manipulate fds 0, 1, 2 → exec(command)
```

### **7. Pipes** 🌊

```bash
cmd1 | cmd2 | cmd3

Translates to:
pipe() → fork() → dup2() → exec(cmd1)
pipe() → fork() → dup2() → exec(cmd2)
fork() → dup2() → exec(cmd3)
```

### **8. Signals** 📡

```
SIGINT  (Ctrl-C)  → Interrupt
SIGTERM           → Polite termination
SIGKILL           → Force kill (uncatchable!)
SIGSTOP (Ctrl-Z)  → Pause
SIGCONT           → Resume
```

Programs can catch signals with `signal()` handler registration.

### **9. Permissions** 🔒

- Users can only signal their own processes
- Root (UID 0) can signal any process
- Principle of least privilege: avoid running as root

### **10. Useful Tools** 🛠️

```
ps      → Snapshot of processes 📸
top     → Live process monitor 📊
kill    → Send signals 💀
jobs    → Shell job control 🎮
lsof    → Open files and connections 🔍
strace  → System call tracer 🔬
```

**Fundamental Design Principles Demonstrated:** 💡

1. **Separation of Concerns** 🧩
   - fork() does one thing: copy
   - exec() does one thing: transform
   - wait() does one thing: synchronize

2. **Composition** 🔗
   - Simple primitives combine for complex behavior
   - Pipes enable unlimited program chaining

3. **Abstraction** 🎭
   - Programs don't know if stdin is keyboard or file
   - Everything is a file descriptor

4. **Mechanism vs. Policy** ⚙️
   - System calls provide mechanism (how)
   - Applications choose policy (what)

**What's Next:** 🚀

Now that you've mastered process creation and control, upcoming chapters explore:
- 🔄 **Process scheduling**: How does the OS decide which process runs next?
- 💾 **Memory virtualization**: How does each process get its own address space?
- 🤝 **Inter-process communication**: How do processes coordinate and share data?
- 🧵 **Threads**: Lightweight processes within a process

---

**Previous:** [Chapter 1: Processes](chapter1-processes.md) | **Next:** [Chapter 3: Scheduling](chapter3-scheduling.md)
