# 🔒 Chapter 11: Data Integrity and Protection

**In plain English:** Hard drives occasionally mess up - bits get flipped, blocks get corrupted, or data lands in the wrong place. Your storage system needs to detect these errors and recover from them, or you'll lose data without even knowing it.

**In technical terms:** Data integrity mechanisms use checksums, redundancy, and verification protocols to detect and recover from silent data corruption, latent sector errors, and other partial disk failures that occur in modern storage devices.

**Why it matters:** Unlike total disk failures (which are obvious), silent corruption is insidious - the disk returns bad data without warning. Without integrity protection, you might retrieve corrupted financial records, broken photos, or damaged code without any indication something went wrong.

---

## Table of Contents

1. [Introduction: Beyond RAID](#1-introduction-beyond-raid)
2. [Disk Failure Modes](#2-disk-failure-modes)
   - 2.1. [The Fail-Stop vs. Fail-Partial Model](#21-the-fail-stop-vs-fail-partial-model)
   - 2.2. [Latent Sector Errors (LSEs)](#22-latent-sector-errors-lses)
   - 2.3. [Silent Corruption](#23-silent-corruption)
   - 2.4. [Frequency and Statistics](#24-frequency-and-statistics)
3. [Handling Latent Sector Errors](#3-handling-latent-sector-errors)
   - 3.1. [Detection and Recovery](#31-detection-and-recovery)
   - 3.2. [RAID Reconstruction Problem](#32-raid-reconstruction-problem)
   - 3.3. [RAID-DP: Dual Parity Solution](#33-raid-dp-dual-parity-solution)
4. [Detecting Corruption: The Checksum](#4-detecting-corruption-the-checksum)
   - 4.1. [What is a Checksum?](#41-what-is-a-checksum)
   - 4.2. [Common Checksum Functions](#42-common-checksum-functions)
   - 4.3. [XOR Checksums](#43-xor-checksums)
   - 4.4. [Addition Checksums](#44-addition-checksums)
   - 4.5. [Fletcher Checksum](#45-fletcher-checksum)
   - 4.6. [Cyclic Redundancy Check (CRC)](#46-cyclic-redundancy-check-crc)
   - 4.7. [Collisions and Tradeoffs](#47-collisions-and-tradeoffs)
5. [Checksum Layout](#5-checksum-layout)
   - 5.1. [Per-Sector Layout](#51-per-sector-layout)
   - 5.2. [520-Byte Sectors](#52-520-byte-sectors)
   - 5.3. [Packed Checksum Layout](#53-packed-checksum-layout)
6. [Using Checksums](#6-using-checksums)
   - 6.1. [Read Verification Process](#61-read-verification-process)
   - 6.2. [Write Process](#62-write-process)
   - 6.3. [What to Do on Corruption](#63-what-to-do-on-corruption)
7. [Misdirected Writes](#7-misdirected-writes)
   - 7.1. [The Problem](#71-the-problem)
   - 7.2. [Physical Identifier Solution](#72-physical-identifier-solution)
   - 7.3. [Enhanced Checksum Layout](#73-enhanced-checksum-layout)
8. [Lost Writes](#8-lost-writes)
   - 8.1. [The Lost Write Problem](#81-the-lost-write-problem)
   - 8.2. [Write Verify Solution](#82-write-verify-solution)
   - 8.3. [Checksum-in-Inode Solution](#83-checksum-in-inode-solution)
9. [Disk Scrubbing](#9-disk-scrubbing)
   - 9.1. [The Bit Rot Problem](#91-the-bit-rot-problem)
   - 9.2. [How Scrubbing Works](#92-how-scrubbing-works)
   - 9.3. [Scheduling Strategies](#93-scheduling-strategies)
10. [Overheads of Checksumming](#10-overheads-of-checksumming)
    - 10.1. [Space Overhead](#101-space-overhead)
    - 10.2. [Time Overhead](#102-time-overhead)
    - 10.3. [Optimization Techniques](#103-optimization-techniques)
11. [Summary](#11-summary)

---

## 1. Introduction: Beyond RAID

**In plain English:** You've learned about RAID protecting against entire disk failures. But what happens when the disk seems to work fine, yet occasionally returns garbage? This chapter tackles that harder problem.

RAID systems traditionally assumed simple **fail-stop** behavior: disks either work perfectly or die completely. Reality is messier.

**Modern disks exhibit partial failures:**
- Individual sectors become unreadable (latent sector errors)
- Data gets corrupted without detection (silent corruption)
- Blocks land in wrong locations (misdirected writes)
- Write operations report success but never persist (lost writes)

**The core challenge:**

```
Traditional model:        Reality:
  ┌─────────┐              ┌─────────┐
  │ Working │              │ Working │
  │  Disk   │              │  Disk   │  ← But block 42,719 is corrupt
  │   ✓     │              │   ?     │  ← And sector 103 is unreadable
  └─────────┘              └─────────┘  ← And writes sometimes fail silently
      vs.                       vs.
  ┌─────────┐              ┌─────────┐
  │  Dead   │              │  Dead   │
  │  Disk   │              │  Disk   │
  │   ✗     │              │   ✗     │
  └─────────┘              └─────────┘
```

This chapter explores **data integrity mechanisms** that detect and recover from these partial, silent failures.

> **💡 Insight**
>
> The transition from fail-stop to fail-partial disk models mirrors the evolution of distributed systems. As systems scale (whether storage arrays or data centers), partial failures become the norm rather than the exception. Robust systems must assume components are "mostly working" rather than "perfect or dead."

---

## 2. Disk Failure Modes

### 2.1. The Fail-Stop vs. Fail-Partial Model

**Fail-Stop Model (Traditional):**

```
Disk states:
├─ Working: All operations succeed
└─ Failed: All operations fail (disk unresponsive)

Detection: Easy (disk doesn't respond)
RAID handling: Straightforward (rebuild from redundancy)
```

**Fail-Partial Model (Reality):**

```
Disk states:
├─ Working: Most operations succeed
├─ Partial failure: Some blocks inaccessible or corrupted
└─ Failed: Complete failure

Detection: Challenging (disk appears to work)
RAID handling: Complex (need to detect which blocks are bad)
```

### 2.2. Latent Sector Errors (LSEs)

**Definition:** Physical disk damage makes one or more sectors unreadable.

**Causes:**

1. **Head crash:** Disk head touches platter surface (shouldn't happen, but does)
   - Damages magnetic coating
   - Makes affected bits unreadable

2. **Cosmic rays:** High-energy particles flip bits
   - Rare for individual disks
   - Common across millions of drives

3. **Wear and degradation:** Physical media degrades over time

**Detection mechanism:**

```
Disk internal process:
1. Read raw bits from sector
2. Apply Error Correcting Code (ECC)
3. Try to reconstruct original data

Outcomes:
├─ Success: Return corrected data
├─ Uncorrectable: Return I/O error (LSE detected)
└─ Silent corruption: ECC passes but data wrong (worst case)
```

**In plain English:** The disk has built-in error correction (like spell-check), but sometimes the errors are so severe that spell-check gives up and says "I can't read this." That's an LSE.

> **⚠️ Important**
>
> LSEs are **detectable failures** - the disk knows something is wrong and reports an error. This makes them easier to handle than silent corruption, where the disk thinks everything is fine.

### 2.3. Silent Corruption

**Definition:** Data is corrupted but no error is reported.

**Common causes:**

1. **Buggy firmware:** Disk writes block to wrong location
   - Client asks for block 1000
   - Disk writes to block 1001
   - ECC checks pass (data itself is fine)
   - But wrong block is returned on read

2. **Faulty bus:** Data corrupted during transfer
   ```
   CPU → [Memory Bus] → [I/O Bus] → [Disk]
                ↑ Bit flips here

   Result: Disk stores corrupted data
   ECC: Passes (data is consistently corrupted)
   ```

3. **Misdirected writes:** Controller confusion
   - Multi-disk RAID system
   - Write intended for Disk 1, Block 500
   - Actually written to Disk 2, Block 500
   - No error reported

**Why it's insidious:**

```
Timeline:
T0: Write "ABC" to Block 100
    [Corruption occurs - becomes "XBC"]
    Disk reports: Success ✓

T1: Read Block 100
    Disk returns: "XBC"
    Disk reports: Success ✓

Application has no idea data is wrong!
```

**In plain English:** It's like asking someone to file a document, they put it in the wrong cabinet, and later when you ask for it, they confidently hand you the wrong file. No one realizes the mistake.

### 2.4. Frequency and Statistics

**Study scope:**
- ~3 years of observation
- ~1.5 million disk drives
- Two categories: "Cheap" (SATA) vs. "Costly" (SCSI/FC)

**Key findings:**

```
Failure Type         Cheap Drives    Costly Drives
─────────────────────────────────────────────────
LSEs                    9.40%           1.40%
Corruption              0.50%           0.05%
```

**Interpreting these numbers:**

**In plain English:** In a data center with 10,000 cheap drives, expect ~940 drives to develop at least one unreadable sector over three years, and ~50 drives to have silent corruption.

**LSE patterns discovered:**

✅ **Age effects:**
- Error rates increase in year two
- Drives with one LSE likely to develop more

✅ **Capacity correlation:**
- Larger disks have more errors (more surface area to fail)

✅ **Locality:**
- **Spatial:** Errors cluster in nearby sectors
- **Temporal:** Multiple errors occur in bursts

✅ **Most drives have manageable error counts:**
- Typical: < 50 LSEs per affected drive
- But some drives develop many more

✅ **Disk scrubbing effectiveness:**
- Most LSEs discovered through proactive scanning
- Waiting for application access would miss many

**Corruption patterns:**

✅ **Model variation:**
- Huge differences between drive models
- Even within same "class" (SATA vs. SCSI)

✅ **Unpredictable:**
- Workload has little impact
- Disk size has little impact
- Age effects vary by model

✅ **Correlation:**
- Not independent (failures cluster)
- Weak correlation with LSEs
- Spatial locality exists

> **💡 Insight**
>
> The data reveals a sobering truth: partial disk failures are **common**, not rare. In large-scale systems, these failures are happening constantly. Any storage system managing thousands of drives must expect to encounter LSEs and corruption daily. Integrity protection isn't optional—it's essential.

---

## 3. Handling Latent Sector Errors

### 3.1. Detection and Recovery

**The good news:** LSEs are easy to handle because they're **detectable**.

**Basic recovery process:**

```
Read operation encounters LSE:

Step 1: Disk returns error code
        "Sector 42,719 unreadable"

Step 2: Storage system tries alternate source

        Mirrored RAID:
        └─ Read from mirror copy

        RAID-4/5 with parity:
        └─ Reconstruct from other blocks + parity

        No redundancy:
        └─ Return error to application (last resort)

Step 3: Optional - rewrite reconstructed data
        └─ May cause disk to remap bad sector
```

**In plain English:** LSEs are like a book with a torn-out page. You know it's missing, so you get a photocopy from the library (mirror) or reconstruct it from your notes (parity).

**Example: RAID-5 reconstruction:**

```
Goal: Read Block D₂ (has LSE)

Data blocks:   D₀   D₁   D₂   D₃
Values:       [A] [B]  [?]  [D]

Parity:        P = A ⊕ B ⊕ D₂ ⊕ D

Reconstruction:
D₂ = P ⊕ D₀ ⊕ D₁ ⊕ D₃
D₂ = P ⊕ A ⊕ B ⊕ D
D₂ = C  ← Recovered!
```

### 3.2. RAID Reconstruction Problem

**The nightmare scenario:** LSE discovered during RAID rebuild.

**Timeline of disaster:**

```
T₀: RAID-5 array with 4 data disks + 1 parity
    Disk₀ Disk₁ Disk₂ Disk₃ Parity
     [A]   [B]   [C]   [D]    [P]
    All healthy ✓

T₁: Disk₁ fails completely
    Disk₀ Disk₁ Disk₂ Disk₃ Parity
     [A]   [X]   [C]   [D]    [P]
    RAID degraded but functional

T₂: Begin reconstruction to hot spare
    Reading Disk₀... ✓
    Reading Disk₂... LSE! ✗

    Problem: Cannot reconstruct Disk₁ without all other disks
    Result: DATA LOSS
```

**In plain English:** You're copying pages from three books to recreate a lost fourth book. Midway through, you discover one of the three source books has a torn page. Now you can't recreate the corresponding page in the lost book.

**Why this matters:**

1. **Large disks = more LSEs:** As disk capacity grows, probability of LSE during rebuild increases
2. **Long rebuild times:** Multi-hour rebuilds check billions of sectors
3. **Heavy I/O stress:** Rebuild reads entire disk surface (stressful operation)

**Probability example:**

```
Scenario: 4TB drives, RAID-5 with 8 disks
- 1 disk fails (needs rebuild)
- Rebuild reads 7 × 4TB = 28TB of data
- LSE rate: ~9% of drives have at least one LSE

Question: What's the probability of LSE during rebuild?

With correlated failures (realistic):
→ Significant chance of hitting LSE
→ Potential data loss
```

### 3.3. RAID-DP: Dual Parity Solution

**NetApp's solution:** Add a second parity disk.

**Standard RAID-5:**

```
Data:   D₀  D₁  D₂  D₃
Parity:  P
```

**RAID-DP (Double Parity):**

```
Data:   D₀  D₁  D₂  D₃
Parity:  P   Q

Where:
  P = D₀ ⊕ D₁ ⊕ D₂ ⊕ D₃  (standard XOR parity)
  Q = different encoding (Reed-Solomon or similar)
```

**Recovery capability:**

```
Scenario 1: One disk fails
├─ Use P to reconstruct (same as RAID-5)
└─ Q provides backup

Scenario 2: One disk fails + LSE during rebuild
├─ P cannot reconstruct (missing data block with LSE)
├─ Use Q to reconstruct the LSE block
├─ Then use P to reconstruct failed disk
└─ Success! ✓

Scenario 3: Two disks fail simultaneously
├─ Use both P and Q to reconstruct
└─ Success! ✓
```

**The cost:**

**Space:** Two parity blocks instead of one

```
Storage efficiency:
RAID-5:  (N-1)/N  storage utilization
         8 disks = 87.5% efficient

RAID-DP: (N-2)/N  storage utilization
         8 disks = 75% efficient

Cost: ~12.5% more storage needed
```

**Performance:** Writing requires updating two parity blocks

```
Small write penalty:
RAID-5:  4 I/Os (read data, read P, write data, write P)
RAID-DP: 6 I/Os (read data, read P, read Q, write data, write P, write Q)
```

**NetApp WAFL mitigation:**

Log-structured design amortizes parity costs:
- Batches writes into full stripes
- Avoids small-write penalty
- Makes double parity more practical

> **💡 Insight**
>
> RAID-DP demonstrates a recurring pattern in reliable systems: **defense in depth**. One layer of protection (standard parity) handles common failures. A second layer (extra parity) handles rare but catastrophic combinations. The cost (storage, performance) is worth it to avoid data loss scenarios that single-parity RAID cannot survive.

---

## 4. Detecting Corruption: The Checksum

### 4.1. What is a Checksum?

**Definition:** A small summary value computed from data that enables corruption detection.

**In plain English:** A checksum is like a receipt that proves what should be in a box. If someone opens the box and puts different things inside, the receipt won't match the contents anymore.

**Basic concept:**

```
Writing:
  Data: [4KB block] → Checksum Function → [8-byte checksum]
  Store both data and checksum together

Reading:
  Retrieve data + stored checksum
  Recompute checksum over retrieved data
  Compare: stored checksum == computed checksum?

  ✓ Match:    Data probably intact
  ✗ Mismatch: Corruption detected!
```

**Example flow:**

```
T₀: Write data "HELLO WORLD"
    Compute: checksum("HELLO WORLD") = 0x4A2B
    Store: "HELLO WORLD" + 0x4A2B

T₁: Read data back
    Retrieved: "HELLO WORLD"
    Stored checksum: 0x4A2B
    Recompute: checksum("HELLO WORLD") = 0x4A2B
    Compare: 0x4A2B == 0x4A2B ✓
    Result: Data OK

T₂: Read data back (but corruption occurred)
    Retrieved: "HXLLO WORLD"  ← bit flipped
    Stored checksum: 0x4A2B
    Recompute: checksum("HXLLO WORLD") = 0x7C3D
    Compare: 0x4A2B != 0x7C3D ✗
    Result: CORRUPTION DETECTED
```

**Key insight:** Checksums enable detection without requiring multiple copies of data.

### 4.2. Common Checksum Functions

**The tradeoff spectrum:**

```
        Strength ←─────────────────────→ Speed
Stronger                                  Faster
(catches more errors)                     (cheaper to compute)

[Cryptographic]   [CRC]   [Fletcher]   [Addition]   [XOR]
    SHA-256        CRC-32     ✓            ✓          ✓
      ✓
```

**Choosing a checksum:**

- **Storage systems:** Usually CRC or Fletcher (good balance)
- **Networking:** Often CRC (standard in protocols)
- **Cryptographic security:** SHA, MD5 (but more expensive)
- **Simple protection:** XOR or addition (cheap but weaker)

> **⚠️ TNSTAAFL (There's No Such Thing As A Free Lunch)**
>
> Better protection = more CPU cost. Stronger checksums take longer to compute. Storage systems must balance corruption detection strength against performance overhead. Perfect protection is impossible—there's always a tradeoff.

### 4.3. XOR Checksums

**How it works:** XOR chunks of data together.

**Example: 16-byte data, 4-byte checksum**

**Data (hex):**
```
365e c4cd ba14 8a92 ecef 2c3a 40be f666
```

**Data (binary, grouped by 4 bytes):**
```
Row 0: 0011 0110 0101 1110 1100 0100 1100 1101
Row 1: 1011 1010 0001 0100 1000 1010 1001 0010
Row 2: 1110 1100 1110 1111 0010 1100 0011 1010
Row 3: 0100 0000 1011 1110 1111 0110 0110 0110
```

**XOR computation (column by column):**
```
       0011 0110 0101 1110 1100 0100 1100 1101
     ⊕ 1011 1010 0001 0100 1000 1010 1001 0010
     ⊕ 1110 1100 1110 1111 0010 1100 0011 1010
     ⊕ 0100 0000 1011 1110 1111 0110 0110 0110
     ─────────────────────────────────────────
       0010 0000 0001 1011 1001 0100 0000 0011
```

**Result (hex):** `0x201b9403`

**Strengths:**
- ✅ Fast to compute (single pass)
- ✅ Detects single-bit errors
- ✅ Simple to implement

**Weaknesses:**
- ❌ Multiple bit flips in same position across chunks → undetected
- ❌ Certain corruption patterns pass through

**Example of undetected corruption:**

```
Original:
  Chunk 1: 0101
  Chunk 2: 0011
  XOR:     0110 ✓

Corrupted:
  Chunk 1: 0111  ← bit 1 flipped
  Chunk 2: 0001  ← bit 1 flipped
  XOR:     0110  ← Same checksum!
```

### 4.4. Addition Checksums

**How it works:** Add all chunks together (2's complement), ignore overflow.

**Example:**

```c
uint32_t checksum_addition(uint8_t *data, size_t len) {
    uint32_t sum = 0;
    for (size_t i = 0; i < len; i += 4) {
        uint32_t chunk = *(uint32_t*)(data + i);
        sum += chunk;  // overflow ignored
    }
    return sum;
}
```

**Example calculation:**

```
Data:     0x365E  0xC4CD  0xBA14  0x8A92
Sum:      0x365E
        + 0xC4CD
        ──────────
          0xFB2B
        + 0xBA14
        ──────────
          0x1B53F   ← overflow
          ────
          0xB53F    ← keep low 16 bits
        + 0x8A92
        ──────────
          0x13FD1
          ────
          0x3FD1    ← Final checksum
```

**Strengths:**
- ✅ Very fast (single addition per chunk)
- ✅ Detects many common errors
- ✅ Low CPU overhead

**Weaknesses:**
- ❌ Doesn't catch bit-shifts well
- ❌ Order-dependent corruption undetected

**Example of undetected corruption:**

```
Original:
  0x0100 + 0x0002 = 0x0102 ✓

Shifted:
  0x0010 + 0x0020 = 0x0030  ← Different but undetected if we expect 0x0030

Problem: If data gets shifted but additions still work out, error missed
```

### 4.5. Fletcher Checksum

**Inventor:** John G. Fletcher

**How it works:** Computes two check values (s₁, s₂) that provide better error detection.

**Algorithm:**

```
Given data: d₁, d₂, d₃, ..., dₙ

s₁ = 0
s₂ = 0

For each byte dᵢ:
    s₁ = (s₁ + dᵢ) mod 255
    s₂ = (s₂ + s₁) mod 255

Checksum = (s₂ << 8) | s₁
```

**Why it's better:**

```
s₁: Simple sum (like addition checksum)
s₂: "Sum of sums" (weighted by position)

Result: Position-dependent
  → Catches reordering
  → Catches shifts
  → Catches multiple errors
```

**Example:**

```c
uint16_t fletcher16(uint8_t *data, size_t len) {
    uint16_t s1 = 0, s2 = 0;

    for (size_t i = 0; i < len; i++) {
        s1 = (s1 + data[i]) % 255;
        s2 = (s2 + s1) % 255;
    }

    return (s2 << 8) | s1;
}
```

**Detection capabilities:**
- ✅ All single-bit errors
- ✅ All double-bit errors
- ✅ Many burst errors
- ✅ Reordering of data

**Performance:** Slightly more expensive than simple addition, much cheaper than CRC.

**In plain English:** Fletcher is like checking your grocery receipt twice—once for the items, once for the running total. Errors are much harder to slip through both checks.

### 4.6. Cyclic Redundancy Check (CRC)

**How it works:** Treat data as a huge number, divide by a predetermined value (polynomial), keep remainder.

**Mathematical foundation:**

```
Data = D (binary number)
Divisor = k (agreed polynomial)

CRC = D mod k
```

**In plain English:** CRC is like a sophisticated hash function. The math ensures that even tiny changes in data produce completely different remainder values.

**Example (simplified):**

```
Data:     1101001010  (binary number)
Divisor:  1011        (polynomial)

Perform binary division:
  Remainder = 010  ← This is the CRC
```

**Properties:**

✅ **Excellent error detection:**
- Detects all single-bit errors
- Detects all double-bit errors
- Detects burst errors up to polynomial length
- Very low collision probability

✅ **Efficient implementation:**
- Clever algorithms make it fast
- Table-driven approaches
- Hardware support in many systems

✅ **Standardized:**
- CRC-32 (network protocols, Ethernet, ZIP)
- CRC-16 (Modbus, USB)
- CRC-CCITT (Bluetooth, X.25)

**Code example (simplified CRC-8):**

```c
uint8_t crc8(uint8_t *data, size_t len) {
    uint8_t crc = 0;

    for (size_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 0x80)
                crc = (crc << 1) ^ 0x07;  // polynomial
            else
                crc <<= 1;
        }
    }

    return crc;
}
```

**Real implementations use lookup tables for speed:**

```c
uint32_t crc32_fast(uint8_t *data, size_t len) {
    uint32_t crc = 0xFFFFFFFF;

    for (size_t i = 0; i < len; i++) {
        uint8_t index = (crc ^ data[i]) & 0xFF;
        crc = (crc >> 8) ^ crc_table[index];
    }

    return ~crc;
}
```

**Why CRC is popular:**

- Balance of strength and speed
- Well-understood mathematical properties
- Standardized across industries
- Hardware acceleration available

### 4.7. Collisions and Tradeoffs

**Fundamental limitation:** No checksum is perfect.

**Collision:** Two different data blocks with identical checksums.

**Why collisions are inevitable:**

```
Input space:  4KB data block = 4096 bytes = 32,768 bits
              Possible values: 2³²'⁷⁶⁸ (astronomical)

Output space: 8-byte checksum = 64 bits
              Possible values: 2⁶⁴ ≈ 18 quintillion

Result: Many inputs must map to same output (pigeonhole principle)
```

**In plain English:** You're summarizing an entire book (data) with a sentence (checksum). Different books will inevitably have the same summary.

**Example collision:**

```
Data block A: "The quick brown fox jumps over the lazy dog."
Data block B: "Pack my box with five dozen liquor jugs."

Hypothetically: checksum(A) = 0x4B7A9C2E
                checksum(B) = 0x4B7A9C2E  ← Collision!

Storage system cannot distinguish which is correct
```

**Collision probability:**

```
For CRC-32 (32-bit checksum):
  Random collision: ~1 in 4 billion

For CRC-64 (64-bit checksum):
  Random collision: ~1 in 18 quintillion

For SHA-256 (256-bit):
  Random collision: essentially impossible for random data
```

**Design implications:**

1. **Choose checksum size based on risk:**
   - More valuable data → larger checksum
   - Higher corruption rate → stronger algorithm

2. **Combine with other techniques:**
   - Checksums detect corruption
   - RAID provides recovery copies
   - Multiple layers of protection

3. **Accept imperfection:**
   - No checksum catches everything
   - Goal: Reduce corruption to acceptable level
   - "Acceptable" depends on application

> **💡 Insight**
>
> Checksum selection is about **risk management**, not perfection. A financial database might use SHA-256 despite performance cost. A video streaming server might use simple CRC-32 because occasional corruption is acceptable (one bad frame won't ruin the movie). Understanding your corruption tolerance informs checksum choice.

---

## 5. Checksum Layout

### 5.1. Per-Sector Layout

**Ideal layout:** Store checksum immediately adjacent to each data block.

**Without checksums:**

```
┌──────┬──────┬──────┬──────┬──────┬──────┬──────┐
│  D₀  │  D₁  │  D₂  │  D₃  │  D₄  │  D₅  │  D₆  │
└──────┴──────┴──────┴──────┴──────┴──────┴──────┘
512B   512B   512B   512B   512B   512B   512B
```

**With checksums:**

```
┌────┬──────┬────┬──────┬────┬──────┬────┬──────┐
│C[D₀│  D₀  │C[D₁│  D₁  │C[D₂│  D₂  │C[D₃│  D₃  │...
└────┴──────┴────┴──────┴────┴──────┴────┴──────┘
 8B   512B   8B   512B   8B   512B   8B   512B
```

**Advantages:**
- ✅ Checksum always with data (atomic reads)
- ✅ Simple to implement
- ✅ No extra reads needed

**Problem:** Disks write in 512-byte sectors. Where do the 8-byte checksums go?

### 5.2. 520-Byte Sectors

**Solution:** Format disks with larger sectors.

**Standard sector:** 512 bytes
**Extended sector:** 520 bytes (512 data + 8 checksum)

```
Physical sector layout:
┌────────────────────────────────┬──────────┐
│      512 bytes data            │ 8 bytes  │
│                                │ checksum │
└────────────────────────────────┴──────────┘
         User data                  Metadata
```

**How it works:**

1. **Disk formatting:** Low-level format creates 520-byte sectors
2. **OS perspective:** Sees 512-byte blocks (transparent)
3. **Disk firmware:** Automatically manages checksum field

**Advantages:**
- ✅ No space overhead from user perspective
- ✅ Atomic checksum updates
- ✅ Hardware-managed (no software complexity)

**Disadvantages:**
- ❌ Requires special disk formatting
- ❌ Not all disks support it
- ❌ Loses 8 bytes per sector (~1.5% capacity)

**Enterprise adoption:**

Many enterprise drives support 520-byte or 528-byte sectors:
- 520: 512 data + 8 metadata
- 528: 512 data + 16 metadata (more flexible)

### 5.3. Packed Checksum Layout

**For standard 512-byte sectors:** Group checksums into dedicated sectors.

**Layout:**

```
┌────────────────────────────────────────────┐
│  C[D₀] C[D₁] C[D₂] C[D₃] C[D₄] ... C[D₆₃] │  ← Checksum sector
├────────┬────────┬────────┬────────┬────────┤
│   D₀   │   D₁   │   D₂   │   D₃   │   D₄   │  ← Data sectors
├────────┼────────┼────────┼────────┼────────┤
│   D₅   │   D₆   │  ...   │  D₆₂   │  D₆₃   │
└────────┴────────┴────────┴────────┴────────┘
```

**Calculation:**

```
Checksum size: 8 bytes per block
Sector size: 512 bytes
Checksums per sector: 512 / 8 = 64

Layout: 1 checksum sector + 64 data sectors + ...
```

**Read operation:**

```
To read D₄:
1. Read checksum sector
2. Extract C[D₄] (byte offset 32-39)
3. Read data sector D₄
4. Compute checksum over D₄
5. Compare computed vs. stored
```

**Write operation (the inefficiency):**

```
To write D₄:
1. Read checksum sector      ← Extra read
2. Update C[D₄] in memory
3. Write checksum sector      ← Extra write
4. Write data sector D₄       ← Actual write

Total: 1 read + 2 writes (vs. 1 write without checksums)
```

**The problem:** Small writes become expensive.

```
Without checksums:
  Write 1 sector = 1 write

With packed checksums:
  Write 1 sector = 1 read + 2 writes
  Performance penalty: 3x I/O operations
```

**Optimization strategies:**

1. **Checksum caching:**
   ```
   Keep checksum sector in memory
   → Eliminates checksum read
   → Reduces to 2 writes
   ```

2. **Write coalescing:**
   ```
   Batch multiple updates
   → Update checksum sector once for multiple data writes
   → Amortizes overhead
   ```

3. **Log-structured approach:**
   ```
   Write data + checksum to new location
   → Avoids read-modify-write
   → Used by systems like ZFS
   ```

**Space overhead:**

```
Data: 64 sectors × 512 bytes = 32,768 bytes
Checksum: 1 sector × 512 bytes = 512 bytes

Overhead: 512 / 32,768 = 1.56%
```

> **💡 Insight**
>
> Layout decisions have cascading effects. The 520-byte sector approach is elegant but requires special hardware. The packed approach works on any disk but complicates software and hurts performance. Neither is universally better—the right choice depends on hardware capabilities and workload characteristics.

---

## 6. Using Checksums

### 6.1. Read Verification Process

**Complete read flow with integrity checking:**

```
Application: read(block_num)
       ↓
    ┌──────────────────────────┐
    │   File System            │
    │   Translates to sectors  │
    └──────────────────────────┘
       ↓
    ┌──────────────────────────┐
    │   Storage System         │
    │   1. Read data D         │
    │   2. Read checksum Cs[D] │ ← Stored checksum
    │   3. Compute Cc[D]       │ ← Computed checksum
    │   4. Compare Cs vs. Cc   │
    └──────────────────────────┘
       ↓
    ┌──────────────────────────┐
    │   Decision               │
    │                          │
    │   Cs[D] == Cc[D]?        │
    └──────────────────────────┘
       ↓              ↓
      YES            NO
       ↓              ↓
   Return data    Corruption!
                      ↓
                 Try recovery
```

**Step-by-step:**

**Step 1: Retrieve data and checksum**

```c
// Pseudo-code
bool read_with_integrity(int block_num, void *buffer) {
    // Read data block
    read_disk(block_num, buffer);

    // Read stored checksum
    uint32_t stored_checksum = read_checksum(block_num);

    // ... continue to step 2
}
```

**Step 2: Compute checksum over retrieved data**

```c
    // Compute checksum on retrieved data
    uint32_t computed_checksum = crc32(buffer, BLOCK_SIZE);
```

**Step 3: Compare**

```c
    // Verification
    if (stored_checksum == computed_checksum) {
        return true;  // Data OK
    } else {
        handle_corruption(block_num);  // Corruption detected!
        return false;
    }
}
```

**In plain English:** It's like checking a package's tracking number against the label. If they match, the package is correct. If they don't, something went wrong in delivery.

### 6.2. Write Process

**Complete write flow:**

```
Application: write(block_num, data)
       ↓
    ┌──────────────────────────┐
    │   Storage System         │
    │   1. Compute checksum    │ ← C[new_data]
    │   2. Write data          │
    │   3. Write checksum      │
    └──────────────────────────┘
       ↓
    ┌──────────────────────────┐
    │   Disk                   │
    │   Both persisted         │
    └──────────────────────────┘
```

**Implementation:**

```c
bool write_with_integrity(int block_num, void *data) {
    // 1. Compute checksum over new data
    uint32_t checksum = crc32(data, BLOCK_SIZE);

    // 2. Write data
    write_disk(block_num, data);

    // 3. Write checksum
    write_checksum(block_num, checksum);

    return true;
}
```

**Critical requirement: Atomicity**

```
Problem: What if power fails between writes?

Scenario 1: Data written, checksum not written
  Result: Next read will detect "corruption" (old checksum, new data)

Scenario 2: Checksum written, data not written
  Result: Next read will detect corruption (new checksum, old data)

Both cases: Detected but may cause spurious errors
```

**Solution strategies:**

1. **Write ordering:**
   ```
   1. Write new data
   2. Ensure data persisted (flush)
   3. Write new checksum

   Result: Old (data, checksum) or new (data, checksum)
           Never mismatched
   ```

2. **Transactional approach:**
   ```
   Use journaling or copy-on-write:
   - Prepare new (data, checksum) pair
   - Atomically switch pointer
   - Old version remains until commit
   ```

3. **Redundant verification:**
   ```
   Store multiple checksums at different levels:
   - Per-block checksum (catches disk corruption)
   - Per-file checksum in inode (catches lost writes)
   - End-to-end application checksum
   ```

### 6.3. What to Do on Corruption

**Detection is only half the battle. Now what?**

**Decision tree:**

```
Corruption detected
       ↓
  ┌──────────────┐
  │ Redundant    │
  │ copy exists? │
  └──────────────┘
    ↓           ↓
   YES          NO
    ↓           ↓
┌─────────┐  ┌─────────┐
│ Try     │  │ Return  │
│ alternate│  │ error   │
│ copy     │  │ to app  │
└─────────┘  └─────────┘
    ↓
┌─────────────┐
│ Alternate   │
│ copy OK?    │
└─────────────┘
    ↓       ↓
   YES      NO
    ↓       ↓
┌────────┐ ┌──────────┐
│Return  │ │All copies│
│data    │ │corrupted │
│        │ │→ ERROR   │
└────────┘ └──────────┘
    ↓
┌─────────────┐
│ (Optional)  │
│ Repair bad  │
│ copy        │
└─────────────┘
```

**Strategy 1: Try alternate copy (RAID systems)**

```c
bool read_with_recovery(int block_num, void *buffer) {
    // Try primary copy
    if (read_and_verify(DISK_0, block_num, buffer)) {
        return true;
    }

    // Primary corrupt, try mirror
    if (read_and_verify(DISK_1, block_num, buffer)) {
        // Success! Optionally repair primary
        write_disk(DISK_0, block_num, buffer);
        return true;
    }

    // Both copies corrupt - give up
    return false;
}
```

**Strategy 2: Reconstruct from parity (RAID-5/6)**

```c
bool read_with_parity_reconstruction(int block_num, void *buffer) {
    // Try direct read
    if (read_and_verify(block_num, buffer)) {
        return true;
    }

    // Corrupt - reconstruct from other blocks + parity
    void *parity = alloc_buffer();
    void *other_blocks[NUM_DISKS - 1];

    read_parity_group(block_num, other_blocks, parity);
    xor_reconstruct(other_blocks, parity, buffer);

    // Verify reconstruction
    if (verify_checksum(buffer)) {
        // Repair corrupted block
        write_disk(block_num, buffer);
        return true;
    }

    return false;
}
```

**Strategy 3: No redundancy - report error**

```c
bool read_without_redundancy(int block_num, void *buffer) {
    if (read_and_verify(block_num, buffer)) {
        return true;
    }

    // Corruption detected, no way to recover
    log_corruption(block_num);
    return -EIO;  // I/O error to application
}
```

**Application-level handling:**

```
Different applications tolerate errors differently:

Database:
  └─ Cannot tolerate corruption
  └─ Transaction aborted
  └─ Restore from backup

Video player:
  └─ Skip corrupted frame
  └─ Continue playback

File system check (fsck):
  └─ Mark corrupted blocks unusable
  └─ Attempt metadata reconstruction
```

**In plain English:** If your book has a torn page, you try to get a photocopy from the library (mirror). If that doesn't work, you reconstruct from study notes (parity). If nothing works, you admit the page is lost and handle it gracefully (error to application).

> **⚠️ Warning**
>
> **Never return corrupted data silently!** If corruption is detected but cannot be repaired, it's better to return an error than to give the application bad data. Silent corruption is worse than failure because applications make decisions based on incorrect information.

---

## 7. Misdirected Writes

### 7.1. The Problem

**Definition:** Data written to wrong location without any error indication.

**Scenario 1: Wrong sector on same disk**

```
Intended:
  Write "DATA" to Disk 0, Block 1000

What actually happened:
  Wrote "DATA" to Disk 0, Block 1001

Problem:
  ✓ Write successful (disk reports OK)
  ✓ Checksum matches (data itself is correct)
  ✗ Wrong location!
```

**Scenario 2: Wrong disk in RAID**

```
Intended:
  Write "DATA" to Disk 2, Block 500

What actually happened:
  Wrote "DATA" to Disk 3, Block 500

Problem:
  ✓ Write successful
  ✓ Checksum matches
  ✗ Wrong disk!
```

**Why basic checksums don't help:**

```
Read Block 1000:
  Retrieved data: "OLD_DATA" (what was originally there)
  Stored checksum: checksum("OLD_DATA")
  Computed checksum: checksum("OLD_DATA")
  Comparison: MATCH ✓

Everything looks fine!
  But "DATA" is lost in Block 1001
  And Block 1000 has stale data
```

**In plain English:** Imagine filing a document in cabinet 5 when it should go in cabinet 4. Later, when you open cabinet 4, you find the old document still there, looking perfectly fine. You don't realize anything went wrong.

**Root causes:**

1. **Buggy firmware:**
   - Address translation error
   - Controller confusion

2. **Cable/bus errors:**
   - Address bits flipped during transmission
   - Command corruption

3. **RAID controller bugs:**
   - Wrong disk selected
   - Incorrect stripe calculation

### 7.2. Physical Identifier Solution

**Enhancement:** Include location information in checksum metadata.

**Extended checksum structure:**

```
Standard:    [Checksum]
Enhanced:    [Checksum | Disk ID | Block Number]
```

**Example:**

```c
struct checksum_metadata {
    uint32_t checksum;     // CRC-32 over data
    uint16_t disk_id;      // Which disk
    uint64_t block_num;    // Which block
    uint16_t reserved;     // Future use
};  // Total: 16 bytes
```

**Write operation:**

```c
void write_with_physical_id(int disk, int block, void *data) {
    struct checksum_metadata meta;

    // 1. Compute checksum
    meta.checksum = crc32(data, BLOCK_SIZE);

    // 2. Record physical location
    meta.disk_id = disk;
    meta.block_num = block;

    // 3. Write both
    write_disk(disk, block, data);
    write_checksum(disk, block, &meta);
}
```

**Read verification:**

```c
bool read_with_physical_check(int disk, int block, void *data) {
    struct checksum_metadata meta;

    // Read data and metadata
    read_disk(disk, block, data);
    read_checksum(disk, block, &meta);

    // Check 1: Checksum
    if (crc32(data, BLOCK_SIZE) != meta.checksum) {
        log("Checksum mismatch");
        return false;
    }

    // Check 2: Physical location
    if (meta.disk_id != disk || meta.block_num != block) {
        log("Misdirected write detected! Expected D%d/B%d, got D%d/B%d",
            disk, block, meta.disk_id, meta.block_num);
        return false;
    }

    return true;
}
```

**Detection scenario:**

```
Write request: Disk 1, Block 1000, "DATA"
  ↓
Bug causes actual write to: Disk 1, Block 1001
  ↓
Stored metadata at Block 1001:
  checksum = checksum("DATA") ✓
  disk_id = 1 ✓
  block_num = 1000  ← Mismatch!

Later read of Block 1001:
  Expected: disk=1, block=1001
  Stored:   disk=1, block=1000
  Result: MISDIRECTED WRITE DETECTED ✗
```

### 7.3. Enhanced Checksum Layout

**Single-disk system:**

```
┌───────────────────────────────────────┐
│ Checksum | Disk | Block | Reserved   │ Data Block
├───────────────────────────────────────┤
│ 0xA3B2C1 │  0   │  100  │     0      │ [4KB data]
├───────────────────────────────────────┤
│ 0x7F3E2A │  0   │  101  │     0      │ [4KB data]
└───────────────────────────────────────┘
```

**Multi-disk RAID system:**

```
Disk 0:
┌───────────────────────────────────────┐
│ 0xA3B2C1 │  0   │  100  │     0      │ D₀,₁₀₀
├───────────────────────────────────────┤
│ 0x7F3E2A │  0   │  101  │     0      │ D₀,₁₀₁
└───────────────────────────────────────┘

Disk 1:
┌───────────────────────────────────────┐
│ 0x9C8B7A │  1   │  100  │     0      │ D₁,₁₀₀
├───────────────────────────────────────┤
│ 0x2D1E0F │  1   │  101  │     0      │ D₁,₁₀₁
└───────────────────────────────────────┘
```

**Now misdirected writes are caught:**

```
Scenario: Write to Disk 1, Block 100
          But actually written to Disk 0, Block 100

Stored at Disk 0, Block 100:
  checksum = checksum(new_data) ✓
  disk_id = 1  ← Says Disk 1
  block_num = 100 ✓

Read from Disk 0, Block 100:
  Expected: disk_id = 0
  Found: disk_id = 1

  MISMATCH! Misdirected write detected!
```

**Cost analysis:**

```
Standard checksum: 8 bytes
Enhanced metadata:  16 bytes

Overhead increase: 2x
Percentage of block: 16B / 4096B = 0.39%

Verdict: Tiny cost for significant protection
```

> **💡 Insight**
>
> Physical identifiers demonstrate the principle of **redundant verification**. The disk's internal addressing (which block the disk thinks it wrote) is checked against the file system's expectation (which block should be written). When reality doesn't match expectations, corruption is revealed. This redundancy costs almost nothing but catches an entire class of silent failures.

---

## 8. Lost Writes

### 8.1. The Lost Write Problem

**Definition:** Write operation reports success but data never persists.

**Timeline:**

```
T₀: Application writes "NEW_DATA" to Block 500
    Storage system: Acknowledged ✓

T₁: Power loss / crash

T₂: System restarts
    Read Block 500
    Retrieved: "OLD_DATA" (write never persisted)
```

**Why checksums don't detect it:**

```
Scenario: Lost write to Block 500

Block 500 still contains old data:
  Data: "OLD_DATA"
  Checksum: checksum("OLD_DATA")
  Physical ID: disk=0, block=500

Read verification:
  Computed checksum: checksum("OLD_DATA") ✓
  Matches stored: ✓
  Physical ID correct: ✓

  Everything checks out! But data is WRONG.
```

**The subtle difference:**

```
Corruption:       Data changed → Checksum mismatch
Misdirected:      Location wrong → Physical ID mismatch
Lost write:       Everything matches... but it's old data
                  ↑ Undetectable with previous techniques!
```

**In plain English:** You ask someone to update a file, they say "Done!", but they never actually did it. When you check later, the old version is there, perfectly intact with no signs of corruption. How do you know they forgot?

**Root causes:**

1. **Volatile write buffer:**
   - Disk acknowledges write when data hits buffer
   - Power loss before flush to platter
   - Buffer lost, old data remains

2. **Firmware bugs:**
   - Write command lost
   - Incorrect acknowledgment

3. **Write cache issues:**
   - Battery-backed cache fails
   - Write-back cache disabled incorrectly

### 8.2. Write Verify Solution

**Approach:** Read back immediately after write.

**Process:**

```c
bool write_verify(int block_num, void *data) {
    // 1. Write data
    write_disk(block_num, data);

    // 2. Immediately read back
    void *verify_buffer = alloc_buffer();
    read_disk(block_num, verify_buffer);

    // 3. Compare
    if (memcmp(data, verify_buffer, BLOCK_SIZE) == 0) {
        return true;  // Verified ✓
    } else {
        // Lost write detected!
        // Retry...
        return false;
    }
}
```

**Timeline:**

```
T₀: Write "NEW_DATA"
    ↓
T₁: Disk acknowledges (maybe in cache)
    ↓
T₂: Read back
    ↓
T₃: Compare write vs. read

If lost: Read returns "OLD_DATA" → Mismatch detected
If OK:   Read returns "NEW_DATA" → Success
```

**Advantages:**
- ✅ Catches lost writes reliably
- ✅ Simple to implement
- ✅ Works with any storage device

**Disadvantages:**
- ❌ **Performance penalty: 2x I/O operations**
  - Every write becomes write + read
  - Doubles latency
  - Halves write throughput

```
Without verify:  Write → Done
                 Time: ~5ms

With verify:     Write → Read → Compare → Done
                 Time: ~10ms

Throughput impact: 50% reduction in write performance
```

**Cost analysis:**

```
Workload: 50% reads, 50% writes

Without verify:
  Reads:  50 operations
  Writes: 50 operations
  Total:  100 I/O operations

With write-verify:
  Reads:  50 operations
  Writes: 50 operations
  Verify: 50 operations (one per write)
  Total:  150 I/O operations

Overhead: 50% more I/O
```

**When it's worth it:**
- Critical data (financial transactions, medical records)
- Unreliable hardware
- High-value small writes

**When it's not:**
- High-throughput systems
- Already using redundancy (RAID mirrors catch this differently)
- Low-value data

### 8.3. Checksum-in-Inode Solution

**ZFS approach:** Store checksums at multiple levels of hierarchy.

**File system structure:**

```
Inode (metadata)
  ├─ File attributes (size, permissions, etc.)
  ├─ Checksum for Block 0
  ├─ Checksum for Block 1
  ├─ Checksum for Block 2
  ├─ ...
  └─ Pointer to indirect block
       ├─ Checksum for Block N
       ├─ Checksum for Block N+1
       └─ ...

Each data block also has local checksum:
  [Checksum₀ | Data₀]
  [Checksum₁ | Data₁]
```

**Two-level verification:**

```
Read Block 0:

  Level 1: Check local checksum
    Stored in block: checksum₀
    Computed: checksum(data₀)
    Compare: checksum₀ == checksum(data₀)?

  Level 2: Check inode checksum
    Stored in inode: inode_checksum₀
    Computed: checksum(data₀)
    Compare: inode_checksum₀ == checksum(data₀)?
```

**How it catches lost writes:**

```
Scenario: Lost write to Block 0

Original state:
  Block 0 data: "OLD"
  Block 0 checksum: checksum("OLD")
  Inode checksum: checksum("OLD")
  All consistent ✓

Write "NEW" to Block 0:
  Target state:
    Block 0 data: "NEW"
    Block 0 checksum: checksum("NEW")  ← Should update
    Inode checksum: checksum("NEW")    ← Should update

Lost write scenario:
  Write to inode: Success (inode_checksum = checksum("NEW"))
  Write to block: Lost (block still contains "OLD")

Later read:
  Block checksum: checksum("OLD")
  Inode checksum: checksum("NEW")

  MISMATCH! Lost write detected!
```

**Critical property: Write ordering**

```
Write sequence for Block 0:

Option A (Safe):
  1. Write new data block
  2. Ensure persisted
  3. Write new inode
  ↑ If power fails before step 3:
    Old (data, inode_checksum) pair → Consistent
  ↑ If power fails after step 3:
    New (data, inode_checksum) pair → Consistent

Option B (Unsafe):
  1. Write new inode
  2. Write new data block
  ↑ If power fails between:
    New inode_checksum, old data → Inconsistent
```

**ZFS implementation:**

```
1. Write all data blocks (with checksums)
2. Flush to disk
3. Write indirect blocks (with checksums)
4. Flush to disk
5. Write inode (with checksums)
6. Flush to disk

Root → Indirect → Data  (top-down)
Each level checksums the level below
```

**Advantages:**
- ✅ No extra reads (no write-verify penalty)
- ✅ Catches lost writes
- ✅ Catches corruption at any level
- ✅ Provides data integrity AND metadata integrity

**The failure case:**

```
Only fails if BOTH writes lost:
  - Write to data block: Lost
  - Write to inode: Lost

Probability: (P_lost_write)²
             Very unlikely for independent failures
```

**In plain English:** It's like having two separate people verify your work. If your update gets lost, at least one person will notice the discrepancy between what they expect and what they see.

> **💡 Insight**
>
> The checksum-in-inode approach demonstrates **hierarchical verification**. By storing checksums at both the data level and metadata level, the system creates cross-checks that catch failures invisible to single-level verification. This is cheaper than write-verify (no extra reads) but requires more sophisticated data structures and careful write ordering.

---

## 9. Disk Scrubbing

### 9.1. The Bit Rot Problem

**The challenge:** Most data is written once, rarely read.

**Example statistics:**

```
Typical file system:
  10 TB storage
  5 TB used

  Access patterns:
  - 20% of files: Accessed daily (logs, databases)
  - 30% of files: Accessed weekly (documents)
  - 50% of files: Accessed rarely (archives, backups)
```

**Bit rot:**

```
T₀: Write file "archive_2020.tar"
    All checksums valid ✓

T₁ (1 year later):
    Cosmic ray flips bit in Block 42,719
    File not accessed → corruption undetected

T₂ (2 years later):
    Another bit flips
    Still not accessed

T₃ (3 years later):
    User finally accesses file
    CORRUPTION DETECTED!
    But now multiple blocks corrupted
    May exceed redundancy capacity
```

**In plain English:** Imagine storing books in a warehouse. If you never check on them, moisture and insects might damage dozens of books before you notice. By the time you need a book, it's ruined.

**The cascade problem:**

```
Single corruption:
  ├─ Checksum detects: ✓
  ├─ Mirror provides copy: ✓
  └─ Recovery: SUCCESS

Multiple corruptions before detection:
  ├─ Primary copy: Corrupted (Block 100)
  ├─ Mirror copy: Corrupted (Block 200)
  └─ Recovery: FAILURE (exceeded redundancy)
```

### 9.2. How Scrubbing Works

**Definition:** Proactive background scanning of all data.

**Process:**

```
Scrubbing thread:
  for each block in file_system:
      read block
      verify checksum
      if corrupted:
          attempt recovery
          repair if possible
          log error
      sleep(throttle_delay)  # Avoid overload
```

**Detailed flow:**

```
┌─────────────────────────────────────┐
│ Scrubber starts at Block 0          │
└─────────────────────────────────────┘
       ↓
┌─────────────────────────────────────┐
│ Read Block N                        │
│ Read Checksum[N]                    │
└─────────────────────────────────────┘
       ↓
┌─────────────────────────────────────┐
│ Compute checksum                    │
│ Compare with stored                 │
└─────────────────────────────────────┘
       ↓
    Match? ───→ YES → Next block
       ↓
       NO
       ↓
┌─────────────────────────────────────┐
│ CORRUPTION DETECTED                 │
│ - Log error                         │
│ - Read redundant copy               │
│ - Repair corrupted block            │
│ - Update checksum                   │
└─────────────────────────────────────┘
       ↓
   Next block
```

**Implementation example:**

```c
void disk_scrubber_thread() {
    uint64_t block_num = 0;
    uint64_t total_blocks = get_total_blocks();
    uint64_t errors_found = 0;

    while (true) {
        void *buffer = alloc_buffer();
        struct checksum_metadata meta;

        // Read block and checksum
        read_disk(block_num, buffer);
        read_checksum(block_num, &meta);

        // Verify
        uint32_t computed = crc32(buffer, BLOCK_SIZE);
        if (computed != meta.checksum) {
            // Corruption found!
            errors_found++;
            log_error("Scrubber: Corruption at block %llu", block_num);

            // Attempt repair
            if (repair_block(block_num, buffer)) {
                log_info("Scrubber: Block %llu repaired", block_num);
            } else {
                log_critical("Scrubber: Block %llu UNRECOVERABLE", block_num);
            }
        }

        free(buffer);

        // Move to next block
        block_num = (block_num + 1) % total_blocks;

        // Throttle to avoid overwhelming system
        usleep(SCRUB_THROTTLE_USEC);

        // Print progress occasionally
        if (block_num % 100000 == 0) {
            float progress = (float)block_num / total_blocks * 100;
            printf("Scrub progress: %.1f%% (%llu errors found)\n",
                   progress, errors_found);
        }
    }
}
```

**Repair logic:**

```c
bool repair_block(uint64_t block_num, void *buffer) {
    // Try mirror (RAID-1)
    if (has_mirror()) {
        if (read_and_verify_mirror(block_num, buffer)) {
            write_disk(PRIMARY_DISK, block_num, buffer);
            return true;
        }
    }

    // Try parity reconstruction (RAID-5/6)
    if (has_parity()) {
        if (reconstruct_from_parity(block_num, buffer)) {
            write_disk(PRIMARY_DISK, block_num, buffer);
            return true;
        }
    }

    // No redundancy or all copies bad
    return false;
}
```

### 9.3. Scheduling Strategies

**Frequency:**

```
Conservative: Monthly scrub
  └─ Pro: Minimal performance impact
  └─ Con: Up to 30 days before detection

Moderate: Weekly scrub
  └─ Pro: Balance of detection speed and overhead
  └─ Con: Still significant window

Aggressive: Daily scrub
  └─ Pro: Fast detection
  └─ Con: Performance impact
```

**Timing:**

```
Strategy 1: Off-hours
  ┌────────────────────────────────────┐
  │ 8am-6pm: Scrubbing disabled        │
  │ 6pm-8am: Scrubbing active          │
  └────────────────────────────────────┘
  Pro: No impact on users
  Con: May not complete for large systems

Strategy 2: Adaptive throttling
  ┌────────────────────────────────────┐
  │ System idle: Scrub at 80% I/O      │
  │ System busy: Scrub at 5% I/O       │
  └────────────────────────────────────┘
  Pro: Always making progress
  Con: Complex to tune

Strategy 3: Priority-based
  ┌────────────────────────────────────┐
  │ Critical data: Scrub weekly        │
  │ Normal data: Scrub monthly         │
  │ Archival data: Scrub quarterly     │
  └────────────────────────────────────┘
  Pro: Resources focused on important data
  Con: Less important data at higher risk
```

**Progress tracking:**

```c
struct scrub_state {
    uint64_t last_block_checked;
    time_t last_scrub_start;
    time_t last_scrub_complete;
    uint64_t errors_found_this_run;
    uint64_t errors_repaired;
    uint64_t errors_unrecoverable;
};
```

**Statistics and monitoring:**

```
Scrub report (2024-10-15):
  Total blocks scanned:   1,234,567,890
  Errors detected:        42
  Errors repaired:        40
  Unrecoverable errors:   2
  Time taken:             12 hours, 34 minutes
  Throughput:             27,345 blocks/second
  Next scrub scheduled:   2024-10-22
```

**Real-world example (ZFS):**

```bash
# Check scrub status
$ zpool status tank

  pool: tank
  state: ONLINE
  scrub: scrub completed after 14h23m with 0 errors

# Start manual scrub
$ zpool scrub tank

# Monitor progress
$ zpool status tank
  scan: scrub in progress since Sun Oct 15 08:00:00 2024
        1.2T scanned out of 5.4T at 95.3M/s
        3h45m to go
```

> **💡 Insight**
>
> Scrubbing is **preventive maintenance** for your data. Like rotating stock in a warehouse to check for spoilage, scrubbing checks data before you need it. The earlier corruption is detected, the more likely recovery succeeds. Many systems report that scrubbing discovers 80%+ of LSEs—problems that would otherwise go unnoticed until disaster strikes.

---

## 10. Overheads of Checksumming

### 10.1. Space Overhead

**On-disk overhead:**

```
Typical configuration:
  Data block: 4 KB = 4096 bytes
  Checksum: 8 bytes (CRC-64)
  Metadata: 8 bytes (disk ID, block number)
  Total overhead: 16 bytes

Percentage: 16 / 4096 = 0.39%
```

**For large systems:**

```
10 TB storage:
  Without checksums: 10,000 GB
  Checksum overhead: 0.39% = 39 GB
  Net storage: 9,961 GB

Verdict: Negligible
```

**In-memory overhead:**

**Transient (during I/O):**

```
During read:
  ├─ Load data block: 4 KB
  ├─ Load checksum: 16 bytes
  └─ Compute checksum: 0 bytes (just CPU)

  Total memory: 4 KB + 16 bytes
  Duration: Only while verifying

After verification:
  └─ Discard checksum
  └─ Memory: 4 KB (data only)
```

**Persistent (if checksums kept in memory):**

```
Scenario: Keep checksums cached

Example:
  Data in page cache: 1 GB
  Checksums: 1 GB × 0.39% = ~4 MB

Overhead: 4 MB per 1 GB data
```

**Most systems don't cache checksums:**

```
Typical approach:
1. Read data + checksum
2. Verify immediately
3. Discard checksum
4. Cache only data

Memory overhead: ~0%
```

**Exception: ZFS**

```
ZFS protects against memory corruption:
  ├─ Keeps checksums in memory
  ├─ Rechecks before writing
  └─ Detects RAM bit flips

Extra memory: 0.39% of cached data
Benefit: Catches memory corruption too
```

### 10.2. Time Overhead

**CPU overhead:**

**Checksum computation cost:**

```
CRC-32 performance (modern CPU):
  Throughput: ~10 GB/s (with hardware acceleration)
  Per 4 KB block: ~0.4 microseconds

For comparison:
  Disk read latency: ~5,000 microseconds
  SSD read latency: ~100 microseconds

CPU overhead: < 0.01% of I/O time
```

**Write path:**

```
Without checksum:
  Write data → Done

With checksum:
  Compute checksum → Write data → Write checksum → Done
  └─0.4 μs───────────5000 μs──────────────────────────┘

Overhead: Negligible compared to I/O
```

**Read path:**

```
Without checksum:
  Read data → Done

With checksum:
  Read data → Read checksum → Verify → Done
  └─5000 μs────────────────┴─0.4 μs─────┘

Overhead: Negligible compared to I/O
```

**I/O overhead:**

**Packed checksum layout:**

```
Write single block (worst case):

Without checksums:
  1. Write data block
  Total: 1 write (~5 ms)

With packed checksums:
  1. Read checksum sector
  2. Update checksum in memory
  3. Write checksum sector
  4. Write data block
  Total: 1 read + 2 writes (~15 ms)

Overhead: 3x I/O operations
```

**Mitigation: Checksum caching**

```
With checksum sector cached:
  1. Update checksum in memory (cached)
  2. Write checksum sector (async)
  3. Write data block
  Total: 2 writes (~10 ms)

Overhead: 2x I/O operations
```

**Scrubbing overhead:**

```
Background scrub at 10% I/O capacity:

System capacity: 1000 IOPS
Scrubbing uses: 100 IOPS (10%)
Available to apps: 900 IOPS (90%)

User-perceived impact: Minimal (if throttled properly)
```

### 10.3. Optimization Techniques

**1. Combined Copy-and-Checksum**

**Problem:** Data copied twice (disk → kernel → user)

```
Traditional:
  1. DMA: disk → kernel buffer
  2. Checksum: kernel buffer
  3. Copy: kernel buffer → user buffer

Three memory passes
```

**Optimized:**

```c
uint32_t copy_and_checksum(void *dest, void *src, size_t len) {
    uint32_t checksum = 0;

    for (size_t i = 0; i < len; i++) {
        dest[i] = src[i];           // Copy
        checksum = update_crc32(checksum, src[i]);  // Checksum
    }

    return checksum;
}
```

**Benefit:**

```
Optimized:
  1. DMA: disk → kernel buffer
  2. Copy + Checksum: kernel → user (simultaneously)

Two memory passes (33% reduction)
```

**2. Hardware Acceleration**

**Modern CPUs have CRC instructions:**

```
Intel: CRC32 instruction (SSE 4.2)
ARM: CRC32 instructions
```

**Performance:**

```
Software CRC: ~1 GB/s
Hardware CRC: ~10-50 GB/s

Speedup: 10-50x
```

**Example:**

```c
// x86_64 with SSE 4.2
uint32_t crc32_hw(uint8_t *data, size_t len) {
    uint32_t crc = 0xFFFFFFFF;

    // Process 8 bytes at a time
    while (len >= 8) {
        uint64_t chunk = *(uint64_t*)data;
        crc = _mm_crc32_u64(crc, chunk);  // Hardware instruction
        data += 8;
        len -= 8;
    }

    // Process remaining bytes
    while (len > 0) {
        crc = _mm_crc32_u8(crc, *data);
        data++;
        len--;
    }

    return ~crc;
}
```

**3. Batching**

**Write batching:**

```
Individual writes (expensive):
  Write Block 0 → Update checksum sector
  Write Block 1 → Update checksum sector
  Write Block 2 → Update checksum sector
  Total: 3 data writes + 3 checksum writes

Batched writes (efficient):
  Write Blocks 0, 1, 2
  Update checksum sector once
  Total: 3 data writes + 1 checksum write

Savings: 66% fewer checksum writes
```

**4. Asynchronous Verification**

**Synchronous (blocks application):**

```
Application: read(data)
  ↓
Read data from disk
  ↓
Verify checksum ← blocks here
  ↓
Return to application
```

**Asynchronous (overlaps verification):**

```
Application: read(data)
  ↓
Read data from disk
  ↓
Return to application ← doesn't wait
  ↓
Verify checksum in background
  ↓
If error: Notify application
```

**5. Selective Checksumming**

**Not all data equally valuable:**

```
Critical data (financial records):
  └─ SHA-256 checksums
  └─ Multiple redundancy
  └─ Daily scrubbing

Normal data (documents):
  └─ CRC-32 checksums
  └─ Standard redundancy
  └─ Weekly scrubbing

Temporary data (caches):
  └─ No checksums
  └─ No redundancy
  └─ No scrubbing

Tune overhead to importance
```

**Summary of overhead:**

```
Component              Overhead        Mitigation
─────────────────────────────────────────────────────
Disk space             0.39%           None needed (tiny)
Memory                 ~0%             Transient only
CPU (computation)      <0.01%          Hardware acceleration
I/O (packed layout)    2-3x            Caching, batching
Scrubbing              5-10%           Throttling, scheduling

Overall impact: Low with proper optimizations
```

> **💡 Insight**
>
> Checksumming is a textbook example of **good engineering**. The protection it provides (detecting silent corruption) far outweighs its costs (< 1% space, negligible CPU). Modern optimizations (hardware acceleration, combined operations) have made checksumming virtually free. The real overhead is complexity in software design, not runtime performance.

---

## 11. Summary

**Core concepts:**

**🔧 Disk Failure Models:**

- **Fail-stop (traditional):** Disk either works or dies completely
- **Fail-partial (reality):** Disks work mostly, with occasional sector failures or corruption
- **LSEs (Latent Sector Errors):** Detectable read failures (disk reports error)
- **Silent corruption:** Data wrong but no error reported (insidious)

**📊 Failure Statistics:**

```
Over 3 years, 1.5M drives:

Cheap drives:
  - 9.4% experience LSEs
  - 0.5% experience corruption

Costly drives:
  - 1.4% experience LSEs  (7x better)
  - 0.05% experience corruption  (10x better)

Conclusion: Partial failures are common, not rare
```

**🛡️ Protection Mechanisms:**

**1. Handling LSEs:**
- Use RAID redundancy (mirrors, parity)
- RAID-DP (dual parity) for rebuild safety
- Early detection through scrubbing

**2. Detecting Corruption:**

```
Checksum functions (tradeoff spectrum):

XOR         → Fast, weak
Addition    → Fast, weak
Fletcher    → Medium, good
CRC         → Medium, excellent
SHA/MD5     → Slow, cryptographic

Most storage systems use CRC (best balance)
```

**3. Checksum Layout:**

```
Option A: 520-byte sectors
  [512B data | 8B checksum]
  ✅ Atomic
  ❌ Special disk format

Option B: Packed checksums
  [Checksums for 64 blocks] [64 data blocks] [...]
  ✅ Standard disks
  ❌ Extra I/O overhead
```

**4. Enhanced Protection:**

```
Misdirected writes:
  Add: Disk ID + Block Number
  Detects: Wrong location writes

Lost writes:
  Option 1: Write-verify (read back immediately)
    ✅ Reliable
    ❌ 2x I/O cost

  Option 2: Checksums in inode (ZFS approach)
    ✅ No extra I/O
    ✅ Catches lost writes
    ❌ Complex write ordering needed
```

**5. Scrubbing:**

```
Background process:
  for each block:
    read data
    verify checksum
    if corrupt:
      recover from redundancy
      repair original
    next block

Frequency: Daily/weekly/monthly
Benefit: Proactive detection before data needed
Result: 80%+ of LSEs found this way
```

**⚖️ Overhead Analysis:**

```
Space:  0.39% (negligible)
CPU:    <0.01% of I/O time (with hardware acceleration)
I/O:    Depends on layout
  - 520-byte sectors: ~0%
  - Packed checksums: 2-3x (mitigated by caching)
Scrubbing: 5-10% I/O (throttled to off-hours)

Verdict: Low cost for high protection
```

**🎯 Design Principles Learned:**

1. **Defense in depth:**
   - Basic checksums catch corruption
   - Physical IDs catch misdirection
   - Inode checksums catch lost writes
   - Multiple layers cover different failure modes

2. **Redundancy enables detection AND recovery:**
   - Checksums detect problems
   - RAID provides recovery copies
   - Need both for complete solution

3. **Proactive vs. reactive:**
   - Reactive: Wait for application to find errors
   - Proactive: Scrub to find errors early
   - Early detection = higher recovery success rate

4. **Tradeoffs everywhere:**
   - Strong checksum vs. CPU cost
   - Extra I/O vs. simple layout
   - Scrub frequency vs. performance impact
   - No perfect answer, only informed choices

**🔍 Key Insight:**

```
Traditional error handling:
  Hardware detects errors → OS responds

Modern data integrity:
  Hardware CAN'T detect errors → Software MUST

Silent corruption is the enemy
Checksums are your defense
```

**In plain English:** Modern storage is unreliable at scale. Disks lie about data integrity. Your only defense is paranoia—check everything, verify everything, assume nothing. Checksums, redundancy, and scrubbing aren't optional luxuries, they're essential survival mechanisms.

**Looking ahead:** The techniques in this chapter form the foundation of modern file systems like ZFS, Btrfs, and ReFS. The next chapters explore how these ideas integrate into complete file system designs, where data integrity is baked into every operation.

---

**Previous:** [Chapter 10: Flash-Based SSDs](chapter10-flash-based-ssds.md) | **Next:** [Chapter 12: Distributed Systems](chapter12-distributed-systems.md)