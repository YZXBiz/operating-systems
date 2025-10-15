# 📚 Chapter 13: The Andrew File System (AFS)

_Building scalable distributed file systems through intelligent protocol design_

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [AFS Version 1](#2-afs-version-1)
   - 2.1. [Core Design Philosophy](#21-core-design-philosophy)
   - 2.2. [Protocol Operations](#22-protocol-operations)
3. [Problems with Version 1](#3-problems-with-version-1)
   - 3.1. [Path-Traversal Costs](#31-path-traversal-costs)
   - 3.2. [Excessive TestAuth Messages](#32-excessive-testauth-messages)
4. [AFS Version 2: The Scalable Solution](#4-afs-version-2-the-scalable-solution)
   - 4.1. [Callbacks: The Key Innovation](#41-callbacks-the-key-innovation)
   - 4.2. [File Identifiers (FIDs)](#42-file-identifiers-fids)
   - 4.3. [Client-Server Interaction](#43-client-server-interaction)
5. [Cache Consistency Model](#5-cache-consistency-model)
   - 5.1. [Cross-Machine Consistency](#51-cross-machine-consistency)
   - 5.2. [Same-Machine Consistency](#52-same-machine-consistency)
   - 5.3. [Last Writer Wins](#53-last-writer-wins)
6. [Crash Recovery](#6-crash-recovery)
   - 6.1. [Client Crash Recovery](#61-client-crash-recovery)
   - 6.2. [Server Crash Recovery](#62-server-crash-recovery)
7. [Performance Analysis](#7-performance-analysis)
   - 7.1. [Scalability Improvements](#71-scalability-improvements)
   - 7.2. [AFS vs NFS Comparison](#72-afs-vs-nfs-comparison)
   - 7.3. [Workload Considerations](#73-workload-considerations)
8. [Additional Features](#8-additional-features)
9. [Summary](#9-summary)

---

## 1. Introduction

**In plain English:** Imagine if every time you wanted to check if your email had new messages, you had to call someone. That would be exhausting for both you and the person answering. What if instead, they just called you when something new arrived? That's the fundamental insight behind AFS.

**In technical terms:** The Andrew File System (AFS) was developed at Carnegie-Mellon University in the 1980s by Professor M. Satyanarayanan ("Satya") with one primary goal: **scale**. How can a distributed file system be designed so that a single server can support as many clients as possible?

**Why it matters:** The design choices in a distributed file system's protocol directly determine its scalability. NFS forced clients to constantly check with servers ("polling"), consuming server resources and limiting the number of clients. AFS took a different approach using callbacks ("interrupts"), dramatically improving scalability.

> **💡 Insight**
>
> AFS demonstrates that scalability isn't just about making things faster—it's about reducing unnecessary communication. By shifting from a polling model (clients constantly asking "has anything changed?") to an interrupt model (server notifying clients when changes occur), AFS achieved 2.5x better scalability than its first version.

---

## 2. AFS Version 1

### 2.1. Core Design Philosophy

The original AFS (AFSv1, initially called the ITC distributed file system) introduced several foundational concepts that would define the system:

**Whole-file caching on local disk:**
- When you `open()` a file, the **entire file** is fetched from the server
- The file is stored on your **local disk** (not just memory)
- All `read()` and `write()` operations happen locally (no network)
- Upon `close()`, modified files are flushed back to the server

**The contrast with NFS:**
```
NFS Approach           AFS Approach
────────────          ─────────────
Cache blocks    →     Cache whole files
In memory       →     On local disk
On demand       →     At open time
```

**The client-server architecture:**
- **Venus:** The client-side code running on each machine
- **Vice:** The server-side file server infrastructure

### 2.2. Protocol Operations

AFSv1 defined a simple protocol for client-server communication:

| Protocol Message | Purpose |
|-----------------|---------|
| **Fetch** | Retrieve entire file contents from server |
| **Store** | Send entire file back to server |
| **TestAuth** | Check if cached file is still valid |
| **GetFileStat** | Get file metadata |
| **SetFileStat** | Update file metadata |
| **ListDir** | List directory contents |

**How a file access works:**

```
Client opens /home/remzi/notes.txt

1. Open → Venus sends Fetch("/home/remzi/notes.txt")
2. Server walks path, finds file, sends entire file
3. Venus writes file to local disk cache
4. Application read()/write() → local disk operations (fast!)
5. Close → If modified, Venus sends Store() to server
```

**Subsequent access to the same file:**

```
Client opens /home/remzi/notes.txt again

1. Open → Venus sends TestAuth("/home/remzi/notes.txt")
2. Server responds: "No changes" or "File modified"
3. If no changes → Use local cached copy (no network transfer!)
4. If modified → Fetch new version
```

---

## 3. Problems with Version 1

> **📝 Note: Patterson's Law**
>
> "Measure then build." Before redesigning AFS, the developers spent significant time measuring the existing system to understand exactly what was wrong. This experimental approach transformed system building into a scientific endeavor: you have evidence of the problem, you know how to measure improvements, and you can prove your solution works.

The AFS team identified two critical bottlenecks through careful measurement:

### 3.1. Path-Traversal Costs

**The problem:** Clients sent entire pathnames to the server (e.g., `/home/remzi/notes.txt`), and the server had to traverse the entire path for every operation:

```
Server receives: Fetch("/home/remzi/notes.txt")

Server work required:
1. Look in / to find "home"
2. Look in /home to find "remzi"
3. Look in /home/remzi to find "notes.txt"
4. Read notes.txt and send back

With many clients → Server CPU spends most time walking paths!
```

**Why it matters:** This is pure overhead. The server does the same path-walking work repeatedly, even when the client has already traversed this path before.

### 3.2. Excessive TestAuth Messages

**The problem:** Just like NFS's GETATTR flood, AFSv1 clients constantly checked with the server to validate cached files:

```
Client behavior:
1. Open file → TestAuth("is my cache valid?")
2. Server responds (consuming CPU and bandwidth)
3. Server's answer is usually: "Yes, unchanged"

With many clients → Server drowns in validation requests!
```

**The scalability impact:** AFSv1 servers could only support **20 clients** before becoming overloaded. This was unacceptable for a university environment with hundreds or thousands of users.

> **⚡ Key Insight**
>
> Both problems stemmed from the same issue: **clients asking the server for information the client could track itself**. The solution would be to shift more intelligence to the client and reduce server interactions.

---

## 4. AFS Version 2: The Scalable Solution

### 4.1. Callbacks: The Key Innovation

**The fundamental shift:**

```
AFSv1 (Polling Model)          AFSv2 (Callback Model)
────────────────────          ──────────────────────
Client: "Has file changed?"    Server: "I'll tell you when it changes!"
Server: "No"
[Repeat constantly]            [Silence unless change occurs]
```

**In plain English:** Instead of you constantly calling to check for updates, the server promises to call you when something changes. Until you hear from the server, you can safely assume your cached copy is valid.

**In technical terms:** A **callback** is a promise from the server to the client. When a client caches a file, the server registers that this client has the file and promises to notify it if anyone modifies the file. This is **server-maintained state**.

**The benefits:**
- ✅ Eliminates constant TestAuth messages
- ✅ Clients trust their cache until notified otherwise
- ✅ Dramatically reduces server load
- ✅ Network traffic drops significantly

### 4.2. File Identifiers (FIDs)

AFSv2 introduced **File Identifiers (FIDs)** to replace pathname-based operations:

**FID structure:**
```
FID = (Volume ID, File ID, Uniquifier)
      ───────────────────────────────
      Allows reuse when files deleted
```

**Why this matters:** Instead of the server walking the entire path, the **client walks the path**, caching FIDs for each component:

```
Client opens /home/remzi/notes.txt

Old way (AFSv1):
Server receives: Fetch("/home/remzi/notes.txt")
Server walks: / → home → remzi → notes.txt

New way (AFSv2):
Client walks path incrementally:
1. Fetch(home_FID) → Cache home directory + callback
2. Look up "remzi" in cached home directory
3. Fetch(remzi_FID) → Cache remzi directory + callback
4. Look up "notes.txt" in cached remzi directory
5. Fetch(notes_FID) → Cache file + callback

Subsequent accesses: Client uses cached directories (no server contact!)
```

### 4.3. Client-Server Interaction

**First access to `/home/remzi/notes.txt`:**

```
Client Action                    Server Action
─────────────                   ──────────────
open(notes.txt)
→ Fetch(home, "remzi")       → Find remzi in home
                                 Establish callback(C1, remzi)
                                 Return remzi FID + contents
← Store remzi dir locally
   Record callback status

→ Fetch(remzi, "notes.txt")  → Find notes.txt in remzi
                                 Establish callback(C1, notes.txt)
                                 Return file FID + contents
← Store notes.txt locally
   Record callback status

Open local cached file
Return file descriptor
```

**Subsequent access to the same file:**

```
Client Action                    Server Action
─────────────                   ──────────────
open(notes.txt)
Check callback(home) → VALID
Check callback(remzi) → VALID
Check callback(notes.txt) → VALID

Open local cached file      → (No server contact at all!)
Return file descriptor
```

> **🚀 Performance Win**
>
> After the first access, AFS performs like a local file system. All operations are local to the client machine, providing near-local performance with the benefits of distributed storage.

---

## 5. Cache Consistency Model

### 5.1. Cross-Machine Consistency

AFS provides simple, understandable semantics: **updates become visible when the file is closed**.

**The update sequence:**

```
Client C1                    Server                    Client C2
─────────                   ──────                    ─────────
1. open(file)
2. write(data)
3. write(more)
4. close(file)
   → Store(file) ────────→ Receive new file
                            Break callbacks! ────────→ Invalidate cache!

                                                      5. open(file)
                                                         Cache invalid!
                                                      → Fetch(file)
                            Send new version ────────←
                            Establish callback
```

**Key properties:**
- **Update visibility:** Changes appear at the server when the file is `close()`d
- **Cache invalidation:** Happens at the same time via callback breaks
- **Stale reads prevented:** Other clients' callbacks are invalidated immediately

### 5.2. Same-Machine Consistency

For processes on the **same machine**, AFS provides standard UNIX semantics:

```
Process P1                   Local Cache              Process P2
──────────                  ────────────             ──────────
open(file)
write("A") ───────────────→ Update cache ──────────→ read() sees "A"
write("B") ───────────────→ Update cache ──────────→ read() sees "B"
close()
```

**Why it matters:** This ensures that a single machine behaves exactly like a traditional UNIX system, meeting user expectations for local consistency.

### 5.3. Last Writer Wins

When multiple clients modify the same file simultaneously, AFS uses a **last closer wins** strategy:

```
Client C1                    Server                    Client C2
─────────                   ──────                    ─────────
open(file)                                            open(file)
write("version1")                                     write("version2")
[working...]                                          [working...]
close() [9:00:00]
→ Store(v1) ────────────→ Save version1

                                                      close() [9:00:01]
                                                      → Store(v2)
                          Overwrite! ←────────────────
                          Save version2

Final result: version2 (last closer wins)
```

**Contrast with NFS:**

```
NFS (block-based):           AFS (whole-file):
─────────────────           ──────────────────
C1 writes blocks 1-5    →   C1 writes entire file
C2 writes blocks 3-7    →   C2 writes entire file
Result: Mixed blocks!       Result: One complete file or the other
```

> **⚠️ Important Limitation**
>
> AFS's consistency model is designed for **casual file sharing** (users accessing their files from different machines), not for **concurrent collaborative editing** or **database workloads**. Applications requiring strict concurrency control must implement their own locking mechanisms on top of AFS.

---

## 6. Crash Recovery

The callback mechanism introduces complexity in crash recovery scenarios.

### 6.1. Client Crash Recovery

**The problem:** If a client crashes and reboots, it may have missed callback break messages:

```
Timeline:
1. Client C1 caches file F, receives callback
2. Client C1 reboots (temporarily unavailable)
3. Client C2 updates file F
4. Server sends callback break to C1 → LOST!
5. Client C1 comes back online
   → Still has old cached F, thinks it's valid!
```

**The solution:** Upon rejoining the system, the client treats **all cached contents as suspect**:

```
Client recovery protocol:
1. Reboot completes
2. First access to any cached file F
3. Send TestAuth(F) to server
4. Server responds: Valid or Invalid
5. If invalid → Fetch fresh copy
6. If valid → Reestablish callback, use cache
```

### 6.2. Server Crash Recovery

**The problem:** Callbacks are stored in server memory (state), so a server crash loses all callback information:

```
Before crash:
Server knows: C1 has files {A, B}, C2 has {B, C}, C3 has {D}

After crash:
Server knows: [NOTHING]
```

**The solution:** All clients must be notified of the server crash and treat their caches as suspect:

**Implementation approaches:**

1. **Push notification:**
```
Server recovery:
1. Server reboots
2. For each known client:
   Send "invalidate all caches" message
3. Clients fetch fresh data as needed
```

2. **Heartbeat mechanism:**
```
Normal operation:
Client ←→ Periodic heartbeat →← Server

Server crash detected:
Client: "Server didn't respond!"
Client: Invalidate all cached data
```

> **🔄 Trade-off**
>
> AFS trades simpler crash recovery (like NFS's stateless design) for better scalability and performance. Server crashes are more disruptive in AFS because all clients must revalidate their caches, but the improved day-to-day performance makes this trade-off worthwhile.

---

## 7. Performance Analysis

### 7.1. Scalability Improvements

AFSv2's protocol changes delivered impressive results:

```
Scalability Comparison:
────────────────────
AFSv1: 20 clients per server
AFSv2: 50 clients per server

Improvement: 2.5x increase! 🎉
```

**Why the improvement:**
- ✅ Eliminated constant TestAuth traffic
- ✅ Server no longer repeatedly walks pathnames
- ✅ Clients handle more work independently
- ✅ Server CPU freed up for actual file operations

### 7.2. AFS vs NFS Comparison

Let's analyze different workload patterns to understand when each system excels:

**Notation:**
- `s` = small file (fits in memory)
- `m` = medium file (fits in memory)
- `L` = large file (fits on disk, not memory)
- `net` = network access time
- `mem` = memory access time
- `disk` = disk access time
- Assumption: `net >> disk >> mem`

**Performance comparison table:**

| Workload | NFS | AFS | Winner |
|----------|-----|-----|--------|
| **1. Small file, first read** | s·net | s·net | Tie |
| **2. Small file, re-read** | s·mem | s·mem | Tie |
| **3. Large file, first read** | L·net | L·net | Tie |
| **4. Large file, re-read** | L·net | L·disk | **AFS** 🏆 |
| **5. Sequential write (new)** | s·net | s·net | Tie |
| **6. File overwrite** | s·net | 2·s·net | **NFS** 🏆 |
| **7. Large file, small read** | small·net | L·net | **NFS** 🏆 |
| **8. Large file, small write** | small·net | 2·L·net | **NFS** 🏆 |

**Key insights:**

**🎯 AFS wins: Large file re-reads (Workload 4)**
```
Scenario: User opens a 100MB video file twice

NFS:
- First read: Fetch 100MB over network
- Second read: File doesn't fit in memory → Fetch 100MB again!
- Network congestion, server load

AFS:
- First read: Fetch 100MB, store on local disk
- Second read: Read from local disk (fast!)
- No network, no server load
```

**🎯 NFS wins: File overwrites (Workload 6)**
```
Scenario: Modify an existing file

NFS:
- open() → Fetch only needed blocks
- write() → Overwrite blocks
- close() → Flush modified blocks

AFS:
- open() → Fetch entire file (wasted work!)
- write() → Overwrite local copy
- close() → Send entire file back (wasted bandwidth!)
```

**🎯 NFS wins: Small I/O on large files (Workloads 7, 8)**
```
Scenario: Append 1KB to a 1GB log file

NFS:
- Open file (no data transfer)
- Write 1KB → Send 1KB to server
- Total network: ~1KB

AFS:
- Open file → Fetch entire 1GB!
- Write 1KB locally
- Close → Send entire 1GB back!
- Total network: ~2GB

This is devastating for AFS performance!
```

### 7.3. Workload Considerations

> **💡 Critical Insight on Workload**
>
> System design requires assumptions about how the system will be used. AFS designers, through extensive measurement, found that:
> - Most files are **not frequently shared** between users
> - Most files are **accessed sequentially** in their entirety
> - Most files are **relatively small**
>
> Given these assumptions, AFS's whole-file caching strategy makes perfect sense. However, these assumptions don't hold for all workloads.

**Workloads where AFS struggles:**

1. **Log files with periodic appends**
```
Application: Web server writing to access.log

Every log write:
- Fetch entire log (growing larger each time)
- Append small entry
- Write entire log back

Cost grows O(n²) with log size!
```

2. **Database random updates**
```
Application: Transaction database

Every update:
- Fetch entire database file
- Modify single record
- Write entire file back

Massive overhead for tiny changes!
```

3. **Collaborative document editing**
```
Scenario: Two users editing same document

User A writes → close() → User B's copy invalidated
User B writes → close() → User A's copy invalidated
Result: Ping-pong of full-file transfers!
```

**Workloads where AFS excels:**

1. **User home directories**
```
Pattern: User logs into different workstations

First login: Files cached to local disk
Subsequent work: All local, fast!
Only changes sent to server on close()
```

2. **Software development**
```
Pattern: Developers reading code, occasional writes

Read-heavy workload benefits from local caching
Compiler reading source files: All local after first access!
Occasional commits: Only modified files sent to server
```

---

## 8. Additional Features

Beyond the core protocol innovations, AFS introduced several features that enhanced usability and management:

**🌐 Global Namespace**
```
Traditional NFS:                 AFS:
──────────────                  ────
Each client mounts freely       Single consistent namespace

Client1: /mnt/server/home       All clients: /afs/cs.cmu.edu/user/remzi
Client2: /net/files/home        Same path works everywhere!
Client3: /remote/home

Result: Chaos                   Result: Consistency
```

**Why it matters:** Users can reference files the same way from any machine, simplifying collaboration and system administration.

**🔒 Security and Authentication**

AFS incorporated robust security mechanisms:
- User authentication (Kerberos integration)
- Encrypted communication options
- Private file storage capabilities

NFS, by contrast, had primitive security for many years (trusted client IP addresses).

**🔧 Flexible Access Control**

AFS provides user-managed Access Control Lists (ACLs):

```
Traditional UNIX:               AFS ACLs:
────────────────               ─────────
Owner, group, others           Per-user/group permissions

chmod 755 file                 fs setacl directory user:alice rlidwka
                               fs setacl directory user:bob rl
Limited flexibility            Fine-grained control
```

**📊 Administrative Tools**

AFS introduced **volumes** for load balancing:

```
Problem: Server overloaded          Solution: Move volumes

Server1: [Heavy load]               Server1: [Balanced]
  - user volumes                      - subset of users
  - project volumes                 Server2: [Balanced]
  - system volumes                    - moved users/projects

Administrator: Can't help!          Administrator: fs move volume
```

> **🎓 Management Philosophy**
>
> AFS was designed with system administrators in mind. The tools and abstractions made large-scale deployment practical—critical for university environments with thousands of users and hundreds of machines.

---

## 9. Summary

The Andrew File System represents a fundamentally different approach to distributed file system design, prioritizing scalability and user experience through careful protocol engineering.

**🎯 Core Innovations:**

1. **Callbacks over polling:** Server notifies clients of changes rather than clients constantly checking
2. **Whole-file caching:** Complete files cached on local disk for performance
3. **File identifiers:** Clients walk paths incrementally, caching results
4. **Simple consistency:** Updates visible at close(), easy to understand

**⚡ Performance Characteristics:**

```
Strengths:                      Weaknesses:
─────────                      ───────────
✅ Read-heavy workloads        ❌ Large files with small I/O
✅ Large file re-reads         ❌ File overwrites
✅ Sequential access           ❌ Concurrent modifications
✅ Near-local performance      ❌ Complex crash recovery
✅ Reduced server load         ❌ Server state management
```

**🔄 The Scalability Achievement:**

```
Before (AFSv1): 20 clients/server
After (AFSv2):  50 clients/server

Key: Reducing server interactions, not making servers faster!
```

**📝 Legacy and Impact:**

While AFS itself has declined in market share (NFS became the open standard), its ideas profoundly influenced distributed system design:

- NFSv4 adopted server-side state and "open" protocol messages (AFS-like)
- The callback concept appears in many distributed systems
- The emphasis on cache consistency modeling became standard practice
- The focus on measurement and workload understanding shaped systems research

> **💡 Final Insight**
>
> AFS teaches us that **protocol design is system design**. The way clients and servers communicate determines scalability, consistency, and performance more than any other factor. By carefully rethinking the protocol—shifting from polling to callbacks, from pathnames to FIDs, from server-side path walking to client-side caching—AFS achieved dramatically better scalability while providing simpler, more understandable consistency semantics.

**The philosophical lesson:**

```
Good system design requires:
1. Measurement → Understand the real problems
2. Insight → See what's fundamentally wrong
3. Redesign → Change the core model, not just optimize
4. Validation → Measure again to prove improvement

This is Patterson's Law in action: Measure, then build.
```

AFS remains an excellent case study in distributed systems design, demonstrating how principled engineering—grounded in measurement and guided by clear goals—can produce systems that are both more scalable and easier to reason about.

---

**Previous:** [Chapter 12: Network File System](chapter12-distributed-systems.md)
