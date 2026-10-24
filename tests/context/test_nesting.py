import sys
import threading
from collections import Counter

import pytest

from escudeiro.context import (
    AsyncAtomicContext,
    AsyncContext,
    AtomicContext,
    BoundContext,
    Context,
    atomic,
)
from escudeiro.data import data
from escudeiro.lazyfields import check_marking, lazyfield, mark_class

from .mocks import MockAdapter, MockAsyncAdapter, MockClient


class RecordingAdapter(MockAdapter):
    def __init__(self, in_atomic: bool | None = None) -> None:
        self.calls: Counter[str] = Counter()
        self._in_atomic = in_atomic

    def new(self) -> MockClient:
        self.calls["new"] += 1
        return super().new()

    def is_closed(self, client: MockClient) -> bool:
        self.calls["is_closed"] += 1
        return super().is_closed(client)

    def release(self, client: MockClient) -> None:
        self.calls["release"] += 1
        return super().release(client)

    def begin(self, client: MockClient) -> None:
        self.calls["begin"] += 1
        return super().begin(client)

    def commit(self, client: MockClient) -> None:
        self.calls["commit"] += 1
        return super().commit(client)

    def rollback(self, client: MockClient) -> None:
        self.calls["rollback"] += 1
        return super().rollback(client)

    def in_atomic(self, client: MockClient) -> bool:
        if self._in_atomic is not None:
            return self._in_atomic
        return super().in_atomic(client)


class AsyncRecordingAdapter(MockAsyncAdapter):
    def __init__(self, in_atomic: bool | None = None) -> None:
        self.calls: Counter[str] = Counter()
        self._in_atomic = in_atomic

    async def begin(self, client: MockClient) -> None:
        self.calls["begin"] += 1
        await super().begin(client)

    async def commit(self, client: MockClient) -> None:
        self.calls["commit"] += 1
        await super().commit(client)

    async def rollback(self, client: MockClient) -> None:
        self.calls["rollback"] += 1
        await super().rollback(client)

    async def in_atomic(self, client: MockClient) -> bool:
        if self._in_atomic is not None:
            return self._in_atomic
        return await super().in_atomic(client)


def test_nested_bound_context_releases_base_context():
    base = Context(MockAdapter())
    bound = atomic(base)
    with bound as outer:
        with bound as inner:
            assert inner is outer
            assert base.stack == 2
        assert base.stack == 1
        assert not outer.closed
    assert base.stack == 0
    assert bound.stack == 0
    assert outer.closed
    assert outer.count == 0


async def test_nested_async_bound_context_releases_base_context():
    base = AsyncContext(MockAsyncAdapter())
    bound = atomic(base)
    async with bound as outer:
        async with bound:
            assert base.stack == 2
    assert base.stack == 0
    assert bound.stack == 0
    assert outer.closed
    assert outer.count == 0


def test_nested_bound_context_begins_and_commits_once():
    adapter = RecordingAdapter()
    bound = atomic(Context(adapter))
    with bound as client:
        with bound:
            with bound:
                assert client.count == 1
        assert client.count == 1
    assert adapter.calls["begin"] == 1
    assert adapter.calls["commit"] == 1
    assert client.count == 0


@pytest.mark.parametrize("bound", [True, False])
def test_nested_sync_atomic_begins_and_commits_once(bound: bool):
    adapter = RecordingAdapter()
    ctx = atomic(Context(adapter), bound=bound)
    with ctx as client:
        with ctx:
            assert client.count == 1
        # inner exit must not commit the outer transaction
        assert client.count == 1
        assert not client.closed
    assert adapter.calls["begin"] == 1
    assert adapter.calls["commit"] == 1
    assert ctx.stack == 0
    assert client.closed


@pytest.mark.parametrize("bound", [True, False])
async def test_nested_async_atomic_begins_and_commits_once(bound: bool):
    adapter = AsyncRecordingAdapter()
    ctx = atomic(AsyncContext(adapter), bound=bound)
    async with ctx as client:
        async with ctx:
            assert client.count == 1
        assert client.count == 1
    assert adapter.calls["begin"] == 1
    assert adapter.calls["commit"] == 1
    assert ctx.stack == 0
    assert client.closed


@pytest.mark.parametrize("bound", [True, False])
def test_sync_outermost_exit_rolls_back_on_error(bound: bool):
    adapter = RecordingAdapter()
    ctx = atomic(Context(adapter), bound=bound)
    with pytest.raises(RuntimeError):
        with ctx as client:
            with ctx:
                raise RuntimeError
    assert adapter.calls["rollback"] == 1
    assert adapter.calls["commit"] == 0
    assert client.count == 0
    assert client.closed
    assert ctx.stack == 0


@pytest.mark.parametrize("bound", [True, False])
async def test_async_outermost_exit_rolls_back_on_error(bound: bool):
    adapter = AsyncRecordingAdapter()
    ctx = atomic(AsyncContext(adapter), bound=bound)
    with pytest.raises(RuntimeError):
        async with ctx as client:
            async with ctx:
                raise RuntimeError
    assert adapter.calls["rollback"] == 1
    assert adapter.calls["commit"] == 0
    assert client.count == 0
    assert ctx.stack == 0


