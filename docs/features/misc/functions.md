<!-- filepath: /home/cardoso/Documents/escudeiro/docs/features/misc/functions.md -->
# Miscellaneous Functions

The `functions` module provides a collection of utility functions and decorators for safer type casting, function execution control, retry logic, and more. These tools help simplify common patterns in both synchronous and asynchronous Python code.

---

## Why?

Many Python patterns—such as safe type casting, retrying operations, or memoizing results—require repetitive boilerplate code. The `functions` module centralizes these patterns into reusable, type-safe utilities that work seamlessly with both sync and async code.

---

## Features

- **Safe type casting** (`safe_cast`, `asafe_cast`)
- **Call-once and memoization** (`call_once`, `cache`)
- **Sync-to-async conversion** (`as_async`)
- **No-op function factories** (`make_noop`)
- **Context-managed function execution** (`do_with`, `asyncdo_with`)
- **Retry logic** (sync and async) via `Retry`
- **Frozen coroutine wrapper** (`FrozenCoroutine`)
- **Object path walking** (`walk_object`)

---

## Usage

### Safe Type Casting

```python
from escudeiro.misc.functions import safe_cast, asafe_cast

result = safe_cast(int, "123")  # 123
result = safe_cast(int, "abc", default=0)  # 0

import asyncio
async def parse_async(val):
    return int(val)

result = await asafe_cast(parse_async, "456")  # 456
result = await asafe_cast(parse_async, "oops", default=-1)  # -1
```

### Call Once

```python
from escudeiro.misc.functions import call_once

@call_once
def expensive_init():
    print("Initializing...")
    return 42

expensive_init()  # Prints "Initializing...", returns 42
expensive_init()  # Returns 42 (no print)
```

### Memoization

```python
from escudeiro.misc.functions import cache

@cache
def fib(n):
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)
```

### Sync-to-Async Conversion

```python
from escudeiro.misc.functions import as_async

@as_async
def compute(x):
    return x * 2

result = await compute(21)  # 42
```

### No-Op Functions

```python
from escudeiro.misc.functions import make_noop

noop = make_noop()
noop(1, 2, 3)  # Returns None

async_noop = make_noop(asyncio=True, returns="done")
await async_noop()  # Returns "done"
```

### Context-Managed Execution

```python
from escudeiro.misc.functions import do_with, asyncdo_with

with open("file.txt") as f:
    content = do_with(f, lambda file: file.read())

# Async context manager
import aiofiles
async with aiofiles.open("file.txt") as f:
    content = await asyncdo_with(f, lambda file: file.read())
```

### Retry Logic

```python
from escudeiro.misc.functions import Retry

retry = Retry(signal=ValueError, count=3, delay=1)

@retry
def might_fail():
    # ...
    pass

@retry.acall
async def might_fail_async():
    # ...
    pass
```

### Frozen Coroutine

```python
from escudeiro.misc.functions import FrozenCoroutine

async def fetch():
    print("Fetching...")
    return 123

frozen = FrozenCoroutine(fetch())
result1 = await frozen  # Prints "Fetching..."
result2 = await frozen  # Returns cached result, no print
```

### Walk Object

```python
from escudeiro.misc.functions import walk_object

data = {"user": {"profile": {"age": 30}}}
age = walk_object(data, "user.profile.age")  # 30

lst = [1, 2, [3, 4, 5]]
val = walk_object(lst, "[2].[1]")  # 4
```

---

## API Reference

### `safe_cast`

Safely cast a value using a function, returning a default if an exception occurs.

```python
def safe_cast(caster, value, *ignore_childof, default=None)
```

- **caster**: Function to convert the value.
- **value**: Value to cast.
- **ignore_childof**: Exception types to catch (default: `TypeError`, `ValueError`).
- **default**: Value to return if casting fails.

---

### `asafe_cast`

Async version of `safe_cast`.

```python
async def asafe_cast(caster, value, *ignore_childof, default=None)
```

---

### `call_once`

Decorator to ensure a function is called only once; result is cached.

```python
def call_once(func)
```

---

### `cache`

Memoization decorator (thin wrapper over `functools.cache`).

```python
def cache(f)
```

---

### `as_async`

Decorator/factory to convert a sync function to async (runs in thread by default).

```python
def as_async(func=None, *, cast=asyncio.to_thread)
```

---

### `make_noop`

Creates a no-op function (sync or async) that returns a fixed value.

```python
def make_noop(*, returns=None, asyncio=False)
```

---

### `do_with`

Executes a function within a context manager.

```python
def do_with(context_manager, func, *args, **kwargs)
```

---

### `asyncdo_with`

Async version of `do_with`, supports sync/async context managers and functions.

```python
async def asyncdo_with(context_manager, func, *args, **kwargs)
```

---

### `Retry`

A class for retrying functions on failure (sync and async).

```python
@dataclass
class Retry:
    signal: type[Exception] | tuple[type[Exception], ...]
    count: int = 3
    delay: float = 0
    backoff: float = 1

    def __call__(self, func)
    def acall(self, func)
    def map(self, predicate, collection, strategy="threshold")
    async def amap(self, predicate, collection, strategy="threshold")
    async def agenmap(self, predicate, collection, strategy="threshold")
```

---

### `FrozenCoroutine`

A coroutine wrapper that ensures the coroutine is executed at most once.

```python
class FrozenCoroutine:
    def __init__(self, coro)
    @classmethod
    def decorate(cls, func)
```

---

### `walk_object`

Safely retrieves a value from an object using a dot-separated path.

```python
def walk_object(obj, path)
```

---

## See Also

- [functools](https://docs.python.org/3/library/functools.html)
- [asyncio](https://docs.python.org/3/library/asyncio.html)
- [contextlib](https://docs.python.org/3/library/contextlib.html)
- [dataclasses](https://docs.python.org/3/library/dataclasses.html)
- [Python exceptions](https://docs.python.org/3/tutorial/errors.html)