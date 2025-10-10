# Chapter 6: Proportional Share Scheduling 🎰

_Understanding how to fairly divide CPU time using lottery tickets and deterministic strides_

---

## 📋 Table of Contents

1. [🎯 Introduction](#1-introduction)
2. [🎫 Basic Concept: Tickets Represent Your Share](#2-basic-concept-tickets-represent-your-share)
   - 2.1. [How Lottery Scheduling Works](#21-how-lottery-scheduling-works)
   - 2.2. [The Power of Randomness](#22-the-power-of-randomness)
3. [🔧 Ticket Mechanisms](#3-ticket-mechanisms)
   - 3.1. [Ticket Currency](#31-ticket-currency)
   - 3.2. [Ticket Transfer](#32-ticket-transfer)
   - 3.3. [Ticket Inflation](#33-ticket-inflation)
4. [💻 Implementation](#4-implementation)
   - 4.1. [Data Structures](#41-data-structures)
   - 4.2. [Scheduling Algorithm](#42-scheduling-algorithm)
   - 4.3. [Optimization Strategies](#43-optimization-strategies)
5. [📊 Fairness Analysis](#5-fairness-analysis)
   - 5.1. [Short-Term vs Long-Term Fairness](#51-short-term-vs-long-term-fairness)
   - 5.2. [Experimental Results](#52-experimental-results)
6. [🎯 Stride Scheduling](#6-stride-scheduling)
   - 6.1. [Deterministic Fair-Share](#61-deterministic-fair-share)
   - 6.2. [Stride vs Lottery Tradeoffs](#62-stride-vs-lottery-tradeoffs)
7. [🐧 Linux Completely Fair Scheduler (CFS)](#7-linux-completely-fair-scheduler-cfs)
   - 7.1. [Virtual Runtime](#71-virtual-runtime)
   - 7.2. [Time Slice Calculation](#72-time-slice-calculation)
   - 7.3. [Process Weighting (Nice Values)](#73-process-weighting-nice-values)
   - 7.4. [Red-Black Trees](#74-red-black-trees)
   - 7.5. [Handling I/O and Sleeping Processes](#75-handling-io-and-sleeping-processes)
8. [⚠️ Challenges and Limitations](#8-challenges-and-limitations)
9. [📝 Summary](#9-summary)

---

## 1. 🎯 Introduction

**In plain English:** Imagine you're running a restaurant 🍽️ with one chef 👨‍🍳 and multiple customer orders. Instead of trying to finish orders as fast as possible (like previous scheduling approaches), what if you wanted to give each customer a **fair share** of the chef's time based on how much they paid? A VIP customer who paid $100 gets more chef time than someone who paid $10. That's proportional-share scheduling.

**In technical terms:** Proportional-share schedulers guarantee that each job obtains a certain **percentage of CPU time**, rather than optimizing for turnaround time or response time. Instead of asking "which job finishes fastest?" they ask "does each job get its fair share?"

**Why it matters:** This approach is crucial for:
- 🖥️ **Virtual machines** - Allocating CPU fairly across VMs
- ☁️ **Cloud computing** - Giving customers the CPU they paid for
- 🎮 **Game servers** - Ensuring each player gets equal processing
- 📱 **Mobile devices** - Balancing foreground/background apps

> **💡 Insight**
>
> Proportional-share scheduling represents a **fundamental shift in goals**. Previous schedulers (FIFO, SJF, RR) focused on **performance metrics** (turnaround, response time). Proportional-share focuses on **fairness metrics** (each process gets its promised share). This distinction mirrors resource allocation everywhere: Should we optimize for speed or for fairness? Both matter, just in different contexts.

### 🎯 The Core Challenge

**THE CRUX:** How can we design a scheduler to share the CPU in a proportional manner? What are the key mechanisms for doing so? How effective are they?

**Three approaches we'll explore:**

```
Lottery Scheduling          Stride Scheduling           CFS (Linux)
──────────────────          ─────────────────           ───────────
🎲 Probabilistic           ✅ Deterministic            ⚖️ Virtual Runtime
Random ticket draw         Precise stride tracking     Efficient tracking
Simple, lightweight        Accurate, predictable       Production-ready
```

---

## 2. 🎫 Basic Concept: Tickets Represent Your Share

### 2.1. How Lottery Scheduling Works

**In plain English:** Think of CPU time as a raffle 🎟️. Every process gets tickets based on how much CPU it should receive. Every time slice (say, every 10ms), we draw a random winning ticket. Whoever owns that ticket runs for the next time slice. Processes with more tickets win more often—**probabilistically** getting their fair share over time.

**Core principles:**

```
Ticket Distribution                    Probability
───────────────────                    ───────────

Process A: 75 tickets    ──────────>   75% chance to win
Process B: 25 tickets    ──────────>   25% chance to win
───────────────────────
Total: 100 tickets
```

**Step-by-step lottery example:**

```
Time Slice    Random Number    Winner      Schedule
──────────    ─────────────    ──────      ────────
1             63 (A's range)   A           A runs
2             85 (B's range)   B           B runs
3             70 (A's range)   A           A runs
4             39 (A's range)   A           A runs
5             76 (B's range)   B           B runs
6             17 (A's range)   A           A runs
7             29 (A's range)   A           A runs
8             41 (A's range)   A           A runs

Ticket Ranges:
A holds tickets: 0-74   (75 tickets)
B holds tickets: 75-99  (25 tickets)
```

**Resulting execution pattern:**
```
A A B A A B A A A A A A A A A A B B B B
│                                         │
└─────────────────────────────────────────┘
    Over 20 time slices:
    A ran 16 times (80%) - close to target 75%
    B ran 4 times (20%) - close to target 25%
```

> **💡 Insight**
>
> Notice how **fairness emerges over time** but isn't guaranteed in any short window. In the example, B got exactly 20% instead of 25%—but run this for thousands of time slices, and the percentages converge to the desired values. This is **probabilistic correctness**, similar to how randomized algorithms in data structures (skip lists, hash tables) give expected-case guarantees.

### 2.2. 🎲 The Power of Randomness

**Why use randomness instead of deterministic algorithms?**

**In plain English:** Imagine trying to fairly split dinner duty among roommates 🏠. You could maintain a complex schedule tracking exactly who did what when. Or you could draw straws randomly—simpler, and over time it evens out. Randomness trades short-term precision for long-term simplicity.

**Three key advantages of randomness:**

#### 1️⃣ Avoids Corner Cases

```
Deterministic LRU                Randomized Replacement
─────────────────                ──────────────────────

Cyclic access pattern:           Random selection:
A B C D A B C D A B C D...      Works equally well on
↓                                all patterns
Worst-case performance!          No pathological cases
(0% hit rate)
```

**Example:** The LRU (Least Recently Used) page replacement algorithm performs terribly on sequential-cyclic workloads. Random replacement doesn't have this weakness—it performs consistently (if not optimally) across all workloads.

#### 2️⃣ Lightweight State

```
Fair-Share with Accounting       Lottery Scheduling
──────────────────────           ──────────────────

Per-process state:               Per-process state:
• Total CPU consumed: 10.5s      • Number of tickets: 75
• Target share: 25%
• Current deficit: -2.3s         That's it! 🎉
• Historical average: ...
• Priority adjustments: ...
```

Traditional fair-share schedulers need extensive per-process accounting. Lottery only needs ticket counts—much simpler!

#### 3️⃣ Speed

**Generating a random number is fast:**

```c
// Very fast pseudo-random generation
int random = (state * 1103515245 + 12345) & 0x7fffffff;
int winner = random % total_tickets;
```

No complex calculations, no sorting, no searching through histories. Just generate a number and pick the winner.

> **💡 Insight**
>
> The **randomness tradeoff** appears throughout computer science:
> - **Quicksort**: Random pivot selection avoids O(n²) worst case
> - **Skip lists**: Randomized levels give expected O(log n) search
> - **Hash tables**: Random hash functions prevent adversarial inputs
> - **Load balancing**: Random server selection prevents overload
>
> When you need simplicity, robustness, and good average-case performance, **randomness is often the answer**.

**The ticket abstraction is universally powerful:**

Tickets can represent shares of **any** resource:

```
Resource Type         Ticket Application
─────────────         ──────────────────
💻 CPU time          → Process gets 25% of CPU cycles
💾 Memory            → VM gets 4GB out of 16GB total
🌐 Network           → Connection gets 100Mbps of 1Gbps link
💿 Disk I/O          → App gets 30% of disk bandwidth
```

This abstraction appears in modern systems:
- **VMware ESX Server**: Tickets for memory shares between VMs
- **Lottery scheduling**: Original CPU time application
- **Network QoS**: Bandwidth allocation
- **Storage QoS**: IOPS allocation

---

## 3. 🔧 Ticket Mechanisms

Beyond basic lottery drawing, tickets support sophisticated manipulation mechanisms that make the system more flexible and powerful.

### 3.1. 💱 Ticket Currency

**In plain English:** Imagine you're managing an international company 🌍 where different departments have budgets in different currencies (USD, EUR, JPY). Each department manager allocates their budget to projects internally. The CFO converts everything to a common global currency for company-wide decisions. Ticket currency works the same way.

**How it works:**

**Users** receive tickets in **global currency**. They can allocate tickets among their jobs in their own **local currency**. The system automatically converts local → global for scheduling decisions.

**Example scenario:**

```
Global Allocation
─────────────────
User A: 100 tickets (global)
User B: 100 tickets (global)
─────────────────
Total: 200 tickets (global)


User A's Internal Allocation (A's currency)
────────────────────────────────────────────
Job A1: 500 tickets (A's currency)
Job A2: 500 tickets (A's currency)
────────────────────────────────────────────
Total: 1000 tickets (A's currency)

Conversion: A1 gets (500/1000) × 100 = 50 global tickets
           A2 gets (500/1000) × 100 = 50 global tickets


User B's Internal Allocation (B's currency)
────────────────────────────────────────────
Job B1: 10 tickets (B's currency)
────────────────────────────────────────────
Total: 10 tickets (B's currency)

Conversion: B1 gets (10/10) × 100 = 100 global tickets


Final Global Schedule
─────────────────────
A1: 50 tickets  (25% of CPU)
A2: 50 tickets  (25% of CPU)
B1: 100 tickets (50% of CPU)
─────────────────────
Total: 200 tickets
```

**Why this matters:**
- ✅ Users don't need to coordinate with each other
- ✅ Each user allocates naturally (50/50, 70/30, etc.) in their own units
- ✅ System handles conversion automatically
- ✅ Adding a third job in User A's allocation doesn't require understanding global totals

**Visual representation:**

```
User A (100 global)              User B (100 global)
├── A1: 500 local                └── B1: 10 local
│   └─> 50 global                    └─> 100 global
└── A2: 500 local
    └─> 50 global

Lottery draw over: [A1: 0-49][A2: 50-99][B1: 100-199]
```

### 3.2. 🎁 Ticket Transfer

**In plain English:** Imagine you're in line at a coffee shop ☕. You have a meeting in 5 minutes, so you give your "priority tickets" to the barista temporarily. They serve you faster, then give your tickets back. Ticket transfer lets processes temporarily donate priority to helpers.

**Classic use case: Client-Server**

```
Initial State
─────────────
Client C: 100 tickets
Server S: 50 tickets


Step 1: Client sends request to Server
───────────────────────────────────────
C → S: "Please process my database query"


Step 2: Client transfers tickets to Server
───────────────────────────────────────────
Client C: 0 tickets     (temporarily gave them up)
Server S: 150 tickets   (received client's tickets)

Server now highly likely to win lottery!
Processes client's request quickly.


Step 3: Server completes work and returns tickets
──────────────────────────────────────────────────
Client C: 100 tickets   (tickets returned)
Server S: 50 tickets    (back to normal)
```

**Timeline visualization:**

```
Time →
────────────────────────────────────────────────────────
Client:  Running[100] ─→ Blocked[0] ─────────→ Ready[100]
           ↓             (waiting)                  ↑
         Request      Server working             Response
           ↓                                        ↑
Server:  Ready[50] ──→ Running[150] ─────────→ Ready[50]
                       (boosted!)

Transferred tickets: [=========>]
                                 [<=========]
                                  Returned
```

**Why this matters:**
- ⚡ **Minimizes response time** for the client
- 🎯 **Priority inheritance** happens automatically
- 🚫 **Prevents priority inversion** (low-priority server blocking high-priority client)
- 💪 **Self-optimizing system** - processes that need to finish quickly get temporary boosts

### 3.3. 📈 Ticket Inflation

**In plain English:** Imagine a family 👨‍👩‍👧‍👦 deciding how to split dessert 🍰. If everyone trusts each other, you can just say "I'm extra hungry today, give me a bigger slice" without formal negotiation. Ticket inflation lets **trusted** processes adjust their own priority on the fly.

**How it works:**

A process can **temporarily** raise or lower its ticket count:

```
Process State                    Action
─────────────                    ──────

Initial: 100 tickets             Normal priority

Realizes it needs more CPU       inflate(200)
→ Now has: 200 tickets           Higher priority!

Finishes intensive work          inflate(50)
→ Now has: 50 tickets            Lower priority (nice!)
```

**Important constraints:**

```
✅ SAFE: Cooperative environment
────────────────────────────────
• Group of processes from same user
• Trusted processes that won't cheat
• Example: Multiple threads of same app

❌ DANGEROUS: Competitive environment
──────────────────────────────────────
• Untrusted users competing for CPU
• Malicious process could:
    inflate(999999999)  // Monopolize CPU!
• Breaks fairness completely
```

**Example use case:**

```
Video Player Application (3 threads)
────────────────────────────────────

Decoder Thread:
  • inflate(200) when decoding 4K video
  • inflate(50) when paused

UI Thread:
  • inflate(150) when user is dragging timeline
  • inflate(50) when idle

Network Thread:
  • inflate(100) when buffering
  • inflate(25) when buffer full
```

These threads **trust each other** (same application), so self-adjustment is safe and efficient—no need to ask the OS for permission each time.

> **💡 Insight**
>
> Ticket currency, transfer, and inflation demonstrate **mechanism vs. policy** separation:
> - **Mechanism**: How tickets work (draw, convert, transfer, inflate)
> - **Policy**: When to use each mechanism (application decides)
>
> The OS provides flexible mechanisms; applications implement policies suited to their needs. This is a hallmark of good system design—the same pattern that makes UNIX pipes powerful (mechanism: byte streams; policy: what to do with them).

---

## 4. 💻 Implementation

### 4.1. 📊 Data Structures

**The simplest approach: A linked list of processes**

```c
typedef struct node {
    int tickets;           // Number of tickets this process owns
    struct proc *process;  // Pointer to actual process structure
    struct node *next;     // Next process in list
} node_t;
```

**Visual representation:**

```
Process List (head pointer)
│
├─→ [Job A: 100 tickets] ─→ [Job B: 50 tickets] ─→ [Job C: 250 tickets] ─→ NULL
    │                        │                       │
    └─> Process A PCB        └─> Process B PCB       └─> Process C PCB
```

**Key information we need to track:**

```c
struct lottery_scheduler {
    node_t *head;          // First process in list
    int total_tickets;     // Sum of all tickets (400 in example)
};
```

### 4.2. 🎯 Scheduling Algorithm

**The complete lottery scheduling decision code:**

```c
int counter = 0;

// winner: random number in range [0, totaltickets-1]
int winner = getrandom(0, totaltickets);

// Walk through the list, accumulating tickets
node_t *current = head;
while (current) {
    counter = counter + current->tickets;
    if (counter > winner)
        break;  // Found the winner!
    current = current->next;
}

// 'current' now points to the winning process
schedule(current->process);
```

**Step-by-step example:**

```
Setup:
──────
head → [A:100] → [B:50] → [C:250] → NULL
Total tickets: 400
Random winner: 300


Execution trace:
────────────────

Iteration 1:
  current = A
  counter = 0 + 100 = 100
  Is 100 > 300? No
  Continue...

Iteration 2:
  current = B
  counter = 100 + 50 = 150
  Is 150 > 300? No
  Continue...

Iteration 3:
  current = C
  counter = 150 + 250 = 400
  Is 400 > 300? Yes! ✓
  Break and schedule C
```

**Ticket ranges visualization:**

```
Ticket Number Line
0                    100    150              400
├──────────────────────┼──────┼────────────────┤
│         A            │  B   │       C        │
│     (100 tickets)    │ (50) │  (250 tickets) │
└──────────────────────┴──────┴────────────────┘
                                ↑
                              Winner: 300
                              (Falls in C's range)
```

**Why this algorithm works:**

Each process effectively owns a **range** of ticket numbers:
- A owns tickets **0-99** (100 tickets)
- B owns tickets **100-149** (50 tickets)
- C owns tickets **150-399** (250 tickets)

We pick a random ticket and find which range it falls into—that's our winner!

### 4.3. ⚡ Optimization Strategies

#### 🔄 Sorted List Optimization

**Problem:** If tickets are distributed unevenly, we might traverse many low-ticket processes before finding the winner.

**Solution:** Sort list by ticket count (highest first)

```
Before Sorting (worst case for winner=350):
───────────────────────────────────────────
head → [A:10] → [B:15] → [C:25] → [D:350] → NULL
       ↓         ↓         ↓         ↓
     Iterate   Iterate   Iterate   FOUND! (4 iterations)


After Sorting (best case):
──────────────────────────
head → [D:350] → [C:25] → [B:15] → [A:10] → NULL
       ↓
     FOUND! (1 iteration often)
```

**Trade-off analysis:**

```
Unsorted List                    Sorted List
─────────────                    ───────────
✅ Fast insertion: O(1)          ❌ Slower insertion: O(n)
❌ Slow scheduling: O(n) avg     ✅ Fast scheduling: O(1) often
📝 Good when: tickets equal      📝 Good when: tickets skewed
```

#### 🎲 Random Number Generation

**Naive approach (WRONG):**

```c
// DON'T DO THIS!
int winner = rand() % total_tickets;
```

**Problem:** If `total_tickets` is not a divisor of `RAND_MAX`, you get **biased** results. Some tickets have higher probability of being selected!

**Correct approach:**

```c
// Proper range generation
int getrandom(int min, int max) {
    int range = max - min + 1;
    int limit = RAND_MAX - (RAND_MAX % range);
    int r;

    do {
        r = rand();
    } while (r >= limit);  // Reject biased values

    return min + (r % range);
}
```

> **💡 Insight**
>
> **The biased random number problem** is subtle and easy to miss. It's related to the **modulo bias** issue:
>
> If `RAND_MAX = 10` and `range = 3`:
> - Values 0-9 are generated
> - After `% 3`: We get 0,1,2,0,1,2,0,1,2,0
> - Result: 0 appears 4 times, 1 and 2 appear 3 times each
> - **Not uniform!**
>
> This same issue appears in cryptography, statistics, and game development. Always be careful when mapping one range to another!

---

## 5. 📊 Fairness Analysis

### 5.1. 📏 Short-Term vs Long-Term Fairness

**In plain English:** Flip a fair coin 🪙 10 times. You might get 7 heads and 3 tails (70/30). Not very fair! But flip it 10,000 times and you'll get very close to 5,000 heads and 5,000 tails (50/50). Lottery scheduling is the same—fairness emerges over time.

**Defining fairness:**

```
Fairness Metric (F)
───────────────────
F = Time when first job completes
    ─────────────────────────────
    Time when second job completes

Perfect fairness: F = 1.0 (both finish simultaneously)
Poor fairness: F → 0 (huge gap in completion times)
```

**Example calculation:**

```
Scenario: Two jobs, equal tickets (100 each), same runtime R

Case 1: R = 10 time slices
────────────────────────────
Job 1 finishes at time: 10
Job 2 finishes at time: 20
F = 10/20 = 0.5 (not very fair!)


Case 2: R = 100 time slices
─────────────────────────────
Job 1 finishes at time: 100
Job 2 finishes at time: 200
F = 100/200 = 0.5 (still not perfect, but closer)


Case 3: R = 1000 time slices
──────────────────────────────
Job 1 finishes at time: 1005
Job 2 finishes at time: 1995
F = 1005/1995 ≈ 0.503 (much better!)
```

### 5.2. 📈 Experimental Results

**Fairness vs. job length study:**

```
Study Parameters:
─────────────────
• Two jobs with equal tickets (100 each)
• Same runtime R (varied from 1 to 1000)
• 30 trials per configuration
• Measure: Average fairness F


Results Visualization:

Fairness (F)
1.0 ┤                            ▓▓▓▓▓▓▓▓▓▓▓
    │                        ▓▓▓▓
    │                    ▓▓▓▓
0.8 ┤                ▓▓▓▓
    │            ▓▓▓▓
    │        ▓▓▓▓
0.6 ┤    ▓▓▓▓
    │ ▓▓▓
    │▓▓
0.4 ┤▓
    │
    │
0.2 ┤
    │
    └────────────────────────────────────────
     1    10    100         1000          Job Length (R)


Key Observations:
─────────────────
• R = 1:    F ≈ 0.5  (High variance, poor fairness)
• R = 10:   F ≈ 0.65 (Improving...)
• R = 100:  F ≈ 0.85 (Much better)
• R = 1000: F ≈ 0.95 (Nearly perfect!)
```

**Why this happens:**

```
Short Jobs (R = 10)              Long Jobs (R = 1000)
───────────────────              ────────────────────

Sample execution:                Sample execution:
A A A A A A A B B B             A B A B A B A B A B A B...
↑                                ↑
High variance                    Averages out
(random clusters)                (law of large numbers)

Few lottery draws = lucky        Many lottery draws = fair
streaks possible                 distribution emerges
```

> **💡 Insight**
>
> This illustrates the **Law of Large Numbers** from probability theory: As sample size increases, the sample average converges to the expected value. In our case:
> - **Expected value**: 50% CPU for each job
> - **Short runs**: High variance, might get 70/30
> - **Long runs**: Low variance, approaches 50/50
>
> This same principle underlies Monte Carlo simulations, A/B testing, and polling—you need sufficient samples for statistical validity!

---

## 6. 🎯 Stride Scheduling

### 6.1. ✅ Deterministic Fair-Share

**In plain English:** Lottery scheduling uses randomness, so there's always some uncertainty. What if you want **perfect** fairness—guaranteed? That's stride scheduling. Instead of drawing random tickets, we carefully track exactly how much CPU each process has used and always pick the one that's gotten the least so far.

**Core concept:**

Each process has two values:
1. **Stride**: Inverse of tickets (how much to increment each time)
2. **Pass**: Current progress counter (starts at 0)

**Formula:**

```
Stride Calculation
──────────────────
stride = LARGE_NUMBER / tickets

Example with LARGE_NUMBER = 10,000:
Job A (100 tickets): stride = 10,000 / 100 = 100
Job B (50 tickets):  stride = 10,000 / 50  = 200
Job C (250 tickets): stride = 10,000 / 250 = 40
```

**Algorithm:**

```
At each scheduling decision:
1. Pick process with LOWEST pass value
2. Run that process for one time slice
3. Increment its pass by its stride
4. Repeat
```

### 6.2. 🔄 Complete Stride Scheduling Example

**Initial setup:**

```
Process   Tickets   Stride   Pass
────────  ───────   ──────   ────
A         100       100      0
B         50        200      0
C         250       40       0
```

**Execution trace:**

```
Step   A_Pass   B_Pass   C_Pass   Who Runs?   Why?
────   ──────   ──────   ──────   -────────   ──────────────────
0      0        0        0        A*          Tie, pick any
1      100      0        0        B           0 < 100
2      100      200      0        C           0 < 100 < 200
3      100      200      40       C           40 < 100 < 200
4      100      200      80       C           80 < 100 < 200
5      100      200      120      A           100 < 120 < 200
6      200      200      120      C           120 < 200 = 200
7      200      200      160      C           160 < 200 = 200
8      200      200      200      A,B,C       All tied!
9      300      200      200      B           200 < 200 < 300
...

Execution sequence: A B C C C A C C (A B C) ...
                                    └──┬──┘
                                  Cycle repeats
```

**After one complete cycle (pass values all equal):**

```
Jobs Run Count (in one cycle)
──────────────────────────────
C ran: 5 times  (250/400 = 62.5%) ✓
A ran: 2 times  (100/400 = 25.0%) ✓
B ran: 1 time   (50/400  = 12.5%) ✓

PERFECT proportional sharing! 🎯
```

**Visual timeline:**

```
Time Slice   1   2   3   4   5   6   7   8   9   10  11  12  ...
             │   │   │   │   │   │   │   │   │   │   │   │
Execution    A   B   C   C   C   A   C   C   A   B   C   C  ...
             └───────────────┬──────────────┘ └──────┬──────┘
                     Cycle 1                    Cycle 2

Proportions after cycle 1:
C: 5/8 = 62.5% (target: 62.5%) ✓
A: 2/8 = 25.0% (target: 25.0%) ✓
B: 1/8 = 12.5% (target: 12.5%) ✓
```

> **💡 Insight**
>
> Stride scheduling is **deterministic** while lottery is **probabilistic**:
>
> | Aspect          | Lottery              | Stride               |
> |-----------------|----------------------|----------------------|
> | Fairness        | Eventually converges | Perfect every cycle  |
> | Complexity      | Very simple          | Slightly complex     |
> | State required  | Just ticket counts   | Pass values needed   |
> | Predictability  | Cannot predict       | Fully deterministic  |
> | Adding process  | Easy (no global state)| Hard (what pass value?) |
>
> This trade-off between **simplicity and precision** appears everywhere in CS: lossy vs. lossless compression, approximate vs. exact algorithms, eventual vs. strong consistency.

### 6.3. 🆚 Stride vs Lottery Tradeoffs

**The global state problem:**

```
Scenario: New process D arrives mid-execution
──────────────────────────────────────────────

Current state:
A: pass = 500
B: pass = 800
C: pass = 350

❓ What should D's initial pass value be?

Option 1: Start at 0
─────────────────────
D: pass = 0  (stride = 100)

Problem: D will monopolize CPU!
A(500) B(800) C(350) D(0) → Always picks D
D runs forever until pass catches up to others
⚠️ Unfair to existing processes!


Option 2: Start at current minimum
───────────────────────────────────
D: pass = 350  (same as C)

Better, but still complex:
• Need to track global minimum
• What if C exits? Recalculate minimum
• Requires coordination across all processes
```

**Lottery scheduling advantage:**

```
Same scenario with lottery:
──────────────────────────

Current state:
A: 100 tickets
B: 50 tickets
C: 250 tickets
Total: 400 tickets

New process D arrives:
D: 75 tickets

Simply update:
Total: 400 + 75 = 475 tickets

Next lottery draw is over 475 tickets.
D immediately has fair chance! 🎉

No coordination needed!
No global state to manage!
```

**When to use each:**

```
Use Lottery Scheduling When:            Use Stride Scheduling When:
────────────────────────────            ───────────────────────────
✅ Processes arrive/leave frequently    ✅ Static set of processes
✅ Approximate fairness is acceptable   ✅ Perfect fairness required
✅ Simplicity is paramount              ✅ Predictability matters
✅ Low overhead needed                  ✅ Can tolerate more complexity

Examples:                               Examples:
• Interactive systems                   • Real-time systems
• Cloud multi-tenancy                   • Video encoders
• General-purpose OS                    • Scientific computing
```

> **💡 Insight**
>
> The lottery vs. stride choice exemplifies **engineering trade-offs**:
> - Lottery: Optimized for **dynamism** (easy to add/remove processes)
> - Stride: Optimized for **precision** (exact fairness guarantees)
>
> Neither is "better"—they serve different needs. This is like choosing between:
> - HashMap (fast average case) vs. TreeMap (guaranteed worst case)
> - UDP (low overhead) vs. TCP (reliability)
> - NoSQL (availability) vs. SQL (consistency)
>
> Understanding when to favor simplicity vs. precision is a key engineering skill.

---

## 7. 🐧 Linux Completely Fair Scheduler (CFS)

**In plain English:** CFS is Linux's production scheduler—what runs on billions of devices 📱💻🖥️ worldwide. It's like stride scheduling's practical cousin: deterministic fairness, but engineered for **massive scale** and **efficiency**. Instead of tickets and passes, it uses "virtual runtime" and clever data structures to minimize scheduling overhead.

### 7.1. ⏱️ Virtual Runtime

**Core idea: Track how much CPU each process has consumed**

```
Virtual Runtime (vruntime)
──────────────────────────
Every process accumulates vruntime as it runs.
Scheduler always picks process with LOWEST vruntime.

Simple, elegant! 🎯
```

**How it works:**

```
Initial State (all processes start)
───────────────────────────────────
Process A: vruntime = 0
Process B: vruntime = 0
Process C: vruntime = 0


After A runs for 10ms:
──────────────────────
Process A: vruntime = 10ms  ← Ran for 10ms
Process B: vruntime = 0ms   ← Hasn't run yet (LOWEST!)
Process C: vruntime = 0ms   ← Hasn't run yet

Scheduler picks B (lowest vruntime)


After B runs for 10ms:
──────────────────────
Process A: vruntime = 10ms
Process B: vruntime = 10ms  ← Now caught up
Process C: vruntime = 0ms   ← Still hasn't run (LOWEST!)

Scheduler picks C


After C runs for 10ms:
──────────────────────
Process A: vruntime = 10ms  ← LOWEST (tied)
Process B: vruntime = 10ms  ← LOWEST (tied)
Process C: vruntime = 10ms  ← LOWEST (tied)

All equal! Pick any (round-robin among tied)
```

**Visualization over time:**

```
A B C D process labels
│ │ │ │
├─┬─┬─┤
│ │ │ │
└─┴─┴─┘
  0ms    Initial state (all vruntime = 0)

    A runs 12ms
    ↓
┌───┬─┬─┐
│   │ │ │
├───┼─┼─┤
│12 │0│0│
└───┴─┴─┘
        B runs 12ms (lowest)
        ↓
┌───┬───┬─┐
│   │   │ │
├───┼───┼─┤
│12 │12 │0│
└───┴───┴─┘
            C runs 12ms (lowest)
            ↓
┌───┬───┬───┐
│   │   │   │
├───┼───┼───┤
│12 │12 │12 │
└───┴───┴───┘
  All equal → round-robin
```

### 7.2. ⚙️ Time Slice Calculation

**The dynamic time slice formula:**

Unlike traditional schedulers with fixed time slices (e.g., 10ms), CFS computes time slices **dynamically** based on the number of running processes.

```
Control Parameters
──────────────────
sched_latency:   Target period for fairness (default: 48ms)
min_granularity: Minimum time slice (default: 6ms)


Time Slice Calculation
──────────────────────
time_slice = sched_latency / n

where n = number of running processes
```

**Example scenarios:**

```
Scenario 1: 4 processes running
───────────────────────────────
time_slice = 48ms / 4 = 12ms per process

Timeline (48ms period):
0ms      12ms     24ms     36ms     48ms
├────────┼────────┼────────┼────────┤
│   A    │   B    │   C    │   D    │
└────────┴────────┴────────┴────────┘
All processes run once in 48ms ✓ (perfectly fair!)


Scenario 2: 2 processes finish, now 2 remain
──────────────────────────────────────────────
time_slice = 48ms / 2 = 24ms per process

Timeline (48ms period):
0ms           24ms              48ms
├─────────────┼─────────────────┤
│      A      │        B        │
└─────────────┴─────────────────┘
Processes get longer slices (fewer context switches!)


Scenario 3: 10 processes running
─────────────────────────────────
time_slice = 48ms / 10 = 4.8ms

⚠️ BUT: 4.8ms < min_granularity (6ms)
→ CFS overrides: time_slice = 6ms per process

Timeline (60ms actual period, not 48ms):
0ms   6   12  18  24  30  36  42  48  54  60ms
├────┼───┼───┼───┼───┼───┼───┼───┼───┼───┤
│ A │ B │ C │ D │ E │ F │ G │ H │ I │ J │
└────┴───┴───┴───┴───┴───┴───┴───┴───┴───┘

Total period: 10 × 6ms = 60ms (not 48ms)
Trade-off: Slightly less fair, but acceptable overhead
```

**Why min_granularity matters:**

```
Without minimum (pathological case):
────────────────────────────────────
1000 processes running
time_slice = 48ms / 1000 = 0.048ms (48 microseconds!)

Problems:
⚠️ Context switch cost: ~1-5 microseconds
⚠️ Time slice: 48 microseconds
→ Spending 10%+ of time just switching! (terrible overhead)


With minimum (actual CFS):
──────────────────────────
time_slice = max(48ms / 1000, 6ms) = 6ms

Total period: 1000 × 6ms = 6 seconds
Trade-off: Not perfectly fair over 48ms, but:
✅ Still reasonably fair over 6 seconds
✅ Acceptable context switch overhead
```

> **💡 Insight**
>
> CFS's **adaptive time slice** demonstrates a fundamental OS principle: **balance between fairness and efficiency**.
>
> - **Smaller time slices** → More fair (everyone gets frequent turns)
> - **Larger time slices** → More efficient (less context switching)
>
> This is the same trade-off in:
> - **Network packet size**: Small packets (low latency) vs. large packets (high throughput)
> - **Database transactions**: Short transactions (high concurrency) vs. long transactions (less overhead)
> - **Garbage collection**: Frequent small GC pauses vs. infrequent large pauses

### 7.3. ⚖️ Process Weighting (Nice Values)

**In plain English:** Not all processes are equal. Your video call 📹 should get more CPU than a background file sync. The UNIX `nice` command lets you adjust priority: "be nice to others" (positive nice = lower priority) or "I'm important" (negative nice = higher priority).

**Nice value range:**

```
Priority Level        Nice Value    Priority
──────────────        ──────────    ────────
Highest priority      -20           ████████████████████
                      -15           ████████████████
                      -10           ████████████
                      -5            ██████████
Default               0             ████████
                      +5            ██████
                      +10           ████
                      +15           ██
Lowest priority       +19           █
```

**Weight mapping (from Linux kernel):**

```c
static const int prio_to_weight[40] = {
  /* -20 */  88761, 71755, 56483, 46273, 36291,
  /* -15 */  29154, 23254, 18705, 14949, 11916,
  /* -10 */   9548,  7620,  6100,  4904,  3906,
  /*  -5 */   3121,  2501,  1991,  1586,  1277,
  /*   0 */   1024,   820,   655,   526,   423,
  /*  +5 */    335,   272,   215,   172,   137,
  /* +10 */    110,    87,    70,    56,    45,
  /* +15 */     36,    29,    23,    18,    15,
};
```

**Key property:** Each 1 nice value change ≈ **10% CPU change**

```
Nice Differences and CPU Ratios
────────────────────────────────

Nice 0  vs Nice +1:   1024 vs 820  ≈ 1.25x difference
Nice 0  vs Nice +5:   1024 vs 335  ≈ 3x difference
Nice 0  vs Nice +10:  1024 vs 110  ≈ 9.3x difference
Nice -5 vs Nice 0:    3121 vs 1024 ≈ 3x difference
Nice -10 vs Nice +10: 9548 vs 110  ≈ 86x difference!
```

**Weighted time slice calculation:**

```
Formula:
───────
time_slice_k = (weight_k / Σ(all weights)) × sched_latency


Example: Two processes with different priorities
────────────────────────────────────────────────

Process A: nice = -5  →  weight = 3121
Process B: nice = 0   →  weight = 1024

Total weight = 3121 + 1024 = 4145

A's time slice = (3121 / 4145) × 48ms ≈ 36ms (75%)
B's time slice = (1024 / 4145) × 48ms ≈ 12ms (25%)


Timeline:
0ms              36ms     48ms
├────────────────┼────────┤
│       A        │   B    │
└────────────────┴────────┘

A gets 3× more CPU than B! 🎯
```

**Weighted vruntime accumulation:**

Without weighting, vruntime increases at the same rate for everyone:
```
vruntime += runtime
```

With weighting, lower-priority processes accumulate vruntime **faster**:

```c
// Actual CFS formula
vruntime_i = vruntime_i + (weight_0 / weight_i) × runtime_i

where weight_0 = 1024 (nice 0 weight)
```

**Example:**

```
Process A (nice -5, weight 3121) runs 10ms:
───────────────────────────────────────────
vruntime_A += (1024 / 3121) × 10ms
vruntime_A += 0.328 × 10ms
vruntime_A += 3.28ms  (accumulates slowly!)


Process B (nice 0, weight 1024) runs 10ms:
──────────────────────────────────────────
vruntime_B += (1024 / 1024) × 10ms
vruntime_B += 1.0 × 10ms
vruntime_B += 10ms  (normal accumulation)


Process C (nice +5, weight 335) runs 10ms:
──────────────────────────────────────────
vruntime_C += (1024 / 335) × 10ms
vruntime_C += 3.06 × 10ms
vruntime_C += 30.6ms  (accumulates quickly!)
```

**Why this works:**

```
Scenario: A (weight 3121) and B (weight 1024) compete
──────────────────────────────────────────────────────

Initial state:
A: vruntime = 0
B: vruntime = 0

Round 1: Pick A (lowest vruntime, tied)
A runs 10ms → vruntime_A = 3.28ms

Round 2: Pick B (vruntime 0 < 3.28)
B runs 10ms → vruntime_B = 10ms

Round 3: Pick A (vruntime 3.28 < 10)
A runs 10ms → vruntime_A = 6.56ms

Round 4: Pick A (vruntime 6.56 < 10)
A runs 10ms → vruntime_A = 9.84ms

Round 5: Pick A (vruntime 9.84 < 10)
A runs 10ms → vruntime_A = 13.12ms

Round 6: Pick B (vruntime 10 < 13.12)
B runs 10ms → vruntime_B = 20ms

Pattern: A runs 3× as often as B!
A A B A A A B A A A B ...
└───┬───┘ └───┬───┘
   3:1       3:1
```

> **💡 Insight**
>
> CFS's **weighting system** is beautifully elegant:
> 1. Higher priority → Lower weight → vruntime accumulates slower → Stays low longer → Gets picked more often
> 2. The math naturally produces the desired CPU ratios without explicit percentages
> 3. Adding/removing processes automatically adjusts everyone's share
>
> This is an example of **designing the right metric**—vruntime naturally encodes fairness when weighted correctly. Compare to manual tracking: "A has used 30%, B has used 20%, C is owed 10% more..."—much more complex!

### 7.4. 🌳 Red-Black Trees

**The scalability problem:**

```
Naive approach: Store processes in a list
─────────────────────────────────────────

head → [vruntime: 100] → [vruntime: 200] → ... → [vruntime: 9999]

Finding minimum: O(1) if sorted, but...
Inserting process: O(n) to maintain sort
Removing process: O(n) to search

With 1000s of processes, this is too slow! 🐌
```

**CFS solution: Red-Black Tree**

A red-black tree is a **self-balancing binary search tree** with O(log n) operations.

```
Properties:
───────────
• Each node is red or black
• Root is black
• All leaves (NIL) are black
• Red nodes have black children (no consecutive reds)
• All paths from node to leaves have same number of black nodes


Example CFS red-black tree (vruntime values):
──────────────────────────────────────────────

               [14] B
              /     \
         [9] R       [18] R
        /    \       /     \
    [1] B  [10] B [17] B  [22] B
     /  \               /
  [5] R [NIL]       [21] R
                    /
                [24] R


Legend:
B = Black node
R = Red node
Numbers = vruntime values
```

**Key operations:**

```
Operation         List      Red-Black Tree
─────────         ────      ──────────────
Find minimum      O(n)      O(log n)  ← Just leftmost node!
Insert            O(n)      O(log n)
Delete            O(n)      O(log n)
Search            O(n)      O(log n)
```

**CFS scheduling with red-black tree:**

```c
// Simplified CFS scheduler

struct rb_node *pick_next_task() {
    // Leftmost node = minimum vruntime
    struct rb_node *leftmost = rb_first(&cfs_rq);
    return leftmost;  // O(log n) to find!
}

void enqueue_task(struct task *p) {
    // Insert task into red-black tree by vruntime
    rb_insert(&cfs_rq, p, p->vruntime);  // O(log n)
}

void dequeue_task(struct task *p) {
    // Remove task from red-black tree
    rb_erase(&cfs_rq, p);  // O(log n)
}
```

**Performance comparison:**

```
System Load: 1000 active processes
──────────────────────────────────

List-based scheduler:
  Find next task:     1000 comparisons
  Insert finished:    500 comparisons (avg)
  Per scheduling:     ~1500 operations

Red-black tree scheduler (CFS):
  Find next task:     1 operation (cached leftmost!)
  Insert finished:    ~10 operations (log₂ 1000 ≈ 10)
  Per scheduling:     ~11 operations

Speedup: 1500 / 11 ≈ 136× faster! 🚀
```

**Optimizations in production CFS:**

```
CFS actually caches the leftmost node!
──────────────────────────────────────

struct cfs_rq {
    struct rb_root tasks_timeline;
    struct rb_node *rb_leftmost;  ← Cache!
    ...
};

Why?
─────
• Finding minimum is the MOST frequent operation
• Instead of O(log n), cached leftmost is O(1)
• Update cache when leftmost changes (rare)

Result: Finding next task is effectively FREE! ⚡
```

> **💡 Insight**
>
> **Data structure choice is critical for performance.** CFS demonstrates this beautifully:
>
> Early schedulers: Simple lists, worked fine for 10-100 processes
> Modern data centers: 1000-10000 processes, lists are too slow
> Solution: Red-black tree with caching
>
> This pattern appears everywhere:
> - **Web servers**: Array of connections → hash table of connections
> - **Databases**: Sequential scan → B-tree index → bitmap index
> - **Network routing**: Linear search → trie → compressed trie
>
> As scale increases, algorithm complexity matters more than constant factors. O(n) vs. O(log n) is the difference between "barely works" and "handles millions."

### 7.5. 😴 Handling I/O and Sleeping Processes

**The starvation problem:**

```
Scenario: Process goes to sleep for 10 seconds
──────────────────────────────────────────────

Process A (CPU-bound):    vruntime continuously increasing
  Time 0s:  vruntime = 0
  Time 5s:  vruntime = 5000ms
  Time 10s: vruntime = 10000ms
  Always running!

Process B (I/O-bound):    Goes to sleep, vruntime frozen
  Time 0s:  vruntime = 0
  Time 0s:  [Starts I/O, sleeps]
  Time 10s: [I/O completes, wakes up]
            vruntime = 0  (unchanged!)


❌ Problem: When B wakes up...
───────────────────────────────
B has vruntime = 0
A has vruntime = 10000ms

CFS always picks lowest vruntime → B runs
B "catches up" for 10 seconds straight!
A is starved! 😱
```

**Visual timeline of the problem:**

```
Time (seconds)
0              5              10             20
├──────────────┼──────────────┼──────────────┤
A: ████████████████████████████
B:                            ████████████████
                              ↑
                         B wakes up,
                      monopolizes CPU
                      for 10 seconds
```

**CFS solution: Reset vruntime on wakeup**

```c
void enqueue_task_fair(struct task *p) {
    if (p->state == TASK_WAKING) {
        // Process is waking up from sleep
        u64 min_vruntime = cfs_rq->min_vruntime;

        // Set waking process to minimum of tree
        p->vruntime = max(p->vruntime, min_vruntime);
    }

    rb_insert(&cfs_rq, p);
}
```

**Corrected behavior:**

```
Process B wakes up at time 10s:
───────────────────────────────
min_vruntime in tree = 10000ms (from A)

B's vruntime adjusted:
  Old vruntime: 0ms
  New vruntime: max(0, 10000) = 10000ms

Now both have equal vruntime:
  A: vruntime = 10000ms
  B: vruntime = 10000ms

They compete fairly! ✓
```

**Timeline with fix:**

```
Time (seconds)
0              5              10             15
├──────────────┼──────────────┼──────────────┤
A: ████████████████████████████████████████████
B:                            ██████████████████
                              ↑
                         B wakes up,
                      competes fairly
                      with A (50/50)
```

**Trade-offs of this approach:**

```
✅ Advantages:
──────────────
• Prevents starvation of CPU-bound processes
• Maintains overall system fairness
• Simple to implement

❌ Disadvantages:
─────────────────
• I/O-bound processes don't accumulate "credit"
• Short sleeps are penalized
• Can reduce responsiveness for interactive apps


Example problem:
────────────────
Interactive text editor:
  Runs for 1ms (process input)
  Sleeps for 99ms (waiting for next keystroke)
  Repeat...

With vruntime reset:
  Never accumulates "credit" for sleeping
  Competes equally with CPU hogs
  May feel sluggish! ⚠️
```

**Academic paper findings:**

According to Ousterhout's research [AC97], CFS's approach of resetting vruntime means:

```
Interactive processes that sleep frequently:
────────────────────────────────────────────
• Do NOT get compensated for yielding CPU
• Get same share as processes that never sleep
• May experience poor response time

Traditional schedulers with I/O boost:
──────────────────────────────────────
• Give higher priority to I/O-bound processes
• Better for interactive workloads
• More complex to implement correctly
```

> **💡 Insight**
>
> The **sleeping process problem** reveals a fundamental tension in scheduler design:
>
> 1. **Fairness**: All processes should get equal CPU share
> 2. **Responsiveness**: Interactive processes should respond quickly
>
> These goals conflict! Solutions:
> - **CFS approach**: Prioritize fairness, sacrifice some responsiveness
> - **Traditional approach**: Boost I/O-bound processes, sacrifice some fairness
> - **Android**: Separate "foreground" and "background" groups with different shares
> - **Windows**: Interactive boost heuristics
>
> There's no perfect answer—just different trade-offs for different use cases. This is why modern OSes often have **multiple schedulers** (real-time, deadline, CFS) that applications can choose from.

---

## 8. ⚠️ Challenges and Limitations

### 🎟️ The Ticket Assignment Problem

**The fundamental open question:**

```
Given a set of processes, how many tickets should each receive?
```

**In plain English:** Lottery and stride scheduling are elegant mechanisms, but they dodge the hardest question: "Who deserves what share?" Should your browser get 40 tickets or 400? Should background tasks get 10 or 100?

**Approaches attempted:**

```
1. User-specified allocation
   ───────────────────────────
   Pro: Users know their priorities
   Con: Users don't understand ticket math
        How do I know if 100 tickets is "enough"?

2. System administrator allocation
   ────────────────────────────────
   Pro: Expert can make informed decisions
   Con: Doesn't scale to millions of processes
        Admin can't micromanage every app

3. Default equal allocation
   ─────────────────────────
   Pro: Simple, democratic
   Con: All processes treated equally
        Defeats the purpose of proportional share!

4. Dynamic adjustment (machine learning?)
   ───────────────────────────────────────
   Pro: Could learn from behavior
   Con: Complex, unpredictable, still research area
```

**Example of the difficulty:**

```
User's laptop processes:
────────────────────────
• Video call (Zoom)           → ??? tickets
• Browser (20 tabs)           → ??? tickets
• Text editor                 → ??? tickets
• Background system updates   → ??? tickets
• Music player                → ??? tickets
• File sync (Dropbox)         → ??? tickets

What's the "right" allocation? 🤷
• Video call needs CPU for real-time encoding
• Browser needs responsiveness when user clicks
• Background tasks shouldn't interfere
• But how to quantify this in tickets?
```

> **💡 Insight**
>
> The **ticket assignment problem** is an instance of a broader challenge: **translating human priorities into system parameters**. Similar problems:
> - **Database tuning**: How big should the buffer pool be?
> - **Network QoS**: What bandwidth guarantee for each service class?
> - **Memory limits**: How much RAM should each container get?
>
> Often, the answer is **adaptive systems** that adjust based on observed behavior—but this adds complexity. The tension between simplicity and optimality is eternal!

### 📉 I/O Integration Issues

**The mismatch:**

```
Proportional share schedulers assume:
────────────────────────────────────
• Processes constantly want CPU
• Fair share = equal time percentages


Reality:
────────
• Many processes are I/O-bound
• They voluntarily yield CPU (waiting for disk/network)
• Should they get "credit" for being nice?


Example:
────────
CPU-bound process (A):    Never yields, uses 100% of its time slices
I/O-bound process (B):    Uses 10% of its time slices (rest is I/O wait)

Both have 100 tickets (should get 50% each)

Actual CPU usage:
  A: 90% (it never sleeps)
  B: 10% (it sleeps a lot)

Is this fair? 🤔
```

**Two perspectives:**

```
Perspective 1: This IS fair
───────────────────────────
• B got its fair share of OPPORTUNITIES to run
• B chose to do I/O instead
• The unused time goes to A (productive use)


Perspective 2: This is NOT fair
────────────────────────────────
• B should get compensated when its I/O completes
• Interactive processes are more valuable than batch
• User typing expects instant response, not fair share
```

**Why this is hard:**

```
Attempted solution: Give I/O-bound processes priority boost
────────────────────────────────────────────────────────────

Problems:
⚠️ How much boost? (opens same parameterization problem)
⚠️ Can be gamed: Process does fake I/O to get priority
⚠️ Breaks the fairness guarantee
⚠️ Adds complexity

Result: Most proportional-share schedulers (including CFS)
        don't solve this well. Trade-off accepted.
```

### 🚫 Not a Panacea

**When NOT to use proportional-share scheduling:**

```
❌ Real-time systems
   ─────────────────
   Need: Hard deadlines ("finish in 50ms")
   Proportional share: No timing guarantees
   Use instead: EDF (Earliest Deadline First)

❌ Batch processing
   ────────────────
   Need: Minimize turnaround time
   Proportional share: Slows down all jobs equally
   Use instead: SJF (Shortest Job First)

❌ Energy-constrained devices
   ─────────────────────────
   Need: Maximize sleep time, minimize wakeups
   Proportional share: Frequent scheduling decisions
   Use instead: Batched scheduling

❌ Untrusted environments (no ticket inflation)
   ──────────────────────────────────────────
   Need: Prevent gaming/cheating
   Proportional share: Trusts processes not to inflate
   Use instead: Enforced quotas
```

**Where proportional-share DOES excel:**

```
✅ Virtual machine managers (VMware, KVM)
✅ Cloud resource allocation (AWS, GCP)
✅ Multi-tenant servers
✅ Quality-of-service guarantees
✅ Fair bandwidth/memory sharing
```

> **💡 Insight**
>
> **No scheduler is universal.** Each optimizes for different goals:
>
> | Scheduler Type        | Optimizes For         | Use Case            |
> |-----------------------|------------------------|---------------------|
> | FIFO                  | Simplicity             | Batch queues        |
> | SJF                   | Turnaround time        | Known-length jobs   |
> | Round-robin           | Response time          | Time-sharing        |
> | MLFQ                  | Balance                | General-purpose     |
> | Proportional-share    | Fairness               | Resource allocation |
> | EDF                   | Deadlines              | Real-time systems   |
>
> Modern OSes often support **multiple schedulers** simultaneously:
> - Linux: CFS (general), RT (real-time), Deadline
> - Windows: Priority-based with multiple queues
> - Real-time OSes: Deadline schedulers
>
> Choosing the right scheduler is part of system design, not a one-size-fits-all decision.

---

## 9. 📝 Summary

**Key Takeaways:** 🎯

**1. Proportional-Share Philosophy** 🎫
```
Shift in goals:
  Old schedulers: Minimize turnaround/response time
  Proportional:   Guarantee fair CPU percentage

Core abstraction: Tickets represent share ownership
```

**2. Three Approaches** 🎲

```
Lottery Scheduling
──────────────────
🎲 Random ticket drawing
✅ Simple, lightweight
✅ No global state
✅ Robust against corner cases
❌ Probabilistic fairness (not guaranteed)

Stride Scheduling
─────────────────
🎯 Deterministic pass/stride tracking
✅ Perfect fairness every cycle
✅ Predictable behavior
❌ Global state complicates dynamic addition
❌ More complex implementation

CFS (Linux Production)
──────────────────────
⏱️ Virtual runtime with red-black trees
✅ O(log n) efficiency at scale
✅ Dynamic time slices
✅ Nice value integration
✅ Production-proven (billions of devices)
❌ Doesn't compensate I/O-bound processes well
```

**3. Implementation Insights** 💻

```
Key techniques:
───────────────
• Ticket currency: User-level allocation abstraction
• Ticket transfer: Priority inheritance for client-server
• Ticket inflation: Self-adjustment in cooperative environments
• Red-black trees: O(log n) operations for scalability
• Weighted vruntime: Elegant priority integration
```

**4. Fundamental Trade-offs** ⚖️

```
Simplicity ←──────────→ Precision
   Lottery              Stride

Fairness ←──────────────→ Responsiveness
   CFS vruntime reset    Traditional I/O boost

Static ←────────────────→ Dynamic
   Stride (hard to add)  Lottery (easy to add)
```

**5. Challenges Remaining** ⚠️

```
❓ Ticket assignment: Who gets how many?
❓ I/O integration: Should sleeping processes get credit?
❓ Gaming prevention: How to prevent ticket manipulation?

These are POLICY questions, not mechanism questions.
The mechanisms work; the policies are domain-specific.
```

**What's Next:** 🚀

Upcoming chapters will explore:
- 🔄 **Multiprocessor scheduling** - Fair sharing across many CPUs
- ⏰ **Real-time scheduling** - Deadline guarantees instead of fairness
- 💾 **Memory scheduling** - Applying proportional share to RAM
- 🌐 **Network scheduling** - Fair bandwidth allocation

**Conceptual Connections:** 🧠

```
Proportional-share scheduling connects to:
───────────────────────────────────────────

Economics:         Resource allocation under scarcity
Game Theory:       Fair division problems
Probability:       Law of large numbers (lottery convergence)
Data Structures:   Self-balancing trees (red-black)
Algorithms:        Randomized algorithms vs. deterministic
Distributed Sys:   Quota management, rate limiting
Networking:        Quality-of-Service (QoS), traffic shaping
```

> **💡 Final Insight**
>
> Proportional-share scheduling teaches us that **fairness is measurable and enforceable**, but defining "fair" is subjective. Different contexts demand different fairness models:
>
> - **Egalitarian**: Equal CPU for all (naive lottery)
> - **Weighted**: CPU proportional to priority (CFS nice values)
> - **Utility-based**: CPU proportional to value delivered (economic schedulers)
> - **Deadline-driven**: CPU to whoever is most urgent (real-time)
>
> The **mechanism** (tickets, vruntime, etc.) is the easy part. The **policy** (who deserves what) remains a sociotechnical challenge that blends computer science, economics, and human values. This is why OS design is as much art as science.

---

**Previous:** [Chapter 5: MLFQ Scheduling](chapter5-mlfq.md) | **Next:** [Chapter 7: Multiprocessor Scheduling](chapter7-multiprocessor.md)
