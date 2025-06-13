# WorkerQueue

The `WorkerQueue` class provides an asynchronous, cache-aware worker queue for Python, designed to process items concurrently with automatic caching and graceful shutdown. It is ideal for scenarios where you want to avoid redundant work, manage concurrency, and ensure results are cached for future requests.

---

## Why?

Consider the following scenario:

```python
async def expensive_task(x):
    # Simulate a costly operation
    await asyncio.sleep(1)
    return x * 2

results = {}
async def cache_get(x):
    return results.get(x)

async def cache_set(x, value):
    results[x] = value
```

Managing concurrent requests, avoiding duplicate work, and handling shutdowns can be complex and error-prone. `WorkerQueue` abstracts these concerns, providing a robust, reusable solution:

```python
from escudeiro.ds.worker import WorkerQueue

queue = WorkerQueue(
    worker=expensive_task,
    cache_get=cache_get,
    cache_set=cache_set,
    maxsize=5,
)

result = await queue.require(10)  # Will compute and cache
result2 = await queue.require(10) # Will use cache
```

---

## Features

- **Async worker queue** with concurrent processing
- **Automatic caching** to avoid redundant work
- **Graceful shutdown** and context manager support
- **Exception handling** and error propagation
- **Global registry** for managing multiple queues
- **Customizable concurrency** via `maxsize`

---

## Usage

### Basic Example

```python
import asyncio
from escudeiro.ds.worker import WorkerQueue

async def worker_fn(x):
    await asyncio.sleep(1)
    return x * 2

cache = {}

async def cache_get(x):
    return cache.get(x)

async def cache_set(x, value):
    cache[x] = value

queue = WorkerQueue(
    worker=worker_fn,
    cache_get=cache_get,
    cache_set=cache_set,
    maxsize=3,
)

async def main():
    print(await queue.require(5))  # Computes and caches
    print(await queue.require(5))  # Uses cache

asyncio.run(main())
```

### Using as an Async Context Manager

```python
async with WorkerQueue(
    worker=worker_fn,
    cache_get=cache_get,
    cache_set=cache_set,
) as queue:
    result = await queue.require(42)
```

### Graceful Shutdown

To ensure all tasks are finished and resources are released:

```python
await queue.aclose()
```

Or close all queues:

```python
await WorkerQueue.aclose_all()
```

---

## API Reference

### Class: `WorkerQueue[T: Hashable, R]`

#### Constructor

```python
WorkerQueue(
    worker: Callable[[T], Awaitable[R]],
    cache_get: Callable[[T], Awaitable[R | None]],
    cache_set: Callable[[T, R], Awaitable[None]],
    maxsize: int = 3,
    finish_timeout: float = 3.0,
)
```

- **worker**: Async function to process items.
- **cache_get**: Async function to retrieve cached results.
- **cache_set**: Async function to store results in cache.
- **maxsize**: Maximum number of items in the queue and concurrent tasks.
- **finish_timeout**: Timeout for finishing pending tasks during shutdown.

#### Methods

- `await require(item: T) -> R`: Request processing of an item, using cache if available.
- `await aclose()`: Gracefully shutdown this worker queue.
- `@classmethod await aclose_all()`: Shutdown all active queues.
- `running: bool`: Property indicating if the worker is active.
- `async def __aenter__()`: Start worker on entering async context.
- `async def __aexit__()`: Shutdown worker on exiting async context.

---

## Notes

- If an item is already being processed, `require` will await the result instead of duplicating work.
- The queue automatically starts the worker task as needed.
- Use `aclose()` or context manager to ensure all tasks are completed and exceptions are handled.
- The class maintains a global registry for easy management of multiple queues.

---

## See Also

- [asyncio](https://docs.python.org/3/library/asyncio.html)
- [Python async/await](https://docs.python.org/3/library/asyncio-task.html)