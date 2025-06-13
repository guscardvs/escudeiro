# Pools

The `pools` module provides efficient resource pooling for Python, supporting both synchronous and asynchronous usage patterns. It is designed for managing expensive or limited resources, such as database connections or network sockets, with built-in support for recycling, pre-filling, and thread safety.

---

## Why?

Consider the following scenario:

```python
# Without pooling
def get_connection():
    return connect_to_db()

conn = get_connection()
# use conn
```

Creating and destroying resources repeatedly can be expensive and inefficient. The `pools` module solves this by reusing resources, limiting the number of active instances, and handling resource lifecycle automatically.

```python
from escudeiro.ds.pools import AsyncPool

async def factory():
    return await connect_to_db()

pool = AsyncPool(factory, releaser=close_connection, pool_size=5)
conn = await pool.acquire()
# use conn
await pool.release(conn)
```

---

## Features

- **Synchronous and asynchronous pools**
- **Configurable pool size and recycling**
- **Resource pre-filling**
- **Automatic resource release and reacquire**
- **Thread-safe and asyncio-compatible**
- **Manual disposal and reset**

---

## Usage

### Basic Asynchronous Pool

```python
from escudeiro.ds.pools import AsyncPool

async def factory():
    # create a new resource
    return await connect_to_db()

async def releaser(resource):
    # clean up the resource
    await resource.close()

pool = AsyncPool(factory, releaser, pool_size=10)

async def main():
    conn = await pool.acquire()
    try:
        # use conn
        ...
    finally:
        await pool.release(conn)

await pool.dispose()  # Clean up all resources
```

### Prefilling the Pool

```python
await pool.prefill()  # Pre-create all resources up to pool_size
```

### Recycling Resources

You can set a `pool_recycle` timeout (in seconds) to automatically recycle resources after a certain period.

```python
pool = AsyncPool(factory, releaser, pool_size=5, pool_recycle=3600)
```

---

## API Reference

### `AsyncPool`

```python
class AsyncPool[T]:
    def __init__(
        self,
        factory: Callable[[], Awaitable[T]],
        releaser: Callable[[T], Awaitable[None]],
        queue_class: type[asyncio.Queue[T]] = asyncio.LifoQueue,
        pool_size: int = 10,
        pool_recycle: float = 3600,
    )
```

- **Description:** Asynchronous resource pool.
- **Parameters:**
  - `factory`: Async function to create a new resource.
  - `releaser`: Async function to clean up a resource.
  - `queue_class`: Queue type for managing resources (default: LIFO).
  - `pool_size`: Maximum number of resources.
  - `pool_recycle`: Time in seconds before a resource is recycled.

#### Methods

- `await acquire()`: Acquire a resource from the pool.
- `await release(resource)`: Release a resource back to the pool.
- `await prefill(count: int | None = None)`: Pre-create resources.
- `await dispose()`: Dispose all resources and clear the pool.

---

## Notes

- Use `prefill()` to avoid resource creation delays at runtime.
- Always release resources back to the pool to avoid leaks.
- The pool is thread-safe and can be used in concurrent async tasks.

---

## See Also

- [asyncio.Queue](https://docs.python.org/3/library/asyncio-queue.html)
- [Resource pooling pattern](https://en.wikipedia.org/wiki/Object_pool_pattern)
 