26
Concurrency: An Introduction
Thus far, we have seen the development of the basic abstractions that the
OS performs. We have seen how to take a single physical CPU and turn
it into multiple virtual CPUs, thus enabling the illusion of multiple pro-
grams running at the same time. We have also seen how to create the
illusion of a large, private virtual memory for each process; this abstrac-
tion of the address space enables each program to behave as if it has its
own memory when indeed the OS is secretly multiplexing address spaces
across physical memory (and sometimes, disk).
In this note, we introduce a new abstraction for a single running pro-
cess: that of a thread. Instead of our classic view of a single point of
execution within a program (i.e., a single PC where instructions are be-
ing fetched from and executed), a multi-threaded program has more than
one point of execution (i.e., multiple PCs, each of which is being fetched
and executed from). Perhaps another way to think of this is that each
thread is very much like a separate process, except for one difference:
they share the same address space and thus can access the same data.
The state of a single thread is thus very similar to that of a process.
It has a program counter (PC) that tracks where the program is fetch-
ing instructions from. Each thread has its own private set of registers it
uses for computation; thus, if there are two threads that are running on
a single processor, when switching from running one (T1) to running the
other (T2), a context switch must take place. The context switch between
threads is quite similar to the context switch between processes, as the
register state of T1 must be saved and the register state of T2 restored
before running T2. With processes, we saved state to a process control
block (PCB); now, we’ll need one or more thread control blocks (TCBs)
to store the state of each thread of a process. There is one major difference,
though, in the context switch we perform between threads as compared
to processes: the address space remains the same (i.e., there is no need to
switch which page table we are using).
One other major difference between threads and processes concerns
the stack. In our simple model of the address space of a classic process
(which we can now call a single-threaded process), there is a single stack,
usually residing at the bottom of the address space (Figure 26.1, left).
1
2 CONCURRENCY: AN INTRODUCTION
0KB
1KB
2KB
Program Code Heap
the code segment:
where instructions live
the heap segment:
contains malloc’d data
dynamic data structures
(it grows downward)
0KB
1KB
2KB
Program Code
Heap
(free)
(free)
Stack (2)
Stack
(it grows upward)
the stack segment:
contains local variables
arguments to routines,
return values, etc.
(free)
Stack (1)
15KB
15KB
16KB
16KB
Figure 26.1: Single-Threaded And Multi-Threaded Address Spaces
However, in a multi-threaded process, each thread runs independently
and of course may call into various routines to do whatever work it is do-
ing. Instead of a single stack in the address space, there will be one per
thread. Let’s say we have a multi-threaded process that has two threads
in it; the resulting address space looks different (Figure 26.1, right).
In this figure, you can see two stacks spread throughout the address
space of the process. Thus, any stack-allocated variables, parameters, re-
turn values, and other things that we put on the stack will be placed in
what is sometimes called thread-local storage, i.e., the stack of the rele-
vant thread.
You might also notice how this ruins our beautiful address space lay-
out. Before, the stack and heap could grow independently and trouble
only arose when you ran out of room in the address space. Here, we
no longer have such a nice situation. Fortunately, this is usually OK, as
stacks do not generally have to be very large (the exception being in pro-
grams that make heavy use of recursion).
26.1 Why Use Threads?
Before getting into the details of threads and some of the problems you
might have in writing multi-threaded programs, let’s first answer a more
simple question. Why should you use threads at all?
As it turns out, there are at least two major reasons you should use
threads. The first is simple: parallelism. Imagine you are writing a pro-
gram that performs operations on very large arrays, for example, adding
two large arrays together, or incrementing the value of each element in
the array by some amount. If you are running on just a single proces-
sor, the task is straightforward: just perform each operation and be done.
However, if you are executing the program on a system with multiple
OPERATING
SYSTEMS
[VERSION 1.01]
WWW.OSTEP.ORG
CONCURRENCY: AN INTRODUCTION 3
processors, you have the potential of speeding up this process consider-
ably by using the processors to each perform a portion of the work. The
task of transforming your standard single-threaded program into a pro-
gram that does this sort of work on multiple CPUs is called paralleliza-
tion, and using a thread per CPU to do this work is a natural and typical
way to make programs run faster on modern hardware.
The second reason is a bit more subtle: to avoid blocking program
progress due to slow I/O. Imagine that you are writing a program that
performs different types of I/O: either waiting to send or receive a mes-
sage, for an explicit disk I/O to complete, or even (implicitly) for a page
fault to finish. Instead of waiting, your program may wish to do some-
thing else, including utilizing the CPU to perform computation, or even
issuing further I/O requests. Using threads is a natural way to avoid
getting stuck; while one thread in your program waits (i.e., is blocked
waiting for I/O), the CPU scheduler can switch to other threads, which
are ready to run and do something useful. Threading enables overlap of
I/O with other activities within a single program, much like multipro-
gramming did for processes across programs; as a result, many modern
server-based applications (web servers, database management systems,
and the like) make use of threads in their implementations.
Of course, in either of the cases mentioned above, you could use multi-
ple processes instead of threads. However, threads share an address space
and thus make it easy to share data, and hence are a natural choice when
constructing these types of programs. Processes are a more sound choice
for logically separate tasks where little sharing of data structures in mem-
ory is needed.
26.2 An Example: Thread Creation
Let’s get into some of the details. Say we wanted to run a program
that creates two threads, each of which does some independent work, in
this case printing “A” or “B”. The code is shown in Figure 26.2 (page 4).
The main program creates two threads, each of which will run the
function mythread(), though with different arguments (the string Aor
B). Once a thread is created, it may start running right away (depending
on the whims of the scheduler); alternately, it may be put in a “ready” but
not “running” state and thus not run yet. Of course, on a multiprocessor,
the threads could even be running at the same time, but let’s not worry
about this possibility quite yet.
After creating the two threads (let’s call them T1 and T2), the main
thread calls pthread join(), which waits for a particular thread to
complete. It does so twice, thus ensuring T1 and T2 will run and com-
plete before finally allowing the main thread to run again; when it does,
it will print “main: end” and exit. Overall, three threads were employed
during this run: the main thread, T1, and T2.
Let us examine the possible execution ordering of this little program.
c ⃝ 2008–19, ARPACI-DUSSEAU
THREE
EASY
PIECES
4 CONCURRENCY: AN INTRODUCTION
1 #include <stdio.h>
2 #include <assert.h>
3 #include <pthread.h>
4 #include "common.h"
5 #include "common_threads.h"
6
7 void *mythread(void *arg) {
8 printf("%s\n", (char *) arg);
9 return NULL;
10 }
11
12 int
13 main(int argc, char *argv[]) {
14 pthread_t p1, p2;
15 int rc;
16 printf("main: begin\n");
17 Pthread_create(&p1, NULL, mythread, "A");
18 Pthread_create(&p2, NULL, mythread, "B");
19 // join waits for the threads to finish
20 Pthread_join(p1, NULL);
21 Pthread_join(p2, NULL);
22 printf("main: end\n");
23 return 0;
24 }
Figure 26.2: Simple Thread Creation Code (t0.c)
In the execution diagram (Figure 26.3, page 5), time increases in the down-
wards direction, and each column shows when a different thread (the
main one, or Thread 1, or Thread 2) is running.
Note, however, that this ordering is not the only possible ordering. In
fact, given a sequence of instructions, there are quite a few, depending on
which thread the scheduler decides to run at a given point. For example,
once a thread is created, it may run immediately, which would lead to the
execution shown in Figure 26.4 (page 5).
We also could even see “B” printed before “A”, if, say, the scheduler
decided to run Thread 2 first even though Thread 1 was created earlier;
there is no reason to assume that a thread that is created first will run first.
Figure 26.5 (page 5) shows this final execution ordering, with Thread 2
getting to strut its stuff before Thread 1.
As you might be able to see, one way to think about thread creation
is that it is a bit like making a function call; however, instead of first ex-
ecuting the function and then returning to the caller, the system instead
creates a new thread of execution for the routine that is being called, and
it runs independently of the caller, perhaps before returning from the cre-
ate, but perhaps much later. What runs next is determined by the OS
scheduler, and although the scheduler likely implements some sensible
algorithm, it is hard to know what will run at any given moment in time.
OPERATING
SYSTEMS
[VERSION 1.01]
WWW.OSTEP.ORG
CONCURRENCY: AN INTRODUCTION 5
main Thread 1 Thread2
starts running
prints “main: begin”
creates Thread 1
creates Thread 2
waits for T1
runs
prints “A”
returns
waits for T2
runs
prints “B”
returns
prints “main: end”
Figure 26.3: Thread Trace (1)
main Thread 1 Thread2
starts running
prints “main: begin”
creates Thread 1
runs
prints “A”
returns
creates Thread 2
runs
prints “B”
returns
waits for T1
returns immediately; T1 is done
waits for T2
returns immediately; T2 is done
prints “main: end”
Figure 26.4: Thread Trace (2)
main Thread 1 Thread2
starts running
prints “main: begin”
creates Thread 1
creates Thread 2
runs
prints “B”
returns
waits for T1
runs
prints “A”
returns
waits for T2
returns immediately; T2 is done
prints “main: end”
Figure 26.5: Thread Trace (3)
c ⃝ 2008–19, ARPACI-DUSSEAU
THREE
EASY
PIECES
6 CONCURRENCY: AN INTRODUCTION
26.3 As you also might be able to tell from this example, threads make life
complicated: it is already hard to tell what will run when! Computers are
hard enough to understand without concurrency. Unfortunately, with
concurrency, it simply gets worse. Much worse.
Why It Gets Worse: Shared Data
The simple thread example we showed above was useful in showing
how threads are created and how they can run in different orders depend-
ing on how the scheduler decides to run them. What it doesn’t show you,
though, is how threads interact when they access shared data.
Let us imagine a simple example where two threads wish to update a
global shared variable. The code we’ll study is in Figure 26.6 (page 7).
Here are a few notes about the code. First, as Stevens suggests [SR05],
we wrap the thread creation and join routines to simply exit on failure;
for a program as simple as this one, we want to at least notice an error
occurred (if it did), but not do anything very smart about it (e.g., just
exit). Thus, Pthread create() simply calls pthread create() and
makes sure the return code is 0; if it isn’t, Pthread create()just prints
a message and exits.
Second, instead of using two separate function bodies for the worker
threads, we just use a single piece of code, and pass the thread an argu-
ment (in this case, a string) so we can have each thread print a different
letter before its messages.
Finally, and most importantly, we can now look at what each worker is
trying to do: add a number to the shared variable counter, and do so 10
million times (1e7) in a loop. Thus, the desired final result is: 20,000,000.
We now compile and run the program, to see how it behaves. Some-
times, everything works how we might expect:
prompt> gcc -o main main.c -Wall -pthread
prompt> ./main
main: begin (counter = 0)
A: begin
B: begin
A: done
B: done
main: done with both (counter = 20000000)
Unfortunately, when we run this code, even on a single processor, we
don’t necessarily get the desired result. Sometimes, we get:
prompt> ./main
main: begin (counter = 0)
A: begin
B: begin
A: done
B: done
main: done with both (counter = 19345221)
OPERATING
SYSTEMS
[VERSION 1.01]
WWW.OSTEP.ORG
CONCURRENCY: AN INTRODUCTION 7
1 #include <stdio.h>
2 #include <pthread.h>
3 #include "common.h"
4 #include "common_threads.h"
5
6 static volatile int counter = 0;
7
8 //
9 // mythread()
10 //
11 // Simply adds 1 to counter repeatedly, in a loop
12 // No, this is not how you would add 10,000,000 to
13 // a counter, but it shows the problem nicely.
14 //
15 void *mythread(void *arg) {
16 printf("%s: begin\n", (char *) arg);
17 int i;
18 for (i = 0; i < 1e7; i++) {
19 counter = counter + 1;
20 }
21 printf("%s: done\n", (char *) arg);
22 return NULL;
23 }
24
25 //
26 // main()
27 //
28 // Just launches two threads (pthread_create)
29 // and then waits for them (pthread_join)
30 //
31 int main(int argc, char *argv[]) {
32 pthread_t p1, p2;
33 printf("main: begin (counter = %d)\n", counter);
34 Pthread_create(&p1, NULL, mythread, "A");
35 Pthread_create(&p2, NULL, mythread, "B");
36
37 // join waits for the threads to finish
38 Pthread_join(p1, NULL);
39 Pthread_join(p2, NULL);
40 printf("main: done with both (counter = %d)\n", counter);
41 return 0;
42 }
Figure 26.6: Sharing Data: Uh Oh (t1.c)
c ⃝ 2008–19, ARPACI-DUSSEAU
THREE
EASY
PIECES
8 CONCURRENCY: AN INTRODUCTION
26.4 TIP: KNOW AND USE YOUR TOOLS
You should always learn new tools that help you write, debug, and un-
derstand computer systems. Here, we use a neat tool called a disassem-
bler. When you run a disassembler on an executable, it shows you what
assembly instructions make up the program. For example, if we wish to
understand the low-level code to update a counter (as in our example),
we run objdump(Linux) to see the assembly code:
prompt> objdump -d main
Doing so produces a long listing of all the instructions in the program,
neatly labeled (particularly if you compiled with the -g flag), which in-
cludes symbol information in the program. The objdumpprogram is just
one of many tools you should learn how to use; a debugger like gdb,
memory profilers like valgrindor purify, and of course the compiler
itself are others that you should spend time to learn more about; the better
you are at using your tools, the better systems you’ll be able to build.
Let’s try it one more time, just to see if we’ve gone crazy. After all,
aren’t computers supposed to produce deterministic results, as you have
been taught?! Perhaps your professors have been lying to you? (gasp)
prompt> ./main
main: begin (counter = 0)
A: begin
B: begin
A: done
B: done
main: done with both (counter = 19221041)
Not only is each run wrong, but also yields a different result! A big
question remains: why does this happen?
The Heart Of The Problem: Uncontrolled Scheduling
To understand why this happens, we must understand the code se-
quence that the compiler generates for the update to counter. In this
case, we wish to simply add a number (1) to counter. Thus, the code
sequence for doing so might look something like this (in x86);
mov 0x8049a1c, %eax
add $0x1, %eax
mov %eax, 0x8049a1c
This example assumes that the variable counteris located at address
0x8049a1c. In this three-instruction sequence, the x86 mov instruction is
used first to get the memory value at the address and put it into register
eax. Then, the add is performed, adding 1 (0x1) to the contents of the
eaxregister, and finally, the contents of eaxare stored back into memory
at the same address.
OPERATING
SYSTEMS
[VERSION 1.01]
WWW.OSTEP.ORG
CONCURRENCY: AN INTRODUCTION 9
Let us imagine one of our two threads (Thread 1) enters this region of
code, and is thus about to increment counterby one. It loads the value
of counter (let’s say it’s 50 to begin with) into its register eax. Thus,
eax=50 for Thread 1. Then it adds one to the register; thus eax=51.
Now, something unfortunate happens: a timer interrupt goes off; thus,
the OS saves the state of the currently running thread (its PC, its registers
including eax, etc.) to the thread’s TCB.
Now something worse happens: Thread 2 is chosen to run, and it en-
ters this same piece of code. It also executes the first instruction, getting
the value of counterand putting it into its eax(remember: each thread
when running has its own private registers; the registers are virtualized
by the context-switch code that saves and restores them). The value of
counter is still 50 at this point, and thus Thread 2 has eax=50. Let’s
then assume that Thread 2 executes the next two instructions, increment-
ing eax by 1 (thus eax=51), and then saving the contents of eax into
counter (address 0x8049a1c). Thus, the global variable counter now
has the value 51.
Finally, another context switch occurs, and Thread 1 resumes running.
Recall that it had just executed the mov and add, and is now about to
perform the final movinstruction. Recall also that eax=51. Thus, the final
movinstruction executes, and saves the value to memory; the counter is
set to 51 again.
Put simply, what has happened is this: the code to increment counter
has been run twice, but counter, which started at 50, is now only equal
to 51. A “correct” version of this program should have resulted in the
variable counterequal to 52.
Let’s look at a detailed execution trace to understand the problem bet-
ter. Assume, for this example, that the above code is loaded at address
100 in memory, like the following sequence (note for those of you used to
nice, RISC-like instruction sets: x86 has variable-length instructions; this
movinstruction takes up 5 bytes of memory, and the addonly 3):
100 mov 0x8049a1c, %eax
105 add $0x1, %eax
108 mov %eax, 0x8049a1c
With these assumptions, what happens is shown in Figure 26.7 (page
10). Assume the counter starts at value 50, and trace through this example
to make sure you understand what is going on.
What we have demonstrated here is called a race condition (or, more
specifically, a data race): the results depend on the timing execution of
the code. With some bad luck (i.e., context switches that occur at un-
timely points in the execution), we get the wrong result. In fact, we may
get a different result each time; thus, instead of a nice deterministic com-
putation (which we are used to from computers), we call this result inde-
terminate, where it is not known what the output will be and it is indeed
likely to be different across runs.
c ⃝ 2008–19, ARPACI-DUSSEAU
THREE
EASY
PIECES
10 CONCURRENCY: AN INTRODUCTION
(after instruction)
OS Thread 1 Thread 2 PC %eax counter
before critical section mov 0x8049a1c, %eax add $0x1, %eax 100 0 50
105 50 50
108 51 50
interrupt
save T1’s state
restore T2’s state 100 0 50
mov 0x8049a1c, %eax 105 50 50
add $0x1, %eax 108 51 50
mov %eax, 0x8049a1c 113 51 51
interrupt
save T2’s state
restore T1’s state mov %eax, 0x8049a1c 108 51 51
113 51 51
Figure 26.7: The Problem: Up Close and Personal
Because multiple threads executing this code can result in a race con-
dition, we call this code a critical section. A critical section is a piece of
code that accesses a shared variable (or more generally, a shared resource)
and must not be concurrently executed by more than one thread.
What we really want for this code is what we call mutual exclusion.
This property guarantees that if one thread is executing within the critical
section, the others will be prevented from doing so.
Virtually all of these terms, by the way, were coined by Edsger Dijk-
stra, who was a pioneer in the field and indeed won the Turing Award
because of this and other work; see his 1968 paper on “Cooperating Se-
quential Processes” [D68] for an amazingly clear description of the prob-
lem. We’ll be hearing more about Dijkstra in this section of the book.
26.5 The Wish For Atomicity
One way to solve this problem would be to have more powerful in-
structions that, in a single step, did exactly whatever we needed done
and thus removed the possibility of an untimely interrupt. For example,
what if we had a super instruction that looked like this:
memory-add 0x8049a1c, $0x1
Assume this instruction adds a value to a memory location, and the
hardware guarantees that it executes atomically; when the instruction
executed, it would perform the update as desired. It could not be inter-
rupted mid-instruction, because that is precisely the guarantee we receive
from the hardware: when an interrupt occurs, either the instruction has
not run at all, or it has run to completion; there is no in-between state.
Hardware can be a beautiful thing, no?
Atomically, in this context, means “as a unit”, which sometimes we
take as “all or none.” What we’d like is to execute the three instruction
sequence atomically:
OPERATING
SYSTEMS
[VERSION 1.01]
WWW.OSTEP.ORG
CONCURRENCY: AN INTRODUCTION 11
TIP: USE ATOMIC OPERATIONS
Atomic operations are one of the most powerful underlying techniques
in building computer systems, from the computer architecture, to concur-
rent code (what we are studying here), to file systems (which we’ll study
soon enough), database management systems, and even distributed sys-
tems [L+93].
The idea behind making a series of actions atomic is simply expressed
with the phrase “all or nothing”; it should either appear as if all of the ac-
tions you wish to group together occurred, or that none of them occurred,
with no in-between state visible. Sometimes, the grouping of many ac-
tions into a single atomic action is called a transaction, an idea devel-
oped in great detail in the world of databases and transaction processing
[GR92].
In our theme of exploring concurrency, we’ll be using synchronization
primitives to turn short sequences of instructions into atomic blocks of
execution, but the idea of atomicity is much bigger than that, as we will
see. For example, file systems use techniques such as journaling or copy-
on-write in order to atomically transition their on-disk state, critical for
operating correctly in the face of system failures. If that doesn’t make
sense, don’t worry — it will, in some future chapter.
mov 0x8049a1c, %eax
add $0x1, %eax
mov %eax, 0x8049a1c
As we said, if we had a single instruction to do this, we could just
issue that instruction and be done. But in the general case, we won’t have
such an instruction. Imagine we were building a concurrent B-tree, and
wished to update it; would we really want the hardware to support an
“atomic update of B-tree” instruction? Probably not, at least in a sane
instruction set.
Thus, what we will instead do is ask the hardware for a few useful
instructions upon which we can build a general set of what we call syn-
chronization primitives. By using this hardware support, in combina-
tion with some help from the operating system, we will be able to build
multi-threaded code that accesses critical sections in a synchronized and
controlled manner, and thus reliably produces the correct result despite
the challenging nature of concurrent execution. Pretty awesome, right?
This is the problem we will study in this section of the book. It is a
wonderful and hard problem, and should make your mind hurt (a bit).
If it doesn’t, then you don’t understand! Keep working until your head
hurts; you then know you’re headed in the right direction. At that point,
take a break; we don’t want your head hurting too much.
c ⃝ 2008–19, ARPACI-DUSSEAU
THREE
EASY
PIECES
12 CONCURRENCY: AN INTRODUCTION
26.6 26.7 THE CRUX: HOW TO SUPPORT SYNCHRONIZATION
What support do we need from the hardware in order to build use-
ful synchronization primitives? What support do we need from the OS?
How can we build these primitives correctly and efficiently? How can
programs use them to get the desired results?
One More Problem: Waiting For Another
This chapter has set up the problem of concurrency as if only one type
of interaction occurs between threads, that of accessing shared variables
and the need to support atomicity for critical sections. As it turns out,
there is another common interaction that arises, where one thread must
wait for another to complete some action before it continues. This inter-
action arises, for example, when a process performs a disk I/O and is put
to sleep; when the I/O completes, the process needs to be roused from its
slumber so it can continue.
Thus, in the coming chapters, we’ll be not only studying how to build
support for synchronization primitives to support atomicity but also for
mechanisms to support this type of sleeping/waking interaction that is
common in multi-threaded programs. If this doesn’t make sense right
now, that is OK! It will soon enough, when you read the chapter on con-
dition variables. If it doesn’t by then, well, then it is less OK, and you
should read that chapter again (and again) until it does make sense.
Summary: Why in OS Class?
Before wrapping up, one question that you might have is: why are we
studying this in OS class? “History” is the one-word answer; the OS was
the first concurrent program, and many techniques were created for use
within the OS. Later, with multi-threaded processes, application program-
mers also had to consider such things.
For example, imagine the case where there are two processes running.
Assume they both call write() to write to the file, and both wish to
append the data to the file (i.e., add the data to the end of the file, thus
increasing its length). To do so, both must allocate a new block, record
in the inode of the file where this block lives, and change the size of the
file to reflect the new larger size (among other things; we’ll learn more
about files in the third part of the book). Because an interrupt may occur
at any time, the code that updates these shared structures (e.g., a bitmap
for allocation, or the file’s inode) are critical sections; thus, OS design-
ers, from the very beginning of the introduction of the interrupt, had to
worry about how the OS updates internal structures. An untimely inter-
rupt causes all of the problems described above. Not surprisingly, page
tables, process lists, file system structures, and virtually every kernel data
structure has to be carefully accessed, with the proper synchronization
primitives, to work correctly.
OPERATING
SYSTEMS
[VERSION 1.01]
WWW.OSTEP.ORG
CONCURRENCY: AN INTRODUCTION 13
ASIDE: KEY CONCURRENCY TERMS
CRITICAL SECTION, RACE CONDITION,
INDETERMINATE, MUTUAL EXCLUSION
These four terms are so central to concurrent code that we thought it
worth while to call them out explicitly. See some of Dijkstra’s early work
[D65,D68] for more details.
• A critical section is a piece of code that accesses a shared resource,
usually a variable or data structure.
• A race condition (or data race [NM92]) arises if multiple threads of
execution enter the critical section at roughly the same time; both
attempt to update the shared data structure, leading to a surprising
(and perhaps undesirable) outcome.
• An indeterminate program consists of one or more race conditions;
the output of the program varies from run to run, depending on
which threads ran when. The outcome is thus not deterministic,
something we usually expect from computer systems.
• To avoid these problems, threads should use some kind of mutual
exclusion primitives; doing so guarantees that only a single thread
ever enters a critical section, thus avoiding races, and resulting in
deterministic program outputs.