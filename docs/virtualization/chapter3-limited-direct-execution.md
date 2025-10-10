# Chapter 3: Mechanism: Limited Direct Execution ⚡

_How the OS virtualizes the CPU while maintaining control and performance_

---

## 📋 Table of Contents

1. [🎯 Introduction](#1-introduction)
2. [🚀 Basic Technique: Limited Direct Execution](#2-basic-technique-limited-direct-execution)
   - 2.1. [Direct Execution Without Limits](#21-direct-execution-without-limits)
3. [🔒 Problem #1: Restricted Operations](#3-problem-1-restricted-operations)
   - 3.1. [User Mode vs Kernel Mode](#31-user-mode-vs-kernel-mode)
   - 3.2. [System Calls and Traps](#32-system-calls-and-traps)
   - 3.3. [The Trap Table](#33-the-trap-table)
   - 3.4. [Complete LDE Protocol (Part 1)](#34-complete-lde-protocol-part-1)
4. [⏱️ Problem #2: Switching Between Processes](#4-problem-2-switching-between-processes)
   - 4.1. [Cooperative Approach](#41-cooperative-approach)
   - 4.2. [Non-Cooperative Approach: Timer Interrupts](#42-non-cooperative-approach-timer-interrupts)
   - 4.3. [Context Switching](#43-context-switching)
   - 4.4. [Complete LDE Protocol (Part 2)](#44-complete-lde-protocol-part-2)
5. [🔄 Worried About Concurrency?](#5-worried-about-concurrency)
6. [📝 Summary](#6-summary)

---

## 1. 🎯 Introduction

**In plain English:** Imagine you're managing a shared kitchen 👨‍🍳 in an apartment building. You want everyone to cook efficiently, but you also need to prevent disasters—like someone turning on all burners at once 🔥, or monopolizing the kitchen for hours. You need both **speed** (let people cook directly) and **control** (step in when needed).

**In technical terms:** To virtualize the CPU, the OS must time-share it among many processes, running each for a little while then switching to another. This creates two critical challenges:
1. **Performance** 🚀 - How to virtualize without excessive overhead?
2. **Control** 🎮 - How to run processes efficiently while retaining control?

Without control, a process could run forever and take over the machine, or access forbidden information. The OS must achieve high performance while maintaining control—the central challenge of CPU virtualization.

**Why it matters:** This mechanism is the foundation of modern multitasking. Every time you switch browser tabs while music plays in the background, limited direct execution is at work. Understanding this mechanism reveals how your computer does so much with so little 💪.

> **💡 Insight**
>
> The tension between **performance** and **control** appears throughout computer systems: JIT compilers (fast execution vs safety), web browsers (speed vs security sandboxing), and databases (fast queries vs transaction isolation). Limited Direct Execution's solution—hardware-assisted privilege separation—is a pattern you'll see repeatedly in system design.

### 🎯 The Core Challenge

**THE CRUX:** How can the OS efficiently virtualize the CPU with control?

The OS must virtualize the CPU in an efficient manner while retaining control over the system. To do so, **both hardware and operating-system support** will be required. The OS will use judicious bits of hardware support to accomplish its work effectively.

**Two key problems to solve:**

```
Problem #1: Restricted Operations     Problem #2: Switching Processes
─────────────────────────────────     ──────────────────────────────
How to let processes perform I/O   →  How to regain control if a
and privileged operations without  →  process won't give up the CPU?
giving them complete control?

Solution: User/Kernel modes        →  Solution: Timer interrupts
          + System calls           →            + Context switching
```

---

## 2. 🚀 Basic Technique: Limited Direct Execution

**In plain English:** The simplest way to make a program run fast is... to just run it! 💨 Don't add layers of interpretation or emulation. Load it into memory and let the CPU execute it directly. But **unlimited** direct execution is dangerous—hence we add **limits**.

**In technical terms:** **Limited Direct Execution (LDE)** means:
- **Direct Execution** ⚡ - Run the program directly on the CPU (no virtualization overhead)
- **Limited** 🚧 - Restrict what the program can do without OS assistance

### 2.1. 📋 Direct Execution Without Limits

Here's what happens when the OS simply runs a program without any restrictions:

```
OS                                    Program
──────────────────────────────────    ───────────────────────────
Create entry for process list
Allocate memory for program
Load program into memory (from disk)
Set up stack with argc/argv
Clear registers
Execute call main()                →  Run main()
                                      Execute return from main()
                                  ←
Free memory of process
Remove from process list
```

**Looks simple, right?** ✅ But this approach has serious problems:

**Problem 1:** If we just run a program, how can the OS ensure it doesn't do anything harmful while still running efficiently? 🤔

**Problem 2:** When a process is running on the CPU, the OS is **not** running. If the OS isn't running, how can it switch to another process to implement time-sharing? 🤔

> **💡 Insight**
>
> The "**limited**" part of the name is crucial. Without limits, the OS would be "just a library"—a sad state of affairs! 😢 This reveals a fundamental truth about OS design: **the OS is not continuously executing**. It's more like a puppet master 🎭 that sets up mechanisms, then steps back while processes run, ready to jump in when triggered by events (system calls, interrupts, exceptions).

---

## 3. 🔒 Problem #1: Restricted Operations

### 3.1. 🚦 User Mode vs Kernel Mode

**In plain English:** Think of user mode and kernel mode like a theme park 🎢. Normal visitors (user programs) can ride rides but can't access the control room 🎛️. Park employees (OS/kernel) can access the control room and perform privileged operations like emergency stops. If we let visitors into the control room, chaos ensues! 💥

**THE CRUX:** How can a process perform I/O and other restricted operations without giving it complete control over the system?

**The solution:** Two processor modes provided by hardware:

```
┌─────────────────────────────────────────────────┐
│  👤 USER MODE (Restricted)                      │
│  • Cannot issue I/O requests                    │
│  • Cannot access privileged instructions        │
│  • Cannot modify hardware configuration         │
│  • Cannot access other processes' memory        │
│                                                  │
│  Violation → 💥 Exception → OS kills process    │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  👑 KERNEL MODE (Privileged)                    │
│  • Full access to hardware resources            │
│  • Can execute all instructions                 │
│  • Can issue I/O requests                       │
│  • Can modify page tables, interrupts, etc.     │
│                                                  │
│  Only the OS runs in this mode                  │
└─────────────────────────────────────────────────┘
```

**Examples of restricted operations:**
- 💾 Issuing I/O requests to disk/network
- 🔧 Accessing CPU control registers
- 💻 Modifying page tables (memory mapping)
- ⏰ Configuring hardware timers
- 🔌 Enabling/disabling interrupts

**But what if a user process NEEDS to do I/O?** 🤔 We can't just say "no" to reading files! That's where system calls come in...

### 3.2. 📞 System Calls and Traps

**In plain English:** A system call is like a request form 📋 you fill out to ask the theme park employee (OS) to do something privileged for you. You can't enter the control room yourself, but you can ask someone who can. The employee checks your request, and if it's valid, performs the operation for you.

**Progressive Example:**

**Simple:** Reading a file
```c
// User program wants to read file (requires I/O - privileged!)
char buffer[100];
read(file_descriptor, buffer, 100);  // This is a system call!
```

**Intermediate:** What actually happens
```
User Program                    Hardware                OS Kernel
────────────────                ────────                ─────────
read() function    →
(in C library)

Put syscall# in register
Put args in registers/stack

Execute TRAP instruction  →     Save registers  →
                                Switch to
                                kernel mode
                                Jump to trap      →  Trap handler runs
                                handler              Check syscall number
                                                     Validate arguments
                                                     Perform disk read

                          ←     Restore registers ←  Return-from-trap
                                Switch to            instruction
                                user mode
                                Resume execution

Got data! Continue...
```

**Advanced:** The trap instruction mechanics

**The TRAP instruction does three critical things:** 🎯

1. **Saves state** 💾
   - Push program counter (PC) onto kernel stack
   - Push flags register onto kernel stack
   - Save other critical registers

2. **Raises privilege** 👑
   - Switch CPU from user mode → kernel mode
   - Now privileged instructions are allowed

3. **Jumps into kernel** 🚀
   - Jump to pre-configured trap handler address
   - OS code now executes

**The RETURN-FROM-TRAP instruction reverses this:** ↩️

1. **Restores state** 🔄
   - Pop registers from kernel stack
   - Pop flags from kernel stack
   - Pop PC from kernel stack

2. **Reduces privilege** 👤
   - Switch CPU from kernel mode → user mode
   - Privileged instructions no longer allowed

3. **Returns to user program** 🏃
   - Jump to address in restored PC
   - User code continues executing

> **💡 Insight**
>
> **Why system calls look like procedure calls:** 🤔
>
> When you call `open()` or `read()`, it looks exactly like a regular C function call. Why? Because it IS a procedure call—but hidden inside that library function is the trap instruction! The C library:
> 1. Puts system call arguments in well-known locations (registers/stack)
> 2. Puts the system call **number** in a well-known register
> 3. Executes the `trap` instruction (hand-coded in assembly)
> 4. After trap returns, unpacks return values
>
> This is why you don't write assembly to make system calls—someone already did it for you in libc! 🎉

### 3.3. 📚 The Trap Table

**In plain English:** When you trip a burglar alarm 🚨, it doesn't call random phone numbers—it calls the police 👮 at a pre-configured number. Similarly, when a trap occurs, the hardware doesn't jump to a random address (security disaster! 💥). Instead, it jumps to a pre-configured **trap handler** address set up at boot time.

**The critical question:** When a trap instruction executes, which code should run in the kernel? 🤔

**Bad idea:** ❌ Let the calling process specify an address
```c
// DON'T DO THIS! Security nightmare!
trap(0x8000deadbeef);  // Jump to arbitrary kernel code
                       // Could bypass permission checks!
                       // Could execute arbitrary kernel code!
```

**Good idea:** ✅ The kernel sets up a trap table at boot

**Trap table setup (at boot time):**

```
Boot Sequence (Kernel Mode)
────────────────────────────

┌─────────────────────────────────────────┐
│  1. Machine boots in kernel mode        │
│     (privileged from the start)         │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│  2. OS configures trap table            │
│                                          │
│     Event             Handler Address   │
│     ──────────────    ───────────────   │
│     System call   →   0x8000_1000       │
│     Timer int.    →   0x8000_2000       │
│     Disk int.     →   0x8000_3000       │
│     Keyboard int. →   0x8000_4000       │
│     Div-by-zero   →   0x8000_5000       │
│     Page fault    →   0x8000_6000       │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│  3. Hardware remembers these addresses  │
│     (until next reboot)                 │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│  4. Start running user programs         │
│     (now in user mode)                  │
└─────────────────────────────────────────┘
```

**At runtime (when trap occurs):**

```c
// User code
read(fd, buf, 100);  // Makes system call

// Hardware (automatically):
1. Look up syscall handler in trap table → 0x8000_1000
2. Save registers to kernel stack
3. Switch to kernel mode
4. Jump to 0x8000_1000

// Kernel trap handler at 0x8000_1000:
void syscall_handler() {
    int syscall_num = get_syscall_number();  // From register

    switch(syscall_num) {
        case SYS_READ:
            do_read();
            break;
        case SYS_WRITE:
            do_write();
            break;
        // ... hundreds of system calls
    }

    return_from_trap();  // Back to user code
}
```

**System call numbers provide indirection:** 🎯

Instead of jumping to arbitrary addresses, user code specifies a **number**:
- System call #0: `read()`
- System call #1: `write()`
- System call #2: `open()`
- System call #3: `close()`
- ... (Linux has ~300+ system calls)

The OS validates the number and executes corresponding code. This **indirection** provides protection! 🔒

> **💡 Insight**
>
> **Setting up the trap table is extremely powerful** 💪—and therefore privileged! If you could install your own trap table as a user program, you could:
> - Intercept all system calls (steal passwords 🔑)
> - Bypass permission checks (read any file 📁)
> - Execute arbitrary kernel code (own the machine 💻)
>
> This is why installing trap tables is a **privileged operation**. Try it in user mode? 💥 Exception → OS kills your process. This illustrates a key OS principle: **powerful capabilities must be privileged**.

### 3.4. 📊 Complete LDE Protocol (Part 1)

**The two-phase protocol for limited direct execution:**

```
╔═══════════════════════════════════════════════════════════════╗
║  PHASE 1: AT BOOT TIME (Kernel Mode)                         ║
╚═══════════════════════════════════════════════════════════════╝

OS @ boot                          Hardware
─────────────────────────────      ────────────────────────
Initialize trap table       →      Remember addresses of:
                                   • syscall handler
                                   • timer handler
                                   • exception handlers
                                   (stored until reboot)


╔═══════════════════════════════════════════════════════════════╗
║  PHASE 2: WHEN RUNNING A PROCESS                              ║
╚═══════════════════════════════════════════════════════════════╝

OS @ run                    Hardware                 Program
(kernel mode)                                        (user mode)
─────────────────           ────────────             ───────────
Create entry for
process list

Allocate memory
for program

Load program into
memory

Setup user stack
with argv

Fill kernel stack
with reg/PC

return-from-trap    →      Restore regs
                           (from kernel stack)

                           Move to user mode

                           Jump to main      →      Run main()
                                                     ...
                                                     Call system call

                           Save regs         ←      trap into OS
                           (to kernel stack)

                           Move to kernel
                           mode

                           Jump to trap      →
                           handler
                                                     Handle trap
                                                     Do work of syscall

                    ←      Restore regs      ←      return-from-trap
                           (from kernel
                           stack)

                           Move to user
                           mode

                           Jump to PC after  →      ...
                           trap                     return from main

                           Save regs         ←      trap (via exit())
                           Move to kernel
                           mode
                           Jump to trap      →
                           handler

Free memory of
process

Remove from
process list
```

**Key observations:** 🔍

1. **Two stacks per process** 📚
   - **User stack**: For normal function calls in user code
   - **Kernel stack**: For saving state during traps/syscalls

2. **Privilege transitions** 🔄
   - return-from-trap: kernel mode → user mode (start process)
   - trap: user mode → kernel mode (system call)
   - return-from-trap: kernel mode → user mode (resume process)

3. **The OS sets up and tears down** 🔧
   - Process creation/destruction happens in kernel mode
   - Actual execution happens in user mode (fast!)
   - OS only runs during traps/interrupts (efficient!)

**Security consideration:** 🔒

```
⚠️  USER INPUT MUST BE VALIDATED! ⚠️

Example: write(fd, buffer, size)

OS must check:
✅ Is fd a valid file descriptor?
✅ Does this process have permission to write to it?
✅ Is buffer address valid and in user space?
   (not pointing into kernel memory!)
✅ Is size reasonable? (not 2^64 bytes!)

Failing to validate → Security vulnerabilities! 🐛
```

> **💡 Insight**
>
> **Treat all user inputs with suspicion** 🕵️. Even a "simple" system call like `write()` requires careful validation:
> - Buffer addresses could point into kernel memory (leak secrets!)
> - Sizes could be negative or huge (crash system!)
> - File descriptors could be invalid (access wrong files!)
>
> This paranoid approach is essential for secure systems. One tiny validation bug can compromise the entire OS. Many real-world exploits (privilege escalation, information leaks) stem from inadequate input validation at the system call boundary.

---

## 4. ⏱️ Problem #2: Switching Between Processes

**The philosophical problem:** 🤔

If a process is **running** on the CPU, then by definition the **OS is not running**. If the OS isn't running, how can it do anything at all? (Hint: it can't!)

While this sounds philosophical, it's a **real problem**: there is clearly no way for the OS to take action if it isn't running on the CPU.

**THE CRUX:** How can the OS regain control of the CPU so it can switch between processes?

Two approaches have been used historically:

### 4.1. 🤝 Cooperative Approach

**In plain English:** In a cooperative system, processes are trusted to be "good citizens" 🎩. They're expected to periodically yield the CPU voluntarily, like polite dinner guests who don't monopolize the conversation 🍽️. Everyone takes turns cooperatively.

**How processes give up the CPU cooperatively:**

```
Method 1: System Calls (frequent)
─────────────────────────────────
read(), write(), open()          →  Transfer control to OS
send(), recv()                   →  OS can switch processes
fork(), exec()                   →  if it wants to

Method 2: Explicit Yield
────────────────────────
yield()                          →  "I don't need CPU now"
                                 →  Let someone else run

Method 3: Illegal Operations
────────────────────────────
divide_by_zero()                 →  Exception → Trap to OS
access_invalid_memory()          →  OS kills process
```

**Example: Cooperative scheduling**
```c
// Process A
void process_a() {
    for (int i = 0; i < 100; i++) {
        do_work();
        yield();  // ✅ Be nice, give others a turn
    }
}

// Process B
void process_b() {
    while (true) {
        compute();
        if (need_io()) {
            read_file();  // ✅ System call transfers control
        }
        yield();  // ✅ Voluntary yield
    }
}
```

**Early systems using cooperative scheduling:** 📜
- Early Macintosh OS 🍎
- Xerox Alto
- Windows 3.1 (16-bit)
- Classic Mac OS (pre-OS X)

**The fatal flaw:** ❌

```c
// Malicious (or buggy) process
void evil_process() {
    while (1) {
        // Infinite loop
        // Never makes system calls
        // Never yields
        // NEVER GIVES UP CPU! 😈
    }
}

// Result: Machine becomes unresponsive
// Only solution: Reboot! 🔄
```

**This passive approach is less than ideal!** What happens if a process (malicious or buggy) ends up in an infinite loop and never makes a system call? The OS can't do anything! ⚠️

Your only recourse: **reboot the machine** 🔄 (the ultimate solution to all computer problems! 😅)

### 4.2. ⏰ Non-Cooperative Approach: Timer Interrupts

**THE CRUX:** How can the OS gain control of the CPU even if processes are not being cooperative?

**The answer:** A **timer interrupt** ⏰—a hardware mechanism discovered many years ago that gives the OS periodic control.

**In plain English:** Imagine you're mediating a debate 🎤 but speakers ignore time limits. You set a kitchen timer ⏲️ that dings every 5 minutes. When it dings, you **forcefully** take the microphone 🎤, regardless of whether the speaker wants to stop. The timer gives you **non-cooperative control**.

**How timer interrupts work:**

```
╔═══════════════════════════════════════════════════════════════╗
║  AT BOOT TIME (Kernel Mode)                                   ║
╚═══════════════════════════════════════════════════════════════╝

OS                                    Hardware
──────────────────────────────        ───────────────────────
1. Install trap table          →      Remember timer handler
   (timer handler address)            address

2. Start timer                 →      Configure timer device
   (interrupt every 10ms)              Start counting...

3. Start first process         →


╔═══════════════════════════════════════════════════════════════╗
║  DURING EXECUTION                                              ║
╚═══════════════════════════════════════════════════════════════╝

Time    Process State          Hardware Timer    Action
─────   ─────────────────      ──────────────   ────────────────
0ms     Process A running      Started (10ms)
1ms     Process A running      9ms left
2ms     Process A running      8ms left
...
9ms     Process A running      1ms left
10ms    TIMER FIRES! ⏰        0ms → RESET!     Interrupt!

        Hardware Actions:
        ─────────────────
        1. 💾 Save A's registers → kernel stack
        2. 🔒 Switch to kernel mode
        3. 🚀 Jump to timer interrupt handler

        OS timer handler runs:
        ───────────────────────
        if (should_switch()) {
            context_switch(A, B);  // Switch to Process B
        }
        return_from_trap();        // Resume execution

10ms    Process B running       Started (10ms)   Timer reset
11ms    Process B running       9ms left
...
20ms    TIMER FIRES! ⏰        0ms → RESET!     Interrupt again!

        (repeat forever...)
```

**Timer interrupt properties:** 🎯

1. **Pre-configured frequency** ⏱️
   - Typically 10-100 times per second
   - Linux default: 100 Hz (every 10ms) or 1000 Hz (every 1ms)
   - Configurable for different workloads

2. **Non-maskable (mostly)** 🔓
   - Process cannot prevent timer interrupts
   - Ensures OS always regains control
   - (Some critical sections can temporarily disable interrupts)

3. **Hardware-driven** 🔧
   - Independent timer device on motherboard
   - Raises interrupt line on CPU
   - CPU automatically vectors to handler

4. **Privileged configuration** 👑
   - Starting/stopping timer requires kernel mode
   - User processes cannot disable it
   - Prevents malicious processes from gaining control

**Progressive Example:**

**Simple:** Single rogue process
```
Without timer:                    With timer:
─────────────                     ──────────────
Process runs forever ♾️           0-10ms: Process A runs
System hangs 🔒                   10ms: INTERRUPT! ⏰
Must reboot 🔄                    10-20ms: Process B runs
                                  20ms: INTERRUPT! ⏰
                                  20-30ms: Process A runs
                                  System responsive! ✅
```

**Intermediate:** CPU-bound vs I/O-bound
```c
// CPU-bound process (uses full time slice)
void cpu_bound() {
    while (1) {
        compute_pi();  // No system calls
        // Timer interrupt will force switch after 10ms ⏰
    }
}

// I/O-bound process (yields early)
void io_bound() {
    while (1) {
        char c = getchar();  // System call - voluntary yield
        process(c);
        // Doesn't need full 10ms time slice
    }
}
```

**Advanced:** Timer interrupt handling
```c
// Timer interrupt handler (in OS kernel)
void timer_interrupt_handler() {
    // 1. Hardware has already saved registers

    // 2. Update statistics
    current_process->ticks_used++;
    total_ticks++;

    // 3. Decide whether to switch
    if (current_process->ticks_used >= TIME_SLICE) {
        current_process->ticks_used = 0;

        // 4. Context switch to next process
        struct proc *next = scheduler_pick_next();
        context_switch(current_process, next);
    }

    // 5. Return-from-trap (to current or next process)
    return_from_trap();
}
```

> **💡 Insight**
>
> **The timer interrupt is essential for OS control** ⚡. Without it, cooperative scheduling is the only option, and one buggy/malicious process can hang the entire system. This illustrates a fundamental OS principle: **hardware mechanisms enable OS policies**. The timer (mechanism) allows the OS to implement various scheduling policies (round-robin, priority-based, fair-share, etc.) without cooperation from processes.

**Historical note:** 🏛️ Reboot as a feature!

```
Researchers have shown reboot is actually USEFUL! 🔄

Benefits of periodic reboots:
✅ Returns software to known/tested state
✅ Reclaims leaked resources (memory, handles)
✅ Easy to automate

Large internet services often:
• Periodically reboot machines in clusters
• Improve system reliability
• Prevent resource exhaustion

Next time you reboot: You're not hacking, you're using
a time-tested reliability technique! 😄
```

### 4.3. 🔄 Context Switching

**In plain English:** A context switch is like switching actors 🎭 on stage. Actor A leaves, and you need to:
1. Remember where Actor A was in the script 📜 (save their state)
2. Bring out Actor B with their script position 📍 (restore their state)
3. Continue the play with Actor B 🎬

**In technical terms:** A **context switch** is the OS mechanism for switching from one process to another. It involves:
1. **Saving** register values of currently-running process
2. **Restoring** register values of soon-to-be-executing process
3. **Switching** kernel stacks

**What triggers a context switch?** 🔔

```
Trigger Events
──────────────
1. ⏰ Timer interrupt fired (time slice expired)
2. 💤 Process blocked on I/O (can't run anyway)
3. 🚀 Process yielded voluntarily
4. 💀 Process exited/terminated
5. ⚡ Higher-priority process became ready
```

**The context switch process:**

```
╔═══════════════════════════════════════════════════════════════╗
║  BEFORE: Process A is Running                                 ║
╚═══════════════════════════════════════════════════════════════╝

CPU Registers              Process A PCB            Process B PCB
─────────────              ─────────────            ─────────────
eip = 0x4000 ⭐           eip = (old)              eip = 0x8000
esp = 0x7fff ⭐           esp = (old)              esp = 0x6fff
ebx = 42 ⭐               ebx = (old)              ebx = 100
ecx = 73 ⭐               ...                       ...
edx = 15 ⭐               state = RUNNING          state = READY
...                       kernel_stack = 0xA000    kernel_stack = 0xB000


╔═══════════════════════════════════════════════════════════════╗
║  STEP 1: Timer Interrupt Fires                                 ║
╚═══════════════════════════════════════════════════════════════╝

Action: Hardware saves A's registers → A's kernel stack
        OS decides to switch to Process B


╔═══════════════════════════════════════════════════════════════╗
║  STEP 2: Context Switch Routine (in kernel)                    ║
╚═══════════════════════════════════════════════════════════════╝

void context_switch(struct proc *old, struct proc *new) {
    // 1. Save OLD process's registers to its PCB
    old->context.eip = CPU.eip;  // 💾 Save where we were
    old->context.esp = CPU.esp;  // 💾 Save stack pointer
    old->context.ebx = CPU.ebx;  // 💾 Save all registers
    // ... save all other registers

    // 2. Update states
    old->state = READY;          // No longer running

    // 3. Switch kernel stacks! (critical!)
    switch_to_kernel_stack(new->kernel_stack);

    // 4. Restore NEW process's registers from its PCB
    CPU.eip = new->context.eip;  // 📍 Jump to where B was
    CPU.esp = new->context.esp;  // 📚 Restore B's stack
    CPU.ebx = new->context.ebx;  // ⚡ Restore B's registers
    // ... restore all other registers

    // 5. Update state
    new->state = RUNNING;        // Now running!

    // 6. Return (but into new process's context!)
}


╔═══════════════════════════════════════════════════════════════╗
║  STEP 3: Return-from-trap (into Process B)                     ║
╚═══════════════════════════════════════════════════════════════╝

Hardware: Pop registers from B's kernel stack
          Switch to user mode
          Jump to eip (now 0x8000 - Process B's code!)


╔═══════════════════════════════════════════════════════════════╗
║  AFTER: Process B is Running                                  ║
╚═══════════════════════════════════════════════════════════════╝

CPU Registers              Process A PCB            Process B PCB
─────────────              ─────────────            ─────────────
eip = 0x8000 ⭐           eip = 0x4000 💾          eip = 0x8000
esp = 0x6fff ⭐           esp = 0x7fff 💾          esp = (old)
ebx = 100 ⭐              ebx = 42 💾              ebx = (old)
ecx = 200 ⭐              ecx = 73 💾              ...
edx = 50 ⭐               edx = 15 💾              state = RUNNING
...                       state = READY            kernel_stack = 0xB000
                          kernel_stack = 0xA000
```

**The stack switch is critical!** 🎯

```
Why switch kernel stacks?
─────────────────────────

Process A's kernel stack:      Process B's kernel stack:
┌──────────────────────┐      ┌──────────────────────┐
│ A's saved registers  │      │ B's saved registers  │
│ A's trap frame       │      │ B's trap frame       │
│ A's syscall state    │      │ B's syscall state    │
└──────────────────────┘      └──────────────────────┘

By switching stack pointer:
1. return_from_trap() pops B's state (not A's)
2. Execution resumes in B's context
3. B picks up exactly where it left off

This is the "magic" of context switching! ✨
```

**Real code example: xv6 context switch** 💻

```assembly
# void swtch(struct context *old, struct context *new);
#
# Save current register context in old
# and then load register context from new.

.globl swtch
swtch:
    # Save old registers
    movl 4(%esp), %eax        # put old ptr into eax
    popl 0(%eax)              # save the old IP (return address)
    movl %esp, 4(%eax)        # save stack pointer
    movl %ebx, 8(%eax)        # save other registers
    movl %ecx, 12(%eax)
    movl %edx, 16(%eax)
    movl %esi, 20(%eax)
    movl %edi, 24(%eax)
    movl %ebp, 28(%eax)

    # Load new registers
    movl 4(%esp), %eax        # put new ptr into eax
    movl 28(%eax), %ebp       # restore other registers
    movl 24(%eax), %edi
    movl 20(%eax), %esi
    movl 16(%eax), %edx
    movl 12(%eax), %ecx
    movl 8(%eax), %ebx
    movl 4(%eax), %esp        # 🎯 stack is switched HERE!
    pushl 0(%eax)             # return addr put in place
    ret                        # return into new context! ✨
```

**Key insight:** The `ret` instruction doesn't return to the caller of `swtch()`! It returns to wherever Process B was when it was last context-switched out. This is the magic 🪄 of switching stacks!

> **💡 Insight**
>
> **Two types of register saves during context switching:**
>
> 1. **Implicit save by hardware** (during interrupt/trap):
>    - User registers → kernel stack
>    - Done automatically by CPU
>    - Happens at interrupt entry
>
> 2. **Explicit save by software** (during context switch):
>    - Kernel registers → process PCB
>    - Done manually by OS code
>    - Moves from "running as if trapped from A" to "running as if trapped from B"
>
> Understanding this dual-save mechanism is crucial for understanding how the OS maintains process state across switches.

### 4.4. 📊 Complete LDE Protocol (Part 2)

**The full timeline with timer interrupts:**

```
╔═══════════════════════════════════════════════════════════════╗
║  AT BOOT (Kernel Mode)                                        ║
╚═══════════════════════════════════════════════════════════════╝

OS                                    Hardware
──────────────────────────────        ────────────────────────
initialize trap table          →      remember addresses of...
                                      • syscall handler
                                      • timer handler

start interrupt timer          →      start timer
(interrupt CPU in X ms)               (counting down...)


╔═══════════════════════════════════════════════════════════════╗
║  RUNNING PROCESS A                                             ║
╚═══════════════════════════════════════════════════════════════╝

OS                        Hardware              Process A (user)
────────────────          ────────────          ────────────────
[OS not running]                                Process A runs
                                                ...
                                                (doing work)
                                                ...

                          ⏰ Timer fires!
                          (X ms elapsed)

                          1. Save regs(A)  →
                             to k-stack(A)

                          2. Move to
                             kernel mode

                          3. Jump to       →
                             trap handler

Handle the trap
(timer interrupt
handler runs)

Should we switch?
Yes! Call switch()

  context_switch():
  ─────────────────
  save regs(A)     →
  to proc_t(A)

  restore regs(B)  ←
  from proc_t(B)

  switch to
  k-stack(B)

  return           →

return-from-trap
(into Process B!)

                          Restore regs(B)  ←
                          from k-stack(B)

                          Move to
                          user mode

                          Jump to B's PC   →  Process B runs
                                              ...
                                              (continues where
                                              it left off)
                                              ...
```

**Timing diagram with multiple switches:**

```
Time    CPU State         Process A       Process B       Notes
─────   ───────────────   ─────────────   ─────────────   ──────────────
0ms     A running         RUNNING         READY           A gets CPU
10ms    ⏰ Interrupt
10ms    Kernel running
10ms    Context switch    ↓               ↑               Switching...
10ms    B running         READY           RUNNING         B gets CPU
20ms    ⏰ Interrupt
20ms    Kernel running
20ms    Context switch    ↑               ↓               Switching...
20ms    A running         RUNNING         READY           A gets CPU again
30ms    ⏰ Interrupt
30ms    Kernel running
30ms    Context switch    ↓               ↑               Switching...
30ms    B running         READY           RUNNING         B gets CPU again
...     (repeat forever)
```

**Key observations:** 🔍

1. **OS runs briefly** ⚡
   - Only during interrupts/system calls
   - Then returns to user process
   - Not continuously executing!

2. **Two transition types** 🔄
   - **Interrupt/Trap**: User → Kernel (same process)
   - **Context Switch**: Process A → Process B (different process)

3. **Kernel stack importance** 📚
   - Each process has its own kernel stack
   - Used during interrupts/syscalls
   - Critical for correct context restoration

4. **Hardware + Software cooperation** 🤝
   - Hardware: Saves/restores registers automatically
   - Software: Decides when/where to switch
   - Together: Efficient, controlled virtualization

---

## 5. 🔄 Worried About Concurrency?

**Good question!** 🤔 What happens when:
- During a system call, a timer interrupt occurs?
- While handling one interrupt, another interrupt fires?
- Two CPUs try to access the same kernel data structure?

**The short answer:** Yes, the OS must be **very concerned** about concurrency! ⚠️

**Simple solution: Disable interrupts during critical sections** 🔒

```c
void critical_kernel_operation() {
    disable_interrupts();  // 🔒 Lock the door

    // Modify shared data structure
    process_list->remove(p);
    freed_slots++;

    enable_interrupts();   // 🔓 Unlock the door
}
```

**Pros:** ✅
- Simple to understand
- Prevents nested interrupts
- Guarantees atomicity

**Cons:** ❌
- Disabling too long → lost interrupts (bad!)
- Doesn't work on multiprocessors (other CPUs still running!)
- Coarse-grained (blocks ALL interrupts, even unrelated ones)

**Better solution: Sophisticated locking schemes** 🔐

```c
spinlock_t process_list_lock;

void add_process(struct proc *p) {
    acquire(&process_list_lock);  // 🔒 Fine-grained lock

    // Only this list is protected
    process_list->add(p);

    release(&process_list_lock);  // 🔓 Release
}

void remove_process(struct proc *p) {
    acquire(&process_list_lock);  // 🔒 Same lock

    process_list->remove(p);

    release(&process_list_lock);  // 🔓 Release
}

// Other kernel operations can run concurrently!
// (as long as they use different locks)
```

**Modern OS approach:** 🚀

1. **Fine-grained locking** 🔬
   - Separate locks for different data structures
   - Allows parallelism where safe
   - Complex but performant

2. **Lock-free data structures** ⚡
   - Use atomic operations (compare-and-swap)
   - No locks needed!
   - Tricky to implement correctly

3. **Per-CPU data structures** 🖥️
   - Each CPU has its own copy
   - No sharing → no locking needed!
   - Great for scalability

4. **Read-Copy-Update (RCU)** 📚
   - Readers don't need locks
   - Writers make copies
   - Used heavily in Linux kernel

> **💡 Insight**
>
> **Concurrency is the entire second piece of this course!** 📖 The OS is one giant concurrent program with:
> - Multiple processes running simultaneously
> - Interrupts happening at unpredictable times
> - Multiple CPUs accessing shared data
>
> Concurrency bugs are the **hardest to find and fix**:
> - Race conditions (timing-dependent bugs)
> - Deadlocks (circular waiting)
> - Priority inversion (low-priority blocks high-priority)
>
> This is why OS development is challenging—and fascinating! Understanding concurrency here prepares you for multi-threaded application development, distributed systems, and database internals.

**Example race condition:** 🐛

```c
// Buggy code (no locking!)
void schedule() {
    if (ready_queue->count > 0) {       // ← Check
        struct proc *p = ready_queue->dequeue();  // ← Use
        context_switch(current, p);
    }
}

// What can go wrong?
// Thread 1: Checks (count = 1) ✓
// ⏰ INTERRUPT! Context switch to Thread 2
// Thread 2: Checks (count = 1) ✓
// Thread 2: Dequeues (count = 0)
// ⏰ INTERRUPT! Back to Thread 1
// Thread 1: Tries to dequeue (count = 0) 💥 CRASH!
//           (dequeue from empty queue)

// Fix: Lock around check-and-use
void schedule() {
    acquire(&ready_queue_lock);
    if (ready_queue->count > 0) {
        struct proc *p = ready_queue->dequeue();
        release(&ready_queue_lock);
        context_switch(current, p);
    } else {
        release(&ready_queue_lock);
    }
}
```

---

## 6. 📝 Summary

**Key Takeaways:** 🎯

**1. Limited Direct Execution** ⚡
- **Direct Execution**: Run programs directly on CPU (fast! 🚀)
- **Limited**: Restrict what programs can do (safe! 🔒)
- Achieves both performance AND control

**2. Problem #1: Restricted Operations** 🔐
```
User Mode  →  Can't do I/O or privileged operations
              └→ Use system calls (trap into kernel)

Kernel Mode → Can do anything
              └→ OS runs in this mode
```

**Key mechanisms:**
- 🚦 **Dual-mode execution**: User mode vs Kernel mode
- 📞 **System calls**: Controlled interface for privileged operations
- 🔄 **Trap/Return-from-trap**: Safe transitions between modes
- 📚 **Trap table**: Pre-configured handlers for events

**3. Problem #2: Process Switching** 🔄
```
Cooperative:      ❌ Trust processes to yield
                  → Fails if process misbehaves

Non-cooperative:  ✅ Timer interrupts force control
                  → OS always regains control
```

**Key mechanisms:**
- ⏰ **Timer interrupt**: Hardware-driven periodic interrupts
- 🔄 **Context switch**: Save/restore process state
- 📚 **Kernel stacks**: Per-process interrupt handling
- 🎯 **Scheduler**: Decides which process runs next

**4. The Complete LDE Protocol** 📋

```
Boot Time:                    Runtime:
──────────                    ─────────
1. Setup trap table      →    1. Timer fires ⏰
2. Start timer           →    2. Save registers 💾
3. Start process         →    3. Handle interrupt
                              4. Context switch? 🤔
                              5. Restore registers 📍
                              6. Resume (maybe different process!)
```

**5. Key OS Terminology** 📖

| Term | Definition |
|------|------------|
| **User mode** 👤 | Restricted execution mode for applications |
| **Kernel mode** 👑 | Privileged mode for OS code |
| **System call** 📞 | Controlled request for OS service |
| **Trap** 🎯 | Software-initiated jump into kernel |
| **Interrupt** ⏰ | Hardware-initiated jump into kernel |
| **Trap table** 📚 | Pre-configured handlers for events |
| **Context switch** 🔄 | Switching CPU from one process to another |
| **Kernel stack** 📚 | Per-process stack for interrupt handling |

**6. Performance Considerations** ⚡

**Context switch costs** (on modern systems):
- Direct cost: 1-10 microseconds 🏃
  - Save/restore registers
  - Switch page tables
  - Flush TLB (translation lookaside buffer)

- Indirect cost: Cache pollution 💨
  - New process has different memory access patterns
  - CPU caches get filled with new data
  - Old process's data evicted
  - When old process runs again, cache misses!

**Historical trend:** 📈
- 1996: ~6 microseconds (Linux on 200MHz P6)
- 2025: <1 microsecond (Linux on 3GHz+)
- Improvement ~10x (roughly tracking CPU speed)

**But:** Not all OS operations scale with CPU speed! 🤔
- Memory-intensive operations limited by memory bandwidth
- Memory bandwidth hasn't improved as much as CPU speed
- Buying faster CPU may not speed up OS proportionally

> **💡 Insight**
>
> **Three Fundamental OS Patterns Demonstrated:**
>
> 1. **Hardware-Software Cooperation** 🤝
>    - Hardware provides mechanisms (trap, timer)
>    - Software implements policies (scheduling)
>    - Neither alone is sufficient!
>
> 2. **Privilege Separation** 🔒
>    - Untrusted code (user) has limited capabilities
>    - Trusted code (kernel) has full capabilities
>    - Controlled transitions between levels
>    - Pattern used in browsers, VMs, containers!
>
> 3. **Indirection for Protection** 🎯
>    - Don't let users specify addresses (dangerous!)
>    - Use numbers/IDs that kernel translates
>    - System call numbers, file descriptors, PIDs
>    - Indirection enables validation and security
>
> These patterns appear throughout computer systems: sandboxing in browsers (privilege separation), virtual memory (indirection), hypervisors (hardware cooperation). Master LDE, and you've learned to think like a systems designer!

**What's Next:** 🚀

Now that you understand the **mechanisms** of CPU virtualization:
- 🎯 **Scheduling Policies**: Which process should run? (fairness, performance, response time)
- 📊 **Scheduling Metrics**: How to measure scheduler effectiveness?
- 🔀 **Scheduling Algorithms**: FIFO, SJF, STCF, Round Robin, MLFQ
- 🎛️ **Multi-core Scheduling**: How to schedule on multiple CPUs?

The mechanisms (LDE) provide the "how", and scheduling provides the "which"—together they create efficient CPU virtualization! ⚡

---

**Previous:** [Chapter 2: Process API](chapter2-process-api.md) | **Next:** [Chapter 4: Scheduling Policies](chapter4-scheduling-policies.md)
