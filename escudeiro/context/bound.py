import threading
from types import TracebackType
from typing import override

from escudeiro.context.context import AsyncContext, Context
from escudeiro.context.interfaces import AtomicAdapter, AtomicAsyncAdapter
from escudeiro.data import data, private
from escudeiro.data.helpers import call_init
from escudeiro.lazyfields import mark_class


@mark_class(threading.RLock)
@data(frozen=False)
class BoundContext[T](Context[T]):
    """A context manager for managing atomic transactions with an adapter."""

    adapter: AtomicAdapter[T]
    context: Context[T]

    _already_inited: bool = private(initial=False)

    def __new__(cls, adapter: AtomicAdapter[T], context: Context[T]):
        if not isinstance(context, cls) or adapter is not context.adapter:
            self = object.__new__(cls)
            return self
        return context

    def __init__(self, adapter: AtomicAdapter[T], context: Context[T]) -> None:
        """
        Initialize a BoundContext instance.

        Args:
            adapter (AtomicAdapter[T]): The atomic adapter for managing transactions.
            context (Context[T]): The underlying context to manage.
        """
        if hasattr(self, "_already_inited"):
            return
        call_init(self, adapter, context)
        self._already_inited = True

    @override
    def acquire(self) -> T:
        """
        Acquire the context for a transaction and begin an atomic operation.

        Returns:
            T: The acquired context.
        """
        with self._lock:
            client = self.context.acquire()
            self.stack += 1
            self.adapter.begin(client)
        return client

    @override
    def release(self, commit: bool = True):
        """
        Release the context, committing or rolling back the transaction if needed.

        Args:
            commit (bool, optional): Whether to commit the transaction. Defaults to True.
        """
        with self._lock:
            if self.stack == 1:
                if self.adapter.in_atomic(self.context.client):
                    if commit:
                        self.adapter.commit(self.context.client)
                    else:
                        self.adapter.rollback(self.context.client)
                self.context.release()
            self.stack -= 1

    @override
    def __exit__(
        self,
        *exc: tuple[
            type[BaseException] | None, Exception | None, TracebackType | None
        ],
    ):
        """
        Exit the context manager and release the context.

        Args:
            *exc: Exception information.
        """
        self.release(not any(exc))


@data(frozen=False)
class AsyncBoundContext[T](AsyncContext[T]):
    """An asynchronous context manager for managing atomic transactions with an async adapter."""

    adapter: AtomicAsyncAdapter[T]
    context: AsyncContext[T]
    _already_inited: bool = private(initial=False)

    def __new__(cls, adapter: AtomicAsyncAdapter[T], context: AsyncContext[T]):
        if not isinstance(context, cls) or adapter is not context.adapter:
            self = object.__new__(cls)
            return self
        return context

    def __init__(
        self, adapter: AtomicAsyncAdapter[T], context: AsyncContext[T]
    ) -> None:
        """
        Initialize an AsyncBoundContext instance.

        Args:
            adapter (AtomicAsyncAdapter[T]): The async atomic adapter for managing transactions.
            context (AsyncContext[T]): The underlying async context to manage.
        """
        if hasattr(self, "_already_inited"):
            return
        call_init(self, adapter, context)
        self._already_inited = True

    @override
    async def acquire(self) -> T:
        """
        Acquire the async context for a transaction and begin an atomic operation.

        Returns:
            T: The acquired async context.
        """
        async with self.lock:
            client = await self.context.acquire()
            if self.stack == 0:
                await self.adapter.begin(client)
            self.stack += 1
            return client

    @override
    async def release(self, commit: bool = True):
        """
        Release the async context, committing or rolling back the transaction if needed.

        Args:
            commit (bool, optional): Whether to commit the transaction. Defaults to True.
        """
        async with self.lock:
            client = await self.context.client()
            if self.stack == 1:
                if commit:
                    await self.adapter.commit(client)
                else:
                    await self.adapter.rollback(client)
            self.stack -= 1
        await self.context.release()

    @override
    async def __aexit__(
        self,
        *exc: tuple[
            type[BaseException] | None,
            BaseException | None,
            TracebackType | None,
        ],
    ):
        """
        Exit the async context manager and release the async context.

        Args:
            *exc: Exception information.
        """
        await self.release(not any(exc))
