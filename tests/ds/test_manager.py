# pyright: reportPrivateUsage=false

import asyncio
import gc
import warnings

import pytest

from escudeiro.ds import TaskManager
from escudeiro.lazyfields import is_initialized


async def test_task_manager_start():
    manager = TaskManager()
    assert (
        not is_initialized(manager, "_worker_task")
        or manager._worker_task is None
    )
    _ = await manager.start()
    assert manager._worker_task is not None
    await manager.close()


async def test_task_manager_spawn():
    manager = await TaskManager().start()

    async def sample_task():
        await asyncio.sleep(0.1)

    manager.spawn(sample_task())
    assert not manager._pending_coro.empty()
    await manager.close()


async def test_task_manager_worker_execution():
    manager = await TaskManager().start()
    results = []

    async def sample_task():
        await asyncio.sleep(0.1)
        results.append(1)

    manager.spawn(sample_task())
    await asyncio.sleep(0.2)  # Allow time for execution
    assert results == [1]
    await manager.close()


async def test_task_manager_concurrency_limit():
    manager = await TaskManager(max_tasks=2).start()
    counter = 0
    lock = asyncio.Lock()

    async def sample_task():
        nonlocal counter
        async with lock:
            counter += 1
        await asyncio.sleep(0.2)
        async with lock:
            counter -= 1

    for _ in range(5):
        manager.spawn(sample_task())

    await asyncio.sleep(0.1)  # Allow some tasks to start
    assert counter <= 2  # max_tasks limit
    await manager.close()


async def test_task_manager_drain():
    manager = await TaskManager().start()
    completed = []

    async def sample_task():
        await asyncio.sleep(0.1)
        completed.append(1)

    manager.spawn(sample_task())
    await manager.drain()
    assert completed == [1]
    await manager.close()


async def test_task_manager_shutdown():
    manager = await TaskManager().start()
    running_task = asyncio.Event()

    async def sample_task():
        running_task.set()
        await asyncio.sleep(1)

    manager.spawn(sample_task())
    _ = await running_task.wait()
    await manager.close()
    assert not manager._running_tasks  # Ensure tasks are cleared


async def test_spawn_before_start_raises():
    manager = TaskManager()
    coro = asyncio.sleep(0)
    with pytest.raises(RuntimeError, match="TaskManager must be started"):
        manager.spawn(coro)
    coro.close()


async def test_spawn_returns_result_via_await():
    manager = await TaskManager().start()
    assert await manager.spawn(asyncio.sleep(0, result=42)) == 42
    await manager.close()


async def test_spawn_propagates_exception():
    manager = await TaskManager().start()

    async def boom():
        raise ValueError("expected")

    with pytest.raises(ValueError, match="expected"):
        _ = await manager.spawn(boom())
    await manager.close()


async def test_future_for_lifecycle():
    manager = await TaskManager().start()
    release = asyncio.Event()

    async def slow():
        await release.wait()

    spawned = manager.spawn(slow())
    assert manager.future_for(spawned.task_id) is spawned.future
    release.set()
    _ = await spawned
    assert manager.future_for(spawned.task_id) is None
    await manager.close()


async def test_is_task_running_and_queued():
    manager = await TaskManager(max_tasks=1).start()
    release = asyncio.Event()
    first_started = asyncio.Event()

    async def first():
        first_started.set()
        await release.wait()

    async def second():
        pass

    s1 = manager.spawn(first())
    _ = await first_started.wait()
    s2 = manager.spawn(second())
    for _ in range(50):
        if manager.is_task_queued(s2.task_id):
            break
        await asyncio.sleep(0)
    assert manager.is_task_queued(s2.task_id)
    assert not manager.is_task_running(s2.task_id)
    assert manager.is_task_running(s1.task_id)
    release.set()
    _ = await s1
    _ = await s2
    assert not manager.is_task_queued(s2.task_id)
    assert not manager.is_task_running(s2.task_id)
    await manager.close()


async def test_wait_current_snapshot_only_initial_futures():
    manager = await TaskManager().start()
    hold = asyncio.Event()
    b_block = asyncio.Event()

    async def blocked():
        await hold.wait()

    async def long_b():
        await b_block.wait()

    _ = manager.spawn(blocked())
    await asyncio.sleep(0)
    wait_task = asyncio.create_task(manager.wait_current_snapshot())
    await asyncio.sleep(0)
    spawned_b = manager.spawn(long_b())
    hold.set()
    await asyncio.wait_for(wait_task, timeout=2.0)
    assert not spawned_b.future.done()
    b_block.set()
    _ = await spawned_b
    await manager.close()


