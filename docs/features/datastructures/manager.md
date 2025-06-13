# TaskManager

The `TaskManager` class provides a robust, asynchronous task management utility for Python, designed to control and monitor concurrent coroutine execution. It offers features such as concurrency limits, graceful shutdown, and context manager support, making it a safer and more manageable alternative to using `asyncio.create_task` directly.

---

## Why?

While `asyncio.create_task` is the standard way to schedule coroutines in Python, it leaves the developer responsible for tracking, limiting, and cleaning up tasks. This can lead to resource leaks, unhandled exceptions, and difficulty in shutting down applications gracefully.

**Example with `asyncio.create_task`:**

```python
tasks = []
for coro in coros:
    tasks.append(asyncio.create_task(coro))
# No built-in limit, tracking, or shutdown handling
```

**With `TaskManager`:**

```python
from escudeiro.ds.manager import TaskManager

async with TaskManager(max_tasks=10) as manager:
    for coro in coros:
        manager.spawn(coro)
# Automatic concurrency control and graceful shutdown
```

**Key differences:**

- **Concurrency control:** `TaskManager` enforces a maximum number of concurrent tasks.
- **Graceful shutdown:** Ensures all tasks are completed or cancelled within a timeout.
- **Tracking:** Tasks are tracked by unique IDs for easier management.
- **Context manager:** Integrates with `async with` for automatic resource management.
- **Exception handling:** Catches and logs exceptions from tasks.

---

## Features

- **Concurrency limiting** via `max_tasks`
- **Graceful shutdown** with configurable timeout
- **Automatic task tracking** and cleanup
- **Context manager** and `await` support
- **Exception handling** for all tasks
- **Type-safe and dataclass-based**

---

## Usage

### Basic Example

```python
from escudeiro.ds.manager import TaskManager
import asyncio

async def my_coro(n):
    await asyncio.sleep(1)
    print(f"Done {n}")

async def main():
    async with TaskManager(max_tasks=3) as manager:
        for i in range(10):
            manager.spawn(my_coro(i))
    # All tasks are completed or cancelled on exit

asyncio.run(main())
```

### Manual Start and Shutdown

```python
manager = await TaskManager(max_tasks=5).start()
for coro in coros:
    manager.spawn(coro)
await manager.close()
```

### Awaitable Manager

```python
manager = await TaskManager(max_tasks=2)
manager.spawn(my_coro(1))
await manager.close()
```

---

## API Reference

### `TaskManager` class

#### Initialization

```python
TaskManager(
    close_timeout_seconds: int = 10,
    max_tasks: int = 35
)
```

- **close_timeout_seconds:** Maximum time (in seconds) to wait for tasks to finish during shutdown.
- **max_tasks:** Maximum number of concurrent tasks.

#### Methods

- `spawn(coro: Coroutine) -> None`: Enqueue a coroutine for execution.
- `start() -> Self`: Start the manager and worker task.
- `close() -> Awaitable[None]`: Gracefully shut down the manager.
- `aclose() -> Awaitable[None]`: Alias for `close()`, for use with `contextlib.aclosing`.
- `drain() -> Awaitable[None]`: Wait for all running and pending tasks to complete.
- `__await__()`: Await the manager to start it.
- `__aenter__() -> Self`: Async context manager entry.
- `__aexit__(*_) -> None`: Async context manager exit.

#### Internal Lazy Fields

- `_pending_coro`: Queue of pending coroutines.
- `slots`: Semaphore for concurrency control.
- `_event`: Event to signal shutdown.
- `_running_tasks`: Dictionary of running tasks.
- `_worker_task`: Background worker task.

---

## Notes

- Always use `spawn()` to add coroutines; do not call `asyncio.create_task` directly.
- Use as an async context manager (`async with`) for automatic startup and shutdown.
- Exceptions in tasks are logged but do not stop the manager.
- The manager can be awaited directly to start it.

---

## See Also

- [asyncio.create_task](https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task)
- [asyncio.Semaphore](https://docs.python.org/3/library/asyncio-sync.html#asyncio.Semaphore)
- [asyncio.Queue](https://docs.python.org/3/library/asyncio-queue.html)
- [Python coroutines](https://docs.python.org/3/library/asyncio-task.html#coroutines)