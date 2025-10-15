# 📁 Chapter 4: Files and Directories

## Table of Contents

1. [Introduction](#1-introduction)
2. [Files and Directories - Core Abstractions](#2-files-and-directories---core-abstractions)
   - 2.1. [The File Abstraction](#21-the-file-abstraction)
   - 2.2. [The Directory Abstraction](#22-the-directory-abstraction)
   - 2.3. [The Directory Tree](#23-the-directory-tree)
3. [Creating Files](#3-creating-files)
   - 3.1. [The open() System Call](#31-the-open-system-call)
   - 3.2. [File Descriptors](#32-file-descriptors)
4. [Reading and Writing Files](#4-reading-and-writing-files)
   - 4.1. [Sequential Access](#41-sequential-access)
   - 4.2. [Random Access with lseek()](#42-random-access-with-lseek)
   - 4.3. [The Open File Table](#43-the-open-file-table)
   - 4.4. [Sharing File Table Entries](#44-sharing-file-table-entries)
5. [File Synchronization](#5-file-synchronization)
6. [Renaming Files](#6-renaming-files)
7. [File Metadata](#7-file-metadata)
8. [Directory Operations](#8-directory-operations)
   - 8.1. [Making Directories](#81-making-directories)
   - 8.2. [Reading Directories](#82-reading-directories)
   - 8.3. [Deleting Directories](#83-deleting-directories)
9. [Hard Links](#9-hard-links)
10. [Symbolic Links](#10-symbolic-links)
11. [Permissions and Access Control](#11-permissions-and-access-control)
    - 11.1. [Permission Bits](#111-permission-bits)
    - 11.2. [Access Control Lists](#112-access-control-lists)
12. [Making and Mounting File Systems](#12-making-and-mounting-file-systems)
13. [Summary](#13-summary)

---

## 1. Introduction

**In plain English:** Imagine your operating system as a virtual librarian. It already gives each program its own CPU (via processes) and its own memory (via address spaces). Now it needs to manage the library's collection - how books (files) are stored, organized, and protected so they don't disappear when the lights go out.

**In technical terms:** Persistent storage devices store information permanently, unlike memory which loses contents on power loss. The OS must carefully manage these devices because this is where users keep data they truly care about.

### 🎯 The Core Challenge

> **How should the OS manage a persistent device? What are the APIs? What are the important aspects of the implementation?**

This chapter explores the interface for managing persistent data - the system calls you'll use when interacting with a UNIX file system.

> **💡 Insight**
>
> Persistence completes the virtualization puzzle: virtual CPU (process) + virtual memory (address space) + persistent storage (file system) = complete programming environment

---

## 2. Files and Directories - Core Abstractions

Two key abstractions emerged over time for virtualizing storage. Understanding these is fundamental to working with any file system.

### 2.1. The File Abstraction

**In plain English:** A file is like a numbered box that holds a sequence of bytes. You can read or write these bytes, but the box itself has a secret identity number that you rarely see.

**In technical terms:** A file is a linear array of bytes that can be read or written. Each file has a low-level name called an **inode number** that uniquely identifies it within the file system.

#### Key Characteristics

- **Linear byte array:** Simple, sequential organization
- **Inode number:** Low-level numeric identifier
- **Content-agnostic:** The OS doesn't interpret file structure (images, text, code - all treated as bytes)
- **Persistence guarantee:** Get back exactly what you stored

**Why it matters:** This simplicity makes files incredibly flexible. The same mechanism handles documents, programs, images, and databases without the OS needing special knowledge about each type.

### 2.2. The Directory Abstraction

**In plain English:** A directory is like a phone book. It maps human-friendly names like "vacation-photo.jpg" to the secret identity numbers (inodes) that the file system actually uses.

**In technical terms:** A directory has its own inode number, but contains a specific structure: a list of (human-readable name, inode number) pairs.

#### Directory Structure

```
Directory Entry Format:
┌─────────────────┬──────────────┐
│ User-Read Name  │ Inode Number │
├─────────────────┼──────────────┤
│ "foo"           │ 10           │
│ "bar.txt"       │ 25           │
│ "report.pdf"    │ 102          │
└─────────────────┴──────────────┘
```

**Each entry refers to:**
- A file (ends the path)
- Another directory (continues the path)

### 2.3. The Directory Tree

**In plain English:** By putting directories inside other directories, you build a tree structure - like a family tree for your files, starting from a single ancestor.

**In technical terms:** Directories can contain other directories, creating an arbitrary directory hierarchy rooted at `/` (the root directory). Files are accessed via pathnames using `/` as a separator.

#### Example Directory Structure

```
/                           (root)
├── foo/
│   └── bar.txt
└── bar/
    ├── bar/               (directory inside directory)
    └── foo/
        └── bar.txt
```

#### Valid Paths in This Tree

**Directories:**
- `/`
- `/foo`
- `/bar`
- `/bar/bar`
- `/bar/foo`

**Files:**
- `/foo/bar.txt`
- `/bar/foo/bar.txt`

**Note:** Files and directories can share names if they're in different locations. The full pathname ensures uniqueness.

#### File Naming Conventions

**In plain English:** File extensions like `.txt` or `.jpg` are just hints - the OS doesn't enforce them. A file named `photo.txt` could actually contain an image; the system doesn't check.

**Convention vs. enforcement:**
- `bar.txt` - arbitrary name + extension
- `.txt`, `.jpg`, `.mp3` - indicate file type
- No enforcement: convention only

> **💡 Insight**
>
> UNIX philosophy: "Everything is a file." Not just regular files, but devices, pipes, and even processes can be accessed through the file system. This uniform naming simplifies the conceptual model and makes the system more modular.

---

## 3. Creating Files

### 3.1. The open() System Call

**In plain English:** Creating a file is like checking out a library book. You tell the librarian (OS) you want a new book, what you plan to do with it, and who can read it. The librarian hands you a numbered ticket (file descriptor) to track your checkout.

**In technical terms:** The `open()` system call with the `O_CREAT` flag creates new files.

#### Creating a New File

```c
int fd = open("foo", O_CREAT|O_WRONLY|O_TRUNC, S_IRUSR|S_IWUSR);
```

**Flag breakdown:**
- `O_CREAT` - Create the file if it doesn't exist
- `O_WRONLY` - File can only be written to
- `O_TRUNC` - If file exists, truncate to zero bytes (remove existing content)

**Permissions (third parameter):**
- `S_IRUSR` - Owner can read
- `S_IWUSR` - Owner can write
- Result: `-rw-------` (readable and writable by owner only)

#### The Legacy creat() Call

The older `creat()` system call is equivalent to:

```c
int fd = creat("foo"); // Equivalent to open() with O_CREAT|O_WRONLY|O_TRUNC
```

> **📝 Note**
>
> When Ken Thompson was asked what he would do differently if redesigning UNIX, he replied: "I'd spell creat with an e."

### 3.2. File Descriptors

**In plain English:** A file descriptor is your ticket number. Once the librarian gives you this number, you use it for all future interactions - reading pages, writing notes, returning the book. Each person (process) has their own set of numbered tickets.

**In technical terms:** A file descriptor is an integer that's private per process. It's used to access files after opening them. Think of it as a **capability** - an opaque handle granting power to perform operations.

#### File Descriptor Properties

**Key characteristics:**
- Just an integer (e.g., 3, 4, 5, ...)
- Private per process
- Acts as a pointer to a `file` object
- Enables operations: `read()`, `write()`, etc.

#### OS Data Structure

The OS maintains file descriptors in the process structure:

```c
struct proc {
    ...
    struct file *ofile[NOFILE];  // Open files array
    ...
};
```

**Each entry:**
- Index = file descriptor number
- Value = pointer to `struct file` (tracks file state)

#### Standard File Descriptors

**Pre-opened files:**
- `0` - Standard input (stdin) - read input
- `1` - Standard output (stdout) - write output
- `2` - Standard error (stderr) - write errors

**Why first open() returns 3:**
When you open your first file, descriptors 0, 1, and 2 are already taken, so you get 3.

```c
int fd = open("myfile.txt", O_RDONLY);  // Returns 3 (first available)
```

> **💡 Insight**
>
> File descriptors abstract away the complexity of file access. You don't need to know about inodes, disk blocks, or caching - just use the descriptor number.

---

## 4. Reading and Writing Files

### 4.1. Sequential Access

**In plain English:** Reading a file sequentially is like reading a book from beginning to end. The system remembers your current page, so each time you say "read more," it continues from where you left off.

**In technical terms:** Sequential access involves reading or writing from start to finish, with the OS automatically tracking the current offset.

#### Example: Reading a File

Let's see what happens when the `cat` command reads a file:

```bash
$ echo hello > foo
$ cat foo
hello
```

#### Tracing with strace

**In plain English:** `strace` is like a surveillance camera for system calls - it shows exactly what a program asks the OS to do.

```bash
$ strace cat foo
...
open("foo", O_RDONLY|O_LARGEFILE) = 3
read(3, "hello\n", 4096) = 6
write(1, "hello\n", 6) = 6
hello
read(3, "", 4096) = 0
close(3) = 0
...
```

#### Understanding the Trace

**Step-by-step breakdown:**

1. **Open the file**
   ```c
   open("foo", O_RDONLY|O_LARGEFILE) = 3
   ```
   - `O_RDONLY` - Read-only access
   - `O_LARGEFILE` - Support 64-bit offsets
   - Returns file descriptor 3

2. **Read data**
   ```c
   read(3, "hello\n", 4096) = 6
   ```
   - Read from descriptor 3
   - Buffer size: 4096 bytes (4KB)
   - Actually read: 6 bytes ("hello" + newline)

3. **Write to stdout**
   ```c
   write(1, "hello\n", 6) = 6
   ```
   - Write to descriptor 1 (stdout)
   - Displays "hello" on screen

4. **Try to read more**
   ```c
   read(3, "", 4096) = 0
   ```
   - Returns 0 - indicates end of file

5. **Close the file**
   ```c
   close(3) = 0
   ```
   - Releases the file descriptor

#### The read() System Call

**Function signature:**
```c
ssize_t read(int fd, void *buffer, size_t count);
```

**Parameters:**
- `fd` - File descriptor (which file to read)
- `buffer` - Where to store the data
- `count` - Maximum bytes to read

**Return value:**
- Number of bytes actually read
- `0` indicates end of file
- `-1` indicates error

#### The write() System Call

**Function signature:**
```c
ssize_t write(int fd, const void *buffer, size_t count);
```

**Parameters:**
- `fd` - File descriptor (which file to write)
- `buffer` - Data to write
- `count` - Number of bytes to write

**Return value:**
- Number of bytes actually written
- `-1` indicates error

**Try it yourself:**
```bash
$ strace dd if=input.txt of=output.txt
```

### 4.2. Random Access with lseek()

**In plain English:** Sometimes you don't want to read a book from beginning to end - maybe you need to jump to chapter 5, or flip back to check something on page 42. `lseek()` lets you jump to any position in a file.

**In technical terms:** `lseek()` repositions the current offset within a file, enabling random access to specific locations.

#### The lseek() System Call

**Function signature:**
```c
off_t lseek(int fildes, off_t offset, int whence);
```

**Parameters:**
- `fildes` - File descriptor
- `offset` - Position to seek to
- `whence` - How to interpret offset

#### The whence Parameter

**Three modes of seeking:**

1. **SEEK_SET** - Absolute position
   ```c
   lseek(fd, 100, SEEK_SET);  // Go to byte 100 from start
   ```

2. **SEEK_CUR** - Relative to current position
   ```c
   lseek(fd, 50, SEEK_CUR);   // Move forward 50 bytes
   lseek(fd, -20, SEEK_CUR);  // Move backward 20 bytes
   ```

3. **SEEK_END** - Relative to end of file
   ```c
   lseek(fd, 0, SEEK_END);    // Go to end of file
   lseek(fd, -100, SEEK_END); // Go to 100 bytes before end
   ```

#### Example: Random Access

```
File: [0...199][200...249][250...299]
      ↑         ↑           ↑
      Start     Middle      End

lseek(fd, 200, SEEK_SET);  // Jump to offset 200
read(fd, buffer, 50);       // Read bytes 200-249
// Current offset now: 250
```

#### Offset Tracking

The OS tracks a "current offset" for each open file:

**Two ways offset changes:**
1. **Implicitly** - After each `read()` or `write()`, offset advances by bytes transferred
2. **Explicitly** - Using `lseek()` to jump to a specific position

> **⚠️ Warning: lseek() Does NOT Perform Disk Seek**
>
> The confusingly-named `lseek()` only changes a variable in OS memory. It does NOT cause any disk I/O. However, subsequent `read()` or `write()` operations at the new offset may cause disk seeks if the data is in a different disk location.

### 4.3. The Open File Table

**In plain English:** The OS keeps a master ledger of all open files. Each entry tracks: which actual file is being accessed, where you are in that file (current offset), and what you're allowed to do (read/write).

**In technical terms:** Each file descriptor points to an entry in the system-wide **open file table**. Each entry contains metadata about the file access.

#### File Structure (xv6)

```c
struct file {
    int ref;                    // Reference count
    char readable;              // Can read?
    char writable;              // Can write?
    struct inode *ip;           // Points to actual file (inode)
    uint off;                   // Current offset
};
```

**Fields explained:**
- `ref` - How many descriptors point here
- `readable` - Permission to read
- `writable` - Permission to write
- `ip` - Points to the inode (file data structure on disk)
- `off` - Current position in file

#### System-Wide Open File Table

```c
struct {
    struct spinlock lock;
    struct file file[NFILE];
} ftable;
```

This array holds ALL currently open files in the system.

#### Example 1: Sequential Reads

Let's trace a process reading a 300-byte file in 100-byte chunks:

```
System Call                    | Return | Current Offset
-------------------------------|--------|---------------
fd = open("file", O_RDONLY);   | 3      | 0
read(fd, buffer, 100);         | 100    | 100
read(fd, buffer, 100);         | 100    | 200
read(fd, buffer, 100);         | 100    | 300
read(fd, buffer, 100);         | 0      | 300  (EOF)
close(fd);                     | 0      | -
```

**Observations:**
- Offset starts at 0
- Each read advances offset by bytes read
- Read returns 0 at end of file
- Offset stays at 300 (doesn't go past EOF)

#### Example 2: Multiple Opens

Opening the same file twice creates separate offsets:

```
System Call                    | Return | OFT[10] | OFT[11]
                               |        | Offset  | Offset
-------------------------------|--------|---------|--------
fd1 = open("file", O_RDONLY);  | 3      | 0       | -
fd2 = open("file", O_RDONLY);  | 4      | 0       | 0
read(fd1, buffer1, 100);       | 100    | 100     | 0
read(fd2, buffer2, 100);       | 100    | 100     | 100
close(fd1);                    | 0      | -       | 100
close(fd2);                    | 0      | -       | -
```

**Key insight:** Each `open()` creates a separate entry in the open file table, with independent offset tracking.

#### Example 3: Using lseek()

```
System Call                    | Return | Current Offset
-------------------------------|--------|---------------
fd = open("file", O_RDONLY);   | 3      | 0
lseek(fd, 200, SEEK_SET);      | 200    | 200
read(fd, buffer, 50);          | 50     | 250
close(fd);                     | 0      | -
```

**What happened:**
- `lseek()` jumped to offset 200
- `read()` got 50 bytes starting at 200
- Offset advanced to 250

> **💡 Insight**
>
> The open file table decouples file descriptors from actual files. Multiple descriptors can point to the same entry (shared offset) or different entries (independent offsets).

### 4.4. Sharing File Table Entries

**In plain English:** Usually, each person reading a book has their own bookmark. But sometimes a parent and child want to share a bookmark - when the child moves it, the parent sees the new position too.

**In technical terms:** In special cases, multiple file descriptors can share the same open file table entry, meaning they share the same current offset.

#### Case 1: fork() Shares Entries

When a process calls `fork()`, the parent and child share open file table entries.

**Example code:**

```c
int main(int argc, char *argv[]) {
    int fd = open("file.txt", O_RDONLY);
    assert(fd >= 0);

    int rc = fork();
    if (rc == 0) {
        // Child process
        rc = lseek(fd, 10, SEEK_SET);
        printf("child: offset %d\n", rc);
    } else if (rc > 0) {
        // Parent process
        (void) wait(NULL);
        printf("parent: offset %d\n",
               (int) lseek(fd, 0, SEEK_CUR));
    }
    return 0;
}
```

**Output:**
```
child: offset 10
parent: offset 10
```

**What happened:**
1. Parent opens file (offset = 0)
2. Parent forks, creating child
3. **Both share the same open file table entry**
4. Child seeks to offset 10
5. Parent sees offset 10 (shared!)

#### Visual Representation

```
Parent Process              Open File Table           File System
┌──────────────┐           ┌─────────────┐          ┌──────────┐
│ File Desc 3  │────┐      │  refcnt: 2  │          │  Inode   │
└──────────────┘    │      │  off: 10    │──────────│  #1000   │
                    └─────→│  inode: ───→│          │(file.txt)│
Child Process               │             │          └──────────┘
┌──────────────┐           └─────────────┘
│ File Desc 3  │────────────────┘
└──────────────┘
```

**Key insight:** Reference count = 2 (both descriptors point here)

#### Why This Is Useful

**Cooperative processes** can write to the same output file without coordination:

```c
// Both parent and child can write sequentially
// to the same file without overlapping
if (fork() == 0) {
    write(fd, "child data\n", 11);
} else {
    write(fd, "parent data\n", 12);
}
```

The shared offset ensures writes don't overlap.

#### Case 2: dup() Creates Shared Entries

**In plain English:** `dup()` is like photocopying your library card. Both cards access the same account, so if you check out a book with one card, it shows on both.

**In technical terms:** `dup()` creates a new file descriptor that refers to the same open file table entry.

**Example code:**

```c
int main(int argc, char *argv[]) {
    int fd = open("README", O_RDONLY);
    assert(fd >= 0);

    int fd2 = dup(fd);
    // Now fd and fd2 can be used interchangeably
    // They share the same offset

    return 0;
}
```

**Use case:** The `dup2()` variant is crucial for shell output redirection:

```bash
$ command > output.txt
```

The shell uses `dup2()` to redirect stdout (descriptor 1) to the output file.

> **💡 Insight**
>
> Understanding when file table entries are shared vs. separate is crucial for correct concurrent file access. Shared entries provide coordination; separate entries provide independence.

---

## 5. File Synchronization

**In plain English:** When you click "save," your data doesn't immediately write to disk - it goes to a fast memory buffer first. The OS promises to write it "soon" (maybe 5-30 seconds later). But what if you need an absolute guarantee it's on disk RIGHT NOW?

**In technical terms:** Most `write()` calls buffer data in memory for performance. The `fsync()` system call forces immediate write to persistent storage.

### The fsync() System Call

**Function signature:**
```c
int fsync(int fd);
```

**What it does:**
- Flushes all dirty (unwritten) data for the specified file to disk
- Blocks until all writes complete
- Returns only when data is truly persisted

### When You Need fsync()

**Critical for:**
- Database management systems (DBMS)
- Recovery protocols
- Financial transactions
- Any application requiring durability guarantees

### Example: Ensuring Persistence

```c
int fd = open("foo", O_CREAT|O_WRONLY|O_TRUNC, S_IRUSR|S_IWUSR);
assert(fd > -1);

int rc = write(fd, buffer, size);
assert(rc == size);

rc = fsync(fd);  // Force write to disk NOW
assert(rc == 0);

// Data is now guaranteed on disk
```

### The Directory Synchronization Gotcha

**Surprise:** `fsync()` on a file is often not enough!

**In plain English:** If you create a new file and `fsync()` it, the file's contents are on disk. But the directory entry pointing to that file might not be! If the system crashes, the file data exists on disk but is unreachable because the directory doesn't know about it.

**The solution:**

```c
// Create and write file
int fd = open("foo", O_CREAT|O_WRONLY|O_TRUNC, S_IRUSR|S_IWUSR);
write(fd, buffer, size);
fsync(fd);  // Flush file data

// Also sync the directory
int dirfd = open(".", O_RDONLY);
fsync(dirfd);  // Flush directory entry
close(dirfd);

close(fd);
```

> **⚠️ Warning: Common Bug**
>
> Forgetting to sync the directory is a frequent application-level bug. Many programs correctly `fsync()` files but forget the directory, leading to data loss after crashes.

### Performance Trade-offs

**Without fsync():**
- ✅ Fast writes (buffered in memory)
- ❌ Risk of data loss on crash

**With fsync():**
- ✅ Guaranteed durability
- ❌ Much slower (waits for disk I/O)

**Best practice:** Use `fsync()` only when durability is critical, not for every write.

> **💡 Insight**
>
> The tension between performance and durability is fundamental in storage systems. `fsync()` gives applications control over this trade-off, but using it correctly is surprisingly tricky.

---

## 6. Renaming Files

**In plain English:** Renaming a file is like swapping one label for another - but here's the magic: either the old label is in place or the new one is, never both, never neither. Even if a tornado strikes mid-rename, you won't end up with a half-renamed file.

**In technical terms:** The `rename()` system call atomically changes a file's name, providing critical guarantees for system crashes.

### The rename() System Call

**Function signature:**
```c
int rename(const char *old, const char *new);
```

**Command-line equivalent:**
```bash
$ mv foo bar  # Rename foo to bar
```

### The Atomicity Guarantee

**Key property:** `rename()` is **atomic** with respect to system crashes.

**What this means:**
- If the system crashes during rename...
- The file will be named either `old` or `new`
- **Never** some in-between state
- **Never** both names
- **Never** neither name

### Use Case: Atomic File Updates

**The problem:** How do you update a file safely? If you crash mid-update, you want either the complete old version or the complete new version - never a partial update.

**The solution:** Write-and-rename pattern

#### Example: Text Editor Saving

```c
// Edit file: foo.txt
// Goal: Insert a line without risking corruption

// Step 1: Write new version to temporary file
int fd = open("foo.txt.tmp", O_WRONLY|O_CREAT|O_TRUNC, S_IRUSR|S_IWUSR);
write(fd, buffer, size);  // Write complete new version
fsync(fd);                // Ensure data on disk
close(fd);

// Step 2: Atomically swap temporary file into place
rename("foo.txt.tmp", "foo.txt");

// Result: foo.txt is now updated atomically
// If crash occurred before rename, old version still intact
// If crash occurred during/after rename, new version in place
```

#### Timeline Visualization

```
Before rename:
  foo.txt      ──→  [old content on disk]
  foo.txt.tmp  ──→  [new content on disk]

During rename (atomic):
  ⚡ System crash here = safe! ⚡

After rename:
  foo.txt      ──→  [new content on disk]
  foo.txt.tmp  ──→  [deleted]
```

### Why Atomicity Matters

**Without atomic rename:**
```c
// DANGEROUS: Non-atomic approach
open("foo.txt");
write(...);      // ⚡ Crash here = partially written file = data loss!
close();
```

**With atomic rename:**
```c
// SAFE: Atomic approach
open("foo.txt.tmp");
write(...);      // ⚡ Crash here = old file still intact
fsync();
close();
rename("foo.txt.tmp", "foo.txt");  // ⚡ Crash during/after = new file in place
```

> **💡 Insight**
>
> Atomic operations are fundamental building blocks for reliable systems. `rename()` provides one of the few atomic file operations in UNIX, making it crucial for implementing crash-safe updates.

---

## 7. File Metadata

**In plain English:** Beyond a file's content, the OS tracks vital statistics: Who owns it? How big is it? When was it last modified? This information is called metadata - "data about data."

**In technical terms:** File systems maintain extensive metadata for each file, stored in a persistent data structure called an **inode**.

### The stat() System Call

**Function signature:**
```c
int stat(const char *pathname, struct stat *statbuf);
int fstat(int fd, struct stat *statbuf);
```

**Two variants:**
- `stat()` - Takes pathname
- `fstat()` - Takes file descriptor

### The stat Structure

```c
struct stat {
    dev_t     st_dev;      // Device ID containing file
    ino_t     st_ino;      // Inode number (low-level name)
    mode_t    st_mode;     // File type and permissions
    nlink_t   st_nlink;    // Number of hard links
    uid_t     st_uid;      // User ID of owner
    gid_t     st_gid;      // Group ID of owner
    dev_t     st_rdev;     // Device ID (if special file)
    off_t     st_size;     // Total size in bytes
    blksize_t st_blksize;  // Block size for I/O
    blkcnt_t  st_blocks;   // Number of blocks allocated
    time_t    st_atime;    // Time of last access
    time_t    st_mtime;    // Time of last modification
    time_t    st_ctime;    // Time of last status change
};
```

### Command-Line Example

```bash
$ echo hello > file
$ stat file
File: 'file'
Size: 6             Blocks: 8          IO Block: 4096   regular file
Device: 811h/2065d  Inode: 67158084    Links: 1
Access: (0640/-rw-r-----) Uid: (30686/ remzi) Gid: (30686/ remzi)
Access: 2011-05-03 15:50:20.157594748 -0500
Modify: 2011-05-03 15:50:20.157594748 -0500
Change: 2011-05-03 15:50:20.157594748 -0500
```

### Understanding Metadata Fields

#### Size Information
- **st_size** - Actual file size in bytes (6 bytes: "hello\n")
- **st_blocks** - Disk blocks allocated (8 blocks)
- **st_blksize** - Optimal I/O block size (4096 bytes)

#### Identity
- **st_ino** - Inode number: 67158084 (file's true name in the file system)
- **st_dev** - Device ID: which disk/partition

#### Ownership
- **st_uid** - User ID: 30686 (user "remzi")
- **st_gid** - Group ID: 30686 (group "remzi")

#### Links
- **st_nlink** - Hard link count: 1 (only one name points to this file)

#### Timestamps
- **st_atime** - Last access (read)
- **st_mtime** - Last modification (write)
- **st_ctime** - Last status change (metadata change)

### The Inode

**In plain English:** An inode is like a file's birth certificate - a permanent record containing all the important information about the file except its name and content.

**In technical terms:** An inode is a persistent data structure stored on disk that contains metadata about a file.

**Key properties:**
- One inode per file
- Stores all metadata
- Identified by inode number
- Lives on disk permanently
- Active inodes cached in memory for performance

**What's NOT in the inode:**
- File name (stored in directory)
- File data/contents (stored in data blocks)

> **💡 Insight**
>
> The separation between inodes (metadata) and directories (names) enables hard links - multiple names can point to the same inode.

---

## 8. Directory Operations

**In plain English:** Directories are special files that organize other files. You can't write to them directly like regular files - the OS controls their format. But you can create them, read their contents, and delete them using special system calls.

### 8.1. Making Directories

**The mkdir() system call:**

```c
int mkdir(const char *pathname, mode_t mode);
```

**Command-line example:**

```bash
$ strace mkdir foo
...
mkdir("foo", 0777) = 0
...
```

**What gets created:**
- A new directory
- Two special entries automatically added:
  - `.` (dot) - refers to the directory itself
  - `..` (dot-dot) - refers to the parent directory

#### Viewing Directory Contents

```bash
$ mkdir foo
$ ls -a foo
./  ../

$ ls -al foo
total 8
drwxr-x---  2 remzi remzi    6 Apr 30 16:17 ./
drwxr-x--- 26 remzi remzi 4096 Apr 30 16:17 ../
```

**Observations:**
- "Empty" directories actually contain `.` and `..`
- `.` points to inode of current directory
- `..` points to inode of parent directory

> **💡 Insight**
>
> The `.` and `..` entries enable relative path navigation (`cd ..`) and make the directory tree traversable in both directions.

### 8.2. Reading Directories

**In plain English:** Reading a directory is different from reading a regular file. You can't just `open()` and `read()` it - you need special directory-specific functions.

**In technical terms:** Use `opendir()`, `readdir()`, and `closedir()` to iterate through directory entries.

#### Example: Listing Directory Contents

```c
int main(int argc, char *argv[]) {
    DIR *dp = opendir(".");
    assert(dp != NULL);

    struct dirent *d;
    while ((d = readdir(dp)) != NULL) {
        printf("%lu %s\n",
               (unsigned long) d->d_ino,
               d->d_name);
    }

    closedir(dp);
    return 0;
}
```

**Output might look like:**
```
67158084 .
67158000 ..
67158085 foo.txt
67158086 bar.txt
```

#### The dirent Structure

```c
struct dirent {
    char           d_name[256];  // Filename
    ino_t          d_ino;        // Inode number
    off_t          d_off;        // Offset to next entry
    unsigned short d_reclen;     // Length of this record
    unsigned char  d_type;       // Type of file
};
```

**Why directories are "light on information":**
- Basically just (name, inode number) mappings
- For detailed info (size, permissions, etc.), call `stat()` on each file

#### Getting Detailed Information

```bash
$ ls        # Uses readdir() - fast, minimal info
foo.txt
bar.txt

$ ls -l     # Uses readdir() + stat() on each file - slower, detailed info
-rw-r--r-- 1 remzi remzi 1024 May 3 10:15 foo.txt
-rw-r--r-- 1 remzi remzi 2048 May 3 10:16 bar.txt
```

**Verify with strace:**
```bash
$ strace ls        # See readdir() calls
$ strace ls -l     # See readdir() + many stat() calls
```

### 8.3. Deleting Directories

**The rmdir() system call:**

```c
int rmdir(const char *pathname);
```

**Command-line:**
```bash
$ rmdir foo
```

#### Safety Requirement

**Must be empty:** Directory can only contain `.` and `..` entries

**Example:**
```bash
$ mkdir test
$ touch test/file.txt
$ rmdir test
rmdir: test: Directory not empty

$ rm test/file.txt
$ rmdir test
(success - directory deleted)
```

**Why this restriction:**
- Prevents accidental deletion of large amounts of data
- Force user to explicitly delete contents first

**Recursive deletion:**
```bash
$ rm -r test     # Delete directory and all contents (dangerous!)
$ rm -rf test    # Force recursive delete (very dangerous!)
```

> **⚠️ Warning: Powerful Commands**
>
> `rm -rf *` from the root directory will delete your entire file system. Always double-check your current directory before running recursive delete commands!

---

## 9. Hard Links

**In plain English:** A hard link is like having two completely equal doorways to the same room. Both doors have different signs on them, but they open to the exact same space. Removing one door doesn't affect the other - the room only disappears when you remove the last door.

**In technical terms:** A hard link creates an additional directory entry (name) that points to the same inode as an existing file. Both names are completely equal - there's no concept of "original" vs "link."

### The Mystery of unlink()

**Question:** Why is the system call to delete a file called `unlink()` instead of `delete()` or `remove()`?

**Answer:** Because creating a file actually does two things:
1. Creates an inode (the actual file data structure)
2. Creates a link (directory entry) from a name to that inode

Deleting a file removes a link, hence `unlink()`.

### Creating Hard Links

**The link() system call:**

```c
int link(const char *oldpath, const char *newpath);
```

**Command-line:**

```bash
$ echo hello > file
$ cat file
hello

$ ln file file2        # Create hard link
$ cat file2
hello
```

**What happened:**
- `file` and `file2` are both names for the same inode
- No data was copied
- Both names are equally "real"

### Viewing Inode Numbers

```bash
$ ls -i file file2
67158084 file
67158084 file2
```

**Key observation:** Both names point to inode 67158084

### How Hard Links Work

**Visual representation:**

```
Directory               Inode Layer            Disk
┌────────────┐         ┌──────────┐          ┌─────────┐
│ file  ─────┼────────→│  Inode   │─────────→│ "hello" │
└────────────┘    │    │ #67158084│          │  data   │
                  │    │ size: 6  │          └─────────┘
┌────────────┐    │    │ links: 2 │
│ file2 ─────┼────┘    │ blocks:..│
└────────────┘         └──────────┘
```

**Key insight:** Both directory entries point to the same inode.

### Understanding unlink()

**When you create a file:**
1. OS creates an inode (tracks size, blocks, permissions, etc.)
2. OS creates a directory entry linking name → inode
3. Inode reference count = 1

**When you create a hard link:**
1. OS creates another directory entry pointing to the same inode
2. Inode reference count increments to 2

**When you call unlink():**
1. OS removes the directory entry (the name)
2. OS decrements inode reference count
3. **Only when reference count reaches 0:**
   - OS frees the inode
   - OS frees the data blocks
   - File is truly deleted

### Reference Count Example

```bash
$ echo hello > file
$ stat file
... Inode: 67158084 Links: 1 ...

$ ln file file2
$ stat file
... Inode: 67158084 Links: 2 ...

$ stat file2
... Inode: 67158084 Links: 2 ...

$ ln file2 file3
$ stat file
... Inode: 67158084 Links: 3 ...

$ rm file
$ stat file2
... Inode: 67158084 Links: 2 ...

$ rm file2
$ stat file3
... Inode: 67158084 Links: 1 ...

$ rm file3
(file truly deleted - reference count reached 0)
```

### Demonstrating File Persistence

```bash
$ echo hello > file
$ ln file file2
$ rm file              # Remove original name
removed 'file'

$ cat file2            # File still accessible!
hello

$ stat file2
... Links: 1 ...       # Last remaining link
```

**Why this works:** The inode and data blocks remain as long as at least one link exists.

> **💡 Insight**
>
> Understanding hard links explains many UNIX behaviors: why "deleting" doesn't immediately free space, why you can modify a running executable, and why directory entries are separate from file data.

---

## 10. Symbolic Links

**In plain English:** A symbolic link (symlink) is like a sticky note that says "the actual file is over there." Unlike a hard link (which is another equally-real door to the same room), a symlink is just a signpost pointing to a path. If you move or delete the target file, the signpost still points to the old location - now pointing to nothing.

**In technical terms:** A symbolic link is a special file type that contains a pathname. When you access a symlink, the OS reads the pathname and redirects to that location.

### Creating Symbolic Links

**Command-line:**

```bash
$ echo hello > file
$ ln -s file file2     # Create symbolic link
$ cat file2
hello
```

**Looks similar to hard links, but they're fundamentally different!**

### Hard Links vs. Symbolic Links

#### Key Differences

**Hard link:**
- Another directory entry to the same inode
- Same inode number as original
- Both names completely equal
- Cannot cross file systems
- Cannot link to directories
- File exists as long as any link exists

**Symbolic link:**
- A separate file of type "symbolic link"
- Different inode number
- Contains pathname as data
- Can cross file systems
- Can link to directories
- If target is deleted, link becomes dangling

### Examining with stat

```bash
$ echo hello > file
$ ln -s file file2

$ stat file
... regular file ...

$ stat file2
... symbolic link ...
```

### Examining with ls

```bash
$ ls -al
-rw-r----- 1 remzi remzi 6 May 3 19:10 file
lrwxrwxrwx 1 remzi remzi 4 May 3 19:10 file2 -> file
```

**Reading the output:**
- First character: `l` = symbolic link (vs. `-` for file, `d` for directory)
- Size: 4 bytes (length of the pathname "file")
- Arrow: `file2 -> file` (shows what it points to)

### Symbolic Link Size

**Why is file2 4 bytes?**

The symlink stores the pathname as its data:

```
file2 (symlink) contains: "file" (4 characters = 4 bytes)
```

**Longer pathname = larger symlink:**

```bash
$ echo hello > alongerfilename
$ ln -s alongerfilename file3

$ ls -al alongerfilename file3
-rw-r----- 1 remzi remzi  6 May 3 19:17 alongerfilename
lrwxrwxrwx 1 remzi remzi 15 May 3 19:17 file3 -> alongerfilename
```

**15 bytes = length of "alongerfilename"**

### Dangling References

**The danger of symbolic links:**

```bash
$ echo hello > file
$ ln -s file file2
$ cat file2
hello

$ rm file              # Delete the target!
removed 'file'

$ cat file2
cat: file2: No such file or directory
```

**What happened:**
- `file2` still exists as a symlink
- `file2` contains the pathname "file"
- But "file" no longer exists
- Following the symlink leads nowhere

**Visual representation:**

```
Before deletion:
file2 (symlink) ──"file"──→ file (inode 100) ──→ [data: "hello"]

After deletion:
file2 (symlink) ──"file"──→ ??? (pathname doesn't exist)
```

### When to Use Each Type

**Use hard links when:**
- You want equal names for a file
- You need it to work within a single file system
- You want the file to persist until all links are removed
- You're linking to regular files (not directories)

**Use symbolic links when:**
- You need to link across file systems
- You need to link to directories
- You want to see which is the "link" vs. "original"
- You're okay with the link breaking if target moves/deletes

### Limitations of Hard Links

**Cannot hard link to directories:**
```bash
$ mkdir dir
$ ln dir dir2
ln: dir: Is a directory
```

**Why?** Risk of creating cycles in the directory tree.

**Cannot hard link across file systems:**
```bash
$ ln /disk1/file /disk2/file2
ln: failed to create hard link: Invalid cross-device link
```

**Why?** Inode numbers are only unique within a file system.

**Symbolic links don't have these limitations:**
```bash
$ ln -s dir dir2             # Works!
$ ln -s /disk1/file /disk2/file2  # Works!
```

> **💡 Insight**
>
> Symbolic links trade simplicity for flexibility. Hard links are "true" names but have restrictions. Symlinks are more flexible but introduce the possibility of dangling references.

---

## 11. Permissions and Access Control

**In plain English:** Unlike virtual CPUs and memory (which are private to each process), files are often shared. The file system needs mechanisms to control who can access what - from simple owner/group/other permissions to sophisticated access control lists.

**In technical terms:** File systems provide multiple mechanisms for enabling various degrees of sharing, from traditional UNIX permission bits to more advanced access control lists (ACLs).

### 11.1. Permission Bits

**The classic UNIX permission model:**

```bash
$ ls -l foo.txt
-rw-r--r-- 1 remzi wheel 0 Aug 24 16:29 foo.txt
```

**Breaking down the permissions:** `-rw-r--r--`

```
-    rw-    r--    r--
│    │      │      │
│    │      │      └── Others (everyone else)
│    │      └───────── Group (members of 'wheel')
│    └──────────────── Owner (user 'remzi')
└───────────────────── File type (- = regular file)
```

#### File Type Character

**First character indicates type:**
- `-` Regular file
- `d` Directory
- `l` Symbolic link
- `c` Character device
- `b` Block device
- `p` Named pipe
- `s` Socket

#### Permission Bits

**Three groups of three bits each:**

```
Owner      Group      Others
r w x      r w x      r w x
│ │ │      │ │ │      │ │ │
│ │ │      │ │ │      │ │ └── Execute
│ │ │      │ │ │      │ └──── Write
│ │ │      │ │ │      └────── Read
│ │ │      │ │ └────────────── Execute
│ │ │      │ └──────────────── Write
│ │ │      └────────────────── Read
│ │ └──────────────────────── Execute
│ └────────────────────────── Write
└──────────────────────────── Read
```

**Bit meanings:**
- `r` (read) - Can read file contents (4)
- `w` (write) - Can modify file contents (2)
- `x` (execute) - Can execute file as program (1)

#### Example Breakdown

**`-rw-r--r--`**
- Owner: `rw-` (read + write, no execute)
- Group: `r--` (read only)
- Others: `r--` (read only)

**`-rwxr-xr-x`**
- Owner: `rwx` (read + write + execute)
- Group: `r-x` (read + execute)
- Others: `r-x` (read + execute)

### Changing Permissions

**The chmod command:**

```bash
$ chmod 600 foo.txt
```

**Numeric notation:**
- Each digit is the sum of: read(4) + write(2) + execute(1)
- Three digits: owner, group, others

**Examples:**
- `600` = owner: rw- (4+2=6), group: --- (0), others: --- (0)
- `644` = owner: rw- (6), group: r-- (4), others: r-- (4)
- `755` = owner: rwx (7), group: r-x (5), others: r-x (5)
- `777` = owner: rwx (7), group: rwx (7), others: rwx (7) [dangerous!]

**Symbolic notation:**

```bash
$ chmod u+x file     # Add execute for user (owner)
$ chmod g-w file     # Remove write for group
$ chmod o=r file     # Set others to read-only
$ chmod a+r file     # Add read for all (user, group, others)
```

### Execute Permission

#### For Regular Files

**Determines if file can be run as a program:**

```bash
$ cat hello.sh
#!/bin/bash
echo "Hello, world!"

$ ./hello.sh
bash: ./hello.sh: Permission denied

$ chmod +x hello.sh    # Add execute permission
$ ./hello.sh
Hello, world!
```

#### For Directories

**Different meaning for directories:**

**Execute bit controls:**
- Can `cd` into the directory
- Can access files within (if you know their names)
- Combined with write: can create files

**Examples:**

```bash
$ mkdir test
$ chmod 755 test     # rwxr-xr-x
$ cd test            # Works (execute bit set)

$ chmod 644 test     # rw-r--r-- (no execute)
$ cd test
bash: cd: test: Permission denied
```

**Write + Execute:**
```bash
$ chmod 755 dir      # rwxr-xr-x
$ touch dir/file     # Works (write + execute)

$ chmod 555 dir      # r-xr-xr-x (no write)
$ touch dir/file2
touch: cannot touch 'dir/file2': Permission denied
```

### 11.2. Access Control Lists

**In plain English:** Permission bits are simple but limited - you can only specify owner, group, and everyone else. Access Control Lists (ACLs) let you create precise rules: "Alice can read, Bob can read and write, Carol cannot access at all."

**In technical terms:** ACLs provide a more general and powerful way to represent exactly who can access a given resource, supporting arbitrary lists of users and permissions.

### Example: AFS Access Control

**The AFS distributed file system uses ACLs:**

```bash
$ fs listacl private
Access list for private is
Normal rights:
  system:administrators rlidwka
  remzi rlidwka
```

**Permission characters:**
- `r` - Read
- `l` - Lookup (list directory)
- `i` - Insert (create files)
- `d` - Delete (remove files)
- `w` - Write (modify files)
- `k` - Lock (file locking)
- `a` - Administer (change ACL)

**Granting access to specific user:**

```bash
$ fs setacl private/ andrea rl
```

Now `andrea` can read and lookup files in the `private/` directory.

### ACLs vs. Permission Bits

**Permission bits:**
- ✅ Simple, fast
- ✅ Sufficient for most cases
- ❌ Limited to owner/group/others
- ❌ Can't specify multiple users

**ACLs:**
- ✅ Fine-grained control
- ✅ Support arbitrary user lists
- ✅ More expressive permissions
- ❌ More complex to manage
- ❌ Not universally supported

### Superuser Privileges

**In plain English:** Every system needs an administrator who can override normal permissions - someone who can delete old files, fix broken permissions, or recover data. This powerful user is both necessary and dangerous.

**The superuser (root):**
- Can access all files regardless of permissions
- Can modify any file system metadata
- Required for system administration
- **Major security risk** if compromised

**Distributed file systems:**
- AFS uses `system:administrators` group
- Trusted users can access all files
- Same security risk as single superuser

> **⚠️ Warning: TOCTTOU Problem**
>
> **Time Of Check To Time Of Use (TOCTTOU):**
>
> If a privileged service checks a file's safety (e.g., "is this owned by the user?"), then operates on it, an attacker can swap the file between the check and the operation.
>
> **Example attack:**
> 1. Mail server (running as root) checks that inbox file is safe
> 2. Attacker swaps inbox file with `/etc/passwd` (using `rename()`)
> 3. Mail server writes email to "inbox" - actually writing to `/etc/passwd`!
> 4. Attacker gains root access
>
> **Mitigation:**
> - Reduce services running as root
> - Use `O_NOFOLLOW` flag (prevents following symlinks)
> - Use file descriptors (not pathnames) after checking
> - Use transactional file systems (rare)

> **💡 Insight**
>
> Security is about managing trust and limiting damage. Permission systems try to balance usability (files must be shareable) with security (files must be protected). There's no perfect solution - only trade-offs.

---

## 12. Making and Mounting File Systems

**In plain English:** Imagine you have several separate filing cabinets, each with its own organization system. "Mounting" is how you combine them into one unified system - making it look like everything is in one huge, organized space rather than separate cabinets.

**In technical terms:** A complete directory tree is assembled from multiple underlying file systems using `mkfs` (to create file systems) and `mount` (to attach them to the tree).

### Creating File Systems

**The mkfs tool:**

```bash
$ mkfs -t ext3 /dev/sda1
```

**What this does:**
1. Takes a device (disk partition): `/dev/sda1`
2. Takes a file system type: `ext3`
3. Writes an empty file system to the device
4. Creates a root directory
5. Initializes metadata structures

**Think of it as:** Formatting a blank hard drive - setting up the organizational structure so it can store files.

### Mounting File Systems

**The mount command:**

```bash
$ mount -t ext3 /dev/sda1 /home/users
```

**What this does:**
- Takes an existing directory (`/home/users`) as the **mount point**
- Attaches the file system from `/dev/sda1` to that point
- Makes the new file system's contents accessible at that location

### Mount Example

**Before mounting:**

```
/home/users/                 (empty or existing directory)

/dev/sda1 contains:          (unmounted file system)
  root/
  ├── a/
  │   └── foo
  └── b/
      └── foo
```

**After mounting:**

```bash
$ mount -t ext3 /dev/sda1 /home/users
$ ls /home/users/
a b
```

**Now accessible via:**
- `/home/users/` → root of the mounted file system
- `/home/users/a/` → directory `a`
- `/home/users/b/` → directory `b`
- `/home/users/a/foo` → file `foo` in directory `a`
- `/home/users/b/foo` → file `foo` in directory `b`

### Visual Representation

```
Main File System Tree
/
├── home/
│   └── users/  ──────┐ (mount point)
│                     │
│   ┌─────────────────┘
│   │  Mounted File System (/dev/sda1)
│   └→ /
│      ├── a/
│      │   └── foo
│      └── b/
│          └── foo
└── var/
    └── log/
```

**Key insight:** From the user's perspective, everything looks like one unified tree. The fact that `/home/users/` is on a different physical device is transparent.

### Viewing Mounted File Systems

```bash
$ mount
/dev/sda1 on / type ext3 (rw)
proc on /proc type proc (rw)
sysfs on /sys type sysfs (rw)
/dev/sda5 on /tmp type ext3 (rw)
/dev/sda7 on /var/vice/cache type ext3 (rw)
tmpfs on /dev/shm type tmpfs (rw)
AFS on /afs type afs (rw)
```

**Reading this output:**

```
Device          Mount Point    Type        Options
/dev/sda1   →   /          →   ext3    →   (rw)
/dev/sda5   →   /tmp       →   ext3    →   (rw)
tmpfs       →   /dev/shm   →   tmpfs   →   (rw)
```

**Different file system types:**
- `ext3` - Standard disk-based file system
- `proc` - Virtual file system for process information
- `sysfs` - Virtual file system for kernel information
- `tmpfs` - RAM-based temporary file system
- `afs` - Distributed file system

### Why Mounting Matters

**Benefits of unified namespace:**
1. **Uniform naming** - All files accessible via pathnames from `/`
2. **Transparent access** - Users don't need to know which physical device
3. **Flexible organization** - Can put `/home` on one disk, `/tmp` on another
4. **Heterogeneous systems** - Mix different file system types seamlessly

**Common mounting patterns:**

```
/               Main system partition (ext4)
/home           User files (separate disk, ext4)
/tmp            Temporary files (tmpfs - RAM disk)
/mnt/usb        USB drive (vfat/exfat)
/media/cdrom    CD-ROM (iso9660)
```

**Practical example:**

```bash
# Separate partition for user data
$ mount /dev/sdb1 /home

# RAM-based temporary storage (fast, but lost on reboot)
$ mount -t tmpfs tmpfs /tmp

# Mount USB drive
$ mount /dev/sdc1 /mnt/usb

# Mount network file system
$ mount -t nfs server:/share /mnt/network
```

> **💡 Insight**
>
> Mounting is a powerful abstraction that hides complexity. Multiple physical devices, different file system types, even network storage - all unified into one coherent tree. This is the "everything is a file" philosophy taken to the file system level.

---

## 13. Summary

### 🎯 Core Abstractions

**File:**
- Linear array of bytes
- Low-level name: inode number
- Content-agnostic (OS doesn't interpret structure)
- Accessed via file descriptors after `open()`

**Directory:**
- Collection of (name, inode number) mappings
- Special entries: `.` (self) and `..` (parent)
- Also has an inode number
- Cannot be written directly (only via operations like creating files)

**Directory tree:**
- Hierarchical organization from root (`/`)
- Enables uniform naming of all resources
- Built by mounting multiple file systems

### 🔧 Essential System Calls

#### File Operations
- `open()` - Create/open file, returns file descriptor
- `read()` - Read bytes from file
- `write()` - Write bytes to file
- `lseek()` - Change current offset (random access)
- `fsync()` - Force write to disk
- `close()` - Release file descriptor

#### Directory Operations
- `mkdir()` - Create directory
- `opendir()`, `readdir()`, `closedir()` - Read directory contents
- `rmdir()` - Delete empty directory

#### Metadata Operations
- `stat()`, `fstat()` - Get file metadata
- `chmod()` - Change permissions
- `rename()` - Atomically rename file

#### Link Operations
- `link()` - Create hard link
- `symlink()` - Create symbolic link
- `unlink()` - Remove link (delete file when count reaches 0)

### 📊 Key Data Structures

**Per-process:**
```c
struct proc {
    struct file *ofile[NOFILE];  // Array of file descriptors
};
```

**System-wide:**
```c
struct file {
    int ref;              // Reference count
    char readable;        // Permissions
    char writable;
    struct inode *ip;     // Points to actual file
    uint off;             // Current offset
};
```

**On-disk:**
```c
struct inode {
    // Metadata: size, permissions, timestamps
    // Block pointers: where data is stored
    // Reference count: number of hard links
};
```

### 💡 Critical Concepts

**File descriptors:**
- Private per process
- Point to open file table entries
- Standard descriptors: 0 (stdin), 1 (stdout), 2 (stderr)

**Open file table:**
- System-wide table of open files
- Tracks current offset
- Can be shared (via `fork()` or `dup()`) or separate

**Inodes:**
- Persistent data structure containing metadata
- Referenced by inode number
- Separate from file names (enabling hard links)

**Hard links:**
- Multiple names → same inode
- All names equal (no "original")
- File deleted only when last link removed
- Cannot cross file systems or link to directories

**Symbolic links:**
- Special file containing pathname
- Can cross file systems and link to directories
- Can become dangling if target deleted

**Atomic operations:**
- `rename()` - Critical for safe updates
- Either old name or new name, never in-between

**Synchronization:**
- `write()` is buffered (fast, but risky)
- `fsync()` forces to disk (safe, but slow)
- Don't forget to sync the directory too!

**Permissions:**
- Basic: owner/group/others with read/write/execute
- Advanced: ACLs for fine-grained control
- Superuser can override (security risk)

**Mounting:**
- Combines multiple file systems into unified tree
- Transparent to applications
- Enables flexible storage organization

### ⚠️ Common Pitfalls

1. **Forgetting to check return values**
   ```c
   int fd = open("file", O_RDONLY);
   // Always check: if (fd < 0) handle error
   ```

2. **Not syncing directories after creating files**
   ```c
   fsync(fd);        // Syncs file data
   fsync(dir_fd);    // Must also sync directory!
   ```

3. **Assuming writes are immediate**
   ```c
   write(fd, data, size);  // Buffered! Use fsync() for guarantee
   ```

4. **TOCTTOU vulnerabilities in privileged code**
   ```c
   // DON'T: check file, then operate (attacker can swap file)
   // DO: open file, then fstat() descriptor
   ```

5. **Using rm -rf without absolute certainty**
   ```bash
   # Always verify current directory first!
   $ pwd
   $ rm -rf *
   ```

### 🚀 Best Practices

1. **Always check return values** - Every system call can fail
2. **Use atomic operations** - `rename()` for safe updates
3. **Close file descriptors** - Avoid resource leaks
4. **Use appropriate link type** - Hard links for same FS, symlinks for flexibility
5. **Set minimal permissions** - Principle of least privilege
6. **Sync when durability matters** - Don't skip `fsync()` for critical data
7. **Use `strace` to learn** - See what programs actually do

### 📚 Further Learning

**To master the file system interface:**
- Read the man pages: `man 2 open`, `man 2 read`, etc.
- Use `strace` extensively to see system calls in action
- Experiment: create files, links, directories - see what breaks
- Read Stevens' "Advanced Programming in the UNIX Environment"
- Understand your file system implementation (next chapters!)

> **💡 Final Insight**
>
> The file system interface is deceptively simple - a handful of system calls can express incredibly complex behavior. But simplicity doesn't mean easy - the interactions between these calls, especially with concurrency and crashes, create subtle challenges. Master the basics in this chapter, and you'll be prepared to understand how file systems actually work under the hood.

---

**Previous:** [Chapter 3: RAID](chapter3-raid.md) | **Next:** [Chapter 5: File System Implementation](chapter5-file-system-implementation.md)
