# TaskManager

The `TaskManager` class provides a robust, asynchronous task management utility
for Python, designed to control and monitor concurrent coroutine execution. It
offers features such as concurrency limits, graceful shutdown, and context
manager support, making it a safer and more manageable alternative to using
`asyncio.create_task` directly.

---

## Why?

While `asyncio.create_task` is the standard way to schedule coroutines in
Python, it leaves the developer responsible for tracking, limiting, and
cleaning up tasks. This can lead to resource leaks, unhandled exceptions, and
difficulty in shutting down applications gracefully.

**Example with `asyncio.create_task`:**

```python
tasks = []
for coro in coros:
    tasks.append(asyncio.create_task(coro))
# No built-in limit, tracking, or shutdown handling
```

**With `TaskManager`:**

```python
from escudeiro.ds import TaskManager

async with TaskManager(max_tasks=10) as manager:
    for coro in coros:
        manager.spawn(coro)
# Automatic concurrency control and graceful shutdown
```

**Key differences:**

- **Concurrency control:** `TaskManager` enforces a maximum number of concurrent tasks.
- **Graceful shutdown:** Ensures all tasks are completed or cancelled within a timeout.
- **Tracking:** Each spawn gets a stable `task_id` and a result future; helpers expose queued vs running state.
- **Context manager:** Integrates with `async with` for automatic resource management.
- **Exception handling:** Exceptions from scheduled work can be observed by awaiting the returned `Spawned` handle; the outer task wrapper still logs failures.

---

## `Spawned`

`spawn` returns **`Spawned[T]`**: a small handle that is **awaitable** (it
delegates to an internal `asyncio.Future[T]`), exposes **`task_id`**, and
shares the same future as **`future_for(task_id)`** while the work is in flight.

```python
from escudeiro.ds import Spawned, TaskManager

async def work() -> int:
    return 7

async def main():
    manager = await TaskManager().start()
    spawned: Spawned[int] = manager.spawn(work())
    assert manager.future_for(spawned.task_id) is spawned.future
    n = await spawned  # same as await spawned.future
    assert n == 7
    await manager.close()
```

Fire-and-forget remains valid: you do not have to await `Spawned` if you only
care about side effects and shutdown via `close` / `drain`.

---

## Features

- **Concurrency limiting** via `max_tasks`
- **Graceful shutdown** with configurable timeout
- **Spawn handles** (`Spawned`) with optional await for results and exceptions
- **Introspection:** `future_for`, `is_task_running`, `is_task_queued`
- **Snapshot wait:** `wait_current_snapshot` waits only for futures present at call time
- **Context manager** and `await` support for starting the manager
- **Type-safe and dataclass-based**

---

## Usage

### Basic Example

```python
from escudeiro.ds import TaskManager
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

### Awaiting a result

```python
from escudeiro.ds import TaskManager

async def compute(x: int) -> int:
    return x * 2

async def main():
    async with TaskManager() as manager:
        out = await manager.spawn(compute(21))
        assert out == 42

# asyncio.run(main())
```

### Manual Start and Shutdown

```python
from escudeiro.ds import TaskManager

manager = await TaskManager(max_tasks=5).start()
for coro in coros:
    manager.spawn(coro)
await manager.close()
```

### Awaitable Manager

```python
from escudeiro.ds import TaskManager

manager = await TaskManager(max_tasks=2)
manager.spawn(my_coro(1))
await manager.close()
```

### Wait for a snapshot of in-flight work

`wait_current_snapshot` copies the set of spawn result futures **once** at entry,
then `asyncio.gather`s them. Spawns created **after** the call begins are not
part of that wait. With `timeout`, propagates `asyncio.TimeoutError` if the
snapshot does not finish in time.

```python
await manager.wait_current_snapshot()
await manager.wait_current_snapshot(timeout=30.0)
```

---

## API Reference

### `Spawned[T]`

Dataclass returned by `TaskManager.spawn`.

- **`task_id: str`** — Stable id for this spawn until the future completes.
- **`future: asyncio.Future[T]`** — Completes with the coroutine result or exception.
- **`await spawned`** — Equivalent to awaiting `spawned.future`.

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

- **`spawn(coro) -> Spawned[T]`** — Enqueue a coroutine for execution. Raises **`RuntimeError`** if the manager was not started (`start()` or `async with`). Requires a running event loop.
- **`future_for(task_id: str) -> asyncio.Future[Any] | None`** — The result future for an active or queued spawn, or `None` if unknown or already finished.
- **`is_task_running(task_id: str) -> bool`** — Whether `task_id` has an executing `asyncio.Task` under the manager.
- **`is_task_queued(task_id: str) -> bool`** — Whether `task_id` is still waiting for a worker slot (accepted by `spawn` but `_run` not yet entered).
- **`wait_current_snapshot(timeout: float | None = None) -> Awaitable[None]`** — Wait for all spawn futures that existed at call time; optional timeout raises `asyncio.TimeoutError`.
- **`start() -> Self`** — Start the manager and worker task.
- **`close() -> Awaitable[None]`** — Gracefully shut down the manager.
- **`aclose() -> Awaitable[None]`** — Alias for `close()`, for use with `contextlib.aclosing`.
- **`drain() -> Awaitable[None]`** — Wait for all running and pending tasks to complete.
- **`__await__()`** — Await the manager to start it.
- **`__aenter__() -> Self`** — Async context manager entry.
- **`__aexit__(*_) -> None`** — Async context manager exit.

#### Internal Lazy Fields (advanced)

- **`_pending_coro`:** Queue of `(task_id, runner)` pairs waiting for a slot.
- **`slots`:** Semaphore for concurrency control.
- **`_event`:** Event to signal shutdown.
- **`_running_tasks`:** Map of `task_id` to executing `asyncio.Task`.
- **`_worker_task`:** Background worker task.

---

## Notes

- Always use **`spawn()`** to add coroutines; do not call `asyncio.create_task` directly for managed work.
- Use **`async with TaskManager()`** for automatic startup and shutdown when possible.
- Awaiting **`Spawned`** surfaces exceptions from the user coroutine; the inner task wrapper may still log other failures.
- The manager can be awaited directly to start it (`manager = await TaskManager()`).

---

## See Also

- [asyncio.create_task](https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task)
- [asyncio.Semaphore](https://docs.python.org/3/library/asyncio-sync.html#asyncio.Semaphore)
- [asyncio.Queue](https://docs.python.org/3/library/asyncio-queue.html)
- [Python coroutines](https://docs.python.org/3/library/asyncio-task.html#coroutines)
