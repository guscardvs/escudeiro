# Lazy Fields

The `lazyfields` module provides advanced lazy evaluation fields for Python classes, supporting both synchronous and asynchronous initialization, with optional per-instance locking for thread safety. This is useful for expensive computations or resources that should be initialized only when accessed.

---

## Why?

Consider the following code snippet:

```python
class MyClass:
    def __init__(self):
        self._expensive = None
    @property
    def expensive(self):
        if self._expensive is None:
            print("Computing...")
            self._expensive = 42  # Simulate an expensive computation
        return self._expensive
```
This pattern is common but can lead to boilerplate code and potential issues with thread safety. 
The `lazyfields` module simplifies this by providing decorators that handle lazy initialization, caching, and locking automatically.
```python
from escudeiro.lazyfields import lazyfield, asynclazyfield, mark_class
class MyClass:
    @lazyfield
    def expensive(self):
        print("Computing...")
        return 42  # Simulate an expensive computation
```

---

## Features

- **Synchronous and asynchronous lazy fields** (`@lazyfield`, `@asynclazyfield`)
- **Per-instance locking** for thread safety (optional)
- **Class marking** for isolation of locks
- **Manual reset and deletion** of lazy values
- **Type-safe and dataclass-friendly**

---

## Usage

### Basic Synchronous Lazy Field

```python
from escudeiro.lazyfields import lazyfield

class MyClass:
    @lazyfield
    def expensive(self):
        print("Computing...")
        return 42

obj = MyClass()
print(obj.expensive)  # Prints "Computing..." then 42
print(obj.expensive)  # Prints 42 (no recomputation)
```

### Asynchronous Lazy Field

```python
from escudeiro.lazyfields import asynclazyfield
import asyncio

class MyAsyncClass:
    @asynclazyfield
    async def expensive(self):
        print("Computing async...")
        await asyncio.sleep(1)
        return 99

async def main():
    obj = MyAsyncClass()
    print(await obj.expensive())  # Prints "Computing async..." then 99
    print(await obj.expensive())  # Prints 99 (no recomputation)

asyncio.run(main())
```

### Using Locks for Thread Safety

```python
import threading
from escudeiro.lazyfields import lazyfield, mark_class

def lock_factory():
    return threading.Lock()

@mark_class(ctx_factory=lock_factory)
class ThreadSafe:
    @lazyfield
    def value(self):
        # expensive computation
        return 123
```

---

## API Reference

### Decorators

#### `@lazyfield`

```python
@overload
def lazyfield[SelfT, T](
    func: Callable[[SelfT], T], /
) -> LazyField[SelfT, T]: ...

@overload
def lazyfield[SelfT, T](
    func: None = None,
    /,
    lock_factory: Callable[[], contextlib.AbstractContextManager] = contextlib.nullcontext,
) -> Callable[[Callable[[SelfT], T]], LazyField[SelfT, T]]: ...
```

- **Description:** Decorator for defining a synchronous lazy field.
- **Parameters:**
  - `func`: The method to compute the value.
  - `lock_factory`: Optional, provides a context manager for locking.

#### `@asynclazyfield`

```python
@overload
def asynclazyfield[SelfT, T](
    func: Callable[[SelfT], Coroutine[Any, Any, T]], /
) -> AsyncLazyField[SelfT, T]: ...

@overload
def asynclazyfield[SelfT, T](
    func: None = None,
    /,
    lock_factory: Callable[[], contextlib.AbstractAsyncContextManager] = contextlib.nullcontext,
) -> Callable[[Callable[[SelfT], Coroutine[Any, Any, T]]], AsyncLazyField[SelfT, T]]: ...
```

- **Description:** Decorator for defining an asynchronous lazy field.
- **Parameters:**
  - `func`: The async method to compute the value.
  - `lock_factory`: Optional, provides an async context manager for locking.

#### `mark_class`

```python
def mark_class(
    ctx_factory: Callable[[], contextlib.AbstractContextManager] | None = None,
    actx_factory: Callable[[], contextlib.AbstractAsyncContextManager] | None = None,
)
```

- **Description:** Marks a class so each instance gets its own lock for lazy fields.
- **Parameters:**
  - `ctx_factory`: Factory for sync locks.
  - `actx_factory`: Factory for async locks.

---

### Utilities

- `is_initialized(instance, attr)`: Returns `True` if the lazy field is initialized.
- `dellazy(instance, lazyf)`: Resets the lazy field (sync or async).
- `getlazyfield(instance, attr)`: Returns the lazy field descriptor.

---

## Notes

- Use `@mark_class` if you want per-instance locking (recommended for thread safety).
- For async fields, always use `await obj.field()`.
- You can manually reset a field using `dellazy(obj, MyClass.expensive)`.

---

## See Also

- [Python descriptors](https://docs.python.org/3/howto/descriptor.html)
- [contextlib](https://docs.python.org/3/library/contextlib.html)
- [asyncio](https://docs.python.org/3/library/asyncio.html)