# Context Management

The `context` module provides robust context managers for resource acquisition and disposal, supporting both synchronous and asynchronous workflows. It is designed to simplify resource handling within stack frames, ensuring resources are properly acquired, reused, and released—without manual checks or boilerplate.

---

## Why?

Managing resources such as database connections, file handles, or network sockets often requires careful acquisition and disposal to avoid leaks and ensure reuse. Manual management can be error-prone:

```python

def inner_function(resource):
    is_resource_active = resource.is_active()
    if not is_resource_active:
        resource.acquire()
    try:
        # Use the resource
        ...
    finally:
        if is_resource_active:
            resource.release()

def my_function(resource):
    is_resource_active = resource.is_active()
    if not is_resource_active:
        resource.acquire()
    try:
        inner_function(resource)
    finally:
        if is_resource_active:
            resource.release()

```

The `context` module abstracts this pattern, allowing you to work with resources safely and efficiently using context managers, with automatic handling of resource reuse and disposal.
With the context module, you write cleaner and more maintainable code that automatically manages resource lifetimes and accomplishes the same goal without the boilerplate:

```python
from escudeiro.context import Context

class Adapter:
    def new(self) -> Resource:
        # Create a new resource
        pass
    def release(self, resource: Resource):
        # Release the resource
        pass
    def is_active(self, resource: Resource) -> bool:
        # Check if the resource is active
        pass

context = Context(adapter=Adapter())

def inner_function(context):
    with context as resource:
        # Use the resource
        ...

def my_function(context):
    with context as resource:
        # Use the resource
        inner_function()
```

---

## Features

- **Synchronous and asynchronous context managers** (`Context`, `AsyncContext`)
- **Automatic resource acquisition and release**
- **Resource reuse** within the same context
- **Stack-based management** for nested usage
- **Thread-safe and async-safe**
- **Atomic and bound context variants** for transactional or scoped resource handling

---

## Usage

### The Adapter interface

### The Adapter Interface

To enable flexible resource management, the `context` module relies on the concept of an **Adapter**. An Adapter defines how to create, check, and release resources, abstracting the specifics of the underlying resource (such as a database connection, file handle, or network client).

The core interfaces are:

```python
from typing import Protocol

class Adapter[T](Protocol):
    def is_closed(self, client: T) -> bool: ...
    def release(self, client: T) -> None: ...
    def new(self) -> T: ...
```

- **`new()`**: Creates and returns a new resource instance.
- **`is_closed(client)`**: Checks if the resource is closed or released.
- **`release(client)`**: Releases or closes the resource.

For asynchronous resources, use the `AsyncAdapter`:

```python
class AsyncAdapter[T](Protocol):
    async def is_closed(self, client: T) -> bool: ...
    async def release(self, client: T) -> None: ...
    async def new(self) -> T: ...
```

Adapters allow the `Context` and `AsyncContext` managers to work with any resource type, as long as an appropriate adapter is provided. This design decouples resource management logic from business logic, making it easy to plug in different resource types or implementations.

For transactional or atomic operations, you can implement the `AtomicAdapter` or `AtomicAsyncAdapter` interfaces, which add methods for transaction management (`begin`, `commit`, `rollback`, `in_atomic`).

By implementing these interfaces, you enable the context management system to handle resource acquisition, reuse, and cleanup automatically.

The atomic interface is as follows:

```python
class AtomicAdapter[T](Protocol):
    def begin(self, client: T) -> None: ...
    def commit(self, client: T) -> None: ...
    def rollback(self, client: T) -> None: ...
    def in_atomic(self, client: T) -> bool: ...
```

and for asynchronous resources:

```python
class AtomicAsyncAdapter[T](Protocol):
    async def begin(self, client: T) -> None: ...
    async def commit(self, client: T) -> None: ...
    async def rollback(self, client: T) -> None: ...
    async def in_atomic(self, client: T) -> bool: ...
```

### Basic Synchronous Context

```python
from escudeiro.context.context import Context

ctx = Context(adapter=my_adapter)

with ctx as resource:
    # Use the resource
    ...
# Resource is automatically released
```

### Asynchronous Context

```python
from escudeiro.context.context import AsyncContext

ctx = AsyncContext(adapter=my_async_adapter)

async with ctx as resource:
    # Use the resource asynchronously
    ...
# Resource is automatically released
```

### Atomic Contexts

Atomic contexts ensure that resource usage is isolated, useful for transactional operations,
by being unbound, they do not share resources with other contexts, and are suitable for critical sections:

```python
from escudeiro.context import atomic, Context

atomic_ctx = Context(adapter=my_adapter)
with atomic(atomic_ctx, bound=False) as resource:
    # Use resource in an atomic (isolated) way
    ...
```

### Bound Contexts

Bound atomic contexts allow scoped resource usage, where the resource is bound to the context and reused within it.
Different from standard atomic contexts, bound contexts reuse connection and atomicity from the parent context, allowing for scoped operations:

```python
from escudeiro.context import atomic, Context
bound_ctx = Context(adapter=my_adapter)
with atomic(bound_ctx, bound=True) as resource:
    # Use resource in a bound (scoped) way
    ...
```

---

## API Reference

### Classes

#### `Context[T]`

```python
class Context[T]:
    adapter: Adapter[T]

    def is_active(self) -> bool: ...
    def acquire(self): ...
    def release(self): ...
    @contextmanager
    def open(self): ...
    @contextmanager
    def begin(self): ...
    def __enter__(self): ...
    def __exit__(self, *args): ...
```

- **Description:** Synchronous context manager for resource handling.
- **Methods:**
  - `is_active()`: Returns `True` if a resource is currently in use.
  - `acquire()`: Acquires a new resource and increases the stack count.
  - `release()`: Releases the resource and decreases the stack count.
  - `open()`: Context manager for acquiring/releasing without returning the resource.
  - `begin()`: Context manager for acquiring/releasing and returning the resource.

#### `AsyncContext[T]`

```python
class AsyncContext[T]:
    adapter: AsyncAdapter[T]

    def is_active(self) -> bool: ...
    async def acquire(self): ...
    async def release(self): ...
    @asynccontextmanager
    async def open(self): ...
    @asynccontextmanager
    async def begin(self): ...
    async def __aenter__(self): ...
    async def __aexit__(self, *args): ...
```

- **Description:** Asynchronous context manager for resource handling.
- **Methods:** Same as `Context`, but async.

#### `AtomicContext[T]` / `AsyncAtomicContext[T]`

- **Description:** Variants that ensure atomic (isolated) resource usage, suitable for transactions or critical sections.

---

## Utilities

- `atomic(context, bound=True)`: Returns an atomic or bound context manager for the given context.
- `dellazy(instance, lazyf)`: Resets the cached resource (see [Lazy Fields](./lazyfields.md)).

---

## Notes

- Use `begin()` to acquire and return the resource for use within a context.
- Use `open()` if you only need to ensure acquisition and release, without direct access to the resource.
- Stack-based management allows nested usage; resources are only released when the stack count drops to zero.
- For thread safety, contexts use locks internally.

---

## See Also

- [Python context managers](https://docs.python.org/3/library/contextlib.html)
- [asyncio](https://docs.python.org/3/library/asyncio.html)
- [Lazy Fields](./lazyfields.md)
