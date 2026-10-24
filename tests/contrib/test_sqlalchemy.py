from pathlib import Path

import pytest

sa = pytest.importorskip("sqlalchemy")
_ = pytest.importorskip("aiosqlite")

from escudeiro.context import atomic  # noqa: E402
from escudeiro.contrib.sqlalchemy import AsyncSaAdapter, SaAdapter  # noqa: E402


@pytest.fixture
def sync_adapter(tmp_path: Path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'db.sqlite'}")
    with engine.begin() as conn:
        _ = conn.execute(sa.text("create table t (v integer)"))
    yield SaAdapter(engine=engine)
    engine.dispose()


@pytest.fixture
async def async_adapter(tmp_path: Path):
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'adb.sqlite'}"
    )
    async with engine.begin() as conn:
        _ = await conn.execute(sa.text("create table t (v integer)"))
    yield AsyncSaAdapter(engine=engine)
    await engine.dispose()


def _count(adapter: SaAdapter) -> int:
    with adapter.context() as conn:
        return conn.execute(sa.text("select count(*) from t")).scalar_one()


async def _acount(adapter: AsyncSaAdapter) -> int:
    async with adapter.context() as conn:
        return (
            await conn.execute(sa.text("select count(*) from t"))
        ).scalar_one()


def test_adapter_requires_uri_or_engine():
    with pytest.raises(TypeError):
        SaAdapter()
    with pytest.raises(TypeError):
        AsyncSaAdapter()


def test_adapter_builds_engine_from_uri(tmp_path: Path):
    adapter = SaAdapter(uri=f"sqlite:///{tmp_path / 'u.sqlite'}")
    ctx = adapter.context()
    with ctx as conn:
        assert conn.execute(sa.text("select 1")).scalar_one() == 1
    assert conn.closed
    adapter._engine.dispose()  # pyright: ignore[reportPrivateUsage]


def test_plain_context_closes_connection(sync_adapter: SaAdapter):
    ctx = sync_adapter.context()
    with ctx as conn:
        assert not sync_adapter.is_closed(conn)
    assert sync_adapter.is_closed(conn)
    assert ctx.stack == 0


@pytest.mark.parametrize("bound", [True, False])
def test_atomic_commits_on_success(sync_adapter: SaAdapter, bound: bool):
    ctx = atomic(sync_adapter.context(), bound=bound)
    with ctx as conn:
        _ = conn.execute(sa.text("insert into t values (1)"))
        assert sync_adapter.in_atomic(conn)
    assert sync_adapter.is_closed(conn)
    assert _count(sync_adapter) == 1


@pytest.mark.parametrize("bound", [True, False])
def test_atomic_rolls_back_on_error(sync_adapter: SaAdapter, bound: bool):
    ctx = atomic(sync_adapter.context(), bound=bound)
    with pytest.raises(RuntimeError):
        with ctx as conn:
            _ = conn.execute(sa.text("insert into t values (1)"))
            raise RuntimeError
    assert sync_adapter.is_closed(conn)
    assert _count(sync_adapter) == 0


@pytest.mark.parametrize("bound", [True, False])
def test_nested_atomic_commits_once_at_outermost_exit(
    sync_adapter: SaAdapter, bound: bool
):
    base = sync_adapter.context()
    ctx = atomic(base, bound=bound)
    with ctx as outer:
        with ctx as inner:
            assert inner is outer
            _ = inner.execute(sa.text("insert into t values (1)"))
        # inner exit must neither commit nor close
        assert outer.in_transaction()
        assert not outer.closed
        _ = outer.execute(sa.text("insert into t values (2)"))
    assert outer.closed
    assert ctx.stack == 0
    assert base.stack == 0
    assert _count(sync_adapter) == 2


@pytest.mark.parametrize("bound", [True, False])
async def test_async_atomic_commits_on_success(
    async_adapter: AsyncSaAdapter, bound: bool
):
    ctx = atomic(async_adapter.context(), bound=bound)
    async with ctx as conn:
        _ = await conn.execute(sa.text("insert into t values (1)"))
        assert await async_adapter.in_atomic(conn)
    assert await async_adapter.is_closed(conn)
    assert await _acount(async_adapter) == 1


@pytest.mark.parametrize("bound", [True, False])
async def test_async_atomic_rolls_back_on_error(
    async_adapter: AsyncSaAdapter, bound: bool
):
    ctx = atomic(async_adapter.context(), bound=bound)
    with pytest.raises(RuntimeError):
        async with ctx as conn:
            _ = await conn.execute(sa.text("insert into t values (1)"))
            raise RuntimeError
    assert await async_adapter.is_closed(conn)
    assert await _acount(async_adapter) == 0


@pytest.mark.parametrize("bound", [True, False])
async def test_async_nested_atomic_commits_once_at_outermost_exit(
    async_adapter: AsyncSaAdapter, bound: bool
):
    base = async_adapter.context()
    ctx = atomic(base, bound=bound)
    async with ctx as outer:
        async with ctx as inner:
            assert inner is outer
            _ = await inner.execute(sa.text("insert into t values (1)"))
        assert outer.in_transaction()
        assert not outer.closed
    assert outer.closed
    assert ctx.stack == 0
    assert base.stack == 0
    assert await _acount(async_adapter) == 1
