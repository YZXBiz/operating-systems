# 💿 Chapter 2: Hard Disk Drives

## Table of Contents

1. [Introduction](#1-introduction)
2. [The Hard Disk Interface](#2-the-hard-disk-interface)
   - 2.1. [Sector-Based Storage](#21-sector-based-storage)
   - 2.2. [The Unwritten Contract](#22-the-unwritten-contract)
3. [Hard Disk Geometry](#3-hard-disk-geometry)
   - 3.1. [Physical Components](#31-physical-components)
   - 3.2. [How Data is Organized](#32-how-data-is-organized)
4. [Understanding Disk Operations](#4-understanding-disk-operations)
   - 4.1. [Single Track: Rotational Delay](#41-single-track-rotational-delay)
   - 4.2. [Multiple Tracks: Seek Time](#42-multiple-tracks-seek-time)
   - 4.3. [The Complete I/O Picture](#43-the-complete-io-picture)
5. [Advanced Disk Features](#5-advanced-disk-features)
   - 5.1. [Track Skew](#51-track-skew)
   - 5.2. [Multi-Zoned Disks](#52-multi-zoned-disks)
   - 5.3. [Disk Cache](#53-disk-cache)
6. [Calculating I/O Performance](#6-calculating-io-performance)
   - 6.1. [The I/O Time Formula](#61-the-io-time-formula)
   - 6.2. [Dimensional Analysis](#62-dimensional-analysis)
   - 6.3. [Random vs Sequential Workloads](#63-random-vs-sequential-workloads)
7. [Disk Scheduling Algorithms](#7-disk-scheduling-algorithms)
   - 7.1. [SSTF: Shortest Seek Time First](#71-sstf-shortest-seek-time-first)
   - 7.2. [SCAN and C-SCAN (Elevator Algorithm)](#72-scan-and-c-scan-elevator-algorithm)
   - 7.3. [SPTF: Shortest Positioning Time First](#73-sptf-shortest-positioning-time-first)
   - 7.4. [Modern Scheduling Considerations](#74-modern-scheduling-considerations)
8. [Summary](#8-summary)

---

## 1. Introduction

**In plain English:** Hard disk drives are like massive record players that spin metal platters coated with magnetic material. A tiny arm with a read/write head swoops across the surface to find and access your data.

**In technical terms:** Hard disk drives (HDDs) have been the primary persistent storage medium in computer systems for decades. Understanding their mechanical operation is crucial for building efficient file systems.

**Why it matters:** The physical limitations of spinning disks - how fast they rotate, how quickly the arm can move - directly impact your system's performance. A file system that ignores these realities will be painfully slow.

> **💡 Insight**
>
> Modern SSDs have replaced HDDs in many systems, but understanding disk mechanics teaches fundamental lessons about latency, throughput, and the gap between sequential and random access patterns that apply to all storage systems.

**The Key Challenge:** How do we store and access data on a spinning magnetic disk efficiently, given the mechanical constraints of rotation and arm movement?

---

## 2. The Hard Disk Interface

### 2.1. Sector-Based Storage

**In plain English:** Think of a hard disk as a giant array of 512-byte boxes, numbered from 0 to billions. You can read or write any box by its number.

**In technical terms:** A hard disk presents a simple interface: a linear array of sectors (512-byte blocks), numbered from 0 to n-1. You can read or write sectors by their address.

**Key characteristics:**

- **Sector size:** 512 bytes (traditional standard)
- **Address space:** 0 to n-1 for a disk with n sectors
- **Multi-sector operations:** Possible (e.g., reading 4KB = 8 sectors at once)
- **Atomicity guarantee:** Only single 512-byte writes are atomic

⚠️ **Warning: Torn Writes**

If you're writing 8 sectors (4KB) and power fails mid-write, you might end up with only 3 sectors written. This is called a "torn write" and is why file systems need journaling or other recovery mechanisms.

```
Normal Write:              Torn Write (power loss):
Sector 100: [✓ Written]    Sector 100: [✓ Written]
Sector 101: [✓ Written]    Sector 101: [✓ Written]
Sector 102: [✓ Written]    Sector 102: [✗ Lost]
Sector 103: [✓ Written]    Sector 103: [✗ Lost]
```

### 2.2. The Unwritten Contract

**In plain English:** While the disk interface is simple (just sector numbers), there's an unspoken understanding: nearby sectors are faster to access than distant ones.

**In technical terms:** This "unwritten contract" includes two key assumptions:

1. **Locality:** Accessing sectors near each other (e.g., sector 100 then 101) is faster than jumping around (e.g., sector 100 then sector 50,000)
2. **Sequential superiority:** Reading consecutive sectors (sequential access) is dramatically faster than random access

**Why this matters:**

```
Sequential Read (Fast):        Random Read (Slow):
Read 100 → 101 → 102 → 103    Read 100 → 5000 → 200 → 8000
            ↓                              ↓
    One seek, one rotation         Multiple seeks + rotations
       ~6ms for 4KB                  ~24ms for same 4KB
```

The difference can be **100-300x** in performance between sequential and random access patterns!

---

## 3. Hard Disk Geometry

### 3.1. Physical Components

**In plain English:** A hard disk is like a stack of vinyl records spinning together, with a robotic arm that can swing across them to read data encoded in magnetic patterns.

**The main components:**

**🎵 Platter:** The spinning disk surface (like a record)
- Made of aluminum or glass
- Coated with thin magnetic layer
- Data persists even when powered off

**🔄 Spindle & Motor:** The rotation mechanism
- Spins all platters at constant speed
- Common speeds: 7,200 to 15,000 RPM
- Example: 10,000 RPM = one rotation every 6 milliseconds

**📍 Disk Head:** The reader/writer (like a record needle)
- Reads magnetic patterns (sensing existing data)
- Writes magnetic patterns (inducing changes)
- One head per platter surface
- Floats nanometers above the surface

**💪 Disk Arm:** The positioning mechanism
- Moves heads across the surface
- All heads move together (attached to single arm)
- Can position over any track

**Visual representation:**

```
                 Side View

    ┌──────────────────────────┐
    │      Disk Platter        │  ← Spinning surface
    └──────────────────────────┘
              ↑
              │  (nanometers gap)
              │
         ┌────┴────┐
         │  Head   │  ← Read/write head
         └────┬────┘
              │
         ─────┴───── ← Arm (moves left/right)
```

### 3.2. How Data is Organized

**In plain English:** Data is arranged in concentric circles (like tree rings) on each platter surface. Each circle is divided into pie-slice segments that hold individual sectors.

**The organizational hierarchy:**

**Track:** One concentric circle of sectors
- Thousands of tracks per surface
- Packed tightly together (hundreds per hair-width)
- Each track holds many sectors

**Surface:** One side of a platter
- Each platter has 2 surfaces (top and bottom)
- Each surface has its own head
- All surfaces together form the disk

**Cylinder:** All tracks at the same position on different surfaces
- Useful concept: data on same cylinder is quick to access
- No seek needed when moving between surfaces in same cylinder

```
Top View of Single Platter:

        Sector Numbers
         ┌─────┐
     11─┤  0  ├─1
    10─┤   •   ├─2      Track = one circle
    9─┤ Spindle ├─3     Sectors numbered around track
     8─┤   •   ├─4
      7─┤  6  ├─5
         └─────┘

Multi-Track View:

         Outer Track: Sectors 0-11
         Middle Track: Sectors 12-23
         Inner Track: Sectors 24-35
```

> **💡 Insight**
>
> The abstraction is clever: the OS sees a simple 1D array of sectors (0, 1, 2, 3...), but the disk internally maps this to a 3D space (platter number, track number, sector on track). This mapping is called the disk's geometry.

---

## 4. Understanding Disk Operations

### 4.1. Single Track: Rotational Delay

**In plain English:** Imagine you want to read sector 0, but the disk head is currently over sector 6. You have to wait for the disk to spin until sector 0 rotates under the head.

**In technical terms:** Rotational delay (or rotational latency) is the time spent waiting for the desired sector to rotate under the disk head.

**Example calculation:**

```
Current position: Sector 6
Desired sector: Sector 0
Disk: 12 sectors per track, 10,000 RPM

Step 1: Calculate time per rotation
  10,000 RPM = 10,000/60 = 166.67 rotations/second
  Time per rotation = 1/166.67 = 6 milliseconds

Step 2: Calculate sectors to rotate
  From 6 to 0: must rotate through sectors 7,8,9,10,11,0
  That's 6 sectors = half the track

Step 3: Calculate rotational delay
  6 sectors / 12 total × 6ms = 3ms rotational delay
```

**Best and worst cases:**

- **Best case:** Desired sector is right under the head (0ms delay)
- **Average case:** Half rotation needed (3ms for our example)
- **Worst case:** Just missed the sector, nearly full rotation (≈6ms)

⏱️ **For performance calculations, we typically use average rotational delay = half a rotation.**

### 4.2. Multiple Tracks: Seek Time

**In plain English:** If your data is on a different track (different concentric circle), the arm must physically swing across the disk surface to get there. This movement is called a seek.

**In technical terms:** A seek is the mechanical process of moving the disk arm to position the head over the correct track. Seeks are expensive - they're one of the slowest operations on a disk.

**The four phases of a seek:**

```
Phase 1: Acceleration          Phase 2: Coasting
  Arm speeds up                 Arm at full speed
     ↗                              →
    ↗                               →
   ↗                                →

Phase 3: Deceleration          Phase 4: Settling
  Arm slows down                Fine positioning
      →                               •
       ↘                           (precise)
        ↘
```

**Phase 4 (Settling) is critical:**
- Takes 0.5 to 2 milliseconds
- Must be precise - if the head is slightly off, you read the wrong track
- Like threading a needle while everything is spinning

**Example scenario:**

```
Current position: Inner track (sectors 24-35)
Request: Read sector 11 (outer track)

Time breakdown:
1. Seek: ~4ms (arm moves from inner to outer track)
2. Rotation: ~3ms (wait for sector 11 to come around)
3. Transfer: ~0.03ms (read the actual data)
Total: ~7ms

During the seek, the disk kept spinning!
So when we arrive at outer track, we might be at sector 9
and need to wait for sector 11.
```

**Visual representation:**

```
Before Seek:                After Seek:
   Track 0 (0-11)              Track 0 (0-11)
   Track 1 (12-23)             Track 1 (12-23)
   Track 2 (24-35) ← HEAD          HEAD → Track 2 (24-35)

The disk rotated ~3 sectors during the seek!
```

> **💡 Insight**
>
> The disk never stops spinning during seeks. This is why seek and rotation interact - by the time your arm arrives at the destination track, the platter has rotated, and you might have to wait for your sector to come around.

### 4.3. The Complete I/O Picture

**In plain English:** Every disk read/write has three steps: (1) move the arm to the right track, (2) wait for the right sector to rotate under the head, (3) read/write the data.

**The three components of I/O time:**

```
Complete I/O Operation:

    Seek           Rotation         Transfer
   (move arm)    (wait for spin)   (read data)
      ↓               ↓                 ↓
   ═══════       ▬▬▬▬▬▬▬         ─
   0----4ms      0----3ms        0-0.03ms

   Total I/O time = 4ms + 3ms + 0.03ms ≈ 7ms
```

**Formula:**

```
T_I/O = T_seek + T_rotation + T_transfer
```

**Why transfer time is (usually) negligible:**

```
Example: 4KB transfer at 125 MB/s

Transfer time = 4KB / 125MB/s
              = 0.004 MB / 125 MB/s
              = 0.000032 seconds
              = 0.032 milliseconds
              = 32 microseconds

Compare to:
  Seek: ~4,000 microseconds (4ms)
  Rotation: ~2,000 microseconds (2ms)
  Transfer: ~30 microseconds (0.03ms)
```

⚡ Transfer time is **100x faster** than seek or rotation for small requests!

**Exception:** For very large sequential reads (e.g., 100MB), transfer time dominates:

```
Large Sequential Read: 100MB

T_seek: 4ms (one-time cost)
T_rotation: 2ms (one-time cost)
T_transfer: 100MB / 125MB/s = 800ms (dominates!)

Total: 806ms ≈ 800ms (transfer is 99% of the time)
```

---

## 5. Advanced Disk Features

### 5.1. Track Skew

**In plain English:** When reading consecutive sectors that span across tracks, you need a tiny buffer time for the arm to move to the next track. Track skew offsets the sector numbering so sector 12 (first sector of track 1) isn't directly below sector 11 (last sector of track 0).

**The problem without track skew:**

```
Track 0: [..., sector 9, 10, 11]
                         ↓ (arm moves to next track)
Track 1: [12, 13, 14, ...]
         ↑
      missed it!

While the arm repositioned (even to an adjacent track),
the disk rotated, and sector 12 already passed by.
Now we wait a FULL rotation to read sector 12.
```

**The solution with track skew:**

```
Track 0: [..., sector 9, 10, 11]
                         ↓ (arm moves to next track)
Track 1: [XX, XX, 12, 13, 14, ...]
              ↑
         perfectly timed!

Sector 12 is offset by 2 positions (track skew = 2).
By the time the arm settles, sector 12 is just arriving.
```

**Visual with 3 tracks:**

```
Without Skew:               With Skew (offset=2):

Track 0: [0-11]            Track 0: [0-11]
Track 1: [12-23]           Track 1: [XX,XX,12-21,22,23]
Track 2: [24-35]           Track 2: [XX,XX,24-33,34,35]

Reading 11→12→13: slow    Reading 11→12→13: fast!
```

### 5.2. Multi-Zoned Disks

**In plain English:** The outer edge of a disk has more physical space than the inner circles, so manufacturers pack more sectors into outer tracks. The disk is divided into zones, where each zone has a consistent number of sectors per track.

**Why geometry matters:**

```
Outer tracks (more space):        Inner tracks (less space):
   Longer circumference              Shorter circumference
            ↓                                  ↓
    More sectors fit                   Fewer sectors fit
            ↓                                  ↓
   Higher data density                Lower data density
```

**Zone organization:**

```
Zone 3 (Outer): 400 sectors/track    }
Zone 3 (Outer): 400 sectors/track    } Outer zone
Zone 3 (Outer): 400 sectors/track    }

Zone 2 (Mid):   350 sectors/track    }
Zone 2 (Mid):   350 sectors/track    } Middle zone
Zone 2 (Mid):   350 sectors/track    }

Zone 1 (Inner): 300 sectors/track    }
Zone 1 (Inner): 300 sectors/track    } Inner zone
Zone 1 (Inner): 300 sectors/track    }
```

**Performance implications:**

- Outer zones have higher transfer rates (more data per rotation)
- Sequential reads on outer tracks are faster
- This is why SSDs advertise "up to X MB/s" - performance varies by zone

### 5.3. Disk Cache

**In plain English:** The disk has a small amount of fast memory (8-16 MB) where it can temporarily store data. This helps with both reads (can store ahead speculatively) and writes (can acknowledge quickly).

**Cache strategies for reads:**

```
Request: Read sector 100

Disk strategy:
1. Read sector 100 (as requested)
2. Also read sectors 101, 102, 103... (rest of track)
3. Store all in cache
4. Return sector 100 to OS

Future request: Read sector 101
  → Already in cache! Return immediately (no seek/rotation)
```

🚀 **This is called track buffering - incredibly effective for sequential reads.**

**Cache strategies for writes:**

**Write-back caching (fast but risky):**

```
OS: Write sector 100
Disk: "Done!" (actually just copied to cache)
      Will write to platter later

Risk: If power fails before platter write, data lost!
```

**Write-through caching (safe but slower):**

```
OS: Write sector 100
Disk: *Writes to platter*
      *Only then* "Done!"

Safe: Data is truly persistent before acknowledging
```

⚠️ **Write-back caching breaks ordering guarantees needed by file systems!**

Example problem:
```
File system: Write block A, then block B
             (B depends on A being written first)

With write-back:
  Disk says "A done!" (but A only in cache)
  Disk says "B done!" (B also in cache)
  *Power fails*
  Disk wrote B but not A → corruption!
```

This is why journaling file systems are essential with modern drives.

---

## 6. Calculating I/O Performance

### 6.1. The I/O Time Formula

**The foundation:**

```
T_I/O = T_seek + T_rotation + T_transfer

Where:
  T_seek: Time to move arm to correct track
  T_rotation: Time to wait for sector to rotate under head
  T_transfer: Time to read/write the data
```

**The I/O rate formula:**

```
R_I/O = Size_transfer / T_I/O

Example: 4KB transfer taking 6ms
R_I/O = 4KB / 6ms = 0.67 MB/s
```

**Typical values for a modern 10,000 RPM drive:**

```
Average seek time: 4-5ms
Average rotation: 3ms (half of 6ms rotation)
Transfer rate: 100-125 MB/s

For 4KB random read:
  T_seek: 4ms
  T_rotation: 3ms
  T_transfer: 4KB / 125MB/s = 0.03ms
  T_I/O: 7.03ms ≈ 7ms
  R_I/O: 4KB / 7ms = 0.57 MB/s
```

### 6.2. Dimensional Analysis

**In plain English:** Dimensional analysis is a technique from physics where you set up units so they cancel out correctly, and the answer "falls out" of the math. It's perfect for disk calculations.

**Example 1: RPM to milliseconds per rotation**

```
Problem: Disk spins at 10,000 RPM. How many milliseconds per rotation?

Setup: Start with what you want:
  Time (ms)
  ─────────
  1 Rotation

Build the equation by canceling units:

  Time (ms)      1 minute        60 seconds      1000 ms
  ─────────  =  ──────────── × ────────────  × ──────────
  1 Rotation    10,000 Rotations   1 minute      1 second

                (Rotation cancels)  (minute cancels) (second cancels)

Result: 60,000 ms / 10,000 = 6 ms per rotation
```

**Example 2: Transfer time calculation**

```
Problem: How long to transfer 512 KB at 100 MB/s?

Setup:
  Time (ms)      512 KB         1 MB         1 second     1000 ms
  ─────────  =  ────────  ×  ────────── × ────────── × ──────────
  1 Request     1 Request     1024 KB      100 MB       1 second

                              (KB cancels)  (MB cancels) (second cancels)

Result: (512 × 1000) / (1024 × 100) = 5 ms per request
```

📝 **The beauty:** If your units don't cancel to give you the answer's units, you know you made a mistake!

### 6.3. Random vs Sequential Workloads

**Two radically different performance profiles:**

**Real-world comparison: High-end vs Capacity drives**

```
                    Cheetah 15K        Barracuda
                  (Performance)       (Capacity)
─────────────────────────────────────────────────
Capacity              300 GB            1 TB
RPM                  15,000            7,200
Average Seek           4 ms             9 ms
Transfer Rate       125 MB/s          105 MB/s
Price              Expensive          Cheap
```

**Random workload (4KB reads):**

```
Cheetah calculation:
  T_seek: 4ms
  T_rotation: 2ms (15K RPM = 4ms/rotation, avg = 2ms)
  T_transfer: 4KB / 125MB/s = 0.03ms
  T_I/O: 6.03ms
  R_I/O: 4KB / 6.03ms = 0.66 MB/s

Barracuda calculation:
  T_seek: 9ms
  T_rotation: 4.2ms (7200 RPM = 8.3ms/rotation, avg = 4.15ms)
  T_transfer: 4KB / 105MB/s = 0.04ms
  T_I/O: 13.24ms
  R_I/O: 4KB / 13.24ms = 0.31 MB/s
```

**Performance: Cheetah is 2x faster on random reads** (0.66 vs 0.31 MB/s)

**Sequential workload (100 MB read):**

```
Cheetah calculation:
  T_seek: 4ms (one-time)
  T_rotation: 2ms (one-time)
  T_transfer: 100MB / 125MB/s = 800ms (dominates!)
  T_I/O: 806ms
  R_I/O: 100MB / 806ms = 124 MB/s (≈ peak transfer rate)

Barracuda calculation:
  T_seek: 9ms
  T_rotation: 4.2ms
  T_transfer: 100MB / 105MB/s = 952ms
  T_I/O: 965ms
  R_I/O: 100MB / 965ms = 104 MB/s (≈ peak transfer rate)
```

**Performance: Both drives approach peak transfer rate**

**The stunning comparison:**

```
Workload Type       Cheetah         Barracuda      Ratio
───────────────────────────────────────────────────────────
Random (4KB)        0.66 MB/s       0.31 MB/s      2x
Sequential (100MB)  124 MB/s        104 MB/s       1.2x

Improvement Factor: 188x            335x
(Sequential vs Random)
```

> **💡 Insight**
>
> The gap between random and sequential performance (188-335x) is MUCH larger than the gap between expensive and cheap drives (2x). This teaches us: **workload design matters more than hardware**.

🎯 **Golden Rule:** Always prefer sequential access patterns. The performance difference is not 10% or 50% - it's often 100-300x!

---

## 7. Disk Scheduling Algorithms

**In plain English:** When multiple programs request disk I/O, the OS must decide which request to handle next. Smart scheduling can dramatically improve performance by minimizing seek and rotation delays.

**The key insight:** Unlike CPU scheduling where we don't know how long a job will take, with disk scheduling we can estimate request time based on current head position, destination track, and rotation delay.

**Scheduling goal:** Follow the Shortest Job First (SJF) principle - handle the fastest requests first to minimize average wait time.

### 7.1. SSTF: Shortest Seek Time First

**In plain English:** Always handle the request closest to where the disk head is currently positioned. Like a taxi picking up the nearest passenger first.

**Algorithm:**

```
1. Look at current head position
2. From all pending requests, pick the one on the nearest track
3. Service that request
4. Repeat
```

**Example scenario:**

```
Current position: Inner track (sectors 24-35)
Pending requests: Sector 21 (middle track)
                  Sector 2 (outer track)

SSTF decision: Service sector 21 first (closer)
  → Seek to middle track
  → Wait for rotation to sector 21
  → Read sector 21
  → Then seek to outer track for sector 2
```

**Visual:**

```
Outer track:    [0 ── 11]         Request: sector 2
                                       ↑
Middle track:   [12 ── 23]        Request: sector 21
                                       ↑
Inner track:    [24 ── 35]        Head currently here
                         ↑

SSTF path: Inner → Middle → Outer
           (shortest seeks first)
```

**Advantages:**
- ✅ Reduces average seek time
- ✅ Simple to understand and implement

**Problems:**

**Problem 1: Geometric information unavailable**

The OS sees sectors as a 1D array (0, 1, 2, 3...) but doesn't know which sectors are on which tracks. Solution: Use **Nearest Block First (NBF)** - schedule the request with the nearest block address, which approximates SSTF.

**Problem 2: Starvation** ⚠️

```
Scenario:
  Head at inner track
  Constant stream of requests to inner track
  One request waiting for outer track

Result: Outer track request NEVER gets serviced!

Time:    0ms      100ms     200ms     300ms     400ms
Serviced: Inner   Inner     Inner     Inner     Inner
Waiting:  Outer   Outer     Outer     Outer     Outer (starving!)
```

This is the fundamental problem: **SSTF is greedy and unfair**.

### 7.2. SCAN and C-SCAN (Elevator Algorithm)

**In plain English:** Instead of always picking the closest request, sweep back and forth across the disk like an elevator going up and down floors. Service all requests in your current direction before reversing.

**SCAN algorithm:**

```
1. Pick a direction (inner-to-outer or outer-to-inner)
2. Move in that direction, servicing all requests you pass
3. When you reach the end, reverse direction
4. Repeat
```

**Example:**

```
Initial state:
  Head at track 1 (middle)
  Requests at tracks: 0, 2, 0, 2, 1, 2
  Direction: moving outward

SCAN execution:
  Sweep 1 (out): Service track 1 → track 2
  Sweep 2 (in):  Service track 2 → track 1 → track 0
  Sweep 3 (out): Service track 0 → track 1 → track 2
  ...continues...
```

**Visual:**

```
Time →
  ↓
  |  Outer [2] ← ← ←  ⬤  ← ← ← Request serviced
  |  Middle[1] ← ⬤ ←  ↑  ← ⬤ ←
  |  Inner [0]   ↑    ↑    ↑
  |              |    |    |
  |          Sweep  Sweep Sweep
  |           1→2   2→0   0→2
```

**Advantage: No starvation!** Every request eventually gets serviced when the sweep passes over it.

**SCAN variants:**

**F-SCAN (Freeze SCAN):**

```
When starting a sweep:
  1. Freeze the current queue
  2. Service only requests in frozen queue during this sweep
  3. New requests that arrive go into next queue
  4. Start new sweep with new queue

Benefit: Prevents newly arriving nearby requests from pushing
         far-away requests further back
```

**C-SCAN (Circular SCAN):**

```
Traditional SCAN:
  Outer → Inner → Outer → Inner

C-SCAN:
  Outer → Inner [reset] Outer → Inner [reset]
           ↓                      ↓
      Don't service        Don't service
      on return trip       on return trip
```

**Why C-SCAN is more fair:**

```
SCAN pattern:
Track:     Outer  Inner  Outer     (Middle serviced twice!)
            ↓      ↓      ↓
Service:    1x → 2x ← 1x

C-SCAN pattern:
Track:     Outer  Inner  Outer     (All serviced once per cycle)
            ↓      ↓      ↓
Service:    1x → 1x    1x →
```

Middle tracks get serviced twice per SCAN cycle (once in each direction), but only once per C-SCAN cycle - more fair!

🎯 **Elevator name origin:** Like an elevator that doesn't jump to floor 4 just because someone pressed it while you're going down from floor 10 to 1. You finish going down, THEN go up.

```
Bad elevator (like SSTF):
  You're on floor 10, going to floor 1
  Someone on floor 3 presses button for floor 4
  Elevator goes UP to floor 4 (it's closer!)
  😡 You're annoyed!

Good elevator (like SCAN):
  Continues down to floor 1
  Then goes up, servicing floor 4 on the way
  😊 Everyone's happy (no starvation)
```

### 7.3. SPTF: Shortest Positioning Time First

**In plain English:** Instead of only considering seek distance, consider BOTH seek time AND rotational delay to pick the truly fastest request. Sometimes it's faster to seek further if it means less waiting for rotation.

**The problem with SSTF/SCAN:**

```
Current position: Sector 30 (inner track)
Requests: Sector 16 (middle track) - closer seek
          Sector 8 (outer track) - farther seek

SSTF would pick sector 16 (closer track)
But is that actually faster?
```

**The answer: It depends on rotation!**

```
Scenario A: Slow rotation, fast seek
  Seek to middle (16): 1ms seek + 5ms rotation = 6ms
  Seek to outer (8):   2ms seek + 1ms rotation = 3ms
  Winner: Outer track (8) - even though seek is longer!

Scenario B: Fast rotation, slow seek
  Seek to middle (16): 3ms seek + 1ms rotation = 4ms
  Seek to outer (8):   6ms seek + 0.5ms rotation = 6.5ms
  Winner: Middle track (16) - seek distance matters more
```

**SPTF calculation:**

```
For each pending request:
  Estimate T_I/O = T_seek + T_rotation + T_transfer
  Pick request with minimum T_I/O

This requires knowing:
  - Current head position (track AND rotational position)
  - Track boundaries
  - Rotational speed
```

**Implementation challenge for OS:**

The OS typically doesn't know:
- Exact track boundaries (disk presents as linear sectors)
- Current rotational position of the platter
- Internal disk geometry

**Solution: Disk-level scheduling** 🔧

```
Modern approach:

OS level:
  - OS picks ~16 "good" requests (using SCAN/NBF)
  - Issues all 16 to disk drive

Disk level:
  - Disk knows exact head position and geometry
  - Disk reorders the 16 requests using true SPTF
  - Services them in optimal order
```

This hybrid approach gets the best of both worlds!

> **💡 Insight**
>
> As disks became more complex (variable sectors per track, track skew, caching), the disk controller gained more knowledge than the OS. Scheduling moved from pure OS control to cooperation between OS and drive firmware.

### 7.4. Modern Scheduling Considerations

**Multiple outstanding requests:**

```
Old disks (1990s):
  OS → Request 1 → Disk
       *Wait for completion*
  OS → Request 2 → Disk
       *Wait for completion*

Modern disks:
  OS → Request 1, 2, 3, ..., 16 → Disk
       (Disk has queue of 16+ requests)
       Disk reorders using SPTF internally
```

**I/O merging** 🔄

```
Request queue:
  Read sector 33
  Read sector 8
  Read sector 34

Scheduler merges:
  Read sector 8
  Read sectors 33-34 (merged into single 2-sector request!)

Benefits:
  - Fewer requests → less overhead
  - Better scheduling decisions
  - More efficient transfers
```

**Work-conserving vs Anticipatory scheduling:**

**Work-conserving (traditional):**

```
If request available → Issue immediately
Never let disk go idle
```

**Anticipatory (sometimes better):**

```
Even if request available → Wait a few milliseconds
Reason: A better request might arrive soon

Example:
  Process A: Read sector 100
  *Disk could issue immediately*
  *But waits 2ms*
  Process A: Read sector 101 (arrives!)
  *Disk issues merged request for 100-101*

Result: One seek instead of two!
```

⚠️ **Anticipatory scheduling trades latency for throughput:**

```
Work-conserving:      Anticipatory:
  Fast response         Wait before responding
  Lower throughput      Higher throughput
  Simple                Complex (when to wait? how long?)
```

The Linux kernel implements anticipatory scheduling with heuristics about process behavior.

**Where scheduling happens today:**

```
Traditional model:     Modern model:

Application            Application
     ↓                      ↓
  OS (schedules)       OS (coarse scheduling)
     ↓                      ↓
  Disk (executes)      Disk (fine scheduling + reordering)
                           ↓
                       Platter (executes)
```

The disk controller has become a sophisticated computer itself, with:
- CPU and memory
- Complex scheduling algorithms (true SPTF)
- Read-ahead and write-back caching
- Defect management and remapping

---

## 8. Summary

Hard disk drives are mechanical marvels that have served as the foundation of persistent storage for decades. Understanding their operation reveals why certain access patterns are fast and others painfully slow.

**Key takeaways:**

🎯 **Interface:** Disks present a simple sector-based interface (numbered blocks) but have complex mechanical operation underneath.

⚙️ **Components:** Platters spin at high RPM, heads read/write magnetic patterns, and an arm seeks across tracks. All coordinated with nanometer precision.

⏱️ **Performance model:**
```
T_I/O = T_seek + T_rotation + T_transfer

Where:
  - Seek and rotation dominate for small random I/O
  - Transfer dominates for large sequential I/O
```

🚀 **Sequential vs Random:** The most important lesson is the massive gap in performance:
- Sequential: ~100-125 MB/s (approaching transfer rate)
- Random: ~0.3-0.7 MB/s (100-300x slower!)

📋 **Scheduling algorithms:**
- **SSTF:** Minimize seeks but risks starvation
- **SCAN/C-SCAN:** Sweep across disk, prevents starvation
- **SPTF:** Consider both seek and rotation (disk-level implementation)
- **Modern:** Hybrid OS + disk-level scheduling with anticipation

🔧 **Advanced features:**
- Track skew enables efficient sequential access across track boundaries
- Multi-zone design packs more sectors on outer tracks
- Disk cache speeds up reads and enables write buffering

**Design implications:**

For file systems:
- Organize data to maximize sequential access
- Group related data on nearby sectors/tracks
- Consider mechanical costs in allocation decisions

For applications:
- Batch I/O requests when possible
- Access data sequentially whenever you can
- Use larger I/O sizes (amortize seek/rotation costs)

For system designers:
- Sequential access is 100-300x faster - design for it!
- Scheduling matters - the OS can dramatically improve I/O throughput
- Understand workload: random vs sequential dictates performance

**The future:** While SSDs have replaced HDDs in many systems, the lessons learned from disk mechanics - latency sensitivity, sequential vs random access patterns, I/O scheduling - remain relevant across all storage technologies.

---

**Previous:** [Chapter 1: I/O Devices](chapter1-io-devices.md) | **Next:** [Chapter 3: Redundant Arrays of Inexpensive Disks (RAID)](chapter3-raid.md)
