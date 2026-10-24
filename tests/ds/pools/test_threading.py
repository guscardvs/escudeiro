# pyright: reportPrivateUsage=false

import threading
import time

import pytest

from escudeiro.data import data
from escudeiro.ds import ThreadPool


@data(frozen=False)
class MockResource:
    state: int
    active: bool

    def close(self):
        time.sleep(0.1)
        self.active = False

    @classmethod
    def create(cls, state: int):
        time.sleep(0.1)
        return cls(state, True)


def get_factory():
    state = 1

    def _factory():
        nonlocal state
        result = MockResource.create(state)
        state += 1
        return result

    return _factory


@pytest.fixture
def thread_pool():
    pool = ThreadPool(get_factory(), MockResource.close)
    yield pool
    pool.dispose()


def test_pool_acquire(thread_pool: ThreadPool[MockResource]):
    resource = thread_pool.acquire()

    assert resource.state == 1


def test_pool_release(thread_pool: ThreadPool[MockResource]):
    resource = thread_pool.acquire()

    thread_pool.release(resource)

    next_resource = thread_pool.acquire()

    assert next_resource is resource


def test_pool_prefill(thread_pool: ThreadPool[MockResource]):
    thread_pool.prefill(3)

    assert thread_pool.resources.qsize() == 3

    thread_pool.prefill(1000)

    assert thread_pool.resources.qsize() == 10


def test_dispose():
    pool = ThreadPool(get_factory(), MockResource.close)

    pool.prefill(3)
    resources = [pool.acquire() for _ in range(pool.resources.qsize())]
    for item in resources:
        pool.release(item)
    pool.dispose()

    for item in resources:
        assert not item.active


def test_thread_pool_racing_condition():
    pool = ThreadPool(get_factory(), MockResource.close, pool_size=2)

    # Acquire the only thread available
    t1 = pool.acquire()

    # Set up a timer to release the thread after a short delay
    timer = threading.Timer(0.5, pool.release, args=[t1])
    timer.start()

    # At the same time, try to acquire a new thread
    # This should result in a race condition
    t2 = pool.acquire()

    # Wait for the timer to release the first thread
    timer.join()

    # Both threads should be different objects
    assert t1 != t2

    # The pool should still only have one available thread
    assert pool._available == 1

    # Release the second thread
    pool.release(t2)

    # The pool should now have two available threads
    assert pool._available == 2


def test_thread_pool_recycle():
    # Create a pool with a pool_recycle timeout of 0.2 seconds
    pool = ThreadPool(
        get_factory(), MockResource.close, pool_size=2, pool_recycle=0.2
    )

    # Acquire a resource and mark its state
    t1 = pool.acquire()
    state = t1.state

    # Release the resource and immediately acquire a new one
    pool.release(t1)
    t2 = pool.acquire()

    # The new resource should have the same state from the previous one
    # if not expired
    assert t2.state == state
    pool.release(t2)

    # Wait for the pool_recycle timeout to expire
    time.sleep(0.3)

    # Acquire a new resource and check its state
    t3 = pool.acquire()

    # The new resource should be recycled and have a new state
    assert t3.state != state
    assert not t1.active

    # Release all resources and dispose of the pool
    pool.release(t3)
    pool.dispose()


# --- regressions: ticket accounting, recycle semantics ------------------


class Plain:
    pass


def _in_thread(fn, timeout: float = 1.0):
    """Run ``fn`` in a daemon thread; fail instead of hanging."""
    out: list[object] = []
    t = threading.Thread(target=lambda: out.append(fn()), daemon=True)
    t.start()
    t.join(timeout)
    assert not t.is_alive(), "call blocked"
    return out[0]


def test_dispose_does_not_shrink_capacity():
    pool = ThreadPool(Plain, lambda r: None, pool_size=3)
    for r in [pool.acquire() for _ in range(3)]:
        pool.release(r)
    pool.dispose()

    assert pool._available == 3
    # all three tickets are still usable (was: the next acquire blocked)
    held = [_in_thread(pool.acquire) for _ in range(3)]
    assert len({id(r) for r in held}) == 3


def test_dispose_with_checked_out_resources_keeps_accounting():
    pool = ThreadPool(Plain, lambda r: None, pool_size=3)
    out = pool.acquire()
    pool.dispose()
    assert pool._available == 2
    pool.release(out)
    assert pool._available == 3


def test_failed_factory_returns_the_ticket():
    calls = 0

    def factory():
        nonlocal calls
        calls += 1
        if calls <= 3:
            raise RuntimeError("factory down")
        return Plain()

    pool = ThreadPool(factory, lambda r: None, pool_size=3)
    for _ in range(3):
        with pytest.raises(RuntimeError):
            pool.acquire()
    assert pool._available == 3  # was: 0
    assert _in_thread(pool.acquire) is not None


def test_failed_recycle_returns_the_ticket():
    broken = False

    def releaser(_: Plain):
        if broken:
            raise RuntimeError("cannot release")

    pool = ThreadPool(Plain, releaser, pool_size=1, pool_recycle=0.01)
    r = pool.acquire()
    pool.release(r)
    time.sleep(0.03)
    broken = True
    with pytest.raises(RuntimeError):
        pool.acquire()
    assert pool._available == 1


def test_blocked_acquire_takes_over_the_released_ticket():
    pool = ThreadPool(Plain, lambda r: None, pool_size=1)
    first = pool.acquire()
    got: list[Plain] = []
    t = threading.Thread(target=lambda: got.append(pool.acquire()), daemon=True)
    t.start()
    time.sleep(0.05)
    assert not got  # blocked: the only ticket is out
    pool.release(first)
    t.join(1)
    assert got == [first]
    # the waiter now holds the ticket (was: released one counted twice)
    assert pool._available == 0
    pool.release(got[0])
    assert pool._available == 1


def test_prefill_respects_checked_out_resources():
    pool = ThreadPool(Plain, lambda r: None, pool_size=2)
    out = pool.acquire()
    pool.prefill(5)
    assert pool.resources.qsize() == 1
    pool.release(out)  # must not overflow the queue
    assert pool.resources.qsize() == 2


def test_pool_recycle_zero_disables_recycling():
    pool = ThreadPool(Plain, lambda r: None, pool_recycle=0)
    r = pool.acquire()
    pool.release(r)
    assert pool.acquire() is r  # was: recycled on every acquire
