# 📦 Chapter 3: Arrays, Strings, and Structs

_How C organizes data without Python's convenient collections_

---

## Table of Contents

1. [Arrays: Fixed-Size Contiguous Memory](#1-arrays-fixed-size-contiguous-memory)
   - 1.1. [Array Declaration and Initialization](#11-array-declaration-and-initialization)
   - 1.2. [Arrays and Pointers](#12-arrays-and-pointers)
   - 1.3. [Multidimensional Arrays](#13-multidimensional-arrays)
   - 1.4. [Arrays vs Python Lists](#14-arrays-vs-python-lists)
2. [Strings: Just Character Arrays](#2-strings-just-character-arrays)
   - 2.1. [String Basics](#21-string-basics)
   - 2.2. [String Functions](#22-string-functions)
   - 2.3. [Common String Pitfalls](#23-common-string-pitfalls)
3. [Structs: Grouping Data](#3-structs-grouping-data)
   - 3.1. [Defining and Using Structs](#31-defining-and-using-structs)
   - 3.2. [Pointers to Structs](#32-pointers-to-structs)
   - 3.3. [Structs vs Python Classes](#33-structs-vs-python-classes)
4. [typedef: Creating Type Aliases](#4-typedef-creating-type-aliases)
5. [Practical Examples](#5-practical-examples)
6. [Summary: C Data Structures for Python Developers](#6-summary-c-data-structures-for-python-developers)

---

## 1. Arrays: Fixed-Size Contiguous Memory

### Python Perspective

**In plain English:** Python lists are flexible, growable containers. C arrays are fixed-size blocks of memory containing the same type. No methods, no growing, just raw memory.

**In technical terms:** C arrays are contiguous memory blocks where elements are stored sequentially. Array size is fixed at creation (stack) or allocation (heap). No bounds checking, no automatic resizing.

**Why it matters:** Understanding arrays is crucial for reading C code. Arrays decay to pointers, which explains many confusing C behaviors.

### 1.1. Array Declaration and Initialization

```python
# Python - dynamic lists
numbers = []              # Empty list
numbers = [1, 2, 3, 4, 5] # Initialized
numbers.append(6)         # Can grow
numbers.pop()             # Can shrink
```

```c
// C - fixed-size arrays
int numbers[5];                    // 5 integers, uninitialized
int values[5] = {1, 2, 3, 4, 5};  // Initialized
int partial[5] = {1, 2};          // {1, 2, 0, 0, 0} - rest is 0
int inferred[] = {1, 2, 3};       // Size inferred: 3

// numbers[5] = 6;  // Out of bounds! Undefined behavior, no error!
```

**Memory Layout:**

```
values[5] = {10, 20, 30, 40, 50}

Address    Index    Value
0x1000     [0]      10
0x1004     [1]      20
0x1008     [2]      30
0x100C     [3]      40
0x1010     [4]      50

Contiguous = no gaps between elements
```

### 1.2. Arrays and Pointers

**In plain English:** In most contexts, an array name "decays" to a pointer to its first element. This is why arrays and pointers seem interchangeable.

```c
int arr[5] = {10, 20, 30, 40, 50};
int *ptr = arr;  // arr decays to &arr[0]

// These are all equivalent:
printf("%d\n", arr[0]);   // 10
printf("%d\n", *arr);     // 10 (dereference pointer to first element)
printf("%d\n", *ptr);     // 10
printf("%d\n", ptr[0]);   // 10 (pointers can use [] syntax!)
```

**Array indexing is pointer arithmetic:**

```c
arr[i]  ≡  *(arr + i)

arr[2]  →  *(arr + 2)  →  "Go 2 elements from arr, get value"
```

```
arr points to 0x1000
arr + 0 → 0x1000 → value 10
arr + 1 → 0x1004 → value 20
arr + 2 → 0x1008 → value 30
```

> **💡 Insight**
>
> **Why `arr[i]` works:** It's syntactic sugar for pointer arithmetic. `arr[i]` is translated to `*(arr + i)` by the compiler. This is why you can write `ptr[i]` even though `ptr` is a pointer, not an array.

### 1.3. Multidimensional Arrays

```python
# Python - list of lists
matrix = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
]
print(matrix[1][2])  # 6
```

```c
// C - true 2D array (contiguous memory)
int matrix[3][3] = {
    {1, 2, 3},
    {4, 5, 6},
    {7, 8, 9}
};

printf("%d\n", matrix[1][2]);  // 6

// Memory layout: all 9 integers in one contiguous block
// 1 2 3 4 5 6 7 8 9
```

**2D array as array of arrays:**

```c
int matrix[3][4];  // 3 rows, 4 columns

// Access patterns
matrix[0][0] = 1;      // First element
matrix[2][3] = 12;     // Last element

// Pointer access
int (*row_ptr)[4] = matrix;  // Pointer to array of 4 ints
```

### 1.4. Arrays vs Python Lists

| Feature | Python List | C Array |
|---------|-------------|---------|
| **Size** | Dynamic (grows/shrinks) | Fixed at creation |
| **Type** | Mixed types allowed | Single type only |
| **Methods** | `.append()`, `.pop()`, `.sort()`, etc. | None - just raw memory |
| **Bounds Checking** | Yes - `IndexError` | No - undefined behavior |
| **Memory** | Non-contiguous (may be scattered) | Always contiguous |
| **Pass to Function** | Reference (modifiable) | Decays to pointer |

```python
# Python - rich functionality
nums = [1, 2, 3]
nums.append(4)           # Easy growth
nums.extend([5, 6])      # Merge
nums.sort()              # Built-in sorting
if 3 in nums:            # Easy search
    print("found")
```

```c
// C - manual everything
int nums[3] = {1, 2, 3};
// Can't append - fixed size
// Can't extend - need malloc + copy
// No built-in sort - write it or use qsort()
// Search: must loop manually
```

---

## 2. Strings: Just Character Arrays

### 2.1. String Basics

**In plain English:** C has no string type. Strings are arrays of characters terminated by a null byte `\0`. This is completely different from Python's immutable string objects.

**In technical terms:** A C string is a `char` array where the last character is `'\0'` (ASCII value 0). String functions iterate until they hit `\0` to determine length.

**Why it matters:** Forgetting the null terminator is a classic C bug. Reading C code, you'll see `\0` checks everywhere.

```python
# Python - first-class string type
s = "hello"
print(len(s))        # 5 - length stored in object
s = s.upper()        # Returns new string (immutable)
```

```c
// C - array of chars with \0
char s[] = "hello";  // Actually 6 bytes: 'h' 'e' 'l' 'l' 'o' '\0'

// Memory layout:
// Index: 0   1   2   3   4   5
// Value: 'h' 'e' 'l' 'l' 'o' '\0'

// Manual string creation
char s2[6] = {'h', 'e', 'l', 'l', 'o', '\0'};  // Same as above

// Length: must count until \0
int len = 0;
while (s[len] != '\0') {
    len++;
}
printf("Length: %d\n", len);  // 5
```

### String Declaration

```c
// Method 1: Array initialization
char str1[] = "hello";      // Size 6 (includes \0)

// Method 2: Explicit size
char str2[10] = "hello";    // Size 10, rest filled with \0

// Method 3: Pointer to string literal
char *str3 = "hello";       // Points to read-only memory
// str3[0] = 'H';           // CRASH! String literals are immutable

// Method 4: Uninitialized (must fill manually)
char str4[10];
str4[0] = 'h';
str4[1] = 'i';
str4[2] = '\0';  // Must add null terminator!
```

### 2.2. String Functions

**In plain English:** C provides a standard library (`<string.h>`) for string operations. No methods - just functions that take pointers.

```python
# Python string operations
s1 = "hello"
s2 = "world"
s3 = s1 + " " + s2    # Concatenation
if s1 == s2:          # Comparison
    pass
n = len(s1)           # Length
```

```c
// C string operations - need #include <string.h>
char s1[] = "hello";
char s2[] = "world";
char s3[20];  // Must allocate space

// Concatenation
strcpy(s3, s1);       // Copy s1 to s3: "hello"
strcat(s3, " ");      // Append: "hello "
strcat(s3, s2);       // Append: "hello world"

// Comparison (can't use ==)
if (strcmp(s1, s2) == 0) {  // Returns 0 if equal
    printf("equal\n");
}

// Length
int len = strlen(s1);  // Counts until \0
```

**Common string functions:**

```c
#include <string.h>

char dest[50];
char src[] = "hello";

strlen(src);              // Length (not including \0)
strcpy(dest, src);        // Copy src to dest
strcat(dest, " world");   // Append to dest
strcmp(s1, s2);           // Compare: 0=equal, <0=less, >0=greater
strncpy(dest, src, n);    // Copy at most n characters
strncat(dest, src, n);    // Append at most n characters
```

### 2.3. Common String Pitfalls

**Pitfall 1: Comparing with ==**

```c
char s1[] = "hello";
char s2[] = "hello";

if (s1 == s2) {  // WRONG! Compares addresses, not contents
    // Never true - different arrays
}

if (strcmp(s1, s2) == 0) {  // CORRECT - compares contents
    printf("equal\n");
}
```

**Pitfall 2: Buffer overflow**

```c
char small[5] = "hi";
strcat(small, " world");  // OVERFLOW! small is only 5 bytes
// Writes beyond array bounds → crash or corruption
```

**Pitfall 3: Forgetting null terminator**

```c
char s[5];
s[0] = 'h';
s[1] = 'i';
// Forgot s[2] = '\0';

printf("%s\n", s);  // Undefined! Keeps reading memory until it finds \0
```

**Pitfall 4: Modifying string literals**

```c
char *s = "hello";  // Points to read-only memory
s[0] = 'H';         // CRASH! Segmentation fault
```

> **💡 Insight**
>
> **Why null terminator?** C has no length field in strings (unlike Python). The only way to know where a string ends is a special marker: `\0`. Functions like `strlen()` and `printf()` iterate until they find `\0`.
>
> **This is a security issue:** If you forget `\0`, functions read past your buffer → buffer over-read, potential crash or leak.

---

## 3. Structs: Grouping Data

### 3.1. Defining and Using Structs

**In plain English:** Structs let you group related variables together. Like Python classes but without methods - just data.

**In technical terms:** A struct is a composite data type that groups variables of different types into a single unit. Members are accessed via dot notation (or arrow for pointers).

```python
# Python class (with methods)
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def distance(self):
        return (self.x**2 + self.y**2)**0.5

p = Point(3, 4)
print(p.x, p.y)
print(p.distance())
```

```c
// C struct (data only)
struct Point {
    int x;
    int y;
};  // Semicolon required!

struct Point p;
p.x = 3;
p.y = 4;
printf("%d %d\n", p.x, p.y);

// Functions separate (not methods)
float distance(struct Point p) {
    return sqrt(p.x*p.x + p.y*p.y);
}
```

### Struct Definition and Initialization

```c
// Define struct type
struct Person {
    char name[50];
    int age;
    float height;
};

// Create and initialize
struct Person p1 = {"Alice", 30, 5.6};  // Positional

struct Person p2 = {
    .name = "Bob",    // Designated initializers (C99)
    .age = 25,
    .height = 5.9
};

// Access members
printf("%s is %d years old\n", p1.name, p1.age);
p2.age = 26;  // Modify
```

### 3.2. Pointers to Structs

**In plain English:** When you have a pointer to a struct, use `->` instead of `.` to access members. It's shorthand for dereferencing then accessing.

```c
struct Point {
    int x;
    int y;
};

struct Point p = {10, 20};
struct Point *ptr = &p;

// Two ways to access via pointer:
printf("%d\n", (*ptr).x);  // Dereference first, then access: 10
printf("%d\n", ptr->x);    // Shorthand - same thing: 10

// The -> operator is for pointers
// The . operator is for actual structs
```

**Common pattern: returning pointers to structs**

```c
struct Point* create_point(int x, int y) {
    struct Point *p = malloc(sizeof(struct Point));
    if (p != NULL) {
        p->x = x;  // Use -> because p is a pointer
        p->y = y;
    }
    return p;
}

int main() {
    struct Point *p = create_point(5, 10);
    printf("(%d, %d)\n", p->x, p->y);
    free(p);
}
```

### 3.3. Structs vs Python Classes

| Feature | Python Class | C Struct |
|---------|--------------|----------|
| **Methods** | Yes - functions inside class | No - functions separate |
| **Inheritance** | Yes | No |
| **Encapsulation** | Yes (private vars) | No - all members public |
| **Memory** | Heap (reference) | Stack or heap (value) |
| **Initialization** | `__init__` method | Direct or designated initializers |

```python
# Python - object with behavior
class Car:
    def __init__(self, make, year):
        self.make = make
        self.year = year

    def honk(self):
        print(f"{self.make} honks!")

car = Car("Toyota", 2020)
car.honk()
```

```c
// C - data structure only
struct Car {
    char make[50];
    int year;
};

void honk(struct Car *c) {  // Function outside struct
    printf("%s honks!\n", c->make);
}

struct Car car = {"Toyota", 2020};
honk(&car);  // Must pass explicitly
```

---

## 4. typedef: Creating Type Aliases

**In plain English:** `typedef` creates a shorthand name for a type. Common with structs to avoid writing `struct` everywhere.

```c
// Without typedef - verbose
struct Point {
    int x;
    int y;
};
struct Point p1;  // Must write "struct Point"

// With typedef - cleaner
typedef struct {
    int x;
    int y;
} Point;  // Point is now a type name

Point p2;  // Just "Point", not "struct Point"
```

**Common pattern:**

```c
typedef struct Node {
    int data;
    struct Node *next;  // Still need "struct" here (self-reference)
} Node;

Node *head = malloc(sizeof(Node));
```

**Other typedef uses:**

```c
typedef unsigned int uint;       // uint instead of unsigned int
typedef char* string;            // string instead of char*

uint count = 100;
string name = "Alice";
```

---

## 5. Practical Examples

### Example 1: Dynamic Array of Structs

```python
# Python - list of objects
people = []
people.append({"name": "Alice", "age": 30})
people.append({"name": "Bob", "age": 25})
```

```c
// C - malloc array of structs
typedef struct {
    char name[50];
    int age;
} Person;

int main() {
    int count = 2;
    Person *people = malloc(count * sizeof(Person));

    strcpy(people[0].name, "Alice");
    people[0].age = 30;

    strcpy(people[1].name, "Bob");
    people[1].age = 25;

    for (int i = 0; i < count; i++) {
        printf("%s: %d\n", people[i].name, people[i].age);
    }

    free(people);
    return 0;
}
```

### Example 2: Linked List Node

```python
# Python - node class
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None

head = Node(1)
head.next = Node(2)
head.next.next = Node(3)
```

```c
// C - linked list with structs
typedef struct Node {
    int data;
    struct Node *next;
} Node;

Node* create_node(int data) {
    Node *node = malloc(sizeof(Node));
    if (node != NULL) {
        node->data = data;
        node->next = NULL;
    }
    return node;
}

int main() {
    Node *head = create_node(1);
    head->next = create_node(2);
    head->next->next = create_node(3);

    // Traverse
    Node *current = head;
    while (current != NULL) {
        printf("%d -> ", current->data);
        current = current->next;
    }
    printf("NULL\n");

    // Free all nodes...
    return 0;
}
```

---

## 6. Summary: C Data Structures for Python Developers

### Key Takeaways

**Arrays:**
- Fixed size, contiguous memory
- No bounds checking (your responsibility)
- Decay to pointers in most contexts
- `arr[i]` is just `*(arr + i)`

**Strings:**
- Character arrays with `\0` terminator
- No methods - use functions from `<string.h>`
- Must manage buffer sizes manually
- Easy to overflow if not careful

**Structs:**
- Group related variables
- No methods (just data)
- Use `.` for struct, `->` for pointer to struct
- typedef makes usage cleaner

---

### Reading Checklist

When you see these in C code:

✅ **Arrays:** Check if size is fixed or allocated, watch for bounds
✅ **Strings:** Look for null terminator handling and buffer sizes
✅ **strcmp/strcpy:** Remember these compare/copy contents, not `==/=`
✅ **struct vs pointer:** Use `.` or `->`? Determines if value or pointer
✅ **malloc with structs:** Always check NULL, always free

---

### Common Patterns

```c
// Pattern 1: String buffer
char buffer[256];  // Fixed size
snprintf(buffer, sizeof(buffer), "Value: %d", x);  // Safe

// Pattern 2: Array iteration
int arr[10];
for (int i = 0; i < 10; i++) {
    arr[i] = i * 2;
}

// Pattern 3: Struct initialization
typedef struct {
    int x;
    int y;
} Point;
Point p = {.x = 5, .y = 10};

// Pattern 4: Pointer to struct
void modify_point(Point *p) {
    p->x = 0;  // Use -> for pointer
    p->y = 0;
}
```

---

`★ Insight ─────────────────────────────────────`
**The Python vs C Data Model:**

**Python's model:** Everything is an object with methods and automatic memory management. Lists, strings, and objects are first-class citizens with rich functionality.

**C's model:** Everything is memory. Arrays are just contiguous bytes. Strings are just char arrays. Structs are just grouped variables. No methods, no magic - just raw data.

**Why learn this?** Understanding C's "everything is memory" model helps you appreciate Python's abstractions and understand what's happening under the hood in performance-critical code.
`─────────────────────────────────────────────────`

---

**Previous:** [← Chapter 2: Pointers and Memory](chapter2-pointers-and-memory.md) | **Next:** [Chapter 4: Functions and Program Structure →](chapter4-functions-and-structure.md)
