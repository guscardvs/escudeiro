from collections.abc import Generator
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Self, final

from escudeiro.misc import AsyncContextWrapper, is_async_context


@final
class KlassContext:
    def __init__(self) -> None:
        self.enter_count = 0
        self.exit_count = 0

    def __enter__(self) -> Self:
        self.enter_count += 1
        return self

    def __exit__(self, *_):
        self.exit_count += 1
        return


@contextmanager
def func_context[T](state: dict[str, Any], returns: T = None) -> Generator[T]:
    state["enter_count"] = 1
    yield returns
    state["exit_count"] = 1


@asynccontextmanager
async def afunc_context(state: dict[str, Any]):
    state["enter_count"] = 1
    yield
    state["exit_count"] = 1


@final
class KlassAsyncContext:
    def __init__(self) -> None:
        self._enter_count = 0
        self._exit_count = 0

    async def __aenter__(self) -> Self:
        self._enter_count += 1
        return self

    async def __aexit__(self, *_):
        self._exit_count += 1
        return


def test_is_async_context_recognizes_correctly():
    assert is_async_context(afunc_context({}))
    assert is_async_context(KlassAsyncContext())

    assert not is_async_context(func_context({}))
    assert not is_async_context(KlassContext())
    assert is_async_context(AsyncContextWrapper(func_context({})))


async def test_async_context_wrapper_behaves_as_expected():
    state = {}
    sentinel = object()

    async with AsyncContextWrapper(func_context(state, sentinel)) as target:
        pass

    assert state["enter_count"] == 1
    assert state["exit_count"] == 1
    assert target is sentinel


async def test_async_context_wrapper_works_for_class_contexts():
    context = KlassContext()

    async with AsyncContextWrapper(context) as target:
        pass

    assert context.enter_count == 1
    assert context.exit_count == 1
    assert target is context
