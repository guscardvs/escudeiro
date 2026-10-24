from sqlalchemy import create_engine
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    create_async_engine,
)

from escudeiro.context import AsyncContext, Context
from escudeiro.lazyfields import lazyfield


class SaAdapter:
    """Atomic adapter that manages SQLAlchemy sync connections."""

    def __init__(
        self, *, uri: str | None = None, engine: Engine | None = None
    ) -> None:
        if uri is None and engine is None:
            raise TypeError("Missing parameters (uri/engine)")
        self._uri = uri
        if engine is not None:
            self._engine = engine

    @lazyfield
    def _engine(self) -> Engine:
        assert self._uri
        return create_engine(self._uri)

    def is_closed(self, client: Connection) -> bool:
        return client.closed

    def new(self) -> Connection:
        return self._engine.connect()

    def release(self, client: Connection) -> None:
        client.close()

    def begin(self, client: Connection) -> None:
        if not client.in_transaction():
            _ = client.begin()

    def commit(self, client: Connection) -> None:
        client.commit()

    def rollback(self, client: Connection) -> None:
        client.rollback()

    def in_atomic(self, client: Connection) -> bool:
        return client.in_transaction()

    def context(self) -> Context[Connection]:
        return Context(self)


class AsyncSaAdapter:
    """Atomic adapter that manages SQLAlchemy async connections."""

    def __init__(
        self,
        *,
        uri: str | None = None,
        engine: AsyncEngine | None = None,
    ) -> None:
        if uri is None and engine is None:
            raise TypeError("Missing parameters (uri/engine)")
        self._uri = uri
        if engine is not None:
            self._engine = engine

    @lazyfield
    def _engine(self) -> AsyncEngine:
        assert self._uri
        return create_async_engine(self._uri)

    async def is_closed(self, client: AsyncConnection) -> bool:
        return client.closed

    async def new(self) -> AsyncConnection:
        return await self._engine.connect()

    async def release(self, client: AsyncConnection) -> None:
        await client.close()

    async def begin(self, client: AsyncConnection) -> None:
        if not client.in_transaction():
            _ = await client.begin()

    async def commit(self, client: AsyncConnection) -> None:
        await client.commit()

    async def rollback(self, client: AsyncConnection) -> None:
        await client.rollback()

    async def in_atomic(self, client: AsyncConnection) -> bool:
        return client.in_transaction()

    def context(self) -> AsyncContext[AsyncConnection]:
        return AsyncContext(self)
