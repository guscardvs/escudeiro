# pyright: reportPrivateUsage=false

import asyncio

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


async def test_task_manager_context_manager():
    async with TaskManager() as manager:
        assert manager._worker_task is not None