async def test_wait_current_snapshot_timeout():
    manager = await TaskManager().start()
    hang = asyncio.Event()

    async def slow():
        await hang.wait()

    _ = manager.spawn(slow())
    with pytest.raises(asyncio.TimeoutError):
        await manager.wait_current_snapshot(timeout=0.05)
    hang.set()
    await manager.close()


async def test_task_manager_context_manager():
    async with TaskManager() as manager:
        assert manager._worker_task is not None


# --- regressions ---------------------------------------------------------


async def test_manager_can_be_restarted():
    manager = TaskManager()
    _ = await manager.start()
    await manager.close()
    _ = await manager.start()  # the shutdown event of the first run is stale
    spawned = manager.spawn(asyncio.sleep(0, "ran"))
    assert await asyncio.wait_for(spawned, 1) == "ran"
    await manager.close()


async def test_start_twice_keeps_a_single_worker():
    manager = await TaskManager().start()
    first = manager._worker_task
    _ = await manager.start()
    assert manager._worker_task is first
    await manager.close()
    assert first is not None and first.done()


async def test_snapshot_timeout_does_not_cancel_users_futures():
    manager = await TaskManager().start()
    release = asyncio.Event()

    async def slow():
        await release.wait()
        return 42

    spawned = manager.spawn(slow())
    await asyncio.sleep(0)
    with pytest.raises(asyncio.TimeoutError):
        await manager.wait_current_snapshot(timeout=0.05)
    assert not spawned.future.cancelled()  # was: cancelled by wait_for
    release.set()
    assert await spawned == 42
    await manager.close()


async def test_snapshot_does_not_raise_task_errors():
    manager = await TaskManager().start()

    async def boom():
        raise ValueError("task error, not the waiter's problem")

    spawned = manager.spawn(boom())
    await manager.wait_current_snapshot(timeout=1)
    with pytest.raises(ValueError):
        _ = await spawned
    await manager.close()


async def test_awaiting_spawned_is_shielded():
    manager = await TaskManager().start()
    release = asyncio.Event()

    async def slow():
        await release.wait()
        return 1

    spawned = manager.spawn(slow())
    timed_out = asyncio.create_task(asyncio.wait_for(spawned, 0.05))
    other = asyncio.create_task(_await(spawned))
    with pytest.raises(asyncio.TimeoutError):
        await timed_out
    assert not spawned.future.cancelled()
    release.set()
    assert await other == 1  # was: CancelledError
    await manager.close()


async def _await(spawned):
    return await spawned


async def test_close_resolves_every_spawned_job():
    """A job dequeued but stuck waiting for a slot is not silently dropped."""
    manager = await TaskManager(close_timeout_seconds=0.1, max_tasks=1).start()
    running = asyncio.Event()

    async def slow():
        running.set()
        await asyncio.sleep(30)

    async def quick():
        return "quick"

    blocker = manager.spawn(slow())
    _ = await running.wait()
    stuck = manager.spawn(quick())  # dequeued by the worker, waits for the slot
    while not manager._pending_coro.empty():  # the worker has taken it
        await asyncio.sleep(0)
    queued = manager.spawn(quick())  # stays in the queue

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        await manager.close()
        gc.collect()

    assert not [w for w in caught if "never awaited" in str(w.message)]
    for spawned in (blocker, stuck, queued):
        assert spawned.future.done()
    assert blocker.future.cancelled()  # ran past close_timeout_seconds
    assert stuck.future.cancelled()  # discarded: coroutine closed, not lost
    assert not manager._spawn_futures
    assert not manager._running_tasks


async def test_close_cancels_jobs_that_exceed_the_timeout():
    manager = await TaskManager(close_timeout_seconds=0.1).start()
    started = asyncio.Event()

    async def forever():
        started.set()
        await asyncio.Event().wait()

    spawned = manager.spawn(forever())
    _ = await started.wait()
    await manager.close()
    assert spawned.future.cancelled()
    with pytest.raises(asyncio.CancelledError):
        _ = await spawned


async def test_close_runs_jobs_queued_when_closing():
    manager = await TaskManager().start()
    spawned = [manager.spawn(asyncio.sleep(0, i)) for i in range(5)]
    await manager.close()
    assert [sp.future.result() for sp in spawned] == [0, 1, 2, 3, 4]


async def test_spawn_after_close_raises_until_restarted():
    manager = await TaskManager().start()
    await manager.close()
    coro = asyncio.sleep(0)
    with pytest.raises(RuntimeError, match="TaskManager must be started"):
        manager.spawn(coro)
    coro.close()
    _ = await manager.start()
    assert await asyncio.wait_for(manager.spawn(asyncio.sleep(0, 1)), 1) == 1
    await manager.close()
