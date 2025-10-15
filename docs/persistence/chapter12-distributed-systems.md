# 🌐 Chapter 12: Distributed File Systems - NFS

Understanding how file systems work across networks and multiple machines.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Basic Distributed File System Architecture](#2-basic-distributed-file-system-architecture)
   - 2.1. [Client-Server Model](#21-client-server-model)
   - 2.2. [Transparent Access](#22-transparent-access)
3. [Network File System (NFS) Overview](#3-network-file-system-nfs-overview)
   - 3.1. [Open Protocol Approach](#31-open-protocol-approach)
   - 3.2. [NFSv2 Design Goals](#32-nfsv2-design-goals)
4. [The Stateless Protocol Design](#4-the-stateless-protocol-design)
   - 4.1. [Understanding State in Protocols](#41-understanding-state-in-protocols)
   - 4.2. [Why Stateless?](#42-why-stateless)
   - 4.3. [Crash Recovery Benefits](#43-crash-recovery-benefits)
5. [NFSv2 Protocol Details](#5-nfsv2-protocol-details)
   - 5.1. [File Handles](#51-file-handles)
   - 5.2. [Core Protocol Operations](#52-core-protocol-operations)
   - 5.3. [Protocol In Action](#53-protocol-in-action)
6. [Handling Failures with Idempotency](#6-handling-failures-with-idempotency)
   - 6.1. [Types of Failure](#61-types-of-failure)
   - 6.2. [Retry Strategy](#62-retry-strategy)
   - 6.3. [Idempotent Operations](#63-idempotent-operations)
7. [Client-Side Caching](#7-client-side-caching)
   - 7.1. [Performance Problem](#71-performance-problem)
   - 7.2. [Caching Strategy](#72-caching-strategy)
   - 7.3. [Cache Consistency Challenge](#73-cache-consistency-challenge)
8. [Solving Cache Consistency](#8-solving-cache-consistency)
   - 8.1. [The Two Subproblems](#81-the-two-subproblems)
   - 8.2. [Flush-on-Close Semantics](#82-flush-on-close-semantics)
   - 8.3. [Attribute Cache Solution](#83-attribute-cache-solution)
   - 8.4. [Trade-offs and Oddities](#84-trade-offs-and-oddities)
9. [Server-Side Write Handling](#9-server-side-write-handling)
   - 9.1. [The Write Buffering Problem](#91-the-write-buffering-problem)
   - 9.2. [Commit-to-Disk Requirement](#92-commit-to-disk-requirement)
   - 9.3. [Performance Solutions](#93-performance-solutions)
10. [VFS/Vnode Innovation](#10-vfsvnode-innovation)
11. [Summary](#11-summary)

---

## 1. Introduction

**In plain English:** Imagine you have multiple computers that all need to access the same files. Instead of copying files between machines, you can have one computer (server) store all the files, and the other computers (clients) access them over the network. It looks like the files are on your local computer, but they're actually stored remotely.

**In technical terms:** A distributed file system enables multiple client machines to access files stored on remote server machines through network protocols, providing transparent access to shared data.

**Why it matters:** This enables collaboration, centralized backups, and consistent data access across an organization without manually copying files between machines.

### 🎯 Core Challenge

> **The fundamental question:** How do you build a distributed file system that survives server crashes, performs well despite network latency, and maintains data consistency across multiple clients?

The basic setup looks like this:

```
Client 0 ─┐
Client 1 ─┼─→ Network ──→ Server ──→ RAID/Disk Array
Client 2 ─┤
Client 3 ─┘
```

**Benefits of this architecture:**

1. **Easy sharing** - Access same files from any client machine
2. **Centralized administration** - Backup from one location instead of many
3. **Security** - Lock servers in secure room, control physical access
4. **Consistency** - Single source of truth for all data

---

## 2. Basic Distributed File System Architecture

### 2.1. Client-Server Model

**In plain English:** The client side pretends to be a normal file system while secretly sending messages over the network. The server side receives those messages and does the actual work with real disks.

**The components:**

```
Client Machine                    Server Machine
──────────────                    ──────────────
Application                       File Server
    ↓                                  ↑
Client-side FS ←─── Network ──────────┘
    ↓
Networking Layer              Networking Layer
                                       ↓
                                    Disks
```

**How a simple read works:**

1. Application calls `read(fd, buffer, size)`
2. Client-side FS sends READ message to server
3. Server reads block from disk (or cache)
4. Server sends data back over network
5. Client-side FS copies data into application buffer
6. Application continues, unaware of network activity

> 💡 **Insight**
>
> The beauty of this design is **transparency** - applications use the exact same system calls (open, read, write, close) whether files are local or remote. The complexity is hidden in the client-side file system implementation.

### 2.2. Transparent Access

**In plain English:** Programs shouldn't need to know or care that files are on a different computer. The distributed file system should look and act like a local file system.

**What transparency means:**

- Same API (open, read, write, close, mkdir, etc.)
- Same semantics (file descriptors, offsets, permissions)
- Only difference: potentially slower performance

**Example - identical code works for local and remote files:**

```c
// This code works the same whether /data is local or on NFS
int fd = open("/data/myfile.txt", O_RDONLY);
char buffer[4096];
read(fd, buffer, 4096);
close(fd);
```

---

## 3. Network File System (NFS) Overview

### 3.1. Open Protocol Approach

**In plain English:** Instead of building a secret, proprietary system, Sun published the exact message formats that clients and servers use to talk. Anyone could build compatible NFS servers and clients.

**Why this mattered:** Sun's open protocol approach created a competitive marketplace where multiple companies (Oracle/Sun, NetApp, EMC, IBM) could build NFS servers that all work with any NFS client.

> 💡 **Insight**
>
> Open protocols enable innovation through competition. By standardizing the communication format rather than the implementation, NFS allowed different companies to compete on performance, features, and price while maintaining compatibility.

### 3.2. NFSv2 Design Goals

**The primary goal:** Simple and fast server crash recovery.

**In plain English:** In a setup where many clients depend on one server, if the server goes down, everyone is stuck. The system must recover quickly when the server reboots.

**Why servers crash:**

- Power outages
- Software bugs (even good code has bugs)
- Memory leaks eventually exhaust memory
- Network partitions (network breaks, server unreachable)

⚠️ **Important consideration:** Every minute the server is down means all clients and their users are unproductive. Recovery speed is critical.

---

## 4. The Stateless Protocol Design

### 4.1. Understanding State in Protocols

**In plain English:** "State" means information the server remembers about what clients are doing. A stateful server tracks which files each client has open, where they're reading from, etc. A stateless server remembers nothing - each request contains everything needed.

**Example of stateful protocol (what NFS avoids):**

```c
// Client code
int fd = open("foo.txt", O_RDONLY);  // Returns fd = 3
read(fd, buffer, 100);                // Server needs to remember fd→file mapping
read(fd, buffer, 100);                // Server needs to track file position
close(fd);                            // Server needs to clean up fd
```

**What the server would track (stateful):**

```
Client 1: fd=3 → "foo.txt", position=0
Client 2: fd=5 → "bar.txt", position=1024
```

### 4.2. Why Stateless?

**The problem with state:**

If the server crashes and reboots, all that state (which files are open, file positions, etc.) is lost. Now clients have file descriptors that mean nothing to the server.

**Example crash scenario:**

```
1. Client: open("foo.txt") → server returns fd=3
2. Client: read(fd=3, buffer, 100) → succeeds
3. [SERVER CRASHES AND REBOOTS]
4. Client: read(fd=3, buffer, 100) → server says "fd=3? I have no idea what that is!"
```

**With stateless design:**

Each request includes the complete file identifier (file handle) and exact operation details:

```
Client: "Read 100 bytes at offset 0 from file /foo.txt"
Server: Returns data (no memory of request needed)
[SERVER CRASHES AND REBOOTS]
Client: "Read 100 bytes at offset 100 from file /foo.txt"
Server: Returns data (works fine, needs no previous context)
```

> 💡 **Insight**
>
> Statelessness trades increased message size (must send complete info each time) for dramatically simplified crash recovery. No special recovery protocol needed - just retry the request!

### 4.3. Crash Recovery Benefits

**Traditional stateful recovery (complex):**

1. Server crashes
2. Server reboots
3. Client detects server is back
4. Client sends "I had fd=3 open to foo.txt at position 100"
5. Server reconstructs state
6. Normal operation resumes

**NFS stateless recovery (simple):**

1. Server crashes
2. Server reboots
3. Client retries request with complete information
4. Server processes request (no state to rebuild)

**No special recovery protocol needed!**

---

## 5. NFSv2 Protocol Details

### 5.1. File Handles

**In plain English:** A file handle is like a complete mailing address for a file. Instead of saying "file descriptor 3" (which only means something if the server remembers what fd=3 refers to), you say exactly which disk, which file, and which version.

**File handle components:**

```
File Handle = [Volume ID] + [Inode Number] + [Generation Number]
              ↓             ↓                 ↓
              Which disk?   Which file?       Which version?
```

**Why each component matters:**

1. **Volume ID** - Server can export multiple file systems
2. **Inode number** - Identifies specific file on that volume
3. **Generation number** - Handles inode reuse (prevents accessing wrong file if inode is reused)

**Example:**

```
File Handle: [volume=2, inode=4587, gen=1]
→ Points to specific file on volume 2
→ If that inode is deleted and reused, gen becomes 2
→ Old file handle with gen=1 will be rejected
```

### 5.2. Core Protocol Operations

**The essential NFS operations:**

#### LOOKUP - Get File Handle

```
Request:  [dir_handle, filename]
Response: [file_handle, attributes]

Example:
  "What is the handle for 'foo.txt' in directory /"
  → Returns handle + metadata for foo.txt
```

#### READ - Read File Data

```
Request:  [file_handle, offset, count]
Response: [data, attributes]

Example:
  "Read 4096 bytes at offset 0 from [volume=2, inode=4587, gen=1]"
  → Returns the actual data bytes
```

#### WRITE - Write File Data

```
Request:  [file_handle, offset, count, data]
Response: [attributes]

Example:
  "Write 4096 bytes at offset 8192 to [volume=2, inode=4587, gen=1]"
  → Server writes data, returns updated attributes
```

#### GETATTR - Get File Attributes

```
Request:  [file_handle]
Response: [attributes]

Example:
  "What are the attributes for [volume=2, inode=4587, gen=1]?"
  → Returns size, timestamps, permissions, etc.
```

#### CREATE, REMOVE, MKDIR, RMDIR

```
CREATE:  [dir_handle, filename, attributes] → nothing
REMOVE:  [dir_handle, filename] → nothing
MKDIR:   [dir_handle, dirname, attributes] → new_dir_handle
RMDIR:   [dir_handle, dirname] → nothing
```

> 💡 **Insight**
>
> Notice how every operation includes the complete file handle. The server never needs to remember "which file was the client working on?" - each request is self-contained.

### 5.3. Protocol In Action

**Complete example: Reading /foo.txt**

```
Client Application          Client FS              Server
──────────────────          ─────────              ──────

fd = open("/foo.txt", O_RDONLY);
                            LOOKUP(root_fh, "foo.txt") →
                                                   Find "foo.txt" in /
                            ← file_handle + attrs

                            Store mapping: fd → file_handle
                            Store position: 0
← Return fd

read(fd, buf, 4096);
                            Get file_handle from fd
                            Get current position (0)

                            READ(file_handle, 0, 4096) →
                                                   Read from disk/cache
                            ← data + attrs

                            Update position: 0 → 4096
← Return data

read(fd, buf, 4096);
                            READ(file_handle, 4096, 4096) →
                                                   Read next chunk
                            ← data + attrs

                            Update position: 4096 → 8192
← Return data

close(fd);
                            Clean up local structures
                            Free fd mapping
                            (No message to server!)
← Return 0
```

**Key observations:**

1. **LOOKUP gets initial file handle** - Only done once per open
2. **Client tracks state** - File descriptor, current position
3. **Each READ is self-contained** - Includes handle, offset, count
4. **CLOSE is client-only** - No server notification (stateless!)

---

## 6. Handling Failures with Idempotency

### 6.1. Types of Failure

**In plain English:** When you send a message over a network and don't get a response, three things could have happened - but you can't tell which!

**The three cases:**

```
Case 1: Request Lost
Client ──X  [request dropped by network]
Server      (never received anything)

Case 2: Server Down
Client ──→  [request sent]
Server      (crashed, not processing requests)

Case 3: Reply Lost
Client ←─X  [reply dropped by network]
Server      (request processed, reply sent)
```

**The problem:** From the client's perspective, all three cases look identical - no response received. What should the client do?

### 6.2. Retry Strategy

**NFS solution: Always retry**

```
1. Send request
2. Set timeout timer (e.g., 5 seconds)
3. If reply received → Cancel timer, done!
4. If timer expires → Assume failure, retry request
5. Repeat until success
```

**Why this works:** Most NFS operations are **idempotent** - doing them multiple times has the same effect as doing them once.

### 6.3. Idempotent Operations

**In plain English:** An idempotent operation gives the same result whether you do it once or many times.

**Idempotent examples:**

```
✅ "Set counter to 5"
   First time: counter becomes 5
   Second time: counter becomes 5 (same result!)

✅ "Store 'hello' at address 0x1000"
   First time: memory[0x1000] = 'hello'
   Second time: memory[0x1000] = 'hello' (same result!)
```

**Non-idempotent examples:**

```
❌ "Increment counter"
   First time: counter = 1
   Second time: counter = 2 (different result!)

❌ "Append 'x' to file"
   First time: file = "x"
   Second time: file = "xx" (different result!)
```

**Why NFS operations are idempotent:**

**READ - Idempotent ✅**
```
READ(file_handle, offset=0, count=100)
→ Always returns same 100 bytes from offset 0
→ Safe to retry
```

**WRITE - Idempotent ✅**
```
WRITE(file_handle, offset=0, count=100, data="aaa...")
→ Always writes same data to same location
→ Result identical whether done once or twice
→ Safe to retry
```

**LOOKUP - Idempotent ✅**
```
LOOKUP(dir_handle, "foo.txt")
→ Always returns same file handle
→ Safe to retry
```

> 💡 **Insight**
>
> The key to WRITE idempotency is including the exact **offset** in every request. Unlike traditional file APIs where reads/writes advance an implicit position, NFS explicitly specifies the offset. Writing 100 bytes at offset 0 gives the same result whether done once or ten times.

**Handling all three failure cases:**

```
Case 1 (Request Lost):
  Client retries → Server receives request → Processes → Reply → Success

Case 2 (Server Down):
  Client retries while server down → Eventually server reboots
  → Client retries again → Server processes → Success

Case 3 (Reply Lost):
  Client retries → Server receives duplicate request
  → Processes again (same result because idempotent)
  → Reply reaches client this time → Success
```

⚠️ **Not everything is perfectly idempotent:**

```
MKDIR("newdir")
  First attempt: Succeeds, creates directory
  Reply lost, client retries
  Second attempt: Fails ("directory already exists")

Client sees: Failure (but directory actually was created!)
```

**Voltaire's Law:** Perfect is the enemy of the good. NFS handles the common cases cleanly. A few edge cases have quirks, but the overall design is simple and practical.

---

## 7. Client-Side Caching

### 7.1. Performance Problem

**In plain English:** Networks are slow compared to local disks and memory. Sending every read/write over the network kills performance.

**Performance comparison:**

```
Local memory:        ~100 nanoseconds
Local SSD:           ~100 microseconds (1000x slower than memory)
Network + remote disk: ~10 milliseconds (100x slower than local disk!)
```

**Without caching:**

```
read("foo.txt", 100 bytes) → 10ms network round-trip
read("foo.txt", 100 bytes) → 10ms network round-trip (again!)
read("foo.txt", 100 bytes) → 10ms network round-trip (again!)

Total: 30ms for operations that should be instant
```

### 7.2. Caching Strategy

**Solution: Cache data on client**

```
First read:  Client → Network → Server → Returns data
             Client caches data locally

Second read: Client serves from cache (no network!)
             ~100 nanoseconds instead of 10ms
```

**What gets cached:**

1. **File data** - The actual contents of files
2. **Metadata** - File attributes (size, timestamps, permissions)
3. **Directory contents** - Results of LOOKUP operations

**Write buffering:**

```
Application writes → Client cache (returns immediately!)
                     ↓
                  (Later) Flush to server
```

**Benefits:**

- Write returns instantly to application
- Multiple small writes can be batched
- Reduces network traffic

### 7.3. Cache Consistency Challenge

**In plain English:** When multiple clients cache the same file, how do they know when another client has changed it?

**The scenario:**

```
Initial state:
  Server has: file.txt = "version 1"

Time 1:
  Client 1 reads file.txt → Caches "version 1"

Time 2:
  Client 2 writes file.txt = "version 2" → Cached, not yet sent to server

Time 3:
  Client 3 reads file.txt → Gets "version 1" from server (stale!)

Time 4:
  Client 2 sends write to server
  Server now has "version 2"

Time 5:
  Client 1 reads file.txt → Gets "version 1" from cache (stale!)
```

**Two distinct problems emerge:**

1. **Update visibility** - When do other clients see changes?
2. **Stale cache** - How do clients know their cache is outdated?

---

## 8. Solving Cache Consistency

### 8.1. The Two Subproblems

**Problem 1: Update Visibility**

```
C2 writes file       [buffered in C2's cache]
C3 reads file        → Gets old version from server
                     → Confusing! Just wrote it on C2!
```

**Problem 2: Stale Cache**

```
C2 writes file       → Eventually reaches server
Server has new version
C1 reads file        → Returns cached old version
                     → Wrong! Server has newer data!
```

### 8.2. Flush-on-Close Semantics

**Solution to update visibility:** Flush all writes when file is closed.

**In plain English:** When you close a file, all your changes are immediately sent to the server. The next person who opens that file will see your changes.

**Example:**

```
Client 2:
  fd = open("file.txt", O_WRONLY)
  write(fd, "new data", 8)        // Buffered locally
  write(fd, "more data", 9)       // Buffered locally
  close(fd)                       // FLUSH TO SERVER NOW

Server now has all writes

Client 3:
  fd = open("file.txt", O_RDONLY) // Gets fresh data from server
  read(fd, buf, 100)              // Sees Client 2's changes
```

**Guarantee:** Close-to-open consistency

```
If:   Client A closes file
Then: Client B opening file sees all of A's writes
```

> 💡 **Insight**
>
> This is weaker than perfect consistency but matches common usage patterns. Most programs follow: open → write → close on one machine, then open → read on another machine.

### 8.3. Attribute Cache Solution

**Solution to stale cache:** Check if file changed before using cached data.

**Naive approach (too expensive):**

```
Before every read:
  Send GETATTR request to server
  If file modified → Invalidate cache, fetch fresh data
  If file unchanged → Use cached data

Problem: Floods server with GETATTR requests!
```

**Optimized approach: Attribute cache**

```
Attribute cache entry:
  {
    file_handle: [vol=2, inode=4587, gen=1]
    last_modified: 2025-10-15 10:30:00
    cached_at: 2025-10-15 10:30:00
    timeout: 3 seconds
  }

Before file access:
  1. Check attribute cache
  2. If entry exists and age < timeout → Use cached file data
  3. If entry missing or expired → Send GETATTR to server
     → Update attribute cache
     → Compare timestamps
     → Invalidate file cache if needed
```

**Timeline example:**

```
T=0s:   Client reads file
        → Sends GETATTR, gets timestamp: 10:30:00
        → Reads file data, caches it
        → Caches attributes (timeout at T=3s)

T=1s:   Application reads again
        → Checks attribute cache: valid (age=1s < 3s timeout)
        → Uses cached file data (no network!)

T=2s:   Application reads again
        → Checks attribute cache: valid (age=2s < 3s timeout)
        → Uses cached file data (no network!)

T=4s:   Application reads again
        → Attribute cache expired (age=4s > 3s timeout)
        → Sends GETATTR to server
        → Server replies: still 10:30:00
        → Uses cached file data
        → Refreshes attribute cache (timeout at T=7s)
```

### 8.4. Trade-offs and Oddities

**What can go wrong:**

```
T=0s:   Client 1 reads file.txt → Caches data and attributes
        (Attribute cache timeout: 3 seconds)

T=1s:   Client 2 writes file.txt → Closes, flushes to server
        Server timestamp now: 10:30:01

T=2s:   Client 1 reads file.txt
        → Attribute cache still valid! (age=2s < 3s)
        → Returns OLD DATA from cache
        → Even though server has new version!

T=4s:   Client 1 reads file.txt
        → Attribute cache expired (age=4s > 3s)
        → Checks with server, sees new timestamp
        → Invalidates cache, fetches new data
        → NOW sees Client 2's changes
```

**Weird but tolerable behavior:**

- Small window (seconds) where stale data might be returned
- Most applications don't notice
- Eventually consistent (within timeout period)

⚠️ **Warning:** This is why NFSv2 is sometimes called "weird" - the exact version of a file you get depends on cache timeout timing, not just who wrote what when.

**Performance vs. temporary file handling:**

```
Short-lived file example:
  create temp.txt
  write data to temp.txt
  close temp.txt          → FLUSHED TO SERVER (unnecessary!)
  delete temp.txt         → Tell server to delete

Better approach would:
  Keep temp files in client memory only
  Never send to server if deleted quickly

But NFS flush-on-close is rigid:
  ALL closed files flushed to server
```

---

## 9. Server-Side Write Handling

### 9.1. The Write Buffering Problem

**In plain English:** Servers have memory caches too. But if a server tells a client "your write succeeded" before actually saving to disk, a server crash can lose data in surprising ways.

**Dangerous scenario:**

```c
// Client application writes three blocks
write(fd, a_buffer, 4096);  // Write block 0 with a's
write(fd, b_buffer, 4096);  // Write block 1 with b's
write(fd, c_buffer, 4096);  // Write block 2 with c's
```

**Expected file contents after all writes:**

```
Block 0: aaaaaaaaaa...
Block 1: bbbbbbbbbb...
Block 2: cccccccccc...
```

**If server buffers writes in memory:**

```
Client sends WRITE(block 0, a's)
  → Server writes to disk, replies SUCCESS ✓

Client sends WRITE(block 1, b's)
  → Server buffers in memory, replies SUCCESS ✓ (DANGEROUS!)
  → [SERVER CRASHES - block 1 never written to disk]
  → [SERVER REBOOTS]

Client sends WRITE(block 2, c's)
  → Server writes to disk, replies SUCCESS ✓
```

**Actual file contents (corrupted!):**

```
Block 0: aaaaaaaaaa...  ✓
Block 1: [old data]     ✗ Lost!
Block 2: cccccccccc...  ✓
```

**Why this is catastrophic:**

- Client believes all writes succeeded
- File has old data in the middle
- Application may corrupt databases, documents, etc.
- Violates client's expectations about crash recovery

### 9.2. Commit-to-Disk Requirement

**NFS rule: WRITE must commit to stable storage before returning success**

```
Client sends WRITE request
  ↓
Server receives request
  ↓
Server writes to disk (or battery-backed RAM)
  ↓
Disk confirms write is durable
  ↓
Server sends SUCCESS reply to client
```

**Why this prevents corruption:**

```
Client sends WRITE(block 0, a's)
  → Server commits to disk
  → Replies SUCCESS

Client sends WRITE(block 1, b's)
  → Server writing to disk...
  → [SERVER CRASHES BEFORE REPLYING]

Client: "No reply for block 1 write!"
  → Timeout expires
  → Retries WRITE(block 1, b's)
  → Server (now rebooted) processes write
  → Replies SUCCESS

All writes succeed or client knows they failed!
```

### 9.3. Performance Solutions

**Problem:** Synchronous disk writes are slow (~10ms each)

**Solution 1: Battery-backed RAM**

```
WRITE request arrives
  ↓
Write to battery-backed RAM (~microseconds)
  ↓
RAM is "stable storage" (survives crashes via battery)
  ↓
Reply SUCCESS immediately
  ↓
Later: Flush RAM to disk in background
```

**How it works:**

- Special RAM with battery backup
- On power loss, battery keeps RAM alive long enough to flush to disk
- As safe as disk but fast as RAM

**Solution 2: Optimized file system layout**

```
Design file system to write sequentially:
- Log-structured file system (all writes sequential)
- Reduces disk seek time
- Can batch multiple writes

Result: Fast sequential writes instead of slow random writes
```

**Real-world example: NetApp**

NetApp built a business on fast NFS writes using:
1. Battery-backed NVRAM (non-volatile RAM)
2. WAFL file system (Write Anywhere File Layout)
3. Can reply to WRITE requests in microseconds, not milliseconds

---

## 10. VFS/Vnode Innovation

**In plain English:** To support NFS in operating systems, Sun invented a plugin architecture that lets multiple file systems coexist.

**The problem NFS introduced:**

```
Before NFS:
  Application → File System → Disk
  (One file system type)

With NFS:
  Application → ??? → Local disk or network?
  (Need to support both!)
```

**Solution: Virtual File System (VFS) layer**

```
Application
    ↓
System calls (open, read, write, close)
    ↓
VFS Layer (routing and caching)
    ↓
┌────────┬──────────┬──────────┐
│ ext4   │   NFS    │   tmpfs  │  (Specific implementations)
└────────┴──────────┴──────────┘
    ↓          ↓          ↓
  Disk     Network    Memory
```

**VFS operations (whole file system):**

- Mount/unmount file system
- Get file system statistics
- Sync dirty data to storage

**Vnode operations (individual files):**

- open, close
- read, write
- Create, delete files
- Get/set attributes

**Why this matters:**

```
To add a new file system:
  1. Implement VFS operations (mount, unmount, etc.)
  2. Implement vnode operations (read, write, etc.)
  3. Register with OS
  4. Done! Works with all existing programs
```

**Modern impact:**

- Linux: VFS layer supports ext4, btrfs, NFS, CIFS, etc.
- macOS: VFS supports APFS, HFS+, NFS, etc.
- Windows: Similar "Installable File System" architecture

> 💡 **Insight**
>
> Sometimes the infrastructure built to support an innovation outlives the innovation itself. Even if NFS usage declines, the VFS/vnode abstraction it required remains fundamental to modern operating systems.

---

## 11. Summary

### 🎯 Key Achievements of NFSv2

**Stateless protocol design:**
- Server maintains no client state
- Each request contains complete information
- Crash recovery is trivial: just retry
- No complex state reconstruction needed

**Idempotent operations:**
- Most operations produce same result when repeated
- Enables safe retry after timeout or crash
- READ, WRITE, LOOKUP all idempotent
- Unifies handling of lost messages and server crashes

**File handles instead of descriptors:**
- Complete addressing: [volume, inode, generation]
- No server-side tracking required
- Enables stateless operation
- Generation number prevents reuse issues

**Client-side caching for performance:**
- Cache file data and metadata locally
- Read from cache (nanoseconds vs. milliseconds)
- Write buffer for batching updates
- Dramatic performance improvement despite network

**Cache consistency solutions:**
- **Flush-on-close:** Writes propagate when file closed
- **Attribute cache:** Reduces GETATTR traffic
- **3-second timeout:** Balance freshness vs. performance
- Trade-off: Occasional stale reads for better performance

**Server write guarantees:**
- Must commit to stable storage before SUCCESS reply
- Prevents data loss from server crashes
- Requires battery-backed RAM or fast disk writes
- Critical for data integrity

### 🔧 Design Patterns We Learned

**Stateless protocols are powerful:**
```
Trade: Larger messages (include complete context)
Gain: Simple crash recovery, no state reconstruction
```

**Idempotency enables retries:**
```
Design operations to be safely repeatable
→ Handle timeouts and crashes uniformly
```

**Layered architecture:**
```
VFS/vnode abstraction
→ Multiple file system implementations
→ Transparent to applications
```

**Cache consistency is hard:**
```
Multiple caches + shared data
→ Need consistency protocols
→ Perfect consistency is expensive
→ Practical solutions accept occasional staleness
```

### 📊 Trade-offs Summary

| Aspect | Choice | Benefit | Cost |
|--------|--------|---------|------|
| Stateless | No server state | Fast crash recovery | Larger messages |
| Caching | Client caches | Fast reads/writes | Consistency challenges |
| Flush-on-close | Write on close() | Simple consistency | Temp files flushed unnecessarily |
| Attribute cache | 3s timeout | Reduce GETATTR traffic | Occasional stale reads |
| Sync writes | Commit before reply | Data integrity | Write performance hit |

### ⚠️ Limitations and Quirks

**Not perfectly consistent:**
- Attribute cache timeout creates staleness window
- Two clients can see different file versions briefly
- Eventually consistent (within seconds)

**MKDIR not perfectly idempotent:**
- First attempt: succeeds
- Retry: fails with "already exists"
- Client sees failure but operation actually worked

**Temporary files flushed unnecessarily:**
- Flush-on-close applies to all files
- Short-lived temp files sent to server
- Could be kept in client memory only

**Security initially weak:**
- Early NFS had minimal authentication
- Easy to impersonate other users
- Later versions integrated Kerberos

### 🎓 Lessons for Distributed Systems

1. **Design for failure** - Assume servers crash, networks drop packets
2. **Idempotency is valuable** - Makes retry safe and simple
3. **Stateless scales better** - Less coordination, easier recovery
4. **Perfect consistency is expensive** - Practical systems make trade-offs
5. **Open protocols enable ecosystems** - Competition drives innovation
6. **Implementation details become semantics** - Cache timeouts affect behavior

---

**Previous:** [Chapter 11: Data Integrity](chapter11-data-integrity.md) | **Next:** [Chapter 13: AFS and Summary](chapter13-summary.md)
