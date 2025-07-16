from __future__ import annotations

import asyncio
from abc import ABC
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any, Never, cast, override

from escudeiro.misc.functions import make_noop


class BaseMonad[T](ABC):
    """Base class for monads, providing a common interface."""

    def __init__(self, value: T):
        self.value: T = value

    def get_value(self) -> T:
        """Returns the value contained in the monad."""
        return self.value

    @classmethod
    def pure(cls, value: T):
        """Creates a new monad instance containing the given value."""
        return cls(value)

    @override
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value!r})"


class Monad[T](BaseMonad[T]):
    """A simple monad implementation that wraps a value."""

    def bind[U: BaseMonad](self, func: Callable[[T], U]) -> U:
        """
        Applies a function to the value contained in the monad and returns a new monad with the result.

        Args:
            func (Callable[[T], Monad[U]]): A function that takes a value of type T and returns a Monad of type U.

        Returns:
            Monad[U]: A new monad containing the result of the function application.
        """
        return func(self.value)

    def map[U](self, func: Callable[[T], U]) -> Monad[U]:
        """
        Applies a function to the value contained in the monad and returns a new monad with the result.

        Args:
            func (Callable[[T], U]): A function that takes a value of type T and returns a value of type U.

        Returns:
            Monad[U]: A new monad containing the result of the function application.
        """
        return Monad.pure(func(self.value))

    def maybe[U](self, func: Callable[[T], U | None]) -> Monad[U] | NullMonad:
        """
        Applies a function to the value contained in the monad if it is not None.

        Args:
            func (Callable[[T], Any]): A function that takes a value of type T.

        Returns:
            Monad[T] | NullMonad: A new monad with the original value if the function returns a non-None value,
            or NullMonad if the function returns None.
        """
        result = func(self.value)
        if result is None:
            return Nothing
        return Monad.pure(result)


class NullMonad(BaseMonad[None]):
    _instance: NullMonad | None = None

    def __new__(cls) -> NullMonad:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.value = None
        return cls._instance

    def __init__(self):
        if getattr(self, "is_initialized", False):
            # Prevent re-initialization
            return
        super().__init__(None)
        self.is_initialized = True

    @override
    def get_value(self) -> Never:
        """Raises an exception when trying to get the value of a NullMonad."""
        raise ValueError("NullMonad has no value")

    def bind(self, func: Callable[[Any], BaseMonad[Any]]) -> NullMonad:
        """
        Returns a NullMonad since it cannot bind to a function.

        Args:
            func (Callable[[None], T]): A function that takes None and returns a value of type T.

        Returns:
            NullMonad: A NullMonad instance.
        """
        del func  # Unused parameter
        return self

    def map(self, func: Callable[[Any], Any]) -> NullMonad:
        """
        Returns a NullMonad since it cannot map to a function.

        Args:
            func (Callable[[None], T]): A function that takes None and returns a value of type T.

        Returns:
            NullMonad: A NullMonad instance.
        """
        del func  # Unused parameter
        return self


class Either[L, R](BaseMonad[L | R]):
    """
    Base class for the Either monad.
    Represents a computation that can result in one of two outcomes:
    a Left value (typically an error) or a Right value (typically a success).
    """

    def bind[U](self, func: Callable[[R], Either[L, U]]) -> Either[L, U]:
        """
        Applies a function to the Right value if present and returns a new Either monad.
        If the current Either is Left, the function is not applied.
        """
        del func
        raise NotImplementedError("Subclasses must implement bind")

    def map[U](self, func: Callable[[R], U]) -> Either[L, U]:
        """
        Applies a function to the Right value if present and wraps the result in a Right.
        If the current Either is Left, the function is not applied.
        """
        del func
        raise NotImplementedError("Subclasses must implement map")


class Left[L, R](Either[L, R]):
    """
    Represents a Left value in the Either monad.
    Typically used to represent an error or failure.
    """

    value: L

    @override
    def bind(self, func: Callable[[R], Either[L, Any]]) -> Left[L, Any]:
        return self

    @override
    def map(self, func: Callable[[R], Any]) -> Left[L, Any]:
        return self


class Right[L, R](Either[L, R]):
    """
    Represents a Right value in the Either monad.
    Typically used to represent a successful computation.
    """

    value: R

    def __init__(self, value: R):
        super().__init__(value)

    @override
    def bind(self, func: Callable[[R], Either[L, Any]]) -> Either[L, Any]:
        return func(self.value)

    @override
    def map(self, func: Callable[[R], Any]) -> Either[L, Any]:
        return Right(func(self.value))

    @override
    def get_value(self) -> R:
        return self.value


Nothing = NullMonad()


class AsyncCell[T]:
    """A simple asynchronous cell that can hold a value and be awaited."""

    def __init__(
        self,
        awaitable: Coroutine[Any, Any, T],
        runner: Callable[[Coroutine[Any, Any, T]], T],
    ):
        self._value = awaitable
        self._runner = runner

    def resolve(self) -> T:
        """Runs the awaitable and returns its value."""
        return self._runner(self._value)


