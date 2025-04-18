import asyncio
import contextlib
import threading

from escudeiro.context.interfaces import Adapter, AsyncAdapter
from escudeiro.data import data
from escudeiro.lazyfields import asynclazyfield, dellazy, lazyfield, mark_class


@mark_class(threading.RLock)
@data(frozen=False)
class Context[T]:
    adapter: Adapter[T]

    @lazyfield
    def stack(self) -> int:
        return 0

    @lazyfield
    def _lock(self) -> threading.Lock:
        return threading.Lock()

    @lazyfield
    def client(self) -> T:
        """
        Returns the current resource being used by the context.
        Acquires a new resource if the current one is closed or doesn't exist.
        """
        return self.adapter.new()

    def is_active(self) -> bool:
        """
        Returns whether the context is currently in use.
        """
        return self.stack > 0

    def acquire(self):
        """
        Acquires a new resource from the adapter and increases the stack count.
        """
        with self._lock:
            if self.adapter.is_closed(self.client):
                dellazy(self, type(self).client)
            self.stack += 1
            return self.client

    def release(self):
        """
        Releases the current resource if the stack count is 1,
        and decreases the stack count.
        """
        if self.stack == 1:
            with self._lock:
                self.adapter.release(self.client)
                dellazy(self, type(self).client)
        self.stack -= 1

    @contextlib.contextmanager
    def open(self):
        """
        A context manager that acquires and releases resources without returning it.
        """
        with self:
            yield

    @contextlib.contextmanager
    def begin(self):
        """
        A context manager that acquires and releases resources and returns it.
        """
        with self as client:
            yield client

    def __enter__(self):
        """
        Acquires a new resource from the adapter and increases the stack count.
        """
        return self.acquire()

    def __exit__(self, *_):
        """
        Releases the current resource if the stack count is 1,
        and decreases the stack count.
        """
        self.release()


@data(frozen=False)
class AsyncContext[T]:
    adapter: AsyncAdapter[T]

    @lazyfield
    def stack(self):
        return 0

    @lazyfield
    def lock(self):
        return asyncio.Lock()

    def is_active(self) -> bool:
        """
        Returns whether the context is currently in use.
        """
        return self.stack > 0

    @asynclazyfield
    async def client(self) -> T:
        """
        Returns the current resource being used by the context.
        Acquires a new resource if the current one is closed or doesn't exist.
        """
        return await self.adapter.new()

    async def acquire(self):
        """
        Acquires a new resource from the adapter and increases the stack count.
        """
        async with self.lock:
            client = await self.client()
            self.stack += 1
            return client

    async def release(self):
        """
        Releases the current resource if the stack count is 1,
        and decreases the stack count.
        """
        async with self.lock:
            if self.stack == 1:
                await self.adapter.release(await self.client())
                await dellazy(self, type(self).client)
            self.stack -= 1

    @contextlib.asynccontextmanager
    async def open(self):
        """
        An async context manager that acquires and releases resources without returning it.
        """
        async with self:
            yield

    @contextlib.asynccontextmanager
    async def begin(self):
        """
        An async context manager that acquires and releases resources and returns it.
        """
        async with self as client:
            yield client

    async def __aenter__(self):
        """
        Acquires a new resource from the adapter and increases the stack count.
        """
        return await self.acquire()

    async def __aexit__(self, *_):
        """
        Releases the current resource if the stack count is 1,
        and decreases the stack count.
        """
        await self.release()