@pytest.mark.parametrize("bound", [True, False])
def test_sync_commit_guarded_by_in_atomic(bound: bool):
    adapter = RecordingAdapter(in_atomic=False)
    ctx = atomic(Context(adapter), bound=bound)
    with ctx as client:
        pass
    assert adapter.calls["commit"] == 0
    assert adapter.calls["rollback"] == 0
    assert client.closed


@pytest.mark.parametrize("bound", [True, False])
async def test_async_commit_guarded_by_in_atomic(bound: bool):
    adapter = AsyncRecordingAdapter(in_atomic=False)
    ctx = atomic(AsyncContext(adapter), bound=bound)
    async with ctx as client:
        pass
    assert adapter.calls["commit"] == 0
    assert adapter.calls["rollback"] == 0
    assert client.closed


@pytest.mark.parametrize("bound", [True, False])
def test_failed_commit_still_releases_client_and_stack(bound: bool):
    class FailingCommit(RecordingAdapter):
        def commit(self, client: MockClient) -> None:
            raise RuntimeError("commit failed")

    base = Context(FailingCommit())
    ctx = atomic(base, bound=bound)
    with pytest.raises(RuntimeError, match="commit failed"):
        with ctx as client:
            pass
    assert ctx.stack == 0
    assert base.stack == 0
    assert client.closed


def test_atomic_context_types():
    adapter = MockAdapter()
    assert isinstance(atomic(Context(adapter), bound=False), AtomicContext)
    assert isinstance(atomic(Context(adapter)), BoundContext)
    assert isinstance(
        atomic(AsyncContext(MockAsyncAdapter()), bound=False),
        AsyncAtomicContext,
    )


def test_acquire_does_not_allocate_client_to_check_closed():
    adapter = RecordingAdapter()
    ctx = Context(adapter)
    client = ctx.acquire()
    # nothing to check on a context that never had a client
    assert adapter.calls["is_closed"] == 0
    assert adapter.calls["new"] == 1
    # a released client is replaced on the next acquire
    ctx.release()
    ctx.acquire()
    assert adapter.calls["new"] == 2
    assert ctx.client is not client


def test_acquire_replaces_externally_closed_client():
    adapter = RecordingAdapter()
    ctx = Context(adapter)
    first = ctx.acquire()
    first.deactivate()
    second = ctx.acquire()
    assert second is not first
    assert not second.closed


@pytest.fixture
def fast_switching():
    previous = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    yield
    sys.setswitchinterval(previous)


@pytest.mark.usefixtures("fast_switching")
def test_sync_context_release_is_consistent_under_threads():
    adapter = RecordingAdapter()
    ctx = Context(adapter)
    threads = 8
    rounds = 300
    errors: list[BaseException] = []
    barrier = threading.Barrier(threads)

    def worker():
        barrier.wait()
        try:
            for _ in range(rounds):
                with ctx:
                    with ctx as client:
                        assert not client.closed
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    pool = [threading.Thread(target=worker) for _ in range(threads)]
    for t in pool:
        t.start()
    for t in pool:
        t.join(timeout=10)

    assert not errors
    assert ctx.stack == 0
    # every client that was created has been released exactly once
    assert adapter.calls["new"] == adapter.calls["release"]


@pytest.mark.usefixtures("fast_switching")
def test_concurrent_final_releases_release_the_client_once():
    for _ in range(200):
        adapter = RecordingAdapter()
        ctx = Context(adapter)
        ctx.acquire()
        ctx.acquire()
        barrier = threading.Barrier(2)

        def worker():
            barrier.wait()
            ctx.release()

        pool = [threading.Thread(target=worker) for _ in range(2)]
        for t in pool:
            t.start()
        for t in pool:
            t.join()
        assert ctx.stack == 0
        assert adapter.calls["release"] == 1


@pytest.mark.parametrize("ctx_type", [Context, AtomicContext])
def test_threads_share_a_single_lock_per_instance(ctx_type: type):
    for _ in range(100):
        ctx = ctx_type(MockAdapter())
        locks: list[int] = []
        barrier = threading.Barrier(6)

        def worker():
            barrier.wait()
            locks.append(id(ctx._lock))  # pyright: ignore[reportPrivateUsage]

        pool = [threading.Thread(target=worker) for _ in range(6)]
        for t in pool:
            t.start()
        for t in pool:
            t.join()
        assert len(set(locks)) == 1


def test_data_subclass_of_marked_class_gets_its_lock():
    @mark_class(threading.RLock)
    class Base:
        @lazyfield
        def value(self):
            return object()

    @data(frozen=False)
    class Child(Base):
        name: str

    child = Child("x")  # pyright: ignore[reportCallIssue]
    assert check_marking(child, is_async=False)
    lock = child._lazyfield_sync_ctx_  # pyright: ignore[reportAttributeAccessIssue]
    assert child.value is child.value
    assert child._lazyfield_sync_ctx_ is lock  # pyright: ignore[reportAttributeAccessIssue]
    other = Child("y")  # pyright: ignore[reportCallIssue]
    assert check_marking(other, is_async=False)
    assert other._lazyfield_sync_ctx_ is not lock  # pyright: ignore[reportAttributeAccessIssue]
