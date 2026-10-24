import asyncio
import gc
from itertools import repeat
from types import SimpleNamespace
from typing import Any, final
from uuid import uuid4

import pytest

from escudeiro.ds import WorkerQueue


def get_worker_func(state: SimpleNamespace):
    """
    Helper function to create a worker function that increments a counter in the given state.

    Args:
        state (SimpleNamespace): The state object to store the counter.

    Returns:
        tuple: The worker function and its unique ID.
    """
    func_id = uuid4().hex
    setattr(state, func_id, 0)

    async def worker_func(item: Any):
        """
        Increment the counter and simulate work by sleeping for a short time.

        Args:
            item: The item to process.

        Returns:
            The processed item.
        """
        setattr(state, func_id, getattr(state, func_id) + 1)
        await asyncio.sleep(0)  # just to simulate some work
        return item

    return worker_func, func_id


@final
class SimpleCache:
    """
    A simple in-memory cache implementation.
    """

    def __init__(self):
        self._cache = {}
        self.cache_hits = 0

    async def get(self, key: Any):
        """
        Get an item from the cache.

        Args:
            key: The key to retrieve.

        Returns:
            The cached item or None if not found.
        """
        result = self._cache.get(key)
        if result is not None:
            self.cache_hits += 1
        return result

    async def put(self, key: Any, value: Any):
        """
        Store an item in the cache.

        Args:
            key: The key under which to store the item.
            value: The item to store.
        """
        self._cache[key] = value


async def test_worker():
    """
    Test the basic functionality of the WorkerQueue.
    Ensure that items are processed and cached correctly.
    """
    state = SimpleNamespace()
    worker_func, func_id = get_worker_func(state)
    cache = SimpleCache()
    async with WorkerQueue(worker_func, cache.get, cache.put) as worker:
        await worker.require(1)
        # Check that the worker function was called
        assert getattr(state, func_id) == 1
        # Check that the item was processed correctly
        assert await worker.require(2) == 2


async def test_gather_worker():
    """
    Test that multiple concurrent requests for the same item are handled correctly.
    Ensure that the worker function is called only once per unique item.
    """
    state = SimpleNamespace()
    worker_func, func_id = get_worker_func(state)
    cache = SimpleCache()
    async with WorkerQueue(worker_func, cache.get, cache.put) as worker:
        results = await asyncio.gather(*(map(worker.require, repeat(10, 5))))
        # Check that the worker function was called only once
        assert getattr(state, func_id) == 1
        # Check that all requests returned the correct result
        assert results == [10, 10, 10, 10, 10]
        # Check that the cache was not hit during the initial requests
        assert not cache.cache_hits
        # Check that the item is now cached
        assert await cache.get(10) == 10


async def test_worker_killed():
    """
    Test that the WorkerQueue stops processing when an exception occurs.
    Ensure that subsequent requests fail after an exception.
    """
    counter = 0

    async def broken_worker(item: Any):
        """
        Simulate a worker function that raises an exception after a certain number of calls.

        Args:
            item: The item to process.

        Returns:
            The processed item or raises an exception.
        """
        nonlocal counter
        curval = counter
        counter += 1
        if curval == 2:
            raise ValueError
        return item

    cache = SimpleCache()
    worker = WorkerQueue(broken_worker, cache.get, cache.put)
    async with worker:
        await worker.require(1)
        await worker.require(2)
    # Check that the worker queue is no longer running
    assert not worker.running
    async with worker:
        with pytest.raises(ValueError):
            await worker.require(3)
        # Check that the worker queue is running again
        assert worker.running


async def test_timeout():
    """
    Test that the WorkerQueue handles timeouts correctly.
    Ensure that a timeout exception is raised when a task exceeds the allowed time.
    """
    max_timeout = 0.1

    async def long_func(item: Any):
        """
        Simulate a worker function that takes longer than the allowed timeout.

        Args:
            item: The item to process.

        Returns:
            The processed item or raises a timeout exception.
        """
        await asyncio.sleep(max_timeout + 4)
        return item

    cache = SimpleCache()
    worker = WorkerQueue(
        long_func, cache.get, cache.put, finish_timeout=max_timeout
    )

    result = await asyncio.gather(
        worker.require(1), worker.aclose(), return_exceptions=True
    )
    # Check that a timeout exception was raised for the worker task
    assert isinstance(result[0], asyncio.TimeoutError)
    # Check that the worker queue closed with the appropriate exceptions
    assert (
        isinstance(result[1], ExceptionGroup)
        and len(result[1].args) == 2
        and result[1].args[1][0] is result[0]
    )


# --- regressions ---------------------------------------------------------


async def _never_cached(_: Any):
    return None


