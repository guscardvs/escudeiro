import asyncio
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
