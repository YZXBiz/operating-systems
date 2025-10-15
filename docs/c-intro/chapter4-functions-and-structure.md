# 🏗️ Chapter 4: Functions and Program Structure

_How C organizes code differently from Python modules_

---

## Table of Contents

1. [Function Basics](#1-function-basics)
   - 1.1. [Function Declarations vs Definitions](#11-function-declarations-vs-definitions)
   - 1.2. [Function Signatures](#12-function-signatures)
   - 1.3. [Return Values](#13-return-values)
2. [Parameter Passing](#2-parameter-passing)
   - 2.1. [Pass by Value](#21-pass-by-value)
   - 2.2. [Pass by Reference (via Pointers)](#22-pass-by-reference-via-pointers)
   - 2.3. [Array Parameters](#23-array-parameters)
3. [Header Files and Compilation](#3-header-files-and-compilation)
   - 3.1. [Why .h and .c Files?](#31-why-h-and-c-files)
   - 3.2. [Creating Header Files](#32-creating-header-files)
   - 3.3. [Include Guards](#33-include-guards)
4. [The Compilation Process](#4-the-compilation-process)
   - 4.1. [Preprocessing](#41-preprocessing)
   - 4.2. [Compilation](#42-compilation)
   - 4.3. [Linking](#43-linking)
5. [Scope and Storage Classes](#5-scope-and-storage-classes)
   - 5.1. [Local vs Global Variables](#51-local-vs-global-variables)
   - 5.2. [static Keyword](#52-static-keyword)
   - 5.3. [extern Keyword](#53-extern-keyword)
6. [Function Pointers (Brief Introduction)](#6-function-pointers-brief-introduction)
7. [Summary: C Program Organization for Python Developers](#7-summary-c-program-organization-for-python-developers)

---

## 1. Function Basics

### 1.1. Function Declarations vs Definitions

**In plain English:** In Python, you just define a function and use it. In C, you often need to declare a function (announce its existence) before defining it (providing the implementation).

**In technical terms:** A function declaration (prototype) tells the compiler the function's signature. A function definition provides the actual implementation. The compiler needs the declaration before any calls to the function.

```python
# Python - just define and use
def add(a, b):
    return a + b

result = add(3, 5)  # Works - function defined above
```

```c
// C - declaration then definition

// Declaration (prototype) - announces function exists
int add(int a, int b);

int main() {
    int result = add(3, 5);  // OK - compiler knows about add()
    return 0;
}

// Definition - actual implementation
int add(int a, int b) {
    return a + b;
}
```

**Why declarations are needed:**

C compiles top-to-bottom. If you call a function before defining it, the compiler doesn't know its signature:

```c
// Without declaration
int main() {
    int x = add(3, 5);  // ERROR! Compiler doesn't know about add()
    return 0;
}

int add(int a, int b) {  // Defined after use
    return a + b;
}
```

**Fix: add declaration at top**

```c
int add(int a, int b);  // Declaration

int main() {
    int x = add(3, 5);  // OK now
    return 0;
}

int add(int a, int b) {  // Definition
    return a + b;
}
```

### 1.2. Function Signatures

**In plain English:** C requires explicit return type and parameter types. Python infers everything.

```python
# Python - no type annotations needed
def calculate(x, y, operation):
    if operation == "add":
        return x + y
    return x - y

result = calculate(10, 5, "add")
```

```c
// C - explicit types everywhere
int calculate(int x, int y, char *operation) {
    if (strcmp(operation, "add") == 0) {
        return x + y;
    }
    return x - y;
}

int result = calculate(10, 5, "add");
```

**Function signature components:**

```c
return_type function_name(parameter_type param1, parameter_type param2) {
    // body
}

// Examples
int add(int a, int b) { ... }           // Returns int, takes two ints
void print_msg(char *msg) { ... }       // Returns nothing, takes string
float average(int arr[], int size) { ... }  // Returns float, takes array
```

### 1.3. Return Values

**In plain English:** Python functions can return anything or nothing. C functions must declare their return type and can only return one value of that type.

```python
# Python - flexible returns
def get_data():
    return 10, 20, "hello"  # Multiple values (tuple)

def process():
    pass  # Returns None implicitly
```

```c
// C - single typed return

int get_number() {
    return 42;  // Must return int
}

void process() {
    // No return statement needed (void = no return value)
    printf("Processing...\n");
}

// Can't return multiple values directly
// Use pointers as output parameters instead
void get_data(int *x, int *y, char *str) {
    *x = 10;
    *y = 20;
    strcpy(str, "hello");
}
```

---

## 2. Parameter Passing

### 2.1. Pass by Value

**In plain English:** By default, C passes copies of values. Changes inside the function don't affect the original.

**In technical terms:** Arguments are copied onto the stack. The function works with copies, not the original variables.

```python
# Python - numbers are immutable, so similar to pass-by-value
def modify(x):
    x = 100  # Only changes local copy

value = 10
modify(value)
print(value)  # Still 10
```

```c
// C - pass by value
void modify(int x) {
    x = 100;  // Only changes local copy
}

int main() {
    int value = 10;
    modify(value);
    printf("%d\n", value);  // Still 10
    return 0;
}
```

**What gets copied:**

```c
void func(int x) {  // x is a copy
    x = 99;
}

int main() {
    int a = 10;
    func(a);
    // a is still 10 - func() worked with a copy
}
```

```
Stack when func() is called:
┌─────────────┐
│  func frame │
│  x = 10     │ ← Copy of a's value
├─────────────┤
│  main frame │
│  a = 10     │ ← Original unchanged
└─────────────┘
```

### 2.2. Pass by Reference (via Pointers)

**In plain English:** To modify the original variable, pass a pointer to it. The function receives the address and can change the value at that address.

```python
# Python - mutable objects modified in-place
def modify(lst):
    lst.append(42)  # Modifies original list

my_list = [1, 2, 3]
modify(my_list)
print(my_list)  # [1, 2, 3, 42] - changed!
```

```c
// C - pass pointer to modify original
void modify(int *ptr) {
    *ptr = 100;  // Dereference and change value at address
}

int main() {
    int value = 10;
    modify(&value);  // Pass address of value
    printf("%d\n", value);  // Now 100!
    return 0;
}
```

**Common pattern: output parameters**

```c
#include <stdbool.h>

bool divide(int a, int b, int *result) {
    if (b == 0) {
        return false;  // Error indicator
    }
    *result = a / b;
    return true;  // Success
}

int main() {
    int quotient;
    if (divide(10, 2, &quotient)) {
        printf("Result: %d\n", quotient);  // 5
    } else {
        printf("Division by zero\n");
    }
}
```

### 2.3. Array Parameters

**In plain English:** Arrays always "decay" to pointers when passed to functions. Changes inside the function affect the original array.

```python
# Python - lists passed by reference
def modify_list(lst):
    lst[0] = 99

my_list = [1, 2, 3]
modify_list(my_list)
print(my_list)  # [99, 2, 3] - changed!
```

```c
// C - arrays decay to pointers
void modify_array(int arr[], int size) {
    // arr is actually a pointer to the first element
    arr[0] = 99;  // Modifies original array
}

int main() {
    int my_array[] = {1, 2, 3, 4, 5};
    modify_array(my_array, 5);
    printf("%d\n", my_array[0]);  // 99 - changed!
}
```

**These are equivalent:**

```c
void func1(int arr[]) { ... }
void func2(int arr[10]) { ... }  // Size ignored!
void func3(int *arr) { ... }

// All three receive a pointer to int
```

**Important: sizeof() doesn't work in functions**

```c
void func(int arr[]) {
    int size = sizeof(arr) / sizeof(arr[0]);  // WRONG!
    // sizeof(arr) is sizeof(int*), not array size
}

int main() {
    int arr[10];
    int size = sizeof(arr) / sizeof(arr[0]);  // OK: 10
    // Must pass size to functions manually
}
```

> **💡 Insight**
>
> **Why arrays behave differently:** Arrays decay to pointers for efficiency. Passing a large array would be slow (copying all elements). Instead, C passes just the address - the function works with the original array. This is why you typically pass array size as a separate parameter.

---

## 3. Header Files and Compilation

### 3.1. Why .h and .c Files?

**In plain English:** Python has single `.py` files you can import. C splits code into header files (`.h`) with declarations and source files (`.c`) with definitions.

**In technical terms:** Header files contain function prototypes, type definitions, and constants - the "interface." Source files contain the actual implementations. This separation allows separate compilation and code reuse.

**Why it matters:** Understanding headers is crucial for reading C projects. You'll see `#include` everywhere.

```python
# Python - single file module
# math_utils.py
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

# main.py
import math_utils
result = math_utils.add(3, 5)
```

```c
// C - split into header and source

// math_utils.h - declarations
int add(int a, int b);
int multiply(int a, int b);

// math_utils.c - definitions
#include "math_utils.h"

int add(int a, int b) {
    return a + b;
}

int multiply(int a, int b) {
    return a * b;
}

// main.c - usage
#include "math_utils.h"

int main() {
    int result = add(3, 5);
    return 0;
}
```

### 3.2. Creating Header Files

**Typical header file structure:**

```c
// point.h
#ifndef POINT_H  // Include guard (prevents multiple inclusion)
#define POINT_H

// Type definitions
typedef struct {
    int x;
    int y;
} Point;

// Function prototypes
Point create_point(int x, int y);
float distance(Point p1, Point p2);
void print_point(Point p);

#endif  // POINT_H
```

**Corresponding source file:**

```c
// point.c
#include "point.h"
#include <math.h>
#include <stdio.h>

Point create_point(int x, int y) {
    Point p = {x, y};
    return p;
}

float distance(Point p1, Point p2) {
    int dx = p2.x - p1.x;
    int dy = p2.y - p1.y;
    return sqrt(dx*dx + dy*dy);
}

void print_point(Point p) {
    printf("(%d, %d)\n", p.x, p.y);
}
```

**Using the module:**

```c
// main.c
#include "point.h"

int main() {
    Point p1 = create_point(0, 0);
    Point p2 = create_point(3, 4);
    float dist = distance(p1, p2);
    printf("Distance: %.2f\n", dist);
    return 0;
}
```

### 3.3. Include Guards

**In plain English:** Include guards prevent header files from being included multiple times, which would cause redefinition errors.

**Without include guards (problem):**

```c
// point.h (no guard)
typedef struct {
    int x;
    int y;
} Point;

// graphics.h
#include "point.h"
// ...

// main.c
#include "point.h"
#include "graphics.h"  // ERROR! Point defined twice
```

**With include guards (solution):**

```c
// point.h (with guard)
#ifndef POINT_H  // "If not defined"
#define POINT_H  // "Define it"

typedef struct {
    int x;
    int y;
} Point;

#endif  // End of guard

// Now multiple includes are safe:
// First include: POINT_H not defined, so typedef executes
// Second include: POINT_H already defined, so skip entire file
```

**Modern alternative: #pragma once**

```c
// point.h
#pragma once  // Compiler handles avoiding multiple inclusion

typedef struct {
    int x;
    int y;
} Point;
```

---

## 4. The Compilation Process

### Python Perspective

**In plain English:** Python reads your `.py` file and runs it directly (with bytecode compilation behind the scenes). C has explicit preprocessing, compilation, and linking steps.

```python
# Python - single step
python main.py  # Interprets and runs
```

```c
// C - multiple steps
gcc -o program main.c math_utils.c  // Compile and link
./program                           // Run executable
```

### 4.1. Preprocessing

**Step 1: Preprocessor handles directives**

```c
// Before preprocessing
#include <stdio.h>
#define PI 3.14159

int main() {
    printf("Pi: %f\n", PI);
}
```

```c
// After preprocessing (simplified)
// (entire stdio.h contents pasted here)
// ... thousands of lines ...

int main() {
    printf("Pi: %f\n", 3.14159);  // PI replaced
}
```

**Preprocessor directives:**
- `#include` - paste file contents
- `#define` - text replacement
- `#ifdef` / `#ifndef` - conditional compilation
- `#pragma` - compiler-specific commands

### 4.2. Compilation

**Step 2: Compile to object code**

```bash
gcc -c main.c       # Produces main.o (object file)
gcc -c math_utils.c # Produces math_utils.o
```

Object files contain:
- Machine code for functions
- Placeholders for external references
- Symbol table (function names, etc.)

### 4.3. Linking

**Step 3: Link object files together**

```bash
gcc -o program main.o math_utils.o  # Links into executable
```

Linker:
- Resolves external function references
- Combines all object code
- Produces executable file

**Full process visualization:**

```
main.c ──┐
         ├─> Preprocessing ──> Compilation ──> main.o ──┐
math.h ──┘                                               │
                                                         ├─> Linking ──> program
math_utils.c ──> Preprocessing ──> Compilation ──> math.o ──┘
```

---

## 5. Scope and Storage Classes

### 5.1. Local vs Global Variables

```python
# Python
x = 10  # Global

def func():
    y = 20  # Local
    print(x)  # Can access global
```

```c
// C
int x = 10;  // Global (visible to all functions in file)

void func() {
    int y = 20;  // Local (only visible in func)
    printf("%d\n", x);  // Can access global
}

int main() {
    printf("%d\n", x);  // Can access global
    // printf("%d\n", y);  // ERROR: y is local to func()
}
```

### 5.2. static Keyword

**For variables: preserves value between calls**

```c
void counter() {
    static int count = 0;  // Initialized once, persists between calls
    count++;
    printf("%d\n", count);
}

int main() {
    counter();  // Prints 1
    counter();  // Prints 2
    counter();  // Prints 3
}
```

**For functions/globals: limits scope to current file**

```c
// file1.c
static int secret = 42;  // Only visible in file1.c

static void helper() {   // Only callable from file1.c
    printf("Helper\n");
}
```

### 5.3. extern Keyword

**Declares a global variable defined elsewhere:**

```c
// file1.c
int global_count = 0;  // Definition

// file2.c
extern int global_count;  // Declaration (tells compiler it exists)

void increment() {
    global_count++;  // Can access variable from file1.c
}
```

---

## 6. Function Pointers (Brief Introduction)

**In plain English:** Functions have addresses too. You can store a function's address in a pointer and call it indirectly.

```c
// Function that takes two ints and returns int
int add(int a, int b) {
    return a + b;
}

int subtract(int a, int b) {
    return a - b;
}

int main() {
    // Function pointer declaration
    int (*operation)(int, int);

    operation = add;  // Point to add function
    printf("%d\n", operation(5, 3));  // Calls add: 8

    operation = subtract;  // Point to subtract
    printf("%d\n", operation(5, 3));  // Calls subtract: 2
}
```

**Common use: callbacks**

```c
void apply(int arr[], int size, int (*func)(int)) {
    for (int i = 0; i < size; i++) {
        arr[i] = func(arr[i]);
    }
}

int double_value(int x) {
    return x * 2;
}

int main() {
    int numbers[] = {1, 2, 3, 4, 5};
    apply(numbers, 5, double_value);  // Pass function as argument
    // numbers is now {2, 4, 6, 8, 10}
}
```

---

## 7. Summary: C Program Organization for Python Developers

### Key Takeaways

**Function Declarations:**
- Must declare before use (or define before use)
- Explicit return type and parameter types
- Use pointers for "pass by reference"

**Header Files:**
- `.h` files contain declarations (interface)
- `.c` files contain definitions (implementation)
- `#include` pastes file contents
- Include guards prevent multiple inclusion

**Compilation:**
- Preprocess → Compile → Link → Executable
- Each `.c` file compiled separately
- Linker combines object files

**Scope:**
- Local variables: function scope
- Global variables: file scope (or all files if not static)
- `static`: limits scope or preserves value
- `extern`: declares global from another file

---

### Reading Checklist

When exploring a C project:

✅ **Look at header files first** - they show the interface
✅ **Find main()** - entry point of the program
✅ **Check #include directives** - what dependencies exist?
✅ **Identify global vs local** - scope of variables
✅ **Watch for pointers in parameters** - indicates modification
✅ **Check return types** - what does function produce?

---

### Common Patterns

```c
// Pattern 1: Header file structure
#ifndef MODULE_H
#define MODULE_H

// Type definitions
typedef struct { ... } MyType;

// Function declarations
int do_something(MyType *data);
void cleanup(MyType *data);

#endif

// Pattern 2: Output parameters
bool get_values(int *x, int *y) {
    *x = 10;
    *y = 20;
    return true;
}

// Pattern 3: Array with size
void process_array(int arr[], int size) {
    for (int i = 0; i < size; i++) {
        arr[i] *= 2;
    }
}

// Pattern 4: Opaque pointer (in headers)
typedef struct Context Context;  // Hide implementation
Context* create_context(void);
void destroy_context(Context *ctx);
```

---

`★ Insight ─────────────────────────────────────`
**The Python vs C Organization Model:**

**Python's model:** Import modules as needed. Everything in one file if you want. Runtime handles dependencies. No separate compilation step.

**C's model:** Split declaration (header) from definition (source). Each file compiled separately. Linker resolves dependencies. Gives you control over what's public vs private.

**Why this matters:** C's model enables:
- Faster compilation (only recompile changed files)
- Better encapsulation (hide implementation details)
- Library distribution (ship headers + compiled code)

The complexity is the price of control and performance.
`─────────────────────────────────────────────────`

---

**Previous:** [← Chapter 3: Arrays, Strings, and Structs](chapter3-arrays-strings-structs.md) | **Next:** [Chapter 5: Common C Patterns →](chapter5-common-patterns.md)