async def _discard(_: Any, __: Any):
    return None


async def test_timeout_of_one_requester_does_not_affect_the_other():
    release = asyncio.Event()
    calls = 0

    async def worker(x: int):
        nonlocal calls
        calls += 1
        await release.wait()
        return x * 2

    q = WorkerQueue(worker, _never_cached, _discard)
    async with q:
        timed_out = asyncio.create_task(asyncio.wait_for(q.require(1), 0.05))
        await asyncio.sleep(0.01)
        other = asyncio.create_task(q.require(1))
        with pytest.raises(asyncio.TimeoutError):
            await timed_out
        release.set()
        assert await other == 2  # was: CancelledError / InvalidStateError
        assert calls == 1


async def test_failed_item_is_retried_not_poisoned():
    calls = 0

    async def worker(x: str):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ValueError("boom")
        return x

    async with WorkerQueue(worker, _never_cached, _discard) as q:
        with pytest.raises(ValueError):
            await q.require("a")
        assert "a" not in q._ongoing
        # was: the stale error was re-raised forever, worker never retried
        assert await asyncio.wait_for(q.require("a"), 1) == "a"
        assert await asyncio.wait_for(q.require("b"), 1) == "b"
        assert calls == 3


async def test_aclose_while_busy_leaves_queue_usable():
    release = asyncio.Event()

    async def worker(x: int):
        await release.wait()
        return x

    q = WorkerQueue(worker, _never_cached, _discard, maxsize=2)
    requests = [asyncio.create_task(q.require(i)) for i in range(2)]
    await asyncio.sleep(0.01)
    closing = asyncio.create_task(q.aclose())
    await asyncio.sleep(0.01)
    release.set()
    await closing
    assert await asyncio.gather(*requests) == [0, 1]
    # was: the queue was padded with Nones, so this put blocked forever
    assert q._worker_queue.qsize() == 0
    assert await asyncio.wait_for(q.require(9), 1) == 9
    assert q.running
    await q.aclose()
    assert not q.running


async def test_shutdown_resolves_every_pending_future():
    async def worker(x: str):
        if x == "bad":
            raise ValueError("bad")
        return x

    loop = asyncio.get_running_loop()
    async with WorkerQueue(worker, _never_cached, _discard, maxsize=1) as q:
        bad, good = loop.create_future(), loop.create_future()
        q._ongoing["bad"], q._ongoing["good"] = bad, good
        await q.aclose()  # was: bad's ValueError aborted the gather
    assert good.result() == "good"
    with pytest.raises(ValueError):
        bad.result()
    assert not q._ongoing


async def test_cancelled_put_does_not_leave_state_behind():
    release = asyncio.Event()
    started = asyncio.Event()

    async def worker(x: int):
        started.set()
        await release.wait()
        return x

    q = WorkerQueue(worker, _never_cached, _discard, maxsize=1)
    async with q:
        first = asyncio.create_task(q.require(1))
        _ = await started.wait()  # the only consumer is busy
        second = asyncio.create_task(q.require(2))  # fills the queue
        await asyncio.sleep(0.01)
        third = asyncio.create_task(q.require(3))  # blocked in put
        await asyncio.sleep(0.01)
        assert 3 in q._ongoing
        _ = third.cancel()
        with pytest.raises(asyncio.CancelledError):
            await third
        assert 3 not in q._ongoing  # was: stale future, retry hung
        release.set()
        assert await first == 1
        assert await second == 2
        assert await asyncio.wait_for(q.require(3), 1) == 3


async def test_aclose_all_closes_everything():
    async def worker(x: int):
        return x

    queues = [WorkerQueue(worker, _never_cached, _discard) for _ in range(3)]
    for i, q in enumerate(queues):
        _ = await q.require(i)
    assert all(q.running for q in queues)
    # was: RuntimeError, dictionary changed size during iteration
    await WorkerQueue.aclose_all()
    assert not any(q.running for q in queues)


async def test_registry_does_not_keep_instances_alive():
    async def worker(x: int):
        return x

    q = WorkerQueue(worker, _never_cached, _discard)
    key = id(q)
    assert key in WorkerQueue._global_registry
    del q
    _ = gc.collect()
    assert key not in WorkerQueue._global_registry


async def test_cache_set_failure_is_reported_on_close():
    async def worker(x: int):
        return x

    async def broken_cache_set(_: Any, __: Any):
        raise OSError("cache down")

    q = WorkerQueue(worker, _never_cached, broken_cache_set)
    assert await q.require(5) == 5  # the result is still delivered
    with pytest.raises(ExceptionGroup) as info:
        await q.aclose()
    assert info.group_contains(OSError)
