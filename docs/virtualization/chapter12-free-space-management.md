# Chapter 12: Free-Space Management 🧩

_Understanding how operating systems and memory allocators manage variable-sized chunks of memory_

---

## 📋 Table of Contents

1. [🎯 Introduction](#1-introduction)
   - 1.1. [The Core Challenge](#11-the-core-challenge)
   - 1.2. [External Fragmentation Problem](#12-external-fragmentation-problem)
2. [📐 Assumptions and Setup](#2-assumptions-and-setup)
   - 2.1. [The malloc/free Interface](#21-the-mallocfree-interface)
   - 2.2. [The Heap and Free List](#22-the-heap-and-free-list)
   - 2.3. [Key Constraints](#23-key-constraints)
3. [🔧 Low-Level Mechanisms](#3-low-level-mechanisms)
   - 3.1. [Splitting Free Chunks](#31-splitting-free-chunks)
   - 3.2. [Coalescing Adjacent Space](#32-coalescing-adjacent-space)
   - 3.3. [Tracking Allocation Sizes](#33-tracking-allocation-sizes)
   - 3.4. [Embedding the Free List](#34-embedding-the-free-list)
   - 3.5. [Growing the Heap](#35-growing-the-heap)
4. [🎯 Basic Allocation Strategies](#4-basic-allocation-strategies)
   - 4.1. [Best Fit](#41-best-fit)
   - 4.2. [Worst Fit](#42-worst-fit)
   - 4.3. [First Fit](#43-first-fit)
   - 4.4. [Next Fit](#44-next-fit)
   - 4.5. [Strategy Comparison](#45-strategy-comparison)
5. [🚀 Advanced Approaches](#5-advanced-approaches)
   - 5.1. [Segregated Lists](#51-segregated-lists)
   - 5.2. [Buddy Allocation](#52-buddy-allocation)
   - 5.3. [Other Modern Ideas](#53-other-modern-ideas)
6. [📝 Summary](#6-summary)

---

## 1. 🎯 Introduction

**In plain English:** Imagine you're managing a parking lot 🅿️ with spaces of different sizes—some for motorcycles 🏍️, some for cars 🚗, some for trucks 🚚. Fixed-size spots are easy: just keep a list of empty spaces. But what if vehicles can be any size? A tiny smart car could take a truck space, wasting room. If you split a truck space into smaller pieces, you might later find you can't fit a truck even though you have enough total empty space—it's just scattered around! This is the free-space management problem.

**In technical terms:** Free-space management becomes challenging when dealing with **variable-sized allocations**. With fixed-size units (like pages), you simply maintain a list of free units. With variable sizes—as in `malloc()`/`free()` libraries or OS memory management with segmentation—you face **external fragmentation**: free space gets chopped into non-contiguous pieces, potentially preventing allocations even when sufficient total space exists.

**Why it matters:** Every time your program calls `malloc()`, a sophisticated allocator is working behind the scenes to find and manage memory. Understanding these algorithms helps you write more memory-efficient code 💾 and appreciate the performance trade-offs in systems programming. The same principles apply to disk space allocation 💿, network buffer management 📡, and database memory pools 🗄️.

> **💡 Insight**
>
> Free-space management demonstrates the **fundamental trade-off between simplicity and efficiency**. Fixed-size allocation is simple but wasteful (internal fragmentation). Variable-size allocation is efficient but complex (external fragmentation). This same trade-off appears throughout computing: packet sizes in networking, database record layouts, and even file system block sizes.

### 1.1. 🎯 The Core Challenge

**THE CRUX:** How should free space be managed when satisfying variable-sized requests? What strategies minimize fragmentation? What are the time and space overheads?

The answers involve:

```
Core Mechanisms              Allocation Policies
────────────────             ───────────────────
Splitting     →              Best Fit
Coalescing    →              Worst Fit
Tracking      →              First Fit
Embedding     →              Next Fit
                             Segregated Lists
                             Buddy Allocation
```

### 1.2. 🧩 External Fragmentation Problem

**Visual Example:**

```
Initial Heap (30 bytes)
┌──────────────────────────────┐
│         FREE (30 bytes)      │
└──────────────────────────────┘
0                              30

After allocating 10 bytes at position 10:
┌─────────┬──────────┬─────────┐
│  FREE   │   USED   │  FREE   │
│ 10 bytes│ 10 bytes │ 10 bytes│
└─────────┴──────────┴─────────┘
0        10         20         30
```

**The Problem:** You now have 20 bytes free (10 + 10), but a request for 15 bytes will **fail** ❌ because there's no single contiguous 15-byte chunk!

**In plain English:** It's like having two parking spaces that are separated—you can't park a vehicle that needs the combined space of both. The total space is there, but it's not **contiguous** (touching).

> **💡 Insight**
>
> External fragmentation is a manifestation of the **locality problem**—resources scattered in space are less useful than concentrated ones. You'll see this same pattern in disk fragmentation (scattered file blocks slow down reads), memory paging (scattered pages require more TLB entries), and even CPU cache behavior (scattered data causes more cache misses).

---

## 2. 📐 Assumptions and Setup

### 2.1. 💻 The malloc/free Interface

The standard C memory allocation interface is elegant in its simplicity:

```c
// Request memory
void *malloc(size_t size);

// Return memory
void free(void *ptr);
```

**Key characteristics:**

```
malloc() Interface              free() Interface
──────────────────              ────────────────
✅ Takes size parameter         ❌ NO size parameter!
✅ Returns pointer              ✅ Takes only pointer
⚠️ Returns NULL on failure     💡 Must figure out size
📍 Pointer to start of block   🔧 Library handles details
```

**In plain English:** When you rent a hotel room 🏨, you tell them how many nights you need (`malloc(nights)`). When you check out, you just give them the room key (`free(key)`)—they already know which room and how big it is because they kept records.

**Example usage:**

```c
// Simple allocation
int *array = malloc(100 * sizeof(int));  // Request 400 bytes
if (array == NULL) {
    // Out of memory!
    return -1;
}

// Use the memory
for (int i = 0; i < 100; i++) {
    array[i] = i * i;
}

// Return it (NO size needed!)
free(array);  // Library knows it's 400 bytes
```

**The tricky part:** How does `free()` know the size? We'll explore this in section 3.3! 🔍

### 2.2. 📚 The Heap and Free List

**In plain English:** The **heap** is like a warehouse 🏭 where your program can request variable-sized storage. The **free list** is the inventory system 📋 tracking which storage bins are available.

**Terminology clarification:**

```
┌─────────────────────────────────────────┐
│          PROGRAM MEMORY LAYOUT          │
├─────────────────────────────────────────┤
│  Stack (function calls) ↓               │
│                                         │
│          (unused address space)         │
│                                         │
│  Heap (dynamic memory) ↑                │  ← "heap" = dynamic allocation region
│  ────────────────────────               │
│  Data (global variables)                │
│  Code (program instructions)            │
└─────────────────────────────────────────┘
```

The **free list** is a data structure tracking free space:

```
Conceptual Free List
────────────────────
head → [addr:0, len:10] → [addr:20, len:10] → NULL
         ↓                    ↓
     bytes 0-9           bytes 20-29
```

**Note:** "List" is a misnomer! 🎭 It could be:
- Linked list (simple, slow)
- Binary tree (balanced, faster)
- Segregated free lists (specialized)
- Bitmap (compact representation)

### 2.3. 🔒 Key Constraints

Our discussion assumes:

**1. External Fragmentation Focus** 🎯
```
External Fragmentation          Internal Fragmentation
──────────────────────          ──────────────────────
Waste BETWEEN allocations       Waste WITHIN allocations
┌────┐ ❌ ┌────┐                ┌────────────┐
│Used│ 5  │Used│                │Used│Wasted │
└────┘ free└────┘               └────┴───────┘
         bytes                  Request 10, given 16
```

**2. No Compaction** 🚫
```c
int *ptr = malloc(100);
// Library CANNOT move this memory to another location
// (pointer would become invalid!)
```

**In plain English:** Once you give someone an address (pointer), you can't move their apartment to a different building without telling them! In C, we can't track all pointers to memory, so we can't move allocated chunks around.

**Exception:** ⚡ Operating systems CAN compact memory when using segmentation because they control the address translation hardware. But user-level allocators cannot.

**3. Contiguous Region** 📏
```
Single Fixed Heap
─────────────────
[Start of heap] ═══════════════ [End of heap]
                 4096 bytes
```

We assume the heap is one contiguous region. In reality, allocators can request more memory from the OS (`sbrk()` system call), but we'll keep it simple initially.

**4. Language Constraints** 🔤
```
C/C++ (no compaction)           Java/Python (compaction OK)
─────────────────────           ───────────────────────────
Hard to find all pointers       Garbage collector tracks
Manual memory management        all references
No automatic cleanup            Can move objects safely
```

> **💡 Insight**
>
> The **no compaction** constraint is fundamental to C/C++ performance. These languages give you direct memory addresses (pointers) for speed. The cost? Fragmentation is unavoidable. Languages with garbage collection (Java, Python, Go) can compact memory because they track all references, but they pay runtime overhead for this bookkeeping. This is the classic **performance vs. safety** trade-off.

---

## 3. 🔧 Low-Level Mechanisms

Before exploring allocation policies, let's understand the fundamental mechanisms that almost all allocators use.

### 3.1. ✂️ Splitting Free Chunks

**In plain English:** Imagine you need to rent a parking space for your motorcycle 🏍️, but only truck-sized spaces 🚚 are available. The parking lot manager gives you a truck space but puts up a divider, creating a motorcycle space and a leftover small-car space. That's **splitting**!

**The Mechanism:**

```
Step 1: Initial free list
────────────────────────────────────────────────
head → [addr:0, len:10] → [addr:20, len:10] → NULL

┌─────────┬──────────┬─────────┐
│  FREE   │   USED   │  FREE   │
│ 10 bytes│ 10 bytes │ 10 bytes│
└─────────┴──────────┴─────────┘
0        10         20         30


Step 2: Request for 1 byte arrives
────────────────────────────────────────────────
Allocator finds second chunk (10 bytes) is big enough

Step 3: Split the chunk
────────────────────────────────────────────────
head → [addr:0, len:10] → [addr:21, len:9] → NULL
                          ↑         ↑
                      start+1   size-1

┌─────────┬──────────┬─┬────────┐
│  FREE   │   USED   │U│  FREE  │
│ 10 bytes│ 10 bytes │1│ 9 bytes│
└─────────┴──────────┴─┴────────┘
0        10         20 21       30
                      ↑
                  returned to caller
```

**Code implementation:**

```c
void *allocate(size_t size) {
    node_t *current = head;

    // Find a chunk big enough
    while (current != NULL) {
        if (current->size >= size) {
            // Found one! Split it.
            void *ptr = (void *)current;  // Return this address
            current->addr += size;         // Shift start forward
            current->size -= size;         // Reduce remaining size

            if (current->size == 0) {
                // Entire chunk used, remove from list
                remove_from_list(current);
            }

            return ptr;
        }
        current = current->next;
    }

    return NULL;  // No suitable chunk found
}
```

**Progressive Example:**

**Simple:** Allocating smaller than available
```
Free: [50 bytes]
Request: 10 bytes
Result: Return 10 bytes, leave 40 bytes free
```

**Intermediate:** Multiple splits
```
Free: [100 bytes]
Request 1: 20 bytes → Free: [80 bytes]
Request 2: 15 bytes → Free: [65 bytes]
Request 3: 30 bytes → Free: [35 bytes]
```

**Advanced:** Splitting with headers (section 3.3)
```
Free: [100 bytes]
Request: 20 bytes (plus 8-byte header needed)
Result: Return 28 bytes total, leave 72 bytes free
```

> **💡 Insight**
>
> Splitting creates a **cascading effect**: each allocation potentially creates a new, smaller free chunk. Over time, this leads to increasingly fragmented memory with many tiny unusable chunks. This is why coalescing (combining adjacent free chunks) is essential—it's the yin to splitting's yang.

### 3.2. 🔗 Coalescing Adjacent Space

**In plain English:** When two adjacent parking spaces become empty, remove the divider between them to create one large space. Otherwise, you'll have many small spaces but can't park large vehicles! This is **coalescing** (also called **merging**).

**The Problem Without Coalescing:**

```
Step 1: Three allocations made
┌─────┬─────┬─────┬──────┐
│Used │Used │Used │ Free │
│ 10  │ 10  │ 10  │  10  │
└─────┴─────┴─────┴──────┘
0    10    20    30      40

Step 2: Free all three (WITHOUT coalescing)
┌─────┬─────┬─────┬──────┐
│Free │Free │Free │ Free │
│ 10  │ 10  │ 10  │  10  │
└─────┴─────┴─────┴──────┘

Free list: [0,10] → [10,10] → [20,10] → [30,10] → NULL

Problem: Request for 25 bytes FAILS! ❌
(Total free: 40 bytes, but no single chunk ≥ 25)
```

**With Coalescing:**

```
Step 1: Free first chunk (addr 0)
┌─────┬─────┬─────┬──────┐
│Free │Used │Used │ Free │
│ 10  │ 10  │ 10  │  10  │
└─────┴─────┴─────┴──────┘

Free list: [0,10] → [30,10] → NULL

Step 2: Free second chunk (addr 10)
┌──────────┬─────┬──────┐
│   Free   │Used │ Free │
│    20    │ 10  │  10  │
└──────────┴─────┴──────┘
    ↑
 Coalesced! [0,10] + [10,10] → [0,20]

Free list: [0,20] → [30,10] → NULL

Step 3: Free third chunk (addr 20)
┌──────────────────────────┐
│          Free            │
│           40             │
└──────────────────────────┘
    ↑
 Triple coalesce! [0,20] + [20,10] + [30,10] → [0,40]

Free list: [0,40] → NULL
```

**Implementation Strategy:**

```c
void free_with_coalesce(void *ptr, size_t size) {
    // Create a new free node
    node_t *new_free = (node_t *)ptr;
    new_free->addr = (void *)ptr;
    new_free->size = size;

    // Try to merge with adjacent free chunks
    node_t *current = head;
    while (current != NULL) {
        // Check if current chunk is right before new chunk
        if (current->addr + current->size == new_free->addr) {
            // Merge forward: current absorbs new_free
            current->size += new_free->size;
            new_free = current;  // Continue with merged chunk
        }

        // Check if current chunk is right after new chunk
        if (new_free->addr + new_free->size == current->addr) {
            // Merge backward: new_free absorbs current
            new_free->size += current->size;
            remove_from_list(current);
        }

        current = current->next;
    }

    // Add the (possibly merged) chunk to free list
    add_to_list(new_free);
}
```

**Optimization: Address-Ordered List** 🎯

**In plain English:** Keep the free list sorted by address. This makes finding adjacent chunks much faster—they're right next to each other in the list!

```
Unordered List                  Address-Ordered List
──────────────                  ────────────────────
[20,10] → [0,10] → [30,10]     [0,10] → [20,10] → [30,10]
    ↓                                ↓
Hard to find neighbors          Easy to find neighbors!
Must scan entire list           Just check list->next
```

> **💡 Insight**
>
> Coalescing is a form of **greedy optimization**—combine chunks as soon as possible. An alternative is **lazy coalescing**: only merge chunks when memory gets tight. This trades current fragmentation for lower free() overhead. Many systems use hybrid approaches: quick coalescing for small chunks, lazy for large ones. The right choice depends on your workload pattern.

### 3.3. 🏷️ Tracking Allocation Sizes

**THE MYSTERY:** How does `free(ptr)` know how many bytes to free when you don't pass a size parameter?

**THE SOLUTION:** Hidden headers! 🎩✨

**In plain English:** It's like a museum coat check 🧥. You hand over your coat and get a ticket (pointer). The ticket has a number, but the size/type of your coat is written on a tag attached to it. When you return with just the ticket number, the attendant finds your coat and can see from the tag what it is.

**Visual Layout:**

```
What the programmer sees:
────────────────────────
ptr → [20 bytes of usable memory]


What actually exists in memory:
────────────────────────────────
       ┌──────────┬────────────────────┐
 hptr→ │  Header  │   User's 20 bytes  │
       │ (8 bytes)│                    │
       └──────────┴────────────────────┘
                  ↑
                 ptr (returned to user)
```

**Header Structure:**

```c
typedef struct {
    size_t size;      // How many bytes allocated?
    int magic;        // Sanity check (e.g., 0x1234567)
} header_t;
```

**Allocation with Header:**

```c
void *malloc(size_t size) {
    // Need space for header + user data
    size_t total_size = size + sizeof(header_t);

    // Find free chunk of at least total_size
    void *chunk = find_free_chunk(total_size);
    if (chunk == NULL) return NULL;

    // Set up header
    header_t *hptr = (header_t *)chunk;
    hptr->size = size;
    hptr->magic = 0x1234567;

    // Return pointer AFTER header
    void *ptr = (void *)(hptr + 1);  // Pointer arithmetic!
    return ptr;
}
```

**Free with Header:**

```c
void free(void *ptr) {
    // Back up to find header
    header_t *hptr = (header_t *)ptr - 1;

    // Sanity check
    if (hptr->magic != 0x1234567) {
        panic("Corrupted header! Double-free or wild pointer!");
    }

    // Now we know the size!
    size_t total_size = hptr->size + sizeof(header_t);

    // Return chunk to free list
    add_to_free_list(hptr, total_size);
}
```

**Progressive Example:**

**Simple:** Single allocation
```c
int *arr = malloc(20);        // User requests 20 bytes
// Actually allocates 28 bytes (8 header + 20 data)

Memory layout:
┌────────────┬────────────────────┐
│size:20     │ arr points here    │
│magic:123...│ (20 bytes)         │
└────────────┴────────────────────┘

free(arr);                    // Finds size from header
```

**Intermediate:** Multiple allocations
```c
char *s1 = malloc(10);   // 18 bytes total (8+10)
int  *s2 = malloc(100);  // 108 bytes total (8+100)
char *s3 = malloc(5);    // 13 bytes total (8+5)

Memory:
┌────┬────┬─────┬─────┬────┬───┐
│hdr │ 10 │ hdr │ 100 │hdr │ 5 │
└────┴────┴─────┴─────┴────┴───┘
  ↑    ↑    ↑     ↑     ↑    ↑
  8    s1   8     s2    8    s3

free(s2);  // Knows to free 108 bytes
free(s1);  // Knows to free 18 bytes
free(s3);  // Knows to free 13 bytes
```

**Advanced:** Detecting errors
```c
int *arr = malloc(100);
free(arr);
free(arr);  // DOUBLE FREE!

// Second free() detects:
// - Magic number corrupted (free list overwrote it)
// - Or magic number still valid but chunk already in free list
// → Abort with error message
```

**The Cost:**

```
Overhead Calculation
────────────────────
Request: 8 bytes
Actual:  16 bytes (8 header + 8 data)
Overhead: 100% 😱

Request: 1024 bytes
Actual:  1032 bytes (8 header + 1024 data)
Overhead: 0.8% ✅

Conclusion: Headers hurt small allocations!
```

> **💡 Insight**
>
> The header technique demonstrates **metadata management**—using a small amount of extra space to enable powerful features (size tracking, corruption detection). You'll see this pattern everywhere:
> - TCP/IP packets have headers (routing, checksums)
> - File systems have inodes (file metadata)
> - Databases have tuple headers (transaction info)
> - Even objects in OOP languages have headers (type info, vtables)
>
> The universal trade-off: **more metadata = more capability, but higher overhead**.

### 3.4. 🗂️ Embedding the Free List

**THE PARADOX:** We need a data structure (free list) to track free memory, but where do we store that data structure? We can't call `malloc()` to allocate list nodes—we're inside `malloc()`! 🤯

**THE SOLUTION:** Store the free list **inside the free space itself**! 🎯

**In plain English:** Imagine a warehouse 📦 where you store the inventory clipboard on one of the empty shelves. The clipboard takes up a shelf, but that's okay—it tells you about all the OTHER empty shelves.

**Node Structure:**

```c
typedef struct node_t {
    size_t size;           // How many bytes in this chunk?
    struct node_t *next;   // Pointer to next free chunk
} node_t;
```

**Example: Initializing a 4KB Heap**

```c
// mmap() gives us a 4096-byte chunk of memory
void *heap = mmap(NULL, 4096, PROT_READ | PROT_WRITE,
                  MAP_ANON | MAP_PRIVATE, -1, 0);

// Cast it to a node and initialize
node_t *head = (node_t *)heap;
head->size = 4096 - sizeof(node_t);  // Subtract node overhead
head->next = NULL;

// Free list now has one entry describing the entire heap
```

**Visual Layout:**

```
Initial Heap (4096 bytes at address 16KB)
─────────────────────────────────────────

Memory address: 16384
┌────────────────────────────────────────────┐
│ size: 4088                                 │
│ next: NULL (0)                             │
│ ... (rest of 4088 bytes available) ...    │
└────────────────────────────────────────────┘
↑
head pointer

Free list: head → [addr:16384, size:4088] → NULL
```

**After Allocation: malloc(100)**

```c
void *ptr = malloc(100);
```

```
Memory after allocation:
────────────────────────

┌──────────┬───────────┬───────────────────────┐
│ Header   │   User    │    Free Chunk         │
│ size:100 │   100     │  size: 3980           │
│magic:123 │   bytes   │  next: NULL           │
└──────────┴───────────┴───────────────────────┘
↑          ↑           ↑
16384      ptr         new free chunk
           (returned)

Free list: head → [addr:16492, size:3980] → NULL
                       ↑
                  16384 + 8 (header) + 100 + 4 (alignment) = 16492
```

**After Three Allocations: malloc(100) x 3**

```
Memory layout:
──────────────

┌────┬────┬────┬────┬────┬────┬─────────────┐
│hdr │100 │hdr │100 │hdr │100 │   Free      │
│8b  │    │8b  │    │8b  │    │ size: 3764  │
└────┴────┴────┴────┴────┴────┴─────────────┘
  ↑    ↑    ↑    ↑    ↑    ↑    ↑
  Used ptr  Used ptr  Used ptr  Free chunk

Free list: head → [addr:16708, size:3764] → NULL
```

**Freeing the Middle Chunk: free(sptr)**

```c
void *ptr1 = malloc(100);  // Chunk 1
void *ptr2 = malloc(100);  // Chunk 2 (middle)
void *ptr3 = malloc(100);  // Chunk 3

free(ptr2);  // Free the middle one
```

```
Memory after free(ptr2):
────────────────────────

┌────┬────┬────────────┬────┬────┬─────────────┐
│hdr │100 │   FREE     │hdr │100 │   FREE      │
│    │Used│ size: 100  │    │Used│ size: 3764  │
└────┴────┴────────────┴────┴────┴─────────────┘
            ↑                       ↑
            New!                    Original

Free list: head → [addr:16492, size:100] → [addr:16708, size:3764] → NULL
                       ↓                           ↓
                   Middle chunk                End chunk
```

**The Free List is Scattered in Memory!** 🌊

```
Conceptual view:
────────────────
head → Node1 → Node2 → NULL

Physical reality:
─────────────────
head → [bytes 16492-16591] → [bytes 16708-20471] → NULL
            ↓                        ↓
        In middle                At end
        of heap                  of heap
```

> **💡 Insight**
>
> Embedding the free list demonstrates **self-referential data structures**—using the resource to track itself. This is a powerful space-saving technique. You'll see it in:
> - **Disk block allocation**: free block list stored in free blocks
> - **Memory page tables**: page table pages stored in regular pages
> - **Database buffer pools**: free buffer list in buffer headers
>
> The key insight: **When a resource is unused, you can use it to track its own availability**.

### 3.5. 🌱 Growing the Heap

**In plain English:** What happens when your allocator runs out of memory? You could give up and return NULL 😢. Or you could ask the operating system for more! 📞

**Two Approaches:**

**1. Fixed Heap (Simple)** 🔒
```c
void *malloc(size_t size) {
    void *ptr = find_free_chunk(size);
    if (ptr == NULL) {
        return NULL;  // Sorry, out of memory! 🚫
    }
    return ptr;
}
```

**2. Growing Heap (Production)** 📈
```c
void *malloc(size_t size) {
    void *ptr = find_free_chunk(size);

    if (ptr == NULL) {
        // Try to grow heap
        if (grow_heap(size) == SUCCESS) {
            ptr = find_free_chunk(size);  // Try again
        }
    }

    return ptr;  // Could still be NULL
}
```

**The `sbrk()` System Call:**

```c
// Request more heap space from OS
void *sbrk(intptr_t increment);

// Example: Grow heap by 4KB
void *old_break = sbrk(4096);
if (old_break == (void *)-1) {
    // OS denied request (out of RAM!)
    return ERROR;
}

// Now we have 4096 more bytes
// Add them to free list
node_t *new_chunk = (node_t *)old_break;
new_chunk->size = 4096 - sizeof(node_t);
new_chunk->next = head;
head = new_chunk;
```

**Visual Example:**

```
Initial heap:
─────────────
┌───────────────┐
│ 4KB           │  ← Original heap
└───────────────┘
0              4KB

After sbrk(4096):
─────────────────
┌───────────────┬───────────────┐
│ 4KB           │ 4KB           │  ← Extended!
└───────────────┴───────────────┘
0              4KB             8KB
                ↑
           Program break (end of heap)
```

**Progressive Example:**

**Simple:** Growing once
```c
// Heap starts at 4KB
// Allocate 3.5KB → OK
void *p1 = malloc(3584);

// Allocate 1KB → Need more space!
void *p2 = malloc(1024);
// → sbrk(4096) called automatically
// → Now have 8KB total
// → Allocation succeeds ✅
```

**Intermediate:** Multiple growth spurts
```c
// Start: 4KB heap
// Allocate 20KB total in small chunks
// → Heap grows multiple times: 4KB → 8KB → 16KB → 32KB
// → Growth strategy: double each time (exponential)
```

**Advanced:** Memory pressure
```c
void *p1 = malloc(1GB);  // Request 1 gigabyte!

// sbrk(1GB) called
// OS checks: Do we have 1GB of free physical RAM?
// - If YES: Grant request ✅
// - If NO:  Return error, malloc() returns NULL ❌
```

**Growth Strategies:** 📊

```
Linear Growth                Exponential Growth
─────────────                ──────────────────
+4KB each time              ×2 each time
4 → 8 → 12 → 16            4 → 8 → 16 → 32

Pros: Predictable           Pros: Fast growth
Cons: Many syscalls         Cons: May waste space
```

> **💡 Insight**
>
> Heap growth demonstrates **lazy resource allocation**—don't request resources until you need them. This pattern appears throughout systems:
> - **Virtual memory**: Allocate pages on first access (demand paging)
> - **Database connections**: Create connections as needed (connection pooling)
> - **Thread pools**: Spawn threads when workload increases
>
> The alternative—**eager allocation**—is simpler but wasteful. Most modern systems favor lazy allocation to optimize resource usage.

---

## 4. 🎯 Basic Allocation Strategies

Now that we understand the mechanisms (splitting, coalescing, tracking), let's explore **policies**—how to choose which free chunk to use when multiple options exist.

**The Setup:**

```
Free list with three chunks:
────────────────────────────
head → [10 bytes] → [30 bytes] → [20 bytes] → NULL

Request arrives: malloc(15)

Question: Which chunk should we use? 🤔
```

### 4.1. 🎯 Best Fit

**Strategy:** Search the entire free list and find the smallest chunk that is big enough.

**In plain English:** It's like finding the smallest parking spot that still fits your car 🚗. Why waste a huge truck space when a compact space will do?

**Example Execution:**

```
Free list: [10] → [30] → [20] → NULL
Request: 15 bytes

Scan:
- 10 bytes? Too small ❌
- 30 bytes? Big enough ✅ (candidate, waste: 15)
- 20 bytes? Big enough ✅ (candidate, waste: 5) ← BEST!

Return: 20-byte chunk (waste only 5 bytes)
Result: [10] → [30] → [5] → NULL
```

**Code:**

```c
void *best_fit(size_t size) {
    node_t *current = head;
    node_t *best = NULL;
    size_t best_waste = SIZE_MAX;

    // Search entire list
    while (current != NULL) {
        if (current->size >= size) {
            size_t waste = current->size - size;
            if (waste < best_waste) {
                best = current;
                best_waste = waste;
            }
        }
        current = current->next;
    }

    if (best != NULL) {
        return allocate_from_chunk(best, size);
    }
    return NULL;
}
```

**Pros and Cons:**

```
✅ Pros                          ❌ Cons
───────                          ────────
Minimizes wasted space           Must search entire list (slow!)
Leaves larger chunks intact      Creates tiny leftover chunks
Good for mixed workloads         "Slivers" of useless space
```

**When Best Fit Fails:**

```
Initial: [100 bytes] free

Request 10 bytes × 9:
────────────────────
[10][10][10][10][10][10][10][10][10][10 leftover]

Now have 10 bytes free, but it's in 1-byte slivers! 😱
[1][1][1][1][1][1][1][1][1][1]

Request for 5 bytes FAILS despite having 10 total free!
```

> **💡 Insight**
>
> Best Fit demonstrates **local optimization vs. global performance**. Each decision (minimize waste now) is locally optimal, but the cumulative effect (many tiny fragments) can be globally poor. This is a classic problem in greedy algorithms—optimal local choices don't guarantee global optimality.

### 4.2. 💥 Worst Fit

**Strategy:** Find the largest chunk and allocate from it.

**In plain English:** Always use the biggest parking lot 🅿️ even for a tiny car 🏍️. The idea? Leave big spaces free, avoid tiny unusable fragments.

**Example Execution:**

```
Free list: [10] → [30] → [20] → NULL
Request: 15 bytes

Scan:
- 10 bytes? Too small ❌
- 30 bytes? Big enough ✅ (candidate, size: 30) ← WORST (BIGGEST)!
- 20 bytes? Big enough ✅ (candidate, size: 20)

Return: 30-byte chunk (leave 15 bytes)
Result: [10] → [15] → [20] → NULL
           ↑
      Still usable!
```

**Code:**

```c
void *worst_fit(size_t size) {
    node_t *current = head;
    node_t *worst = NULL;
    size_t worst_size = 0;

    // Search entire list
    while (current != NULL) {
        if (current->size >= size) {
            if (current->size > worst_size) {
                worst = current;
                worst_size = current->size;
            }
        }
        current = current->next;
    }

    if (worst != NULL) {
        return allocate_from_chunk(worst, size);
    }
    return NULL;
}
```

**The Theory:**

```
Best Fit Result           Worst Fit Result
───────────────           ────────────────
[Large chunks used]       [Large chunks split]
[Tiny slivers left]       [Medium chunks left]
     ↓                         ↓
Unusable fragments        Still usable!
```

**The Reality:** 😞

```
✅ Pros                          ❌ Cons
───────                          ────────
Avoids tiny fragments            Still searches entire list (slow!)
Leaves medium chunks free        Studies show: WORSE fragmentation
Simple logic                     Quickly exhausts large chunks
                                 Poor performance overall
```

**Why It Fails:**

```
Scenario: Server needs 1MB chunks frequently

Initial: [10MB] free

After worst fit allocations:
[9MB][8MB][7MB][6MB][5MB]... fragmented!
           ↓
Eventually no 1MB chunk exists,
despite gigabytes total free! ❌
```

> **💡 Insight**
>
> Worst Fit demonstrates that **intuitive solutions can fail**. The reasoning (leave big chunks) sounds good, but empirical studies show it performs poorly. This is why **benchmarking beats intuition** in systems design. Always measure real workloads!

### 4.3. ⚡ First Fit

**Strategy:** Return the first chunk that is big enough. Stop searching immediately.

**In plain English:** Like taking the first available parking spot 🅿️ you see instead of circling the lot looking for the "perfect" spot. Fast and pragmatic!

**Example Execution:**

```
Free list: [10] → [30] → [20] → NULL
Request: 15 bytes

Scan:
- 10 bytes? Too small ❌
- 30 bytes? Big enough ✅ DONE! (don't check [20])

Return: 30-byte chunk immediately
Result: [10] → [15] → [20] → NULL
```

**Code:**

```c
void *first_fit(size_t size) {
    node_t *current = head;

    // Return FIRST suitable chunk
    while (current != NULL) {
        if (current->size >= size) {
            return allocate_from_chunk(current, size);
        }
        current = current->next;
    }

    return NULL;
}
```

**The Speed Advantage:**

```
Best/Worst Fit             First Fit
──────────────             ─────────
Always scan entire list    Stop at first match
O(n) every time           O(1) best case, O(n) worst
Slow 🐌                   Fast ⚡
```

**The Problem: List Pollution** 🗑️

```
Initial: [10] → [50] → [100] → NULL
Request: 5 bytes (repeatedly)

After many 5-byte allocations:
[5][5][5][5][5][5] → [50] → [100] → NULL
     ↓
Beginning of list fills with small chunks!
Now every allocation must scan past all these!
```

**The Solution: Address-Based Ordering** 🎯

**In plain English:** Keep the free list sorted by memory address (not insertion order). This enables coalescing and prevents beginning-of-list pollution.

```
Insertion-Ordered          Address-Ordered
─────────────────          ───────────────
[20@300] → [5@100]        [5@100] → [10@200] → [20@300]
→ [10@200] → NULL         → NULL
     ↓                         ↓
Random order              Sorted by address
Hard to coalesce          Easy to coalesce!
```

**Pros and Cons:**

```
✅ Pros                          ❌ Cons
───────                          ────────
Fast (stops early)               Can pollute list beginning
Simple implementation            May waste space
Good with address-ordering       Fragmentation varies
No exhaustive search
```

**Performance Comparison:**

```
Workload: 1000 allocations, random sizes

First Fit:     12ms   (stops at first match)
Best Fit:      47ms   (scans entire list)
Worst Fit:     49ms   (scans entire list)

Winner: First Fit ⚡
```

> **💡 Insight**
>
> First Fit demonstrates **satisficing vs. optimizing**—accepting "good enough" instead of searching for "perfect." This heuristic appears throughout computing:
> - **Caching**: Use first cache level that hits (don't search all levels)
> - **Load balancing**: Send request to first available server
> - **Compiler optimization**: Stop at first working register allocation
>
> Often, the cost of finding the "best" solution exceeds the benefit. First Fit exemplifies this pragmatic philosophy.

### 4.4. 🔄 Next Fit

**Strategy:** Like First Fit, but remember where you left off. Start searching from there next time.

**In plain English:** Imagine a circular parking lot 🎡. Instead of always entering from the same gate, remember where you parked last time and start looking from there. This spreads out the wear and tear!

**The Mechanism:**

```c
// Global state: remember last search position
node_t *last_searched = NULL;

void *next_fit(size_t size) {
    node_t *current = (last_searched != NULL) ? last_searched : head;
    node_t *start = current;  // Remember where we started

    // Search from last position
    do {
        if (current->size >= size) {
            last_searched = current->next;  // Remember for next time
            return allocate_from_chunk(current, size);
        }

        current = current->next;
        if (current == NULL) {
            current = head;  // Wrap around to beginning
        }
    } while (current != start);  // Full circle

    return NULL;
}
```

**Example Execution:**

```
Free list: [10@A] → [30@B] → [20@C] → [50@D] → NULL

Request 1: 15 bytes
───────────────────
Start: A (beginning)
Scan: A(10)❌ → B(30)✅
Return: B
last_searched = C

Request 2: 15 bytes
───────────────────
Start: C (continue from last)
Scan: C(20)✅
Return: C
last_searched = D

Request 3: 15 bytes
───────────────────
Start: D (continue from last)
Scan: D(50)✅
Return: D
last_searched = NULL (wrap around)

Request 4: 15 bytes
───────────────────
Start: A (wrapped around)
Scan: A(already used), B(already used), C(already used), D(already used)
Return: NULL
```

**Comparison with First Fit:**

```
First Fit Behavior        Next Fit Behavior
──────────────────        ─────────────────
Always start at head      Resume from last position
Pollutes beginning        Distributes allocations
[Used][Used][Used]→free   [Used]→[Used]→[Used]→free
     ↓                         ↓
Unbalanced                Balanced
```

**Pros and Cons:**

```
✅ Pros                          ❌ Cons
───────                          ────────
Spreads allocations evenly       More complex state
Avoids beginning pollution       Slightly slower than first fit
Similar performance overall      Fragmentation similar to first
```

**Performance:**

```
Benchmark: 10000 allocations

First Fit:  15ms,  27% fragmentation
Next Fit:   16ms,  26% fragmentation

Conclusion: Very similar! 📊
```

> **💡 Insight**
>
> Next Fit demonstrates **stateful algorithms**—using memory of past actions to improve future decisions. This pattern appears in:
> - **Elevator scheduling**: Remember direction (up/down), don't change frivolously
> - **Disk I/O scheduling**: Continue in current direction (SCAN algorithm)
> - **CPU scheduling**: Favor recently run processes (cache warmth)
>
> The trade-off: **Stateful = more complex but potentially more efficient**. Whether it's worth it depends on the workload.

### 4.5. 📊 Strategy Comparison

**Summary Table:**

| Strategy   | Search Cost | Fragmentation | Notes                    |
|-----------|-------------|---------------|--------------------------|
| Best Fit  | O(n) 🐌     | Medium 🟡     | Tiny slivers problem     |
| Worst Fit | O(n) 🐌     | High 🔴       | Poor empirical results   |
| First Fit | O(n) ⚡     | Low-Medium 🟢 | Fast, popular            |
| Next Fit  | O(n) ⚡     | Low-Medium 🟢 | Like first fit, rotates  |

**Example Workload:**

```
Free List: [10] → [30] → [20] → [50] → NULL
Requests: [15] [12] [25] [8]

Best Fit Results:
─────────────────
[15] → 20 (waste 5)
[12] → 30 (waste 18) → now [18] free
[25] → 50 (waste 25) → now [25] free
[8]  → 10 (waste 2)  → now [2] free
Final: [2] → [18] → [25] → NULL (lots of small chunks!)

First Fit Results:
──────────────────
[15] → 30 (waste 15) → now [15] free
[12] → 15 (waste 3)  → now [3] free
[25] → 50 (waste 25) → now [25] free
[8]  → 20 (waste 12) → now [12] free
Final: [10] → [3] → [12] → [25] → NULL (varied sizes)
```

**When to Use Which:**

```
Use Best Fit If:
────────────────
✅ Allocation sizes are predictable
✅ Speed is not critical
✅ You want minimum waste per allocation

Use First Fit If:
─────────────────
✅ Speed matters (real-time systems)
✅ Workload is unpredictable
✅ You use address-ordered lists

Use Next Fit If:
────────────────
✅ Similar to first fit needs
✅ Want to avoid beginning pollution
✅ Circular fairness matters
```

> **💡 Insight**
>
> The strategy comparison reveals a fundamental truth: **There is no universal "best" algorithm**. Performance depends on:
> - **Workload characteristics** (size distribution, allocation/free patterns)
> - **Implementation details** (list ordering, coalescing strategy)
> - **System constraints** (real-time deadlines, memory pressure)
>
> This is why modern allocators use **hybrid approaches**—different strategies for different size classes. Understanding the trade-offs lets you choose wisely.

---

## 5. 🚀 Advanced Approaches

Basic strategies (best/first/worst fit) work but have limitations. Let's explore sophisticated techniques used in production allocators.

### 5.1. 🗂️ Segregated Lists

**In plain English:** Instead of one free list holding all sizes, maintain separate lists for different size classes—like organizing a toolbox 🧰 with separate compartments for screws, nails, and bolts instead of dumping everything in one drawer.

**The Concept:**

```
Traditional Single Free List:
─────────────────────────────
head → [8] → [512] → [16] → [128] → [32] → [1024] → NULL
            ↓
    Must scan through all sizes

Segregated Lists:
─────────────────
Small (8-16):     [8] → [16] → [12] → NULL
Medium (32-128):  [32] → [128] → [64] → NULL
Large (256+):     [512] → [1024] → [256] → NULL
    ↓
Search only relevant size class! ⚡
```

**Implementation:**

```c
#define NUM_SIZE_CLASSES 10

typedef struct {
    node_t *free_lists[NUM_SIZE_CLASSES];
} segregated_allocator_t;

// Size classes (powers of 2)
// [0]: 8-16 bytes
// [1]: 17-32 bytes
// [2]: 33-64 bytes
// [3]: 65-128 bytes
// ...

int get_size_class(size_t size) {
    // Which list should this size use?
    if (size <= 16)   return 0;
    if (size <= 32)   return 1;
    if (size <= 64)   return 2;
    if (size <= 128)  return 3;
    // ... and so on
}

void *segregated_malloc(size_t size) {
    int class = get_size_class(size);
    node_t *list = free_lists[class];

    // Quick allocation from appropriate list
    if (list != NULL) {
        return allocate_from_chunk(list, size);
    }

    // No chunks in this class, try larger classes
    for (int i = class + 1; i < NUM_SIZE_CLASSES; i++) {
        if (free_lists[i] != NULL) {
            return allocate_from_chunk(free_lists[i], size);
        }
    }

    return NULL;  // Out of memory
}
```

**Benefits:**

```
Single List                  Segregated Lists
───────────                  ────────────────
Search all sizes            Search one size class ⚡
Fragmentation varies        Predictable fragmentation
Cache unfriendly            Cache friendly 💾
O(n) search                 O(1) for exact size match
```

**The Slab Allocator:** 🎯

**In plain English:** Pre-allocate full "slabs" (pages) of commonly-used object sizes. For example, if your kernel frequently allocates 64-byte locks 🔒, dedicate entire pages to 64-byte chunks.

**Example: Solaris Kernel Slab Allocator**

```
Object Caches (one per common type)
────────────────────────────────────

Lock Cache (64 bytes each):
┌────────────────────────────────┐
│ [Lock][Lock][Lock]...[Lock]    │ ← Slab 1 (4KB page)
│ [Lock][Lock][Free]...[Free]    │ ← Slab 2 (4KB page)
└────────────────────────────────┘

Inode Cache (256 bytes each):
┌────────────────────────────────┐
│ [Inode][Inode][Inode][Inode]   │ ← Slab 1 (4KB page)
│ [Free][Free][Free][Free]       │ ← Slab 2 (4KB page)
└────────────────────────────────┘

Process Cache (512 bytes each):
┌────────────────────────────────┐
│ [Proc][Proc][Proc][Proc]       │ ← Slab 1 (4KB page)
│ [Proc][Proc][Free][Free]       │ ← Slab 2 (4KB page)
└────────────────────────────────┘
```

**Key Innovation: Object Reuse** ♻️

```c
// Normal allocation
void *ptr = malloc(sizeof(struct lock));
initialize_lock(ptr);  // Set up initial state
use_lock(ptr);
free(ptr);             // Destructor tears down state

// Next allocation
void *ptr2 = malloc(sizeof(struct lock));
initialize_lock(ptr2); // Reinitialize! ⚠️ Overhead!
```

**Slab allocator optimization:**

```c
// Slab keeps freed objects INITIALIZED!
void *ptr = slab_alloc(lock_cache);
// ptr is ALREADY initialized from last use! ⚡
use_lock(ptr);
slab_free(lock_cache, ptr);
// Object stays initialized on free list

// Next allocation
void *ptr2 = slab_alloc(lock_cache);
// ptr2 is pre-initialized, ZERO overhead! 🎉
```

**Benefits of Slab Allocator:**

```
✅ Zero fragmentation (fixed size objects)
✅ Fast allocation/free (O(1) pop/push)
✅ Cache-friendly (objects reused = warm cache)
✅ Avoids initialization overhead
✅ Returns memory to OS when pressure high
```

**Allocation Flow:**

```
Request: Allocate a lock
         ↓
┌────────────────────────────┐
│ Lock cache has free lock?  │
└────────┬──────────┬────────┘
        YES        NO
         ↓          ↓
    ┌────────┐  ┌──────────────┐
    │ Return │  │ Lock cache   │
    │ it! ⚡ │  │ requests new │
    └────────┘  │ slab from    │
                │ page allocator│
                └───────┬───────┘
                        ↓
                   ┌─────────┐
                   │ Return  │
                   │ object  │
                   │ from new│
                   │ slab    │
                   └─────────┘
```

> **💡 Insight**
>
> Segregated lists demonstrate **specialization for performance**. By tailoring the allocator to specific size classes, you gain:
> - **Speed** (search smaller lists)
> - **Predictability** (known fragmentation per class)
> - **Cache locality** (similar sizes near each other)
>
> This pattern appears throughout high-performance systems:
> - **Thread pools**: Separate pools for different task types
> - **Database buffer pools**: Separate pools for different page sizes
> - **Network processing**: Separate queues for different packet priorities
>
> The trade-off: **Complexity for performance**. Is it worth it? For kernel allocators and high-performance servers, absolutely!

### 5.2. 🪓 Buddy Allocation

**In plain English:** Start with a large block (say 64KB). Need 7KB? Split the 64KB in half → 32KB. Still too big? Split again → 16KB. Keep splitting until you find a "good enough" size. When freeing, check if your "buddy" (the other half from the same split) is also free. If so, merge them back together! This is like a recursive binary tree 🌳 of memory.

**The Mechanism:**

```
Initial: 64KB free block
────────────────────────

Request: 7KB
Step 1: 64KB too big, split in half
┌─────────────┬─────────────┐
│   32KB      │   32KB      │
└─────────────┴─────────────┘

Step 2: 32KB still too big, split again
┌──────┬──────┬─────────────┐
│ 16KB │ 16KB │   32KB      │
└──────┴──────┴─────────────┘

Step 3: 16KB still too big, split again
┌───┬───┬──────┬─────────────┐
│8KB│8KB│ 16KB │   32KB      │
└───┴───┴──────┴─────────────┘

Step 4: 8KB is acceptable (even though only need 7KB)
Allocate leftmost 8KB, mark as used
┌───┬───┬──────┬─────────────┐
│ U │8KB│ 16KB │   32KB      │  U = Used
└───┴───┴──────┴─────────────┘
```

**The Tree Representation:**

```
                 64KB
                /    \
             32KB    32KB
            /   \
         16KB   16KB
        /   \
      8KB   8KB
      [U]  [Free]

Legend:
[U]    = Used (7KB allocation)
[Free] = Available
```

**The Magic: Buddy Calculation** ✨

**How to find your buddy:**

```c
// Buddy address can be computed with XOR!
void *find_buddy(void *block, size_t size) {
    uintptr_t addr = (uintptr_t)block;
    uintptr_t buddy_addr = addr ^ size;
    return (void *)buddy_addr;
}
```

**Example:**

```
Block at address 0x1000, size 8KB (0x2000)
Buddy = 0x1000 ^ 0x2000 = 0x3000

Block at address 0x3000, size 8KB (0x2000)
Buddy = 0x3000 ^ 0x2000 = 0x1000

They're each other's buddies! 👯
```

**Coalescing Example:**

```
Initial state after 8KB allocation:
┌───┬───┬──────┬─────────────┐
│ U │8KB│ 16KB │   32KB      │
└───┴───┴──────┴─────────────┘

Free the 8KB block:
Step 1: Check buddy (next 8KB)
┌───┬───┬──────┬─────────────┐
│8KB│8KB│ 16KB │   32KB      │
└───┴───┴──────┴─────────────┘
Buddy is FREE! Coalesce → 16KB

Step 2: Check buddy of 16KB (next 16KB)
┌──────┬──────┬─────────────┐
│ 16KB │ 16KB │   32KB      │
└──────┴──────┴─────────────┘
Buddy is FREE! Coalesce → 32KB

Step 3: Check buddy of 32KB (next 32KB)
┌─────────────┬─────────────┐
│   32KB      │   32KB      │
└─────────────┴─────────────┘
Buddy is FREE! Coalesce → 64KB

Final: Back to original single 64KB block! 🎉
┌──────────────────────────────┐
│          64KB                │
└──────────────────────────────┘
```

**Implementation:**

```c
typedef struct buddy_block {
    size_t size;                  // Power of 2
    bool is_free;
    struct buddy_block *next;
} buddy_block_t;

void *buddy_alloc(size_t size) {
    // Round up to next power of 2
    size_t alloc_size = next_power_of_2(size);

    // Find block of this size (or larger)
    buddy_block_t *block = find_block(alloc_size);

    if (block == NULL) {
        return NULL;  // Out of memory
    }

    // Split until we get right size
    while (block->size > alloc_size) {
        block->size /= 2;  // Split in half

        // Create buddy
        buddy_block_t *buddy = (void *)block + block->size;
        buddy->size = block->size;
        buddy->is_free = true;
        add_to_free_list(buddy);
    }

    block->is_free = false;
    return (void *)block;
}

void buddy_free(void *ptr) {
    buddy_block_t *block = (buddy_block_t *)ptr;
    block->is_free = true;

    // Recursive coalescing
    while (1) {
        buddy_block_t *buddy = find_buddy(block, block->size);

        // Can we coalesce?
        if (buddy == NULL || !buddy->is_free || buddy->size != block->size) {
            break;  // Can't coalesce
        }

        // Merge with buddy
        if (buddy < block) {
            block = buddy;  // Use lower address as base
        }
        block->size *= 2;  // Double the size
        remove_from_free_list(buddy);
    }

    add_to_free_list(block);
}
```

**Pros and Cons:**

```
✅ Pros                          ❌ Cons
───────                          ────────
Fast coalescing (buddy calc)     Internal fragmentation! 😱
Simple recursive structure       (7KB request → 8KB allocation)
Easy to implement                Only power-of-2 sizes
Good for kernel allocators       Wastes space on odd sizes
O(log n) operations
```

**Internal Fragmentation Example:**

```
Request Sizes     Allocation     Waste
─────────────     ──────────     ─────
7KB       →       8KB            1KB (14%)
100KB     →       128KB          28KB (28%)
513KB     →       1024KB         511KB (50%!) 💸
```

**When to Use Buddy Allocation:**

```
✅ Good for:
- Kernel memory allocators (page-sized allocations)
- Systems with predictable power-of-2 sizes
- When fast coalescing is critical

❌ Bad for:
- Arbitrary user allocations
- Memory-constrained systems
- When every byte counts
```

> **💡 Insight**
>
> Buddy allocation demonstrates **algorithmic elegance through constraints**. By restricting to power-of-2 sizes, the algorithm gains:
> - **Simple buddy calculation** (XOR trick)
> - **Fast splitting/coalescing** (binary tree structure)
> - **No complex bookkeeping** (sizes are implicit in tree level)
>
> The cost is internal fragmentation. This trade-off—**simplicity and speed vs. space efficiency**—is fundamental to allocator design. Linux kernel's buddy allocator accepts this trade-off for page-level allocation, then uses slab allocators for sub-page objects.

### 5.3. 💡 Other Modern Ideas

**1. Advanced Data Structures** 🌲

**Problem:** Linked lists are slow (O(n) search)

**Solutions:**

```
Balanced Binary Trees         Splay Trees              Partially-Ordered Trees
────────────────────          ───────────              ───────────────────────
O(log n) insert/delete        Self-adjusting           Cache frequently used
Always balanced               Hot items → root          chunks at front
Red-black trees common        Adaptive to workload     Probabilistic ordering
```

**Example: Red-Black Tree Free List**

```c
typedef struct rb_node {
    size_t size;
    void *addr;
    struct rb_node *left, *right;
    bool is_red;  // Red-black tree color
} rb_node_t;

void *rb_malloc(size_t size) {
    // Search tree for best fit
    rb_node_t *node = rb_search_gte(root, size);  // O(log n)

    if (node != NULL) {
        rb_delete(root, node);  // O(log n)
        return split_chunk(node, size);
    }

    return NULL;
}
```

**2. Multiprocessor Scalability** 🖥️🖥️🖥️

**Problem:** Single global free list = lock contention with multiple CPUs

**Solution: Per-CPU Allocators**

```
Traditional (lock contention)       Per-CPU (no contention)
─────────────────────────           ───────────────────────
       Global Free List                   CPU 0: [Free List]
            🔒                            CPU 1: [Free List]
    CPU0 → [waits] ← CPU1               CPU 2: [Free List]
    CPU2 → [waits] ← CPU3               CPU 3: [Free List]
         Bottleneck! 😞                   No locks! 🎉
```

**Example: tcmalloc (Google's Thread-Caching Malloc)**

```
Per-Thread Cache                Central Free List
────────────────                ─────────────────
Thread 1: [Small objects]   →   [Large objects pool]
Thread 2: [Small objects]   →   [Shared when cache full]
Thread 3: [Small objects]   →   [Refill when cache empty]
     ↓
Fast path (no locks) ⚡
```

**Benefits:**

```
Single-threaded app:  Same performance
Multi-threaded app:   10-100x faster! 🚀
                      (no lock contention)
```

**3. hoard Allocator** 🏠

**Concept:** Blend per-thread caches with global heap

```c
// Each thread has local heap
typedef struct {
    void *blocks[NUM_SIZE_CLASSES];
    size_t usage;  // How full am I?
} thread_heap_t;

void *hoard_malloc(size_t size) {
    thread_heap_t *my_heap = get_thread_heap();

    // Fast path: allocate from thread-local heap
    void *ptr = allocate_from_heap(my_heap, size);

    if (ptr == NULL) {
        // Slow path: get more from global heap
        refill_from_global(my_heap);
        ptr = allocate_from_heap(my_heap, size);
    }

    return ptr;
}

void hoard_free(void *ptr) {
    thread_heap_t *heap = find_owning_heap(ptr);
    free_to_heap(heap, ptr);

    // If heap becomes too empty, return memory to global
    if (heap->usage < THRESHOLD) {
        return_to_global(heap);
    }
}
```

**4. jemalloc** 💎

**Used by:** Firefox, FreeBSD, Facebook

**Key ideas:**
- Multiple arenas (reduce contention)
- Size classes with run-based allocation
- Extensive profiling support

```
jemalloc Structure
──────────────────

Thread → Arena 0 ─┬─→ Small: [Runs of same size]
Thread → Arena 1 ─┤   Medium: [Segregated lists]
Thread → Arena 2 ─┘   Large: [Binary tree]
     ↓
Automatic load balancing
```

**5. Real-World Example: glibc malloc** 🔧

```
Size Ranges          Strategy
───────────          ────────
< 64 bytes      →    Fast bins (LIFO cache)
64-512 bytes    →    Small bins (size classes)
512KB-128KB     →    Large bins (tree-sorted)
> 128KB         →    mmap() (direct OS allocation)

Additional features:
- Thread-local caching
- Corruption detection (canaries)
- Automatic trimming (return to OS)
- Extensive statistics
```

> **💡 Insight**
>
> Modern allocators demonstrate **hybrid design**—combining multiple strategies:
> - **Fast path** (thread-local cache) for common case
> - **Slow path** (global heap) for edge cases
> - **Size-specific strategies** (different for 8 bytes vs. 1GB)
> - **Runtime adaptation** (profile and optimize)
>
> This is systems engineering at its finest: no single algorithm works best, so combine the strengths of many. The complexity is worth it for critical infrastructure like memory allocation.

---

## 6. 📝 Summary

**Key Takeaways:** 🎯

**1. The Core Problem** 🧩

```
Variable-Sized Allocation → External Fragmentation
                           ↓
                   Free space scattered
                   Total space sufficient
                   But no single large chunk
```

**2. Essential Mechanisms** 🔧

```
Splitting          Split large chunks into smaller pieces
Coalescing         Merge adjacent free chunks
Tracking           Headers store allocation size
Embedding          Free list lives in free space
Growing            Request more from OS (sbrk)
```

**3. Basic Strategies** 📊

| Strategy  | Speed  | Fragmentation | Use Case              |
|-----------|--------|---------------|-----------------------|
| Best Fit  | Slow   | Medium        | Predictable sizes     |
| Worst Fit | Slow   | High          | Avoid (poor results)  |
| First Fit | Fast   | Low-Medium    | General purpose ⭐    |
| Next Fit  | Fast   | Low-Medium    | Avoid list pollution  |

**4. Advanced Techniques** 🚀

```
Segregated Lists   →   Separate lists per size class
Slab Allocator     →   Pre-initialized object caches
Buddy Allocation   →   Power-of-2 recursive splitting
Per-CPU Heaps      →   Eliminate lock contention
Hybrid Approaches  →   Combine multiple strategies
```

**5. Trade-offs** ⚖️

```
Simplicity   ↔   Performance
Speed        ↔   Space Efficiency
Generality   ↔   Specialization
Single List  ↔   Multiple Lists
Fixed Size   ↔   Variable Size
```

**6. Real-World Impact** 💻

```
Every C/C++ program        →   Uses malloc/free
Every OS kernel            →   Manages physical memory
Every database             →   Allocates buffer pools
Every garbage collector    →   Builds on these principles
```

**Design Patterns You've Learned:**

```
🎯 Specialization for Performance
   → Different strategies for different sizes

♻️ Reuse Over Reinitialization
   → Slab allocator keeps objects ready

🔄 Lazy vs. Eager Operations
   → When to coalesce, when to split

📊 Data Structure Choice Matters
   → Lists vs. trees vs. bitmaps

⚡ Fast Path / Slow Path
   → Optimize common case, handle edge cases correctly
```

**What Makes a Good Allocator:** ✅

```
✅ Fast allocation/free (low latency)
✅ Low fragmentation (space efficient)
✅ Scalable (multi-core friendly)
✅ General purpose (any workload)
✅ Robust (detects corruption)
✅ Measurable (provides stats)

Spoiler: You can't have all six perfectly!
Must choose based on your workload 🎯
```

**The Fundamental Challenge:**

```
┌────────────────────────────────────────┐
│  The Impossible Triangle of Memory     │
│        Allocation                      │
│                                        │
│           Fast ⚡                      │
│          /    \                        │
│         /      \                       │
│        /        \                      │
│    Space        General                │
│  Efficient 💾   Purpose 🌐            │
│                                        │
│  Pick any two! (Can't have all three)  │
└────────────────────────────────────────┘
```

**What's Next:** 🚀

This chapter covered **user-level allocators** (`malloc/free`). Coming up:

- **Paging**: Fixed-size allocation (eliminates fragmentation!)
- **Virtual Memory**: How OS manages entire address spaces
- **Swapping**: Moving memory to disk when RAM is full
- **Page Replacement**: Which pages to evict under pressure

> **💡 Final Insight**
>
> Free-space management exemplifies a fundamental truth in systems design: **There are no perfect solutions, only trade-offs**. The "best" allocator depends entirely on:
> - **Workload** (what sizes, what patterns)
> - **Constraints** (speed, space, simplicity)
> - **Environment** (single-threaded, multi-core, embedded)
>
> Great engineers understand the options, measure real workloads, and choose wisely. You now have the tools to do exactly that! 🎓

---

**Previous:** [Chapter 11: TBD](chapter11.md) | **Next:** [Chapter 13: Paging Introduction](chapter13-paging-introduction.md)
