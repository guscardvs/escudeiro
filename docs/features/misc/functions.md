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
- **No-op function factories** (`make_noop`, `return_param`)
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
from escudeiro.misc.functions import make_noop, return_param

noop = make_noop()
noop(1, 2, 3)  # Returns None

async_noop = make_noop(asyncio=True, returns="done")
await async_noop()  # Returns "done"

return_param(True) # Returns True
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

### Date conversion

```python
from escudeiro.misc.functions import as_datetime, join_into_datetime

dt = as_datetime(date(2023, 1, 1))  # 2023-01-01 00:00:00
dt2 = join_into_datetime(date(2023, 1, 1), time(12, 0))  # 2023-01-01 12:00:00
```

### Iterable conversion

```python
from escudeiro.misc.functions import as_async_iterable

async def main():
    async for item in as_async_iterable([1, 2, 3]):
        print(item)

```

### Exception conversion

```python
from escudeiro.misc.functions import raise_insteadof

@raise_insteadof(TypeError, ValueError, "CustomError")
def faulty_function():
    raise TypeError("This is a type error")
```

### Instance Casting

```python
from escudeiro.misc.functions import isinstance_or_cast
from functools import partial


@partial(isinstance_or_cast, int)
def cast_to_int(value: str) -> int:
    return int(value)

cast_to_int("123")  # 123
cast_to_int(123)  # does nothing

```

### Caster

```python
from escudeiro.misc.functions import Caster

caster = (
    Caster
        .isinstance_or_cast(str, bytes.decode)
        .join(float)
        .with_rule(lambda val: val > 0, "Must be positive")
        .or_(lambda: None, TypeError, ValueError)
        .safe_cast()
)
result = caster("123.45")  # 123.45
result = caster(b"abc")  # None
result = caster("-123.45")  # raises InvalidCast
```

### Decorator utilities

```python
from escudeiro.misc.functions import wrap_result_with, awrap_result_with, as_async

@wrap_result_with(str)
def sync_function():
    return 42

@awrap_result_with(as_async(float))
async def async_function():
    return 42

result = sync_function() # "42"
result = await async_function() # 42.0
```

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

### `return_param`

Returns a parameter from a function. Useful for creating simple functions that just return their input.

```python
def return_param(param):
    return param
```

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

### `as_datetime`

Converts a date or datetime object to a datetime object.

```python
from escudeiro.misc.functions import as_datetime

date = as_datetime(date(2023, 1, 1), tz=timezone.utc)
```

### `join_into_datetime`

Joins a date and time into a datetime object.

```python
from escudeiro.misc.functions import join_into_datetime

dt = join_into_datetime(date(2023, 1, 1), time(12, 0, 0), tz=timezone.utc)
```

### `as_async_iterable`

Converts a synchronous iterable into an asynchronous iterable.

```python
from escudeiro.misc.functions import as_async_iterable

async for item in as_async_iterable([1, 2, 3]):
    print(item)
```

### `raise_insteadof`

Raises a different exception instead of the original one.
Can be used as a decorator or a context manager.

```python
from escudeiro.misc.functions import raise_insteadof

@raise_insteadof(ValueError, TypeError)
def func():
    raise ValueError("This is a ValueError")

# or

def func():
    with raise_insteadof(ValueError, TypeError):
        raise ValueError("This is a ValueError")
```

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

### `isinstance_or_cast`

Checks if an object is an instance of a class or attempts to cast it.

```python
from escudeiro.misc.functions import isinstance_or_cast

caster = isinstance_or_cast(str, bytes.decode)
result = caster("hello")  # "hello"
result = caster(b"world")  # "world"
```

### `Caster`

A class for creating casting pipelines.

#### `constructor`

Returns a caster instance with a custom name.

```python
from escudeiro.misc.functions import Caster

caster = Caster(str, "custom_string_caster")
```

#### `__call__`

Caster instances are callable.

```python
result = caster("hello")  # "hello"
```

#### `join`

Joins multiple casters creating a sequential casting pipeline.

```python

caster = Caster(bytes.decode).join(float)
# Calls bytes.decode and then float
result = caster(b"42")  # 42.0
```

#### `strict`

Raises `InvalidCast` if caster returns None

```python
caster = Caster(lambda x: float(x) if x is not None else None).strict()

result = caster(b"42")  # 42.0
result = caster(None)  # Raises InvalidCast
```

#### `safe`

Opposite of strict, returns None if specified exceptions are raised.
If no exceptions are specified, it will catch TypeError and ValueError.

```python
caster = Caster(float)

result = caster.safe(b"42")  # 42.0
result = caster.safe("not a number")  # None
```

#### `safe_cast`

Same as safe but returns a caster, not the direct function. Useful for a pipeline.
Does not catch exceptions raised by components defined after the safe_cast.

```python
caster = Caster(float).safe_cast().join(int)

result = caster(b"42")  # 42
result = caster("not a number")  # Raises TypeError as None cannot be casted to int
```

#### `or_`

Calls a fallback function if the caster raises a specified exception.
If no exception is specified, it will catch TypeError and ValueError.

```python
caster = Caster(float).or_(lambda x: 0.0)

result = caster(b"42")  # 42.0
result = caster("not a number")  # 0.0
```

#### `with_rule`

Adds a validation rule to the caster. If using a lambda, the rule name is not optional.

```python
caster = Caster(float).with_rule(lambda x: x > 0, "Must be positive")

result = caster(b"42")  # 42.0
result = caster(b"-42")  # Raises ValueError: Must be positive
```

### `wrap_result_with`

Wraps the result of a function with the specified function

```python

@wrap_result_with(float)
def my_function():
    return "42"

my_function() # 42.0

```

### `awrap_result_with`

Wraps the result of an asynchronous function with the specified function

```python
@awrap_result_with(as_async(float))
async def my_function():
    return "42"

await my_function() # 42.0

```

## See Also

- [functools](https://docs.python.org/3/library/functools.html)
- [asyncio](https://docs.python.org/3/library/asyncio.html)
- [contextlib](https://docs.python.org/3/library/contextlib.html)
- [dataclasses](https://docs.python.org/3/library/dataclasses.html)
- [Python exceptions](https://docs.python.org/3/tutorial/errors.html)
