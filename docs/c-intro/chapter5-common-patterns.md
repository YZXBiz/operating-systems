# 🔍 Chapter 5: Common C Patterns for Python Developers

_Recognizing idiomatic C code when you see it_

---

## Table of Contents

1. [Error Handling Patterns](#1-error-handling-patterns)
   - 1.1. [Return Codes](#11-return-codes)
   - 1.2. [NULL Checks](#12-null-checks)
   - 1.3. [errno and perror](#13-errno-and-perror)
2. [String Manipulation Patterns](#2-string-manipulation-patterns)
   - 2.1. [Null-Terminated Loops](#21-null-terminated-loops)
   - 2.2. [String Building](#22-string-building)
   - 2.3. [Safe String Operations](#23-safe-string-operations)
3. [Memory Management Patterns](#3-memory-management-patterns)
   - 3.1. [Constructor/Destructor Pattern](#31-constructordestructor-pattern)
   - 3.2. [Ownership Transfer](#32-ownership-transfer)
   - 3.3. [Resource Cleanup](#33-resource-cleanup)
4. [Array and Buffer Patterns](#4-array-and-buffer-patterns)
   - 4.1. [Fixed-Size Buffers](#41-fixed-size-buffers)
   - 4.2. [Dynamic Arrays](#42-dynamic-arrays)
   - 4.3. [Sentinel Values](#43-sentinel-values)
5. [Iteration Patterns](#5-iteration-patterns)
   - 5.1. [Index-Based Loops](#51-index-based-loops)
   - 5.2. [Pointer-Based Iteration](#52-pointer-based-iteration)
   - 5.3. [Linked List Traversal](#53-linked-list-traversal)
6. [Preprocessor Patterns](#6-preprocessor-patterns)
   - 6.1. [Constants and Macros](#61-constants-and-macros)
   - 6.2. [Conditional Compilation](#62-conditional-compilation)
   - 6.3. [Common Macro Idioms](#63-common-macro-idioms)
7. [Type and Casting Patterns](#7-type-and-casting-patterns)
8. [Common Idioms You'll See in Real Code](#8-common-idioms-youll-see-in-real-code)
9. [Summary: Reading C Code Like a Native](#9-summary-reading-c-code-like-a-native)

---

## 1. Error Handling Patterns

### 1.1. Return Codes

**In plain English:** Python uses exceptions. C uses return values to indicate success or failure.

**In technical terms:** Functions return integer status codes (0 or 1 for success, negative for error) or NULL for pointer-returning functions. Callers must check return values.

```python
# Python - exceptions
try:
    file = open("data.txt", "r")
    content = file.read()
except FileNotFoundError:
    print("File not found")
except IOError as e:
    print(f"Error: {e}")
finally:
    file.close()
```

```c
// C - return codes
#include <stdio.h>
#include <errno.h>

FILE *file = fopen("data.txt", "r");
if (file == NULL) {  // Check for error
    perror("Error opening file");  // Print error message
    return 1;  // Return error code
}

// Use file...

if (fclose(file) != 0) {  // Check close for errors too
    perror("Error closing file");
    return 1;
}

return 0;  // Success
```

**Common patterns:**

```c
// Pattern 1: Return 0 for success, -1 for error
int do_something() {
    if (error_condition) {
        return -1;  // Error
    }
    // Do work...
    return 0;  // Success
}

if (do_something() != 0) {
    // Handle error
}

// Pattern 2: Return pointer, NULL on error
char* allocate_buffer(size_t size) {
    char *buf = malloc(size);
    if (buf == NULL) {
        return NULL;  // Allocation failed
    }
    return buf;
}

char *buffer = allocate_buffer(1024);
if (buffer == NULL) {
    // Handle allocation failure
}

// Pattern 3: Return boolean-style (0=false, non-zero=true)
int is_valid(int x) {
    return x > 0 && x < 100;
}

if (is_valid(value)) {  // Non-zero = true
    // Valid
}
```

### 1.2. NULL Checks

**Defensive programming: always check pointers**

```c
// Pattern: Check after malloc
int *arr = malloc(n * sizeof(int));
if (arr == NULL) {
    fprintf(stderr, "Out of memory\n");
    return -1;
}

// Pattern: Check before dereference
if (ptr != NULL) {
    printf("%d\n", *ptr);
}

// Pattern: Early return on null
void process(Data *data) {
    if (data == NULL) {
        return;  // Guard clause
    }
    // Process data...
}
```

### 1.3. errno and perror

**System calls set global `errno` on error:**

```c
#include <errno.h>
#include <string.h>

FILE *f = fopen("missing.txt", "r");
if (f == NULL) {
    // Method 1: perror (prints descriptive message)
    perror("fopen failed");  // Prints: "fopen failed: No such file or directory"

    // Method 2: strerror (get error string)
    printf("Error: %s\n", strerror(errno));

    // Method 3: Check errno directly
    if (errno == ENOENT) {
        printf("File not found\n");
    }
}
```

---

## 2. String Manipulation Patterns

### 2.1. Null-Terminated Loops

**Pattern: Iterate until `\0`**

```c
// Count string length
int my_strlen(const char *s) {
    int len = 0;
    while (s[len] != '\0') {  // Or: while (s[len])
        len++;
    }
    return len;
}

// Copy string
void my_strcpy(char *dest, const char *src) {
    int i = 0;
    while (src[i] != '\0') {
        dest[i] = src[i];
        i++;
    }
    dest[i] = '\0';  // Don't forget null terminator!
}

// Pointer-based version (very common in C)
void my_strcpy_ptr(char *dest, const char *src) {
    while (*src != '\0') {  // Or: while (*src)
        *dest++ = *src++;   // Copy and advance both pointers
    }
    *dest = '\0';
}

// Ultra-compact version (you'll see this)
void my_strcpy_compact(char *dest, const char *src) {
    while ((*dest++ = *src++))  // Copy until \0, which terminates loop
        ;
}
```

**Python comparison:**

```python
# Python - no null terminator needed
def my_len(s):
    return len(s)  # Built-in, O(1)

def my_copy(s):
    return s  # Strings are immutable, just reference
```

### 2.2. String Building

**Python makes this easy; C requires manual buffer management:**

```python
# Python
parts = []
for i in range(5):
    parts.append(f"Item {i}")
result = ", ".join(parts)
```

```c
// C - fixed buffer with snprintf
char buffer[256] = "";
char temp[64];
int offset = 0;

for (int i = 0; i < 5; i++) {
    snprintf(temp, sizeof(temp), "Item %d", i);
    if (i > 0) {
        offset += snprintf(buffer + offset, sizeof(buffer) - offset, ", ");
    }
    offset += snprintf(buffer + offset, sizeof(buffer) - offset, "%s", temp);
}
```

### 2.3. Safe String Operations

**Common bug: buffer overflow. Safe alternatives:**

```c
// UNSAFE - no bounds checking
char dest[10];
strcpy(dest, "This is a very long string");  // OVERFLOW!

// SAFE - use strncpy (but tricky)
strncpy(dest, source, sizeof(dest) - 1);
dest[sizeof(dest) - 1] = '\0';  // Ensure null termination

// SAFER - use snprintf
snprintf(dest, sizeof(dest), "%s", source);  // Always null-terminates

// SAFEST - check sizes
if (strlen(source) < sizeof(dest)) {
    strcpy(dest, source);
} else {
    fprintf(stderr, "String too long\n");
}
```

---

## 3. Memory Management Patterns

### 3.1. Constructor/Destructor Pattern

**Python has `__init__` and `__del__`. C uses functions:**

```python
# Python
class Buffer:
    def __init__(self, size):
        self.data = [0] * size
        self.size = size

    def __del__(self):
        pass  # Cleanup (usually automatic)

buf = Buffer(100)
del buf  # Destructor called
```

```c
// C - manual constructor/destructor pattern
typedef struct {
    int *data;
    int size;
} Buffer;

// Constructor
Buffer* buffer_create(int size) {
    Buffer *buf = malloc(sizeof(Buffer));
    if (buf == NULL) return NULL;

    buf->data = malloc(size * sizeof(int));
    if (buf->data == NULL) {
        free(buf);  // Clean up partial allocation
        return NULL;
    }

    buf->size = size;
    return buf;
}

// Destructor
void buffer_destroy(Buffer *buf) {
    if (buf != NULL) {
        free(buf->data);  // Free inner allocation
        free(buf);         // Free struct itself
    }
}

// Usage
Buffer *buf = buffer_create(100);
if (buf != NULL) {
    // Use buf...
    buffer_destroy(buf);  // Manual cleanup
}
```

### 3.2. Ownership Transfer

**Pattern: Caller owns returned memory**

```c
// Function returns allocated memory
char* create_message(const char *name) {
    char *msg = malloc(100);
    if (msg != NULL) {
        snprintf(msg, 100, "Hello, %s!", name);
    }
    return msg;  // Caller must free!
}

// Usage
char *greeting = create_message("Alice");
if (greeting != NULL) {
    printf("%s\n", greeting);
    free(greeting);  // Caller's responsibility
}
```

**Pattern: Function takes ownership**

```c
// Function frees the passed pointer
void consume_buffer(char *buf) {
    // Use buf...
    free(buf);  // Takes ownership, frees it
}

char *data = malloc(1000);
consume_buffer(data);  // Don't use data after this!
// data = NULL;  // Good practice
```

### 3.3. Resource Cleanup

**Pattern: goto for cleanup (controversial but common)**

```c
int process_files() {
    FILE *input = NULL;
    FILE *output = NULL;
    char *buffer = NULL;
    int result = -1;

    input = fopen("input.txt", "r");
    if (input == NULL) goto cleanup;

    output = fopen("output.txt", "w");
    if (output == NULL) goto cleanup;

    buffer = malloc(1024);
    if (buffer == NULL) goto cleanup;

    // Do work...
    result = 0;  // Success

cleanup:
    if (buffer) free(buffer);
    if (output) fclose(output);
    if (input) fclose(input);
    return result;
}
```

---

## 4. Array and Buffer Patterns

### 4.1. Fixed-Size Buffers

**Very common pattern: stack-allocated buffers**

```c
// Pattern: Fixed-size char buffer
char buffer[256];
fgets(buffer, sizeof(buffer), stdin);

// Pattern: Buffer for string formatting
char message[128];
snprintf(message, sizeof(message), "Value: %d", x);

// Pattern: Path buffer (common size constants)
char path[PATH_MAX];  // Usually 4096
realpath("file.txt", path);
```

### 4.2. Dynamic Arrays

**Pattern: Growable array (manual implementation)**

```c
typedef struct {
    int *data;
    int size;
    int capacity;
} DynamicArray;

void array_init(DynamicArray *arr) {
    arr->data = NULL;
    arr->size = 0;
    arr->capacity = 0;
}

int array_push(DynamicArray *arr, int value) {
    if (arr->size >= arr->capacity) {
        // Grow capacity (common: double it)
        int new_cap = arr->capacity == 0 ? 8 : arr->capacity * 2;
        int *new_data = realloc(arr->data, new_cap * sizeof(int));
        if (new_data == NULL) return -1;

        arr->data = new_data;
        arr->capacity = new_cap;
    }

    arr->data[arr->size++] = value;
    return 0;
}

void array_free(DynamicArray *arr) {
    free(arr->data);
    arr->data = NULL;
    arr->size = arr->capacity = 0;
}
```

### 4.3. Sentinel Values

**Pattern: Use special value to mark end**

```c
// -1 as sentinel
int numbers[] = {10, 20, 30, 40, -1};  // -1 marks end

int i = 0;
while (numbers[i] != -1) {
    printf("%d\n", numbers[i]);
    i++;
}

// NULL as sentinel for pointer arrays
char *names[] = {"Alice", "Bob", "Charlie", NULL};

for (int i = 0; names[i] != NULL; i++) {
    printf("%s\n", names[i]);
}
```

---

## 5. Iteration Patterns

### 5.1. Index-Based Loops

**Most explicit and common:**

```c
int arr[] = {1, 2, 3, 4, 5};
int size = sizeof(arr) / sizeof(arr[0]);

// Forward iteration
for (int i = 0; i < size; i++) {
    printf("%d\n", arr[i]);
}

// Reverse iteration
for (int i = size - 1; i >= 0; i--) {
    printf("%d\n", arr[i]);
}
```

### 5.2. Pointer-Based Iteration

**Efficient and idiomatic:**

```c
int arr[] = {1, 2, 3, 4, 5};
int *end = arr + 5;

// Iterate with pointer
for (int *p = arr; p < end; p++) {
    printf("%d\n", *p);
}

// String iteration (common pattern)
char *str = "hello";
for (char *p = str; *p != '\0'; p++) {
    printf("%c\n", *p);
}

// Ultra-compact (you'll see this)
while (*str) {
    printf("%c", *str++);
}
```

### 5.3. Linked List Traversal

**Classic pattern:**

```c
typedef struct Node {
    int data;
    struct Node *next;
} Node;

// Traverse and print
Node *current = head;
while (current != NULL) {
    printf("%d -> ", current->data);
    current = current->next;
}
printf("NULL\n");

// Find element
Node *find(Node *head, int target) {
    for (Node *cur = head; cur != NULL; cur = cur->next) {
        if (cur->data == target) {
            return cur;
        }
    }
    return NULL;
}
```

---

## 6. Preprocessor Patterns

### 6.1. Constants and Macros

```c
// Constants
#define MAX_SIZE 1000
#define PI 3.14159
#define TRUE 1
#define FALSE 0

// Function-like macros
#define MAX(a, b) ((a) > (b) ? (a) : (b))
#define MIN(a, b) ((a) < (b) ? (a) : (b))
#define SQUARE(x) ((x) * (x))

// Be careful with side effects!
int x = 5;
int y = SQUARE(x++);  // Expands to: ((x++) * (x++)) - x incremented twice!
```

### 6.2. Conditional Compilation

```c
// Debug vs Release
#ifdef DEBUG
    #define LOG(msg) printf("DEBUG: %s\n", msg)
#else
    #define LOG(msg)  // No-op in release
#endif

// Platform-specific code
#ifdef _WIN32
    #include <windows.h>
    #define PATH_SEP '\\'
#else
    #include <unistd.h>
    #define PATH_SEP '/'
#endif

// Feature flags
#if defined(FEATURE_X) && !defined(FEATURE_Y)
    // Code for specific configuration
#endif
```

### 6.3. Common Macro Idioms

```c
// Array size (very common)
#define ARRAY_SIZE(arr) (sizeof(arr) / sizeof((arr)[0]))

int numbers[] = {1, 2, 3, 4, 5};
int count = ARRAY_SIZE(numbers);  // 5

// Stringify
#define STRINGIFY(x) #x
printf("%s\n", STRINGIFY(hello));  // Prints: "hello"

// Token pasting
#define CONCAT(a, b) a##b
int CONCAT(var, 123) = 42;  // Creates: int var123 = 42;

// Do-while(0) trick for multi-statement macros
#define SWAP(a, b) do { \
    typeof(a) temp = (a); \
    (a) = (b); \
    (b) = temp; \
} while (0)

// Usage (works correctly in all contexts)
if (condition)
    SWAP(x, y);  // Semicolon required, no ambiguity
```

---

## 7. Type and Casting Patterns

**Pattern: Casting for generic functions**

```c
// void* for generic pointers
void* memcpy(void *dest, const void *src, size_t n) {
    char *d = (char*)dest;  // Cast to byte pointer
    const char *s = (const char*)src;
    for (size_t i = 0; i < n; i++) {
        d[i] = s[i];
    }
    return dest;
}

// Callback pattern with void*
typedef int (*compare_fn)(const void*, const void*);

void sort(void *base, size_t nmemb, size_t size, compare_fn cmp) {
    // Generic sorting
}

int compare_ints(const void *a, const void *b) {
    int ia = *(const int*)a;  // Cast back to int*
    int ib = *(const int*)b;
    return ia - ib;
}
```

---

## 8. Common Idioms You'll See in Real Code

### Idiom 1: Comma Operator in Loops

```c
// Multiple updates in for loop
for (int i = 0, j = n-1; i < j; i++, j--) {
    // i and j move toward each other
}
```

### Idiom 2: Ternary for Conditionals

```c
int max = (a > b) ? a : b;
char *status = (error) ? "failed" : "success";
```

### Idiom 3: Short-Circuit Evaluation

```c
// Check pointer before dereferencing
if (ptr && ptr->valid) {
    // Safe: ptr checked first
}

// Set default value
int value = get_config() || DEFAULT_VALUE;
```

### Idiom 4: Assignment in Condition

```c
// Read until EOF
char buffer[256];
while (fgets(buffer, sizeof(buffer), file) != NULL) {
    // Process buffer
}

// Common pattern with malloc
if ((data = malloc(size)) == NULL) {
    // Handle error
}
```

### Idiom 5: Pointer Arithmetic for Arrays

```c
// End pointer
int arr[10];
int *end = arr + 10;
for (int *p = arr; p < end; p++) {
    *p = 0;
}

// String termination
char *find_end(char *str) {
    while (*str) str++;
    return str;
}
```

### Idiom 6: XOR Swap (Clever but avoid)

```c
// Swap without temp variable (don't actually use this)
a ^= b;
b ^= a;
a ^= b;
// Now a and b are swapped (confusing, use temp instead)
```

### Idiom 7: Bit Manipulation

```c
// Set bit n
x |= (1 << n);

// Clear bit n
x &= ~(1 << n);

// Toggle bit n
x ^= (1 << n);

// Check if bit n is set
if (x & (1 << n)) {
    // Bit is set
}
```

---

## 9. Summary: Reading C Code Like a Native

### Recognition Patterns

**When you see...**

| Pattern | Meaning |
|---------|---------|
| `if (ptr == NULL)` | Error checking after allocation/function call |
| `while (*str)` | Iterate through null-terminated string |
| `for (int i = 0; i < n; i++)` | Index-based array iteration |
| `ptr->field` | Accessing struct field via pointer |
| `(type*)malloc(...)` | Heap allocation with cast (in C++) |
| `#define MACRO` | Compile-time constant or text substitution |
| `static int count` | File-local variable or persistent function variable |
| `func(..., int *out)` | Output parameter pattern |
| `return 0;` in main | Success exit code |
| `goto cleanup` | Resource cleanup pattern |

---

### Mental Checklist for Reading C

✅ **Memory:** Who allocates? Who frees? Stack or heap?
✅ **Pointers:** Where does this point? Could it be NULL?
✅ **Buffers:** Fixed or dynamic size? Checked for overflow?
✅ **Strings:** Null-terminated? Length tracked?
✅ **Errors:** What indicates failure? Is it checked?
✅ **Ownership:** Who owns this memory? When is it freed?
✅ **Types:** What's the actual type? Any casting?

---

### Compare Python to C Patterns

```python
# Python: List comprehension
squares = [x**2 for x in range(10)]

# Python: Exception handling
try:
    data = risky_operation()
except Exception as e:
    print(f"Error: {e}")

# Python: With statement
with open("file.txt") as f:
    content = f.read()

# Python: String formatting
msg = f"Hello, {name}! You are {age} years old."
```

```c
// C: Manual loop
int squares[10];
for (int i = 0; i < 10; i++) {
    squares[i] = i * i;
}

// C: Return code checking
int result = risky_operation(&data);
if (result != 0) {
    fprintf(stderr, "Error code: %d\n", result);
}

// C: Manual resource management
FILE *f = fopen("file.txt", "r");
if (f != NULL) {
    // Read content
    fclose(f);
}

// C: Manual string building
char msg[100];
snprintf(msg, sizeof(msg), "Hello, %s! You are %d years old.", name, age);
```

---

`★ Insight ─────────────────────────────────────`
**Reading C Code:**

**Don't try to write it at first** - focus on reading comprehension. When you encounter C code:

1. **Start with the types** - function signatures tell you what goes in and out
2. **Follow the pointers** - understand what points where
3. **Track the memory** - who allocates, who frees
4. **Check for errors** - look for NULL checks and return code handling
5. **Recognize patterns** - most C code uses these common idioms

**The more C you read, the more patterns you'll recognize automatically.**

Think of it like learning to read a foreign language - you don't need to write essays to understand news articles. Reading C is a skill separate from writing C.
`─────────────────────────────────────────────────`

---

**Previous:** [← Chapter 4: Functions and Program Structure](chapter4-functions-and-structure.md) | **Next:** [Back to C Intro →](README.md)
