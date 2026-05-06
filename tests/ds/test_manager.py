# pyright: reportPrivateUsage=false

import asyncio

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
