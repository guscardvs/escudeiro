import asyncio

import pytest

from escudeiro.misc.monad import (
    AsyncCell,
    AsyncMonadHelper,
    BaseMonad,
    Either,
    LazyMonad,
    Left,
    Monad,
    Nothing,
    NullMonad,
    Right,
    cast_to_lazy,
    if_,
    make_lazy,
    resolve_lazy,
)


class TestBaseMonad:
    def test_get_value_and_repr(self):
        m = BaseMonad.pure(10)
        assert m.get_value() == 10
        assert repr(m) == "BaseMonad(10)"

    def test_pure_creates_instance(self):
        m = BaseMonad.pure("abc")
        assert isinstance(m, BaseMonad)
        assert m.get_value() == "abc"


class TestMonad:
    def test_map(self):
        m = Monad.pure(2)
        m2 = m.map(lambda x: x + 3)
        assert isinstance(m2, Monad)
        assert m2.get_value() == 5

    def test_bind(self):
        m = Monad.pure(2)

        def f(x: int):
            return Monad.pure(x * 10)

        m2 = m.bind(f)
        assert isinstance(m2, Monad)
        assert m2.get_value() == 20

    def test_maybe_returns_monad(self):
        m = Monad.pure(2)
        m2 = m.maybe(lambda x: x * 2)
        assert isinstance(m2, Monad)
        assert m2.get_value() == 4

    def test_maybe_returns_nothing(self):
        m = Monad.pure(2)
        m2 = m.maybe(lambda x: None)
        assert m2 is Nothing


class TestNullMonad:
    def test_singleton(self):
        n1 = NullMonad()
        n2 = NullMonad()
        assert n1 is n2
        assert n1.value is None

    def test_get_value_raises(self):
        n = NullMonad()
        with pytest.raises(ValueError, match="NullMonad has no value"):
            n.get_value()

    def test_bind_and_map_return_self(self):
        n = NullMonad()
        assert n.bind(lambda x: Monad.pure(1)) is n
        assert n.map(lambda x: 2) is n


class TestEither:
    def test_left_and_right(self):
        left = Left("err")
        r = Right(123)
        assert isinstance(left, Left)
        assert isinstance(r, Right)
        assert left.value == "err"
        assert r.value == 123

    def test_left_bind_and_map(self):
        left = Left("fail")
        assert left.bind(lambda x: Right(x + 1)) is left
        assert left.map(lambda x: x + 1) is left

    def test_right_bind_and_map(self):
        r = Right(10)
        r2 = r.bind(lambda x: Right(x * 2))
        assert isinstance(r2, Right)
        assert r2.value == 20
        r3 = r.map(lambda x: x + 5)
        assert isinstance(r3, Right)
        assert r3.value == 15

    def test_right_get_value(self):
        r = Right("abc")
        assert r.get_value() == "abc"

    def test_either_base_not_implemented(self):
        e = Either("lvalue")
        with pytest.raises(NotImplementedError):
            _ = e.bind(lambda x: x)
        with pytest.raises(NotImplementedError):
            _ = e.map(lambda x: x)


class TestAsyncCell:
    def test_async_cell_resolve(self):
        async def coro():
            await asyncio.sleep(0)
            return 42

        loop = asyncio.new_event_loop()
        try:
            future = asyncio.ensure_future(coro(), loop=loop)
            cell = AsyncCell(future, lambda f: loop.run_until_complete(f))
            assert cell.resolve() == 42
        finally:
            loop.close()

class TestAsyncMonadHelper:
    def test_wrap_eager_and_lazy(self):
        async def coro(x: int):
            await asyncio.sleep(0)
            return x * 2

        loop = asyncio.new_event_loop()
        try:
            helper = AsyncMonadHelper(loop)
            eager = helper.wrap_eager(coro)
            lazy = helper.wrap_lazy(coro)
            m = eager(5)
            assert isinstance(m, Monad)
            assert m.get_value() == 10
            cell = lazy(6)
            assert isinstance(cell, AsyncCell)
            assert cell.resolve() == 12
        finally:
            loop.close()


class TestLazyMonad:
    def test_lazy_monad_map_and_bind(self):
        m = LazyMonad(2)
        m2 = m.map(lambda x: x + 3)
        assert isinstance(m2, LazyMonad)
        m3 = m2.bind(lambda x: Monad.pure(x * 2))
        assert isinstance(m3, LazyMonad)
        resolved = m3.resolve()
        assert isinstance(resolved, Monad)
        assert resolved.get_value() == 10

    def test_lazy_monad_resolve_without_binder(self):
        m = LazyMonad(7)
        result = m.resolve()
        assert isinstance(result, Monad)
        assert result.get_value() == 7

    def test_lazy_monad_badly_formed(self):
        parent = LazyMonad(1)
        m = LazyMonad(2, parent=parent, binder=None)
        with pytest.raises(TypeError, match="Badly formed LazyMonad"):
            _ = m.resolve()


class TestResolveLazy:
    def test_resolve_lazy(self):
        m = LazyMonad(3).map(lambda x: x + 1)
        result = resolve_lazy(m)
        assert isinstance(result, Monad)
        assert result.get_value() == 4


class TestCastToLazy:
    def test_cast_to_lazy(self):
        m = LazyMonad(1).map(lambda x: x + 1)
        lazy = cast_to_lazy(10, m)
        assert isinstance(lazy, LazyMonad)
        resolved = lazy.resolve()
        assert resolved.get_value() == 10


class TestMakeLazy:
    def test_make_lazy(self):
        def binder(x: int):
            return Monad.pure(x * 5)

        lazy_func = make_lazy(binder)
        m = lazy_func(2)
        assert isinstance(m, LazyMonad)
        result = m.resolve()
        assert result.get_value() == 10


class TestIf_:
    def test_if_true(self):
        def cond(x: int):
            return x > 0

        def ontrue(x: int):
            return x + 1

        onfalse = -1
        f = if_(cond, ontrue, onfalse)
        result = f(2)
        assert isinstance(result, Right)
        assert result.value == 3

    def test_if_false(self):
        def cond(x: int):
            return x < 0

        def ontrue(x: int):
            return x + 1

        onfalse = -1
        f = if_(cond, ontrue, onfalse)
        result = f(2)
        assert isinstance(result, Left)
        assert result.value == -1
