27
Interlude: Thread API
This chapter briefly covers the main portions of the thread API. Each part
will be explained further in the subsequent chapters, as we show how
to use the API. More details can be found in various books and online
sources [B89, B97, B+96, K+96]. We should note that the subsequent chap-
ters introduce the concepts of locks and condition variables more slowly,
with many examples; this chapter is thus better used as a reference.
CRUX: HOW TO CREATE AND CONTROL THREADS
What interfaces should the OS present for thread creation and control?
How should these interfaces be designed to enable ease of use as well as
utility?
27.1 Thread Creation
The first thing you have to be able to do to write a multi-threaded
program is to create new threads, and thus some kind of thread creation
interface must exist. In POSIX, it is easy:
#include <pthread.h>
int
pthread_create( pthread_t * thread,
const pthread_attr_t * attr,
void * (*start_routine)(void*),
void * arg);
This declaration might look a little complex (particularly if you haven’t
used function pointers in C), but actually it’s not too bad. There are
four arguments: thread, attr, start routine, and arg. The first,
thread, is a pointer to a structure of type pthread t; we’ll use this
structure to interact with this thread, and thus we need to pass it to
pthread create()in order to initialize it.
1
2 INTERLUDE: THREAD API
The second argument, attr, is used to specify any attributes this thread
might have. Some examples include setting the stack size or perhaps in-
formation about the scheduling priority of the thread. An attribute is
initialized with a separate call to pthread attr init(); see the man-
ual page for details. However, in most cases, the defaults will be fine; in
this case, we will simply pass the value NULLin.
The third argument is the most complex, but is really just asking: which
function should this thread start running in? In C, we call this a function
pointer, and this one tells us the following is expected: a function name
(start routine), which is passed a single argument of type void *(as
indicated in the parentheses after start routine), and which returns a
value of type void *(i.e., a void pointer).
If this routine instead required an integer argument, instead of a void
pointer, the declaration would look like this:
int pthread_create(..., // first two args are the same
void * (*start_routine)(int),
int arg);
If instead the routine took a void pointer as an argument, but returned
an integer, it would look like this:
int pthread_create(..., // first two args are the same
int (*start_routine)(void *),
void * arg);
Finally, the fourth argument, arg, is exactly the argument to be passed
to the function where the thread begins execution. You might ask: why
do we need these void pointers? Well, the answer is quite simple: having
a void pointer as an argument to the function start routineallows us
to pass in any type of argument; having it as a return value allows the
thread to return any type of result.
Let’s look at an example in Figure 27.1. Here we just create a thread
that is passed two arguments, packaged into a single type we define our-
selves (myarg t). The thread, once created, can simply cast its argument
to the type it expects and thus unpack the arguments as desired.
And there it is! Once you create a thread, you really have another
live executing entity, complete with its own call stack, running within the
same address space as all the currently existing threads in the program.
The fun thus begins!
27.2 Thread Completion
The example above shows how to create a thread. However, what
happens if you want to wait for a thread to complete? You need to do
something special in order to wait for completion; in particular, you must
call the routine pthread join().
int pthread_join(pthread_t thread, void **value_ptr);
OPERATING
SYSTEMS
[VERSION 1.00] WWW.OSTEP.ORG
INTERLUDE: THREAD API 3
1 #include <pthread.h>
2
3 typedef struct __myarg_t {
4 int a;
5 int b;
6 } myarg_t;
7
8 void *mythread(void *arg) {
9 myarg_t *m = (myarg_t *) arg;
10 printf("%d %d\n", m->a, m->b);
11 return NULL;
12 }
13
14 int
15 main(int argc, char *argv[]) {
16 pthread_t p;
17 int rc;
18
19 myarg_t args;
20 args.a = 10;
21 args.b = 20;
22 rc = pthread_create(&p, NULL, mythread, &args);
23 ...
24 }
Figure 27.1: Creating a Thread
This routine takes two arguments. The first is of type pthread t, and
is used to specify which thread to wait for. This variable is initialized by
the thread creation routine (when you pass a pointer to it as an argument
to pthread create()); if you keep it around, you can use it to wait for
that thread to terminate.
The second argument is a pointer to the return value you expect to get
back. Because the routine can return anything, it is defined to return a
pointer to void; because the pthread join()routine changes the value
of the passed in argument, you need to pass in a pointer to that value, not
just the value itself.
Let’s look at another example (Figure 27.2, page 4). In the code, a
single thread is again created, and passed a couple of arguments via the
myarg t structure. To return values, the myret t type is used. Once
the thread is finished running, the main thread, which has been waiting
inside of the pthread join()routine1, then returns, and we can access
the values returned from the thread, namely whatever is in myret t.
A few things to note about this example. First, often times we don’t
have to do all of this painful packing and unpacking of arguments. For
example, if we just create a thread with no arguments, we can pass NULL
in as an argument when the thread is created. Similarly, we can pass NULL
into pthread join()if we don’t care about the return value.
Second, if we are just passing in a single value (e.g., an int), we don’t
1 Note we use wrapper functions here; specifically, we call Malloc(), Pthread join(), and
Pthread create(), which just call their similarly-named lower-case versions and make sure the
routines did not return anything unexpected.
c ⃝ 2008–18, ARPACI-DUSSEAU
THREE
EASY
PIECES
4 INTERLUDE: THREAD API
1 #include <stdio.h>
2 #include <pthread.h>
3 #include <assert.h>
4 #include <stdlib.h>
5
6 typedef struct __myarg_t {
7 int a;
8 int b;
9 } myarg_t;
10
11 typedef struct __myret_t {
12 int x;
13 int y;
14 } myret_t;
15
16 void *mythread(void *arg) {
17 myarg_t *m = (myarg_t *) arg;
18 printf("%d %d\n", m->a, m->b);
19 myret_t *r = Malloc(sizeof(myret_t));
20 r->x = 1;
21 r->y = 2;
22 return (void *) r;
23 }
24
25 int
26 main(int argc, char *argv[]) {
27 pthread_t p;
28 myret_t *m;
29
30 myarg_t args = {10, 20};
31 Pthread_create(&p, NULL, mythread, &args);
32 Pthread_join(p, (void **) &m);
33 printf("returned %d %d\n", m->x, m->y);
34 free(m);
35 return 0;
36 }
Figure 27.2: Waiting for Thread Completion
have to package it up as an argument. Figure 27.3 (page 5) shows an
example. In this case, life is a bit simpler, as we don’t have to package
arguments and return values inside of structures.
Third, we should note that one has to be extremely careful with how
values are returned from a thread. In particular, never return a pointer
which refers to something allocated on the thread’s call stack. If you do,
what do you think will happen? (think about it!) Here is an example of a
dangerous piece of code, modified from the example in Figure 27.3.
1 void *mythread(void *arg) {
2 myarg_t *m = (myarg_t *) arg;
3 printf("%d %d\n", m->a, m->b);
4 myret_t r; // ALLOCATED ON STACK: BAD!
5 r.x = 1;
6 r.y = 2;
7 return (void *) &r;
8 }
OPERATING
SYSTEMS
[VERSION 1.00] WWW.OSTEP.ORG
INTERLUDE: THREAD API 5
void *mythread(void *arg) {
int m = (int) arg;
printf("%d\n", m);
return (void *) (arg + 1);
}
int main(int argc, char *argv[]) {
pthread_t p;
int rc, m;
Pthread_create(&p, NULL, mythread, (void *) 100);
Pthread_join(p, (void **) &m);
printf("returned %d\n", m);
return 0;
}
Figure 27.3: Simpler Argument Passing to a Thread
In this case, the variable ris allocated on the stack of mythread. How-
ever, when it returns, the value is automatically deallocated (that’s why
the stack is so easy to use, after all!), and thus, passing back a pointer to
a now deallocated variable will lead to all sorts of bad results. Certainly,
when you print out the values you think you returned, you’ll probably
(but not necessarily!) be surprised. Try it and find out for yourself2!
Finally, you might notice that the use of pthread create()to create
a thread, followed by an immediate call to pthread join(), is a pretty
strange way to create a thread. In fact, there is an easier way to accom-
plish this exact task; it’s called a procedure call. Clearly, we’ll usually be
creating more than just one thread and waiting for it to complete, other-
wise there is not much purpose to using threads at all.
We should note that not all code that is multi-threaded uses the join
routine. For example, a multi-threaded web server might create a number
of worker threads, and then use the main thread to accept requests and
pass them to the workers, indefinitely. Such long-lived programs thus
may not need to join. However, a parallel program that creates threads
to execute a particular task (in parallel) will likely use join to make sure
all such work completes before exiting or moving onto the next stage of
computation.
27.3 Locks
Beyond thread creation and join, probably the next most useful set of
functions provided by the POSIX threads library are those for providing
mutual exclusion to a critical section via locks. The most basic pair of
routines to use for this purpose is provided by the following:
int pthread_mutex_lock(pthread_mutex_t *mutex);
int pthread_mutex_unlock(pthread_mutex_t *mutex);
2 Fortunately the compiler gccwill likely complain when you write code like this, which
is yet another reason to pay attention to compiler warnings.
c ⃝ 2008–18, ARPACI-DUSSEAU
THREE
EASY
PIECES
6 INTERLUDE: THREAD API
The routines should be easy to understand and use. When you have a
region of code that is a critical section, and thus needs to be protected to
ensure correct operation, locks are quite useful. You can probably imag-
ine what the code looks like:
pthread_mutex_t lock;
pthread_mutex_lock(&lock);
x = x + 1; // or whatever your critical section is
pthread_mutex_unlock(&lock);
The intent of the code is as follows: if no other thread holds the lock
when pthread mutex lock()is called, the thread will acquire the lock
and enter the critical section. If another thread does indeed hold the lock,
the thread trying to grab the lock will not return from the call until it has
acquired the lock (implying that the thread holding the lock has released
it via the unlock call). Of course, many threads may be stuck waiting
inside the lock acquisition function at a given time; only the thread with
the lock acquired, however, should call unlock.
Unfortunately, this code is broken, in two important ways. The first
problem is a lack of proper initialization. All locks must be properly
initialized in order to guarantee that they have the correct values to begin
with and thus work as desired when lock and unlock are called.
With POSIX threads, there are two ways to initialize locks. One way
to do this is to use PTHREAD MUTEX INITIALIZER, as follows:
pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
Doing so sets the lock to the default values and thus makes the lock
usable. The dynamic way to do it (i.e., at run time) is to make a call to
pthread mutex init(), as follows:
int rc = pthread_mutex_init(&lock, NULL);
assert(rc == 0); // always check success!
The first argument to this routine is the address of the lock itself, whereas
the second is an optional set of attributes. Read more about the attributes
yourself; passing NULLin simply uses the defaults. Either way works, but
we usually use the dynamic (latter) method. Note that a corresponding
call to pthread mutex destroy()should also be made, when you are
done with the lock; see the manual page for all of details.
The second problem with the code above is that it fails to check error
codes when calling lock and unlock. Just like virtually any library rou-
tine you call in a UNIX system, these routines can also fail! If your code
doesn’t properly check error codes, the failure will happen silently, which
in this case could allow multiple threads into a critical section. Minimally,
use wrappers, which assert that the routine succeeded (e.g., as in Fig-
ure 27.4); more sophisticated (non-toy) programs, which can’t simply exit
when something goes wrong, should check for failure and do something
appropriate when the lock or unlock does not succeed.
OPERATING
SYSTEMS
[VERSION 1.00] WWW.OSTEP.ORG
INTERLUDE: THREAD API 7
// Use this to keep your code clean but check for failures
// Only use if exiting program is OK upon failure
void Pthread_mutex_lock(pthread_mutex_t *mutex) {
int rc = pthread_mutex_lock(mutex);
assert(rc == 0);
}
Figure 27.4: An Example Wrapper
The lock and unlock routines are not the only routines within the
pthreads library to interact with locks. In particular, here are two more
routines which may be of interest:
int pthread_mutex_trylock(pthread_mutex_t *mutex);
int pthread_mutex_timedlock(pthread_mutex_t *mutex,
struct timespec *abs_timeout);
These two calls are used in lock acquisition. The trylockversion re-
turns failure if the lock is already held; the timedlockversion of acquir-
ing a lock returns after a timeout or after acquiring the lock, whichever
happens first. Thus, the timedlock with a timeout of zero degenerates
to the trylock case. Both of these versions should generally be avoided;
however, there are a few cases where avoiding getting stuck (perhaps in-
definitely) in a lock acquisition routine can be useful, as we’ll see in future
chapters (e.g., when we study deadlock).
27.4 Condition Variables
The other major component of any threads library, and certainly the
case with POSIX threads, is the presence of a condition variable. Con-
dition variables are useful when some kind of signaling must take place
between threads, if one thread is waiting for another to do something be-
fore it can continue. Two primary routines are used by programs wishing
to interact in this way:
int pthread_cond_wait(pthread_cond_t *cond, pthread_mutex_t *mutex);
int pthread_cond_signal(pthread_cond_t *cond);
To use a condition variable, one has to in addition have a lock that is
associated with this condition. When calling either of the above routines,
this lock should be held.
The first routine, pthread cond wait(), puts the calling thread to
sleep, and thus waits for some other thread to signal it, usually when
something in the program has changed that the now-sleeping thread might
care about. A typical usage looks like this:
pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
pthread_cond_t cond = PTHREAD_COND_INITIALIZER;
Pthread_mutex_lock(&lock);
while (ready == 0)
Pthread_cond_wait(&cond, &lock);
Pthread_mutex_unlock(&lock);
c ⃝ 2008–18, ARPACI-DUSSEAU
THREE
EASY
PIECES
8 INTERLUDE: THREAD API
In this code, after initialization of the relevant lock and condition3, a
thread checks to see if the variable readyhas yet been set to something
other than zero. If not, the thread simply calls the wait routine in order to
sleep until some other thread wakes it.
The code to wake a thread, which would run in some other thread,
looks like this:
Pthread_mutex_lock(&lock);
ready = 1;
Pthread_cond_signal(&cond);
Pthread_mutex_unlock(&lock);
A few things to note about this code sequence. First, when signaling
(as well as when modifying the global variable ready), we always make
sure to have the lock held. This ensures that we don’t accidentally intro-
duce a race condition into our code.
Second, you might notice that the wait call takes a lock as its second
parameter, whereas the signal call only takes a condition. The reason
for this difference is that the wait call, in addition to putting the call-
ing thread to sleep, releases the lock when putting said caller to sleep.
Imagine if it did not: how could the other thread acquire the lock and
signal it to wake up? However, before returning after being woken, the
pthread cond wait()re-acquires the lock, thus ensuring that any time
the waiting thread is running between the lock acquire at the beginning
of the wait sequence, and the lock release at the end, it holds the lock.
One last oddity: the waiting thread re-checks the condition in a while
loop, instead of a simple if statement. We’ll discuss this issue in detail
when we study condition variables in a future chapter, but in general,
using a while loop is the simple and safe thing to do. Although it rechecks
the condition (perhaps adding a little overhead), there are some pthread
implementations that could spuriously wake up a waiting thread; in such
a case, without rechecking, the waiting thread will continue thinking that
the condition has changed even though it has not. It is safer thus to view
waking up as a hint that something might have changed, rather than an
absolute fact.
Note that sometimes it is tempting to use a simple flag to signal be-
tween two threads, instead of a condition variable and associated lock.
For example, we could rewrite the waiting code above to look more like
this in the waiting code:
while (ready == 0)
; // spin
The associated signaling code would look like this:
ready = 1;
3 Note that one could use pthread cond init() (and correspond-
ing the pthread cond destroy() call) instead of the static initializer
PTHREAD COND INITIALIZER. Sound like more work? It is.
OPERATING
SYSTEMS
[VERSION 1.00] WWW.OSTEP.ORG
INTERLUDE: THREAD API 9
Don’t ever do this, for the following reasons. First, it performs poorly
in many cases (spinning for a long time just wastes CPU cycles). Second,
it is error prone. As recent research shows [X+10], it is surprisingly easy
to make mistakes when using flags (as above) to synchronize between
threads; in that study, roughly half the uses of these ad hoc synchroniza-
tions were buggy! Don’t be lazy; use condition variables even when you
think you can get away without doing so.
If condition variables sound confusing, don’t worry too much (yet) –
we’ll be covering them in great detail in a subsequent chapter. Until then,
it should suffice to know that they exist and to have some idea how and
why they are used.
27.5 Compiling and Running
All of the code examples in this chapter are relatively easy to get up
and running. To compile them, you must include the header pthread.h
in your code. On the link line, you must also explicitly link with the
pthreads library, by adding the -pthreadflag.
For example, to compile a simple multi-threaded program, all you
have to do is the following:
prompt> gcc -o main main.c -Wall -pthread
As long as main.cincludes the pthreads header, you have now suc-
cessfully compiled a concurrent program. Whether it works or not, as
usual, is a different matter entirely.
27.6 Summary
We have introduced the basics of the pthread library, including thread
creation, building mutual exclusion via locks, and signaling and waiting
via condition variables. You don’t need much else to write robust and
efficient multi-threaded code, except patience and a great deal of care!
We now end the chapter with a set of tips that might be useful to you
when you write multi-threaded code (see the aside on the following page
for details). There are other aspects of the API that are interesting; if you
want more information, type man -k pthread on a Linux system to
see over one hundred APIs that make up the entire interface. However,
the basics discussed herein should enable you to build sophisticated (and
hopefully, correct and performant) multi-threaded programs. The hard
part with threads is not the APIs, but rather the tricky logic of how you
build concurrent programs. Read on to learn more.
c ⃝ 2008–18, ARPACI-DUSSEAU
THREE
EASY
PIECES
10 INTERLUDE: THREAD API
ASIDE: THREAD API GUIDELINES
There are a number of small but important things to remember when
you use the POSIX thread library (or really, any thread library) to build a
multi-threaded program. They are:
• Keep it simple. Above all else, any code to lock or signal between
threads should be as simple as possible. Tricky thread interactions
lead to bugs.
• Minimize thread interactions. Try to keep the number of ways
in which threads interact to a minimum. Each interaction should
be carefully thought out and constructed with tried and true ap-
proaches (many of which we will learn about in the coming chap-
ters).
• Initialize locks and condition to code that sometimes works variables. Failure to do so will lead
and sometimes fails in very strange
ways.
• Check your return codes. Of course, in any C and UNIX program-
ming you do, you should be checking each and every return code,
and it’s true here as well. Failure to do so will lead to bizarre and
hard to understand behavior, making you likely to (a) scream, (b)
pull some of your hair out, or (c) both.
• Be careful with how you pass arguments to, and return values
from, threads. In particular, any time you are passing a reference to
a variable allocated on the stack, you are probably doing something
wrong.
• Each thread has its own stack. As related to the point above, please
remember that each thread has its own stack. Thus, if you have a
locally-allocated variable inside of some function a thread is exe-
cuting, it is essentially private to that thread; no other thread can
(easily) access it. To share data between threads, the values must be
in the heap or otherwise some locale that is globally accessible.
• Always use condition variables to signal between threads. While
it is often tempting to use a simple flag, don’t do it.
• Use the manual pages. On Linux, in particular, the pthread man
pages are highly informative and discuss much of the nuances pre-
sented here, often in even more detail. Read them carefully!