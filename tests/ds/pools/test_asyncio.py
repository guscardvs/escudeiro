# pyright: reportPrivateUsage=false

import asyncio
from collections.abc import Coroutine

import pytest

from escudeiro.data import data
from escudeiro.ds import AsyncPool


@data(frozen=False)
class MockResource:
    state: int
    active: bool

    async def close(self):
        await asyncio.sleep(0.1)
        self.active = False

    @classmethod
    async def create(cls, state: int):
        await asyncio.sleep(0.1)
        return cls(state, True)


def get_factory():
    state = 1

    async def _factory():
        nonlocal state
        result = await MockResource.create(state)
        state += 1
        return result

    return _factory


@pytest.fixture
async def async_pool():
    pool = AsyncPool(get_factory(), MockResource.close)
    yield pool
    await pool.dispose()


async def test_pool_acquire(async_pool: AsyncPool[MockResource]):
    resource = await async_pool.acquire()

    assert resource.state == 1


async def test_pool_release(async_pool: AsyncPool[MockResource]):
    resource = await async_pool.acquire()

    await async_pool.release(resource)

    next_resource = await async_pool.acquire()

    assert next_resource is resource


async def test_pool_prefill(async_pool: AsyncPool[MockResource]):
    await async_pool.prefill(3)

    assert async_pool.resources.qsize() == 3

    await async_pool.prefill(1000)

    assert async_pool.resources.qsize() == 10


async def test_dispose():
    pool = AsyncPool(get_factory(), MockResource.close)

    await pool.prefill(3)
    resources = [await pool.acquire() for _ in range(pool.resources.qsize())]
    for item in resources:
        await pool.release(item)
    await pool.dispose()

    for item in resources:
        assert not item.active


async def delay_coroutine(delay: float, coro: Coroutine):
    await asyncio.sleep(delay)
    return await coro


async def test_async_pool_racing_condition():
    pool = AsyncPool(get_factory(), MockResource.close, pool_size=2)
    # Acquire the only resource available
    r1 = await pool.acquire()

    # Set up a timer to release the resource after a short delay
    task = asyncio.create_task(delay_coroutine(0.5, pool.release(r1)))

    # At the same time, try to acquire a new resource
    # This should result in a race condition
    r2 = await pool.acquire()

    # Wait for the timer to release the first resource
    await task

    # Both resources should be different objects
    assert r1 != r2

    # The pool should still only have one available resource
    assert pool._available == 1

    # Release the second resource
    await pool.release(r2)

    # The pool should now have two available resources
    assert pool._available == 2


async def test_async_pool_recycle():
    # Create a pool with a pool_recycle timeout of 0.2 seconds
    pool = AsyncPool(
        get_factory(), MockResource.close, pool_size=2, pool_recycle=0.2
    )

    # Acquire a resource and mark its state
    r1 = await pool.acquire()
    state = r1.state

    # Release the resource and immediately acquire a new one
    await pool.release(r1)
    r2 = await pool.acquire()

    # The new resource should have the same state from the previous one
    # if not expired
    assert r2.state == state
    await pool.release(r2)

    # Wait for the pool_recycle timeout to expire
    await asyncio.sleep(0.3)

    # Acquire a new resource and check its state
    r3 = await pool.acquire()

    # The new resource should be recycled and have a new state
    assert r3.state != state
    assert not r1.active

    # Release all resources and dispose of the pool
    await pool.release(r3)
    await pool.dispose()


# --- regressions: ticket accounting, recycle semantics ------------------


class Plain:
    pass


async def make_plain():
    return Plain()


async def noop_release(_: Plain):
    return None


async def test_dispose_does_not_shrink_capacity():
    pool = AsyncPool(make_plain, noop_release, pool_size=3)
    for r in [await pool.acquire() for _ in range(3)]:
        await pool.release(r)
    await pool.dispose()

    assert pool._available == 3
    # all three tickets are still usable (was: the next acquire blocked)
    held = [await asyncio.wait_for(pool.acquire(), 0.3) for _ in range(3)]
    assert len({id(r) for r in held}) == 3


async def test_failed_factory_returns_the_ticket():
    calls = 0

    async def factory():
        nonlocal calls
        calls += 1
        if calls <= 3:
            raise RuntimeError("factory down")
        return Plain()

    pool = AsyncPool(factory, noop_release, pool_size=3)
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await pool.acquire()
    assert pool._available == 3
    assert await asyncio.wait_for(pool.acquire(), 0.3) is not None


async def test_cancelled_acquire_returns_the_ticket():
    started = asyncio.Event()

    async def slow_factory():
        started.set()
        await asyncio.Event().wait()

    pool = AsyncPool(slow_factory, noop_release, pool_size=2)
    task = asyncio.create_task(pool.acquire())
    _ = await started.wait()
    _ = task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert pool._available == 2


async def test_failed_recycle_returns_the_ticket():
    broken = False

    async def releaser(_: Plain):
        if broken:
            raise RuntimeError("cannot release")

    pool = AsyncPool(make_plain, releaser, pool_size=1, pool_recycle=0.01)
    r = await pool.acquire()
    await pool.release(r)
    await asyncio.sleep(0.03)
    broken = True
    with pytest.raises(RuntimeError):
        await pool.acquire()
    assert pool._available == 1


async def test_blocked_acquire_takes_over_the_released_ticket():
    pool = AsyncPool(make_plain, noop_release, pool_size=1)
    first = await pool.acquire()
    waiter = asyncio.create_task(pool.acquire())
    await asyncio.sleep(0.02)
    assert not waiter.done()  # blocked: the only ticket is out
    await pool.release(first)
    assert await asyncio.wait_for(waiter, 0.3) is first
    assert pool._available == 0
    await pool.release(first)
    assert pool._available == 1


async def test_prefill_respects_checked_out_resources():
    pool = AsyncPool(make_plain, noop_release, pool_size=2)
    out = await pool.acquire()
    await pool.prefill(5)
    assert pool.resources.qsize() == 1
    await pool.release(out)  # must not overflow the queue
    assert pool.resources.qsize() == 2


async def test_pool_recycle_zero_disables_recycling():
    pool = AsyncPool(make_plain, noop_release, pool_recycle=0)
    r = await pool.acquire()
    await pool.release(r)
    assert await pool.acquire() is r
