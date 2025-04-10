import asyncio
import contextlib
from types import SimpleNamespace
from typing import Any

from escudeiro.context import AsyncContext

from .mocks import MockAsyncAdapter


async def test_asynccontext_acquisition():
    adapter = MockAsyncAdapter()
    context = AsyncContext(adapter)
    async with context.open():
        assert context.stack == 1
        client = await context.acquire()
        assert not client.closed
        client2 = await context.acquire()
        assert client == client2
        await context.release()
        await context.release()
    assert context.stack == 0
    assert client.closed


async def test_asynccontext_release():
    adapter = MockAsyncAdapter()
    context = AsyncContext(adapter)
    client = await context.acquire()
    assert not client.closed
    await context.release()
    assert context.stack == 0
    assert client.closed


async def test_asynccontext_double_release():
    adapter = MockAsyncAdapter()
    context = AsyncContext(adapter)
    client = await context.acquire()
    assert not client.closed
    await context.release()
    assert context.stack == 0
    assert client.closed


async def test_asynccontext_multitask():
    adapter = MockAsyncAdapter()
    context = AsyncContext(adapter)

    async def worker():
        async with context.open():
            async with context.begin() as client:
                assert context.stack == 2
                assert not client.closed
                client2 = await context.acquire()
                assert client == client2
                await context.release()
        assert context.stack == 0
        assert client.closed

    tasks = []
    for _ in range(5):
        tasks.append(asyncio.create_task(worker()))
    _ = await asyncio.gather(*tasks)


async def test_asynccontext_releases_resource_even_on_error():
    adapter = MockAsyncAdapter()
    context = AsyncContext(adapter)

    client: Any = SimpleNamespace()
    with contextlib.suppress(Exception):
        async with context.begin() as client:
            raise Exception

    assert client.closed
    assert context.stack == 0

    with contextlib.suppress(Exception):
        async with context.open():
            client = await context.acquire()
            await context.release()
            raise Exception

    assert client.closed
    assert context.stack == 0

    with contextlib.suppress(Exception):
        async with context as client:
            raise Exception

    assert client.closed
    assert context.stack == 0
