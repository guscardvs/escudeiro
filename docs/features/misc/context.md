# Context Manager Utilities

The `contextx` module provides utilities for working with Python context managers, including seamless adaptation between synchronous and asynchronous contexts, and type-safe detection of async context managers. This is useful for writing generic code that works with both sync and async resources.

---

## Why?

Python's context managers (`with` and `async with`) are powerful for resource management, but sometimes you need to:

- Use a synchronous context manager in an async context.
- Detect if a context manager is async or sync at runtime.
- Write generic code that works with both.

The `contextx` module solves these problems with minimal boilerplate.

---

## Features

- **Async wrapper for sync context managers** (`AsyncContextWrapper`)
- **Type-safe detection of async context managers** (`is_async_context`)
- **Compatible with standard and custom context managers**

---

## Usage

### Wrapping a Sync Context Manager for Async Use

Suppose you have a synchronous context manager:

```python
from contextlib import contextmanager

@contextmanager
def my_resource():
    print("enter")
    yield "resource"
    print("exit")
```

You can use it in an async context with `AsyncContextWrapper`:

```python
from escudeiro.misc.contextx import AsyncContextWrapper

async def main():
    async with AsyncContextWrapper(my_resource()) as res:
        print(res)  # Prints "resource"

# Output:
# enter
# resource
# exit
```

### Detecting Async Context Managers

You can check if a context manager is asynchronous:

```python
from escudeiro.misc.contextx import is_async_context
from contextlib import nullcontext, asynccontextmanager

print(is_async_context(nullcontext()))  # False

@asynccontextmanager
async def acontext():
    yield

print(is_async_context(acontext()))  # True
```

---

## API Reference

### `AsyncContextWrapper`

```python
@dataclass
class AsyncContextWrapper[T](AbstractAsyncContextManager):
    context: AbstractContextManager[T]

    def __enter__(self) -> T: ...
    def __exit__(self, exc_type, exc_value, traceback) -> Any: ...
    async def __aenter__(self) -> T: ...
    async def __aexit__(self, exc_type, exc_value, traceback) -> Any: ...
```

- **Description:** Wraps a synchronous context manager so it can be used with `async with`.
- **Parameters:**
  - `context`: The synchronous context manager to wrap.

### `is_async_context`

```python
def is_async_context[T](
    context: AbstractContextManager[T] | AbstractAsyncContextManager[T],
) -> TypeIs[AbstractAsyncContextManager[T]]:
    ...
```

- **Description:** Returns `True` if the context manager is asynchronous (has `__aenter__` and `__aexit__`).
- **Parameters:**
  - `context`: The context manager to check.

---

## Notes

- `AsyncContextWrapper` does not make the underlying resource truly asynchronous; it only adapts the interface.
- Use `is_async_context` for runtime checks when writing generic context manager utilities.

---

## See Also

- [contextlib — Context Manager Utilities](https://docs.python.org/3/library/contextlib.html)
- [PEP 492 — Coroutines with async and await syntax](https://peps.python.org/pep-0492/)
- [Python async context managers](https://docs.python.org/3/reference/datamodel.html#asynchronous-context-managers)