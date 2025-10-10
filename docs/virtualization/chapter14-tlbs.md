# Chapter 14: TLBs - Faster Address Translation ⚡

_Making paging practical through hardware caching of address translations_

---

## 📋 Table of Contents

1. [🎯 Introduction](#1-introduction)
   - 1.1. [The Performance Problem](#11-the-performance-problem)
   - 1.2. [The Solution: Translation Caching](#12-the-solution-translation-caching)
2. [🔧 TLB Basic Algorithm](#2-tlb-basic-algorithm)
   - 2.1. [The Hardware Control Flow](#21-the-hardware-control-flow)
   - 2.2. [TLB Hit: The Fast Path](#22-tlb-hit-the-fast-path)
   - 2.3. [TLB Miss: The Slow Path](#23-tlb-miss-the-slow-path)
3. [📊 Example: Accessing An Array](#3-example-accessing-an-array)
   - 3.1. [Array Layout in Virtual Memory](#31-array-layout-in-virtual-memory)
   - 3.2. [Step-by-Step Trace](#32-step-by-step-trace)
   - 3.3. [The Role of Locality](#33-the-role-of-locality)
4. [🖥️ Who Handles The TLB Miss?](#4-who-handles-the-tlb-miss)
   - 4.1. [Hardware-Managed TLBs](#41-hardware-managed-tlbs)
   - 4.2. [Software-Managed TLBs](#42-software-managed-tlbs)
   - 4.3. [Trade-offs](#43-trade-offs)
5. [🗂️ TLB Contents and Structure](#5-tlb-contents-and-structure)
   - 5.1. [TLB Entry Format](#51-tlb-entry-format)
   - 5.2. [Fully Associative Design](#52-fully-associative-design)
   - 5.3. [Protection and Valid Bits](#53-protection-and-valid-bits)
6. [🔄 Context Switches and the TLB](#6-context-switches-and-the-tlb)
   - 6.1. [The Problem](#61-the-problem)
   - 6.2. [Solution 1: Flush on Switch](#62-solution-1-flush-on-switch)
   - 6.3. [Solution 2: Address Space Identifiers](#63-solution-2-address-space-identifiers)
   - 6.4. [Sharing Pages Across Processes](#64-sharing-pages-across-processes)
7. [♻️ Replacement Policy](#7-replacement-policy)
   - 7.1. [LRU (Least Recently Used)](#71-lru-least-recently-used)
   - 7.2. [Random Replacement](#72-random-replacement)
   - 7.3. [When Reasonable Policies Fail](#73-when-reasonable-policies-fail)
8. [💎 A Real TLB: MIPS R4000](#8-a-real-tlb-mips-r4000)
   - 8.1. [Entry Format](#81-entry-format)
   - 8.2. [Special Features](#82-special-features)
   - 8.3. [TLB Management Instructions](#83-tlb-management-instructions)
9. [📝 Summary](#9-summary)

---

## 1. 🎯 Introduction

### 1.1. ⚡ The Performance Problem

**In plain English:** Imagine you're working in an office 🏢 where every time you need to make a phone call, you have to walk to a file cabinet in the basement, look up the person's phone number, walk back to your desk, and then dial. You'd spend more time looking up numbers than actually talking! This is exactly what happens with paging without a TLB.

**In technical terms:** Paging chops the address space into small, fixed-sized pages, which means the OS needs a **lot** of mapping information (one entry per page). If this mapping information lives in physical memory, every virtual memory access requires:
1. A memory access to read the page table entry
2. Another memory access to get the actual data

**Double the memory accesses = Half the speed!** 😱

**THE CRUX:** How can we speed up address translation and avoid the extra memory reference that paging seems to require? What hardware support is needed? What OS involvement?

> **💡 Insight**
>
> This is a classic **performance problem**: a correct but slow solution. The page table in memory works perfectly—it's just too slow for practical use. This pattern appears everywhere in computing:
> - **Disk is slow** → Add RAM cache
> - **RAM is slow** → Add CPU cache
> - **Page table is slow** → Add TLB cache
>
> The universal pattern: **Add a faster, smaller cache near where it's needed**.

### 1.2. 💾 The Solution: Translation Caching

**The answer:** Add a **translation-lookaside buffer (TLB)**—a hardware cache of popular virtual-to-physical address translations.

**Better name:** Address-translation cache! The name "TLB" is historical and confusing, but we're stuck with it.

**Where it lives:**
```
CPU Core                          Main Memory (RAM)
┌─────────────────────┐          ┌──────────────────┐
│  Registers          │          │  Page Table      │
│  ───────────────    │          │  (all trans-     │
│  TLB (cache)        │ Fast! ⚡ │   lations)       │  Slow 🐌
│  ───────────────    │          │                  │
│  ALU, Control       │          │  Data            │
└─────────────────────┘          └──────────────────┘
        ↑                               ↑
        └─ On-chip, 1-2 cycles         └─ Off-chip, 100+ cycles
```

**How it works:**

```
Virtual Address Generated
         ↓
    Check TLB first
         ↓
    ┌─────────────┐
    │ In TLB?     │
    └──┬──────┬───┘
      YES    NO
       ↓      ↓
    TLB HIT  TLB MISS
    Fast! ⚡  Slow 🐌
    (1-2     (100+
    cycles)   cycles)
       ↓       ↓
    Use it!  Access page table,
             Update TLB,
             Retry
```

**Performance impact:**

```
Without TLB:
────────────
Memory access: 100 cycles
Page table access: 100 cycles
Total: 200 cycles per memory access 😱

With TLB (95% hit rate):
────────────────────────
TLB hit:  1 cycle (95% of time)
TLB miss: 201 cycles (5% of time)
Average: 0.95×1 + 0.05×201 = 11 cycles ⚡

18× faster! 🎉
```

> **💡 Insight**
>
> TLBs demonstrate **caching as a performance multiplier**. Without TLBs, paging would be impractically slow—every memory access would double in cost. With TLBs achieving 99%+ hit rates, the overhead becomes negligible. This is why TLBs are considered **essential for virtual memory**—they don't just improve performance, they make it viable.

---

## 2. 🔧 TLB Basic Algorithm

### 2.1. 🖥️ The Hardware Control Flow

Let's walk through what the hardware does on every memory access when using a TLB.

**Assumptions:**
- Hardware-managed TLB (hardware walks the page table on miss)
- Simple linear page table (array of page table entries)

**The Algorithm:**

```c
// Step 1: Extract VPN from virtual address
VPN = (VirtualAddress & VPN_MASK) >> SHIFT

// Step 2: Check TLB
(Success, TlbEntry) = TLB_Lookup(VPN)

if (Success == True) {
    // ═══════════════════════════════════════
    // TLB HIT - Fast path! ⚡
    // ═══════════════════════════════════════

    if (CanAccess(TlbEntry.ProtectBits) == True) {
        // Extract offset and form physical address
        Offset = VirtualAddress & OFFSET_MASK
        PhysAddr = (TlbEntry.PFN << SHIFT) | Offset
        Register = AccessMemory(PhysAddr)
    } else {
        RaiseException(PROTECTION_FAULT)
    }

} else {
    // ═══════════════════════════════════════
    // TLB MISS - Slow path 🐌
    // ═══════════════════════════════════════

    // Hardware walks page table
    PTEAddr = PTBR + (VPN * sizeof(PTE))
    PTE = AccessMemory(PTEAddr)  // Extra memory access!

    if (PTE.Valid == False) {
        RaiseException(SEGMENTATION_FAULT)
    } else if (CanAccess(PTE.ProtectBits) == False) {
        RaiseException(PROTECTION_FAULT)
    } else {
        // Update TLB with new translation
        TLB_Insert(VPN, PTE.PFN, PTE.ProtectBits)
        RetryInstruction()  // Run instruction again
    }
}
```

**Visual Flow:**

```
┌──────────────────────────┐
│  Virtual Address         │
│  VPN=5, Offset=12        │
└────────┬─────────────────┘
         ↓
    Extract VPN=5
         ↓
┌────────────────────────────┐
│  Look up VPN in TLB        │
└────┬───────────────┬───────┘
    HIT             MISS
     ↓               ↓
┌─────────┐    ┌──────────────────┐
│ Get PFN │    │ PTBR + VPN×size  │
│ from    │    │ ↓                │
│ TLB     │    │ Access memory    │
│ (fast!) │    │ Get PTE          │
└────┬────┘    │ ↓                │
     │         │ Insert in TLB    │
     │         │ ↓                │
     │         │ Retry            │
     │         └────┬─────────────┘
     │              ↓
     └──────────────┴──────────────┐
                                   ↓
                    ┌──────────────────────────┐
                    │  Form Physical Address:  │
                    │  PhysAddr = PFN:Offset   │
                    │  = 42:12                 │
                    └─────────┬────────────────┘
                              ↓
                    ┌──────────────────────┐
                    │  Access Memory       │
                    │  at PhysAddr         │
                    └──────────────────────┘
```

### 2.2. ⚡ TLB Hit: The Fast Path

**What happens:**
1. VPN is extracted from virtual address
2. TLB is checked in **parallel** (all entries at once)
3. Match found! PFN retrieved
4. Physical address formed: `PFN << SHIFT | Offset`
5. Memory accessed

**Time:** 1-2 CPU cycles (TLB is on-chip and very fast)

**Why it's fast:**
```
TLB: Small (32-128 entries), On-chip, Fully associative
      ↓
  Parallel search (all entries checked simultaneously)
      ↓
  1-2 cycle access time ⚡
```

### 2.3. 🐌 TLB Miss: The Slow Path

**What happens:**
1. VPN not found in TLB
2. Hardware computes page table entry address
3. **Extra memory access** to read PTE from page table
4. Validate PTE (valid bit, protection bits)
5. Insert translation into TLB
6. **Retry the instruction** (now it will hit in TLB)

**Time:** 100+ CPU cycles (includes memory access)

**Why it's slow:**
```
TLB Miss → Access main memory → 100+ cycles
           (Page table is in RAM)
```

**The retry mechanism:**

**In plain English:** Think of it like a waiter taking your order 📝. You say "I'll have the special." The waiter doesn't know what the special is (TLB miss), so they walk to the kitchen and ask (check page table). They write it down on their notepad (update TLB). Then they come back and ask "What would you like?" again. This time they know! (TLB hit) Same instruction, different outcome.

**Why retry?** The instruction execution is restarted from the beginning, so the TLB lookup happens again—but this time it hits!

> **💡 Insight**
>
> The **retry instruction** mechanism is brilliant engineering. Instead of having two separate code paths (hit vs. miss), the hardware handles misses by updating the TLB and then *running the same instruction again*. This simplifies the hardware design—there's only one path through the instruction execution pipeline, and TLB misses just delay the instruction.
>
> You'll see this "retry on failure" pattern in:
> - **CPU pipeline stalls**: Retry on cache miss
> - **Transaction systems**: Retry on conflict
> - **Network protocols**: Retry on packet loss

---

## 3. 📊 Example: Accessing An Array

Let's trace through a real example to see how TLBs improve performance through **locality**.

### 3.1. 📐 Array Layout in Virtual Memory

**Setup:**
- Array of 10 integers (4 bytes each): `int a[10]`
- Array starts at virtual address 100
- 8-bit virtual address space (tiny! just for demonstration)
- 16-byte pages
- Address breakdown: 4-bit VPN + 4-bit offset

**Virtual address space:**

```
Virtual Pages (16 bytes each)
───────────────────────────────

VPN=06  [04 - 15]  ← a[0], a[1], a[2]
VPN=07  [00 - 15]  ← a[3], a[4], a[5], a[6]
VPN=08  [00 - 11]  ← a[7], a[8], a[9]

Detailed layout:
────────────────

Page 06 (bytes 96-111):
┌────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┐
│ 96 │ 97 │ 98 │ 99 │100 │101 │102 │103 │104 │105 │106 │107 │108 │109 │110 │111 │
└────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┘
  Offset: 00   01   02   03   04   05   06   07   08   09   10   11   12   13   14   15
                              └─────a[0]────┘└─────a[1]────┘└─────a[2]────┘

Page 07 (bytes 112-127):
┌────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┐
│112 │113 │114 │115 │116 │117 │118 │119 │120 │121 │122 │123 │124 │125 │126 │127 │
└────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┘
└─────a[3]────┘└─────a[4]────┘└─────a[5]────┘└─────a[6]────┘

Page 08 (bytes 128-143):
┌────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┐
│128 │129 │130 │131 │132 │133 │134 │135 │136 │137 │138 │139 │140 │141 │142 │143 │
└────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┘
└─────a[7]────┘└─────a[8]────┘└─────a[9]────┘
```

### 3.2. 🔍 Step-by-Step Trace

**The code:**

```c
int sum = 0;
for (int i = 0; i < 10; i++) {
    sum += a[i];
}
```

**Access pattern:**

```
Access  Virtual Addr  VPN  Offset  TLB Result  Reason
──────  ────────────  ───  ──────  ──────────  ──────
a[0]         100       06     04     MISS       First access to page 06
a[1]         104       06     08     HIT ⚡     Same page as a[0]!
a[2]         108       06     12     HIT ⚡     Same page as a[0]!
a[3]         112       07     00     MISS       First access to page 07
a[4]         116       07     04     HIT ⚡     Same page as a[3]!
a[5]         120       07     08     HIT ⚡     Same page as a[3]!
a[6]         124       07     12     HIT ⚡     Same page as a[3]!
a[7]         128       08     00     MISS       First access to page 08
a[8]         132       08     04     HIT ⚡     Same page as a[7]!
a[9]         136       08     08     HIT ⚡     Same page as a[7]!

TLB Performance:
────────────────
Misses: 3
Hits:   7
Hit rate: 70% 🎯
```

**Visual representation:**

```
TLB State Over Time:
────────────────────

After a[0]: TLB = [VPN=06 → PFN=?]
After a[1]: TLB = [VPN=06 → PFN=?]  (hit!)
After a[2]: TLB = [VPN=06 → PFN=?]  (hit!)
After a[3]: TLB = [VPN=06 → PFN=?, VPN=07 → PFN=?]
After a[4]: TLB = [VPN=06 → PFN=?, VPN=07 → PFN=?]  (hit!)
After a[5]: TLB = [VPN=06 → PFN=?, VPN=07 → PFN=?]  (hit!)
After a[6]: TLB = [VPN=06 → PFN=?, VPN=07 → PFN=?]  (hit!)
After a[7]: TLB = [VPN=06 → PFN=?, VPN=07 → PFN=?, VPN=08 → PFN=?]
After a[8]: TLB = [VPN=06 → PFN=?, VPN=07 → PFN=?, VPN=08 → PFN=?]  (hit!)
After a[9]: TLB = [VPN=06 → PFN=?, VPN=07 → PFN=?, VPN=08 → PFN=?]  (hit!)
```

### 3.3. 🌊 The Role of Locality

**Spatial locality:** Array elements are packed together in memory. Once we access one element on a page, subsequent elements on that page are "free" (TLB hit).

**Effect of page size:**

```
16-byte pages (our example):
────────────────────────────
Elements per page: 4 (16 bytes ÷ 4 bytes/int)
Misses: 3 (one per page)
Hit rate: 70%

32-byte pages (2× larger):
──────────────────────────
Elements per page: 8
Misses: 2 (pages would be: [a[0]-a[7]], [a[8]-a[9]])
Hit rate: 80%

4KB pages (typical real system):
────────────────────────────────
Elements per page: 1024 (4096 bytes ÷ 4 bytes/int)
Misses: 1 (entire array fits on one page!)
Hit rate: 90%
```

**Temporal locality:** What if we loop through the array again immediately?

```c
for (int i = 0; i < 10; i++) {
    sum += a[i];
}
// Loop again!
for (int i = 0; i < 10; i++) {
    sum += a[i];
}
```

**Second loop access pattern:**

```
Access  TLB Result
──────  ──────────
a[0]     HIT ⚡    (VPN=06 still in TLB from first loop!)
a[1]     HIT ⚡
a[2]     HIT ⚡
a[3]     HIT ⚡    (VPN=07 still in TLB!)
a[4]     HIT ⚡
a[5]     HIT ⚡
a[6]     HIT ⚡
a[7]     HIT ⚡    (VPN=08 still in TLB!)
a[8]     HIT ⚡
a[9]     HIT ⚡

Hit rate: 100%! 🎉
```

> **💡 Insight**
>
> TLBs exploit **two types of locality**:
>
> **Spatial locality** (nearby accesses):
> - Array elements packed together
> - First access to page misses, subsequent accesses hit
> - Larger pages = better spatial locality exploitation
>
> **Temporal locality** (repeated accesses):
> - Recently accessed pages stay in TLB
> - Loops over same data hit repeatedly
> - Longer TLB retention = better temporal locality
>
> This is why **dense data structures** (arrays, packed structs) perform better than **sparse data structures** (linked lists, scattered objects). The TLB loves locality!

---

## 4. 🖥️ Who Handles The TLB Miss?

When a TLB miss occurs, someone needs to walk the page table and update the TLB. But who? The hardware or the software (OS)?

**THE CRUX:** Who is responsible for handling TLB misses? What are the trade-offs?

### 4.1. 🔧 Hardware-Managed TLBs

**Approach:** The hardware handles everything.

**How it works:**

```
TLB Miss Detected
      ↓
Hardware knows:
  - Page table location (PTBR register)
  - Page table format (fixed, known to hardware)
      ↓
Hardware walks page table:
  1. Compute PTE address: PTBR + VPN × sizeof(PTE)
  2. Access memory to read PTE
  3. Check valid bit, protection bits
  4. Extract PFN
  5. Insert into TLB
      ↓
Retry instruction
```

**Example architecture:** Intel x86

```c
// x86 uses CR3 register to point to page table
// Hardware knows the multi-level page table format

// On TLB miss, hardware automatically:
// 1. Uses CR3 to find page directory
// 2. Walks page directory → page table
// 3. Gets PTE
// 4. Updates TLB
// 5. Retries instruction

// OS just sets up page tables correctly!
```

**Pros:**
```
✅ Fast (no trap/context switch overhead)
✅ Simple for OS (just set up page tables)
✅ Predictable latency
```

**Cons:**
```
❌ Hardware complexity (must know page table format)
❌ Inflexible (can't change page table structure easily)
❌ Hardware and OS tightly coupled
```

### 4.2. 💻 Software-Managed TLBs

**Approach:** The hardware raises an exception; OS handles it.

**How it works:**

```
TLB Miss Detected
      ↓
Hardware raises exception
      ↓
┌────────────────────────────────┐
│  Save PC, switch to kernel     │
│  mode, jump to trap handler    │
└──────────┬─────────────────────┘
           ↓
┌────────────────────────────────┐
│  OS TLB Miss Handler:          │
│  1. Look up translation in     │
│     page table (any format!)   │
│  2. Use privileged instruction │
│     to update TLB              │
│  3. Return from trap           │
└──────────┬─────────────────────┘
           ↓
Hardware retries instruction
      ↓
TLB Hit! ⚡
```

**Example architecture:** MIPS, SPARC

```c
// Simplified TLB miss handler (software)
void handle_TLB_miss() {
    // Get faulting virtual address
    VAddr va = get_faulting_address();
    VPN = extract_VPN(va);

    // Look up in page table (OS can use ANY structure!)
    PTE pte = page_table_lookup(VPN);

    if (!pte.valid) {
        // Page not mapped
        handle_page_fault();
        return;
    }

    // Update TLB using privileged instruction
    tlb_insert(VPN, pte.PFN, pte.protection_bits);

    // Return from trap (retry instruction)
    return_from_trap();
}
```

**Control flow algorithm:**

```c
VPN = (VirtualAddress & VPN_MASK) >> SHIFT
(Success, TlbEntry) = TLB_Lookup(VPN)

if (Success == True) {
    // TLB Hit
    if (CanAccess(TlbEntry.ProtectBits) == True) {
        Offset = VirtualAddress & OFFSET_MASK
        PhysAddr = (TlbEntry.PFN << SHIFT) | Offset
        Register = AccessMemory(PhysAddr)
    } else {
        RaiseException(PROTECTION_FAULT)
    }
} else {
    // TLB Miss - Raise exception for OS to handle
    RaiseException(TLB_MISS)  ← Different from hardware-managed!
}
```

**Special considerations:**

**1. Return to the same instruction** ⚠️

```
Regular system call:          TLB miss:
────────────────────          ─────────
call foo()                    mov [eax], ebx  ← Causes TLB miss
  ↓ (syscall)                   ↓ (trap)
OS handles                    OS handles
  ↓                              ↓
return to NEXT instruction    return to SAME instruction
  ↓                              ↓
instruction after call        mov [eax], ebx  ← Retries
```

**Why?** The instruction didn't complete—it needs to try again now that the TLB has the translation!

**2. Avoid infinite TLB misses** 🔄

**The problem:**

```
TLB miss occurs
  → Jump to TLB miss handler code
  → Handler code causes TLB miss!
  → Infinite loop! 😱
```

**Solutions:**

```
Solution 1: Keep handler in physical memory
────────────────────────────────────────────
TLB miss handler code:
  ✅ Mapped in physical memory (no translation needed)
  ✅ Hardware jumps directly to physical address
  ❌ More complex hardware

Solution 2: Wire TLB entries
────────────────────────────
TLB has "wired" entries:
  ✅ Reserved for OS critical code/data
  ✅ Never evicted from TLB
  ✅ Guarantees handler always hits
  ✅ Simple and elegant

Solution 3: Separate instruction and data TLBs
───────────────────────────────────────────────
Split TLB:
  ✅ ITLB (instruction) keeps handler code
  ✅ DTLB (data) may miss
  ✅ Handler can run even if data TLB misses
```

**Pros:**
```
✅ Flexible (OS can use any page table structure!)
✅ Simple hardware (just raise exception)
✅ OS can optimize for workload
✅ Can use trees, hash tables, etc.
```

**Cons:**
```
❌ Slower (trap overhead: ~100 cycles)
❌ More complex OS
❌ Must avoid infinite TLB miss loops
```

### 4.3. ⚖️ Trade-offs

**Comparison:**

| Aspect              | Hardware-Managed      | Software-Managed        |
|---------------------|-----------------------|-------------------------|
| **Speed**           | Faster (no trap) ⚡   | Slower (trap) 🐌        |
| **Flexibility**     | Fixed page table      | Any structure 🎨        |
| **Hardware complexity** | High             | Low                     |
| **OS complexity**   | Low                   | High                    |
| **Examples**        | x86, ARM (some)       | MIPS, SPARC, RISC-V     |

**Historical trend:**

```
1970s-1980s: Hardware-managed
             (OS developers weren't trusted!)
             "Let hardware do it right"

1990s-2000s: Software-managed
             (RISC revolution)
             "Keep hardware simple, let OS optimize"

2010s-now:   Hybrid approaches
             (x86 adds software hints,
              ARM has both modes)
```

> **💡 Insight**
>
> The hardware vs. software debate mirrors the **RISC vs. CISC** philosophy:
>
> **Hardware-managed (CISC approach)**:
> - Put intelligence in hardware
> - Fast but inflexible
> - Good when one size fits all
>
> **Software-managed (RISC approach)**:
> - Keep hardware simple
> - Let software optimize
> - Good when workloads vary
>
> Modern systems increasingly use **hybrid approaches**—hardware handles the common case quickly, software handles unusual cases flexibly. This is the "fast path / slow path" pattern appearing again!

---

## 5. 🗂️ TLB Contents and Structure

### 5.1. 📋 TLB Entry Format

**Basic TLB entry:**

```
┌─────────────┬─────────────┬──────────────────┐
│     VPN     │     PFN     │   Other Bits     │
└─────────────┴─────────────┴──────────────────┘
```

**Why both VPN and PFN?**

**In plain English:** Unlike a direct-mapped cache where position implies the tag, a TLB can store *any* translation in *any* slot (fully associative). So each entry must say "I map VPN X to PFN Y."

**Example TLB:**

```
Slot 0:  VPN=10  →  PFN=42   valid=1  prot=r-x
Slot 1:  VPN=5   →  PFN=17   valid=1  prot=rw-
Slot 2:  VPN=20  →  PFN=99   valid=1  prot=rw-
Slot 3:  —       —   —        valid=0  —
```

When looking up VPN=5, hardware checks **all slots in parallel** and finds it in Slot 1.

### 5.2. 🔍 Fully Associative Design

**What "fully associative" means:**

```
Direct-Mapped Cache:          Fully Associative TLB:
───────────────────           ────────────────────────

VPN=5 → Slot (5 mod 4)       VPN=5 → Check ALL slots
      = Slot 1                       in parallel
                                     ↓
Fixed location                Find match anywhere
Simple, fast                  Flexible, more complex
```

**Search algorithm:**

```c
TLBEntry tlb_lookup(VPN vpn) {
    // Check all entries in PARALLEL
    for (int i = 0; i < TLB_SIZE; i++) {
        if (tlb[i].valid && tlb[i].vpn == vpn) {
            return tlb[i];  // Found it!
        }
    }
    return TLB_MISS;
}
```

**In hardware:** This happens in 1-2 cycles because all comparisons happen simultaneously using parallel comparators.

**Trade-offs:**

```
Fully Associative TLB          Direct-Mapped Cache
──────────────────────          ───────────────────
✅ High hit rate                ❌ More conflicts
✅ Flexible placement           ✅ Simpler hardware
❌ Complex hardware             ✅ Faster (no search)
❌ More power consumption       ✅ Lower power
❌ More area on chip            ✅ Smaller area

Verdict: For TLBs, high hit rate is CRITICAL,
so fully associative is worth the complexity!
```

### 5.3. 🛡️ Protection and Valid Bits

**TLB entry fields:**

```
┌─────┬─────┬───────┬──────────┬────────┬────────┬────────┐
│ VPN │ PFN │ Valid │ Protect  │  ASID  │ Dirty  │ Global │
└─────┴─────┴───────┴──────────┴────────┴────────┴────────┘
```

**Field descriptions:**

**1. Valid bit** ✅

```
Purpose: Is this TLB entry valid?

States:
  valid=0  →  Entry is empty/invalid
  valid=1  →  Entry contains a valid translation

When set to 0:
  - System boot (TLB starts empty)
  - Context switch (flush TLB)
  - Explicit TLB invalidation
```

**2. Protection bits** 🔒

```
Common encodings:
  r--  Read only
  rw-  Read/Write
  r-x  Read/Execute (code pages)
  rwx  Read/Write/Execute (unusual, security risk!)

Check on every access:
  if (access_type == WRITE && prot != rw-) {
      RaiseException(PROTECTION_FAULT);
  }
```

**3. ASID (Address Space Identifier)** 🆔

We'll cover this in the next section!

**4. Dirty bit** 🖊️

```
Purpose: Has this page been written to?

Used by OS for:
  - Copy-on-write optimization
  - Swap to disk (only write back dirty pages)
  - Memory-mapped files

Updated by hardware automatically on writes
```

**5. Global bit** 🌐

```
Purpose: Is this translation shared across all processes?

Use cases:
  - Kernel code/data (same for all processes)
  - Shared libraries
  - Memory-mapped devices

Effect:
  global=1  →  Ignore ASID (valid for all processes)
  global=0  →  Match ASID too
```

**Important distinction:** ⚠️

```
┌──────────────────────────────────────────────┐
│  TLB Valid Bit  ≠  Page Table Valid Bit      │
└──────────────────────────────────────────────┘

Page Table Valid Bit:
  valid=0  →  Page not allocated by process
               Accessing it = bug/error
               OS kills process 💀

TLB Valid Bit:
  valid=0  →  Translation not cached
               Accessing it = TLB miss
               Fill from page table 🔄

Different meanings!
```

**Example:**

```
Scenario: Process accesses VPN=10

Page Table:  VPN=10  valid=1  PFN=42
TLB:         Empty (all entries valid=0)

Result:
  1. TLB lookup fails (TLB valid=0)
  2. TLB miss handler runs
  3. Checks page table: valid=1 ✓
  4. Inserts into TLB
  5. Retry succeeds

If page table had valid=0:
  1. TLB lookup fails
  2. TLB miss handler runs
  3. Checks page table: valid=0 ✗
  4. Page fault exception!
  5. Process killed or page allocated
```

> **💡 Insight**
>
> The TLB entry structure demonstrates **metadata efficiency**. Each entry is typically only 8-16 bytes, but it packs in:
> - Translation (VPN → PFN)
> - Security (protection bits)
> - Process identity (ASID)
> - State tracking (valid, dirty)
> - Sharing information (global)
>
> This compact representation enables fast parallel search while maintaining all necessary functionality. Great hardware design is about **doing more with less**.

---

## 6. 🔄 Context Switches and the TLB

### 6.1. ⚠️ The Problem

**Scenario:** Two processes, each with VPN=10 mapped to different physical frames.

```
Process P1:
  Page table: VPN=10 → PFN=100

Process P2:
  Page table: VPN=10 → PFN=170
```

**What if both translations are in the TLB?**

```
TLB Contents:
─────────────
VPN   PFN   Valid  Prot
10    100   1      rwx   ← P1's translation
10    170   1      rwx   ← P2's translation
```

**The problem:** 😱

```
P2 is running...
  Access VPN=10
    ↓
  Hardware searches TLB for VPN=10
    ↓
  Finds FIRST match: PFN=100 (P1's mapping!)
    ↓
  Accesses wrong physical memory! 💥
```

**In plain English:** It's like a hotel 🏨 reusing room numbers. Room 101 in Building A isn't the same as Room 101 in Building B! But if the key just says "101," you might open the wrong door.

**THE CRUX:** How can we manage TLB contents correctly across context switches?

### 6.2. 🔄 Solution 1: Flush on Context Switch

**Approach:** Empty the TLB whenever we switch processes.

**How it works:**

```c
void context_switch(Process *old, Process *new) {
    // Save old process state
    save_registers(old);

    // Flush TLB (invalidate all entries)
    tlb_flush();  // Sets all valid bits to 0

    // Switch page table
    PTBR = new->page_table_base;

    // Load new process state
    restore_registers(new);

    // Resume new process
}
```

**Visual:**

```
Before context switch (P1 running):
────────────────────────────────────
TLB:
  VPN=5  → PFN=20   valid=1
  VPN=10 → PFN=100  valid=1
  VPN=15 → PFN=42   valid=1

Context switch to P2:
─────────────────────
1. tlb_flush() called
   ↓
TLB:
  VPN=5  → PFN=20   valid=0  ← Invalidated!
  VPN=10 → PFN=100  valid=0  ← Invalidated!
  VPN=15 → PFN=42   valid=0  ← Invalidated!

2. Switch PTBR to P2's page table

3. P2 starts running
   ↓
Every access misses initially! 🐌
  VPN=10 → TLB miss → Walk page table → Find PFN=170 → Update TLB
  VPN=5  → TLB miss → Walk page table → Find PFN=99  → Update TLB
  ...

TLB gradually refills:
  VPN=10 → PFN=170  valid=1  ← P2's translations
  VPN=5  → PFN=99   valid=1
```

**Performance cost:**

```
Frequent context switches:
──────────────────────────

P1 runs 10ms → TLB warms up → Good hit rate ✅
  ↓
Context switch to P2
  ↓
TLB flushed → All entries invalid
  ↓
P2 runs 10ms → TLB warms up → Good hit rate ✅
  ↓
Context switch back to P1
  ↓
TLB flushed → All entries invalid
  ↓
P1 runs 10ms → Must rebuild TLB again! 😞
  Every access initially misses
  High cost! 💸
```

**When it's acceptable:**

```
✅ Long time slices (processes run for seconds)
✅ Few context switches per second
✅ Simple hardware (no ASID support)

❌ Short time slices (milliseconds)
❌ Many processes competing
❌ Interactive workloads
```

### 6.3. 🆔 Solution 2: Address Space Identifiers (ASIDs)

**Approach:** Tag each TLB entry with a process identifier so multiple processes can safely share the TLB.

**How it works:**

```
TLB Entry with ASID:
────────────────────
┌─────┬─────┬───────┬──────┬──────┐
│ VPN │ PFN │ Valid │ Prot │ ASID │
└─────┴─────┴───────┴──────┴──────┘
```

**ASID = Address Space Identifier**
- Like a process ID (PID), but smaller (typically 8 bits)
- OS assigns a unique ASID to each process
- TLB lookup matches *both* VPN and ASID

**Example with ASIDs:**

```
TLB Contents:
─────────────
VPN   PFN   Valid  Prot  ASID
10    100   1      rwx   1     ← P1's mapping (ASID=1)
5     42    1      r-x   1     ← P1's mapping
10    170   1      rwx   2     ← P2's mapping (ASID=2)
20    99    1      rw-   2     ← P2's mapping

When P1 (ASID=1) accesses VPN=10:
  → Hardware checks: VPN=10 AND ASID=1
  → Matches first entry → PFN=100 ✅

When P2 (ASID=2) accesses VPN=10:
  → Hardware checks: VPN=10 AND ASID=2
  → Matches third entry → PFN=170 ✅

No confusion! 🎉
```

**Lookup algorithm:**

```c
TLBEntry tlb_lookup_with_asid(VPN vpn, ASID asid) {
    for (int i = 0; i < TLB_SIZE; i++) {
        if (tlb[i].valid &&
            tlb[i].vpn == vpn &&
            tlb[i].asid == asid) {  ← Extra check!
            return tlb[i];
        }
    }
    return TLB_MISS;
}
```

**Context switch with ASID:**

```c
void context_switch(Process *old, Process *new) {
    // NO TLB flush needed! ⚡

    // Just update current ASID register
    set_current_asid(new->asid);

    // Switch page table
    PTBR = new->page_table_base;

    // Done! TLB entries for both processes can coexist
}
```

**Performance comparison:**

```
Flush on switch:              ASID-based:
────────────────              ───────────

Context switch to P2          Context switch to P2
  ↓                             ↓
Flush TLB                     Set ASID=2
  ↓                             ↓
All misses initially 🐌      Some hits immediately! ⚡
                              (if P2 ran recently)

Example:
P1 → P2 → P1 → P2 → P1
 ↓    ↓    ↓    ↓    ↓
Flush each time              No flush, TLB shared

Every switch: rebuild         Switches: near-zero cost
Cost: HIGH 💸                Cost: LOW ✅
```

**ASID limits:**

```
Problem: ASID is only 8 bits → 256 unique values
What if we have 1000 processes running?

Solutions:
──────────

1. Reuse ASIDs:
   When out of ASIDs, flush TLB and reset counter

2. LRU ASID allocation:
   Give ASIDs to recently-run processes

3. Flush on ASID wrap:
   ASID=0..255 used → Flush → Start over at 0

Most systems: Few processes actively use CPU
256 ASIDs is usually enough!
```

### 6.4. 🤝 Sharing Pages Across Processes

**Use case:** Multiple processes mapping the same physical memory.

**Examples:**
- Shared libraries (libc, libm)
- Code pages from same binary
- Explicitly shared memory regions

**TLB with shared pages:**

```
Process P1 and P2 both use libc.so

TLB:
────
VPN   PFN   Valid  Prot  ASID
50    101   1      r-x   1     ← P1 maps code to VPN=50
100   101   1      r-x   2     ← P2 maps SAME code to VPN=100
      ↑                            Both point to PFN=101!
   Same physical page
```

**In plain English:** Two neighbors share a lawnmower 🚜. One stores it at the back of their garage (VPN=50), the other at the side of their shed (VPN=100), but it's the *same lawnmower* (PFN=101).

**Benefits:**

```
Without sharing:
────────────────
P1 loads libc → Uses 1MB RAM
P2 loads libc → Uses 1MB RAM
P3 loads libc → Uses 1MB RAM
Total: 3MB RAM 💸

With sharing:
─────────────
P1, P2, P3 all map same physical pages
Total: 1MB RAM ✅
Savings: 2MB!

With 100 processes: Save 99MB! 🎉
```

**Global pages:**

Some TLBs support a **global bit** to optimize kernel/shared pages:

```
VPN   PFN   Valid  Prot  ASID  Global
200   500   1      r-x   —     1      ← Kernel code, ignore ASID

When global=1:
  → ASID is ignored
  → Page is valid for ALL processes
  → No need for duplicate TLB entries

Use for:
  ✅ Kernel code/data
  ✅ Memory-mapped I/O
  ✅ Very common shared libraries
```

> **💡 Insight**
>
> ASIDs demonstrate **disambiguation through tagging**. By adding a small tag (8 bits) to each entry, we can safely multiplex the TLB across processes. This pattern appears everywhere:
>
> - **VLAN tags** in networking (tag packets with network ID)
> - **Thread IDs** in caches (tag cache lines with thread)
> - **Transaction IDs** in databases (tag rows with transaction)
>
> The trade-off: **Small space overhead (tag bits) for huge performance gain (avoid flushes)**. Almost always worth it!

---

## 7. ♻️ Replacement Policy

When the TLB is full and we need to insert a new translation, which entry should we evict?

**THE CRUX:** How should we design the TLB replacement policy to maximize hit rate?

### 7.1. 📉 LRU (Least Recently Used)

**Strategy:** Evict the entry that hasn't been used for the longest time.

**Rationale:** Exploit **temporal locality**—recently used entries will likely be used again soon.

**How it works:**

```
TLB with timestamps:
────────────────────
VPN   PFN   Last Access Time
10    42    t=1000   ← Used long ago
5     17    t=1500
20    99    t=1900   ← Used recently

New access needs entry (TLB full)
  → Evict VPN=10 (oldest timestamp)
```

**Implementation options:**

```
Perfect LRU:                    Approximate LRU:
────────────                    ────────────────
✅ Track exact order            ✅ Use access bits
❌ Expensive (64! permutations  ✅ Periodic clearing
   for 64-entry TLB)            ✅ Much cheaper
❌ Rarely used                  ✅ Good enough

Common approximation:
  - Each entry has "accessed" bit
  - Hardware sets bit on access
  - OS periodically clears all bits
  - Evict entry with cleared bit
```

**When LRU works well:**

```
Loop over small dataset:
────────────────────────
for (int i = 0; i < 10; i++) {
    access(page[i]);  // 10 pages, 64-entry TLB
}

All pages stay in TLB ✅
Hit rate: 100% after first iteration 🎉
```

**When LRU fails:** (See next section!)

### 7.2. 🎲 Random Replacement

**Strategy:** Evict a random entry.

**Rationale:** Simple, fast, and avoids worst-case behavior.

**How it works:**

```c
int evict_random() {
    return rand() % TLB_SIZE;  // That's it!
}
```

**Pros:**
```
✅ Extremely simple (no bookkeeping)
✅ Fast (just generate random number)
✅ Avoids pathological cases
✅ Works well in practice
```

**Cons:**
```
❌ Doesn't exploit locality
❌ Might evict frequently-used entry by bad luck
```

### 7.3. 💥 When "Reasonable" Policies Fail

**The n+1 problem:**

```
Scenario:
  - TLB has 64 entries
  - Program loops over 65 pages
  - Access pattern: page 0, 1, 2, ..., 64, 0, 1, 2, ..., 64, ...

TLB State with LRU:
───────────────────

First iteration:
  Access 0 → TLB miss, insert page 0
  Access 1 → TLB miss, insert page 1
  ...
  Access 63 → TLB miss, insert page 63
  TLB now full (64 entries)

  Access 64 → TLB miss, evict LEAST recently used = page 0

Second iteration:
  Access 0 → TLB miss! (we just evicted it!)
             Evict page 1 (LRU)
  Access 1 → TLB miss! (we just evicted it!)
             Evict page 2 (LRU)
  Access 2 → TLB miss! (we just evicted it!)
             ...

Result: EVERY SINGLE ACCESS MISSES! 💀
Hit rate: 0%
```

**Why LRU fails here:**

```
LRU always evicts the page we're about to access next!

Access pattern: 0, 1, 2, ..., 64, 0, 1, 2, ...
                              ↑
                     Evicts 0 right before we need it again
```

**Random replacement performance:**

```
Same scenario with random:
──────────────────────────

Access 64 → Evict random page (let's say page 37)
Access 0  → Hit! (still in TLB)
Access 1  → Hit! (still in TLB)
Access 2  → Hit! (still in TLB)
...
Access 37 → Miss (we evicted it)
...
Access 64 → Hit! (still in TLB)

Expected hit rate: ~63/65 = 97% ⚡

Much better than LRU's 0%! 🎉
```

**Comparison table:**

```
Workload                 LRU Performance    Random Performance
────────────────────     ───────────────    ──────────────────
Loop < TLB size          100% ✅            ~95% ✅
Loop = TLB size          100% ✅            ~98% ✅
Loop = TLB size + 1      0% 💀              ~97% ✅
Loop >> TLB size         ~0% 💀             ~TLB/N (bad) 🐌
General workload         Good ✅            Good ✅

Conclusion: Random is more robust!
```

**Real-world policies:**

Many systems use **hybrid approaches**:

```
Intel x86:
  - Pseudo-LRU (approximate)
  - Hardware-managed

ARM:
  - PLRU or Random
  - Configurable

MIPS:
  - OS-managed
  - Can implement any policy
  - Often uses random + hints

Modern approach:
  - Hardware provides hints (access bits)
  - OS makes policy decision
  - Best of both worlds
```

> **💡 Insight**
>
> The replacement policy debate illustrates **the danger of intuition over measurement**. LRU *sounds* smart: "keep recently used things." But edge cases like the n+1 problem show that "smart" policies can fail catastrophically.
>
> Random replacement's success teaches us:
> - **Simplicity has value** (less code, fewer bugs)
> - **Avoiding worst case matters** (0% hit rate is unacceptable)
> - **Robustness beats optimization** (97% reliably > occasional 100% with occasional 0%)
>
> This is why many modern systems favor **simple, robust algorithms over complex, fragile optimizations**.

---

## 8. 💎 A Real TLB: MIPS R4000

Let's examine a real TLB implementation to see how theory meets practice.

### 8.1. 🔍 Entry Format

**MIPS R4000 TLB entry** (64 bits total):

```
┌──────┬───┬──────┬──────┬──────┬───┬───┐
│  VPN │ G │ ASID │  PFN │  C   │ D │ V │
└──────┴───┴──────┴──────┴──────┴───┴───┘
  19    1    8      24      3     1   1

Total: 57 bits used, 7 bits unused
```

**Field breakdown:**

**VPN (Virtual Page Number): 19 bits**
```
MIPS R4000: 32-bit address space, 4KB pages
Expected VPN: 32 - 12 (offset) = 20 bits

But only 19 bits used! Why?
  → User space is only half of address space
  → Upper half reserved for kernel
  → Only need to translate user addresses
  → 31-bit user space → 19-bit VPN

Address space split:
┌─────────────────────┐ 0xFFFFFFFF
│  Kernel (untrans-   │
│   lated/special)    │
├─────────────────────┤ 0x80000000
│  User space         │
│  (needs TLB)        │ ← 19-bit VPN
└─────────────────────┘ 0x00000000
```

**PFN (Physical Frame Number): 24 bits**
```
24 bits of PFN + 12 bits of offset = 36-bit physical address

Address space: 2^36 = 64GB of physical memory ✅
              (Large for 1990s! Future-proof design)

Example:
  Page size: 4KB = 2^12 bytes
  Physical pages: 2^24 = 16,777,216 pages
  Total memory: 16M × 4KB = 64GB
```

**G (Global): 1 bit**
```
Global bit:
  G=1  →  Translation valid for all processes
          Ignore ASID field

  G=0  →  Translation is process-specific
          Match ASID too

Use for kernel mappings:
  Kernel code/data shared across all processes
  No need for duplicate TLB entries per process
```

**ASID (Address Space ID): 8 bits**
```
8 bits = 256 unique process identifiers

Enough for most workloads:
  - Desktop: Usually < 50 active processes
  - Server: Usually < 100 active processes
  - 256 is plenty!

If more needed:
  - Flush TLB, reuse ASIDs
  - LRU ASID assignment
```

**C (Coherence): 3 bits**
```
Cache coherence attributes
Determines how page is cached:

Values:
  000  Uncached (memory-mapped I/O)
  001  Cached non-coherent
  010  Cached coherent (multiprocessor)
  ...

Important for:
  ✅ Memory-mapped device registers (must be uncached)
  ✅ Multiprocessor cache coherence
  ✅ DMA buffer management
```

**D (Dirty): 1 bit**
```
Dirty bit:
  D=0  →  Page has not been written to
  D=1  →  Page has been modified

Set by hardware on write
Read by OS for:
  - Swap: Only write back dirty pages
  - Copy-on-write: Track modifications
  - Memory-mapped files: Sync changes
```

**V (Valid): 1 bit**
```
Valid bit:
  V=0  →  Entry is invalid (empty slot)
  V=1  →  Entry contains valid translation

Different from page table valid bit!
  TLB valid=0: Translation not cached (TLB miss)
  PT valid=0:  Page not allocated (page fault)
```

### 8.2. ⚙️ Special Features

**1. Wired register** 🔒

```
Purpose: Reserve TLB entries for OS

MIPS TLB: 64 entries total

Wired register: Set to N
  → First N entries are "wired" (never evicted)
  → Used for OS critical code/data
  → Remaining 64-N entries for user programs

Example:
  Wired = 4
  → Entries 0-3: OS (TLB miss handler, etc.)
  → Entries 4-63: User programs

Benefit:
  ✅ TLB miss handler code ALWAYS in TLB
  ✅ No infinite miss loop possible
  ✅ Critical code guaranteed fast access
```

**2. Multiple page sizes** 📏

```
MIPS supports variable page sizes:
  - 4KB (default)
  - 16KB
  - 64KB
  - 256KB
  - 1MB
  - 4MB
  - 16MB

Page mask field (not shown in diagram) specifies size

Use cases:
  - 4KB: Normal pages
  - 4MB: Database buffers (huge working set)
  - 16MB: Framebuffer (large contiguous region)

Benefit:
  Fewer TLB entries needed for large regions
  Better TLB coverage! ⚡
```

**3. Software-managed** 💻

```
MIPS philosophy: Keep hardware simple

Hardware does:
  ✅ Parallel TLB lookup
  ✅ Set dirty/accessed bits
  ✅ Raise TLB miss exception

Hardware does NOT:
  ❌ Walk page tables
  ❌ Choose replacement victim
  ❌ Know page table format

Result:
  → OS has complete flexibility
  → Can use any data structure for page table
  → Can optimize for specific workloads
```

### 8.3. 🔧 TLB Management Instructions

MIPS provides four privileged instructions for TLB management:

**1. TLBP (TLB Probe)** 🔍

```assembly
TLBP

Purpose: Check if translation is in TLB

How it works:
  1. OS puts VPN in EntryHi register
  2. Execute TLBP
  3. Hardware searches TLB
  4. If found: Index register = entry number
  5. If not found: Index register high bit set

Use case:
  Before inserting, check if already present
```

```c
void tlb_probe_example() {
    EntryHi = (VPN << 12) | ASID;
    asm("tlbp");  // Probe TLB

    if (Index & 0x80000000) {
        // Not found
        printf("TLB miss for VPN %d\n", VPN);
    } else {
        // Found at Index
        printf("TLB hit for VPN %d at entry %d\n", VPN, Index);
    }
}
```

**2. TLBR (TLB Read)** 📖

```assembly
TLBR

Purpose: Read TLB entry into registers

How it works:
  1. OS sets Index register to entry number
  2. Execute TLBR
  3. Entry contents loaded into EntryHi, EntryLo

Use case:
  Inspect TLB contents for debugging
```

```c
void tlb_read(int index) {
    Index = index;
    asm("tlbr");  // Read TLB entry

    VPN = EntryHi >> 12;
    ASID = EntryHi & 0xFF;
    PFN = EntryLo >> 12;

    printf("Entry %d: VPN=%d ASID=%d → PFN=%d\n",
           index, VPN, ASID, PFN);
}
```

**3. TLBWI (TLB Write Indexed)** ✍️

```assembly
TLBWI

Purpose: Write TLB entry at specific index

How it works:
  1. OS sets Index to entry number
  2. OS sets EntryHi (VPN, ASID)
  3. OS sets EntryLo (PFN, flags)
  4. Execute TLBWI
  5. Entry updated

Use case:
  Replace specific TLB entry (deterministic)
```

```c
void tlb_write_indexed(int index, VPN vpn, PFN pfn, int asid) {
    Index = index;
    EntryHi = (vpn << 12) | asid;
    EntryLo = (pfn << 12) | 0x06;  // Valid + Dirty

    asm("tlbwi");  // Write TLB entry

    printf("Inserted VPN=%d → PFN=%d at entry %d\n",
           vpn, pfn, index);
}
```

**4. TLBWR (TLB Write Random)** 🎲

```assembly
TLBWR

Purpose: Write TLB entry at random index

How it works:
  1. OS sets EntryHi (VPN, ASID)
  2. OS sets EntryLo (PFN, flags)
  3. Execute TLBWR
  4. Hardware chooses random entry in range [Wired, TLB_SIZE)
  5. Entry updated

Use case:
  Insert new entry (random replacement)
  Most common in TLB miss handler
```

```c
void handle_tlb_miss() {
    // Get faulting address from BadVAddr register
    VAddr bad_addr = BadVAddr;
    VPN vpn = bad_addr >> 12;

    // Look up in page table (OS data structure)
    PTE pte = page_table_lookup(vpn);

    if (!pte.valid) {
        // Page fault
        handle_page_fault();
        return;
    }

    // Insert into TLB using random replacement
    EntryHi = (vpn << 12) | current_asid;
    EntryLo = (pte.pfn << 12) | pte.flags;

    asm("tlbwr");  // Random TLB write

    // Return from exception, retry instruction
}
```

**Typical TLB miss handler flow:**

```
1. TLB miss exception
     ↓
2. Save registers
     ↓
3. Get faulting VPN from BadVAddr
     ↓
4. Look up in page table
     ↓
5. If valid: TLBWR to insert
     ↓
6. Restore registers
     ↓
7. Return from exception (eret)
     ↓
8. Instruction retries → TLB hit! ⚡
```

**Security note:** 🔒

```
All four instructions are PRIVILEGED

If user code tries to execute them:
  → Coprocessor Unusable Exception
  → Kernel kills process 💀

Why?
  User controlling TLB = security disaster!
  Could access any physical memory
  Could impersonate other processes
  Could take over entire system
```

> **💡 Insight**
>
> The MIPS TLB design exemplifies **RISC philosophy**: simple hardware, powerful software. By providing only four basic operations, MIPS hardware stays small and fast. The OS gains complete flexibility:
>
> - **Any page table structure** (linear, multi-level, hashed, inverted)
> - **Any replacement policy** (LRU, random, custom)
> - **Any optimization** (superpages, shared pages, lazy allocation)
>
> This contrasts with x86's complex hardware page walker. Neither is "better"—they represent different philosophies:
> - **MIPS**: Simple hardware, smart OS
> - **x86**: Complex hardware, simpler OS
>
> Both achieve high performance through different paths!

---

## 9. 📝 Summary

### 🎯 Key Takeaways

**1. The Core Problem** ⚡

```
Paging requires page table lookup
     ↓
Page table is in memory
     ↓
Every memory access → 2× memory accesses
     ↓
Unacceptably slow! 💀

Solution: TLB caching
     ↓
Cache translations on-chip
     ↓
95-99% hit rate → ~1% overhead ✅
```

**2. TLB Basics** 🔧

```
What: Hardware cache of address translations
Where: On-chip, part of MMU
Size: 32-128 entries (small but fast!)
Type: Fully associative (parallel search)
Speed: 1-2 cycles on hit, 100+ on miss

Access pattern:
  VPN → Check TLB → Hit? Use PFN : Walk page table
```

**3. TLB Management** 🖥️

```
Hardware-Managed              Software-Managed
─────────────────             ────────────────
Hardware walks page table     OS handles TLB miss
Fast (no trap)                Flexible (any structure)
Example: x86                  Example: MIPS, RISC-V

Both work well! Different trade-offs.
```

**4. Context Switches** 🔄

```
Problem: Multiple processes share TLB
         Same VPN → Different PFN per process

Solution 1: Flush on switch (simple, slower)
Solution 2: ASIDs (complex, faster)

ASIDs = Winner in modern systems! ⚡
```

**5. Replacement Policies** ♻️

```
LRU:     Exploits locality, but n+1 problem
Random:  Simple, robust, no worst case

Winner: Random or pseudo-LRU
        (Simple + robust > complex + fragile)
```

**6. Real-World Impact** 💻

```
Without TLBs: Paging would be impractical
With TLBs:   Virtual memory is fast! ⚡

Modern systems:
  99% TLB hit rate
  < 1% performance overhead
  Virtual memory "just works"

TLBs are ESSENTIAL infrastructure! 🎯
```

### 📊 Performance Summary

**TLB Hit vs. Miss:**

```
TLB Hit (99% of time):
─────────────────────
1-2 cycles ⚡
Translation cached on-chip
Nearly free!

TLB Miss (1% of time):
──────────────────────
100-1000 cycles 🐌
Must access page table in RAM
Expensive!

Average (99% hit rate):
───────────────────────
0.99 × 2 + 0.01 × 100 = 3 cycles
Still excellent! ✅
```

### 🎓 Design Principles Learned

**1. Caching is fundamental** 💾
```
Slow resource (page table in RAM)
    ↓
Add fast cache (TLB on-chip)
    ↓
Amortize cost over many accesses
```

**2. Locality matters** 🌊
```
Spatial: Array elements close → Share pages → TLB reuse
Temporal: Loop over data → Same pages → TLB hits
```

**3. Small caches can be effective** 📦
```
TLB: Only 64-128 entries
But:  Hit rate > 95%
Why:  Working set usually small
Lesson: Right-sized cache > huge cache
```

**4. Hardware/software co-design** 🤝
```
Hardware: Fast common case (TLB hit)
Software: Handle rare case (TLB miss, replacement)

Both must work together for performance
```

**5. Simple can beat clever** 🎲
```
Random replacement: Simple, robust
LRU: Complex, fails in edge cases

Lesson: Measure, don't assume!
```

### 🔮 What's Next

```
We now have fast address translation!

But new questions arise:
  - How to handle HUGE address spaces? (Multi-level page tables)
  - What about processes larger than RAM? (Swapping)
  - How to share memory efficiently? (Shared pages, copy-on-write)
  - What about really large pages? (Huge pages, superpages)

Next chapters:
  → Multi-level page tables (smaller page table overhead)
  → Advanced page tables (inverted, hashed)
  → Swapping (using disk as extended memory)
```

### 💡 Final Insights

> **The Fundamental Trade-off**
>
> TLBs embody the classic **space/time trade-off**:
> - **Space**: Small cache (128 entries × 8 bytes = 1KB)
> - **Time**: Huge speedup (100× faster than page table lookup)
>
> This asymmetry—tiny space cost, massive time benefit—is why TLBs are universally adopted.

> **Culler's Law: RAM Isn't Always RAM**
>
> Random access to memory isn't truly uniform cost:
> - **TLB hit**: ~2 cycles
> - **TLB miss**: ~100 cycles
> - **Page fault**: ~10,000,000 cycles (disk access!)
>
> Access patterns matter enormously. Sequential array access: fast. Random pointer chasing: slow. The TLB amplifies this difference.

> **The Power of Caching**
>
> TLBs are just one instance of caching appearing throughout the system:
>
> ```
> CPU Registers    →  Cache L1 values
> L1 Cache         →  Cache L2/RAM data
> L2/L3 Cache      →  Cache RAM data
> TLB              →  Cache page table entries
> Page Table       →  Cache disk→RAM mappings
> Disk Cache       →  Cache disk sectors
>
> Caching all the way down! 🐢🐢🐢
> ```

**The bottom line:** TLBs transform paging from a neat idea into a practical reality. Without them, virtual memory would be too slow to use. With them, we get memory protection, isolation, and abstraction at negligible cost. Engineering at its finest! 🎉

---

**Previous:** [Chapter 13: Paging Introduction](chapter13-paging-introduction.md) | **Next:** [Chapter 15: Smaller Page Tables](chapter15-smaller-page-tables.md)