class AsyncMonadHelper:
    def __init__(self, loop: asyncio.AbstractEventLoop | None):
        self.loop = loop or asyncio.new_event_loop()
        self.runner = asyncio.Runner(loop_factory=self._get_loop)

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """Returns the current event loop."""
        return self.loop

    def wrap_eager[T, U](
        self, corofunc: Callable[[U], Coroutine[Any, Any, T]]
    ) -> Callable[[U], Monad[T]]:
        """
        Wraps a coroutine function to run it eagerly in the current event loop.

        Args:
            corofunc (Callable[[U], Coroutine[Any, Any, T]]): A coroutine function that takes a value of type U and returns a value of type T.

        Returns:
            Callable[[U], Monad[T]]: A function that runs the coroutine and returns a Monad with the result.
        """

        def wrapper(value: U) -> Monad[T]:
            return Monad.pure(self.runner.run(corofunc(value)))

        return wrapper

    def wrap_lazy[T, U](
        self, corofunc: Callable[[U], Coroutine[Any, Any, T]]
    ) -> Callable[[U], AsyncCell[T]]:
        """
        Wraps a coroutine function to run it lazily in the current event loop.

        Args:
            corofunc (Callable[[U], Coroutine[Any, Any, T]]): A coroutine function that takes a value of type U and returns a value of type T.

        Returns:
            Callable[[U], AsyncCell[T]]: A function that creates an AsyncCell with the coroutine.
        """

        def wrapper(value: U) -> AsyncCell[T]:
            return AsyncCell(
                corofunc(value),
                cast(Callable[[Awaitable[T]], T], self.runner.run),
            )

        return wrapper


class LazyMonad[T, U](BaseMonad[T]):
    """
    A monad that won't run any computation until resolve is called.
    This is useful for deferring computations until they are needed.
    """

    def __init__(
        self,
        value: T,
        parent: LazyMonad[T, U] | None = None,
        binder: Callable[[T], Monad[U]] | None = None,
    ):
        super().__init__(value)
        self._parent = parent
        self._binder = binder

    def bind(self, func: Callable[[T], Monad[U]]) -> LazyMonad[T, U]:
        """
        Binds a function to the value contained in the monad, returning a new LazyMonad.

        Args:
            func (Callable[[T], Monad[U]]): A function that takes a value of type T and returns a Monad of type U.

        Returns:
            LazyMonad[U]: A new LazyMonad containing the result of the function application.
        """
        return LazyMonad(self.value, self, func)

    def map(self, func: Callable[[T], U]) -> LazyMonad[T, U]:
        """
        Applies a function to the value contained in the monad and returns a new LazyMonad with the result.

        Args:
            func (Callable[[T], U]): A function that takes a value of type T and returns a value of type U.

        Returns:
            LazyMonad[U, None]: A new LazyMonad containing the result of the function application.
        """

        def _binder(value: T) -> Monad[U]:
            return Monad.pure(func(value))

        return LazyMonad(self.value, self, _binder)

    def resolve(self, parent_value: Any | None = None) -> Monad[U]:
        """
        Resolves the LazyMonad by applying the binder function to the value.
        If there is a parent, it resolves the parent first.

        Returns:
            Monad[U]: A Monad containing the result of the binder function applied to the value.
        """
        if not self._binder:
            if self._parent:
                raise TypeError(
                    "Badly formed LazyMonad, no binder set, but parent is set."
                )
            return Monad.pure(self.value)
        if self._parent:
            if parent_value is None:
                parent_value = self._parent.resolve().get_value()
            return self._binder(parent_value)
        return self._binder(self.value)


def resolve_lazy[T, U](monad: LazyMonad[T, U]) -> Monad[U]:
    """
    Resolves a LazyMonad by calling its resolve method.

    Args:
        monad (LazyMonad[T, U]): The LazyMonad to resolve.

    Returns:
        Monad[U]: A Monad containing the result of the LazyMonad's resolve method.
    """
    return monad.resolve()


def cast_to_lazy[S, T](
    value: S, lazy_monad: LazyMonad[S, T]
) -> LazyMonad[S, T]:
    """
    Casts a value to a LazyMonad.

    Args:
        value (S): The value to cast.
        lazy_monad (LazyMonad[S, Any]): The LazyMonad to cast the value to.

    Returns:
        LazyMonad[S, Any]: A LazyMonad containing the value.
    """
    return LazyMonad(value, lazy_monad, make_noop(returns=Monad.pure(value)))


def make_lazy[T, U](
    binder: Callable[[T], Monad[U]],
) -> Callable[[T], LazyMonad[T, U]]:
    """
    Creates a LazyMonad from a binder function.

    Args:
        binder (Callable[[T], Monad[U]]): A function that takes a value of type T and returns a Monad of type U.

    Returns:
        Callable[[T], LazyMonad[T, U]]: A function that creates a LazyMonad with the given binder.
    """

    def _wrapper(value: T) -> LazyMonad[T, U]:
        return LazyMonad(value).bind(binder)

    return _wrapper


def if_[T, OnTrue, OnFalse](
    cond: Callable[[T], bool],
    ontrue: Callable[[T], OnTrue],
    onfalse: OnFalse,
) -> Callable[[T], Either[OnFalse, OnTrue]]:
    """
    Conditional monad that returns one of two values based on the boolean value of the monad.

    Args:
        monad (BaseMonad[bool]): A monad containing a boolean value.
        ontrue (Callable[[T], OnTrue]): A function to call if the condition is True.
        onfalse (OnFalse): A value to return if the condition is False.

    Returns:
        Callable[[T], Either[OnFalse, OnTrue]]: A function that takes a value of type T and returns an Either monad.
    """

    def _wrapper(value: T) -> Either[OnFalse, OnTrue]:
        if cond(value):
            return Right(ontrue(value))
        return Left(onfalse)

    return _wrapper
