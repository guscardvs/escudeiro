from types import TracebackType
from typing import override

from escudeiro.context.context import AsyncContext, Context
from escudeiro.context.interfaces import (
    AtomicAdapter,
    AtomicAsyncAdapter,
)
from escudeiro.data import data
from escudeiro.lazyfields import dellazy, lazyfield


@data(frozen=False)
class AtomicContext[T](Context[T]):
    adapter: AtomicAdapter[T]

    def __post_init__(self):
        Context.__init__(self, self.adapter)

    @lazyfield
    def client(self):
        return self.adapter.new()

    @override
    def acquire(self) -> T:
        with self._lock:
            if self.adapter.is_closed(self.client):
                dellazy(self, type(self).client)
            self.stack += 1
            self.adapter.begin(self.client)
        return self.client

    @override
    def release(self, commit: bool = True):
        with self._lock:
            if self.stack == 1:
                if self.adapter.in_atomic(self.client):
                    if commit:
                        self.adapter.commit(self.client)
                    else:
                        self.adapter.rollback(self.client)
                self.adapter.release(self.client)
                dellazy(self, type(self).client)
            self.stack -= 1

    @override
    def __exit__(
        self,
        *exc: tuple[
            type[BaseException] | None,
            BaseException | None,
            TracebackType | None,
        ],
    ):
        self.release(not any(exc))


@data(frozen=False)
class AsyncAtomicContext[T](AsyncContext[T]):
    adapter: AtomicAsyncAdapter[T]

    def __post_init__(self):
        AsyncContext.__init__(self, self.adapter)

    @override
    async def acquire(self):
        async with self.lock:
            client = await self.client()
            if self.stack == 0:
                await self.adapter.begin(client)
            self.stack += 1
            return client

    @override
    async def release(self, commit: bool = True):
        async with self.lock:
            client = await self.client()
            if self.stack == 1:
                if await self.adapter.in_atomic(client):
                    if commit:
                        await self.adapter.commit(client)
                    else:
                        await self.adapter.rollback(client)
                await self.adapter.release(client)
                await dellazy(self, type(self).client)
            self.stack -= 1

    @override
    async def __aexit__(
        self,
        *exc: tuple[
            type[BaseException] | None,
            BaseException | None,
            TracebackType | None,
        ],
    ):
        await self.release(not any(exc))
