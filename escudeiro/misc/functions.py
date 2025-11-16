"""Utilities for safer type casting and function execution.

This module provides functions for safely performing type casting operations
and controlling function execution patterns.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import re
import typing
from collections.abc import (
    AsyncGenerator,
    AsyncIterable,
    Awaitable,
    Callable,
    Collection,
    Coroutine,
    Generator,
    Iterable,
)
from contextlib import (
    AbstractAsyncContextManager,
    AbstractContextManager,
    contextmanager,
)
from dataclasses import dataclass
from datetime import date, datetime, time, tzinfo
from time import sleep
from types import FunctionType, LambdaType, MethodType
from typing import (
    TYPE_CHECKING,
    Any,
    Concatenate,
    Literal,
    cast,
    final,
    overload,
)

from escudeiro.exc.errors import ErrorGroup, InvalidCast, RetryError
from escudeiro.misc.contextx import AsyncContextWrapper, is_async_context
from escudeiro.misc.strings import sentence, squote


def safe_cast[V, T, D](
    caster: Callable[[V], T],
    value: V,
    *ignore_childof: type[Exception],
    default: D = None,
) -> T | D:
    """Safely casts a value using the provided casting function.

    Attempts to cast the given value using the casting function. If the casting
    operation raises any of the specified exceptions, returns the default value.

    Args:
        caster: A function that converts the input value to the target type.
        value: The value to be cast.
        *ignore_childof: Exception types to catch. Defaults to (TypeError, ValueError)
                         if none are specified.
        default: The value to return if casting fails. Defaults to None.

    Returns:
        The result of the casting operation if successful, otherwise the default value.
    """
    if not ignore_childof:
        ignore_childof = (TypeError, ValueError)

    try:
        return caster(value)
    except ignore_childof:
        return default


async def asafe_cast[V, D, T](
    caster: Callable[[V], Awaitable[T]],
    value: V,
    *ignore_childof: type[Exception],
    default: D = None,
) -> T | D:
    """Safely casts a value using the provided asynchronous casting function.

    Asynchronous version of safe_cast. Attempts to cast the given value using the
    asynchronous casting function. If the casting operation raises any of the
    specified exceptions, returns the default value.

    Args:
        caster: An asynchronous function that converts the input value to the target type.
        value: The value to be cast.
        *ignore_childof: Exception types to catch. Defaults to (TypeError, ValueError)
                         if none are specified.
        default: The value to return if casting fails. Defaults to None.

    Returns:
        The result of the casting operation if successful, otherwise the default value.
    """
    if not ignore_childof:
        ignore_childof = (TypeError, ValueError)
    try:
        return await caster(value)
    except ignore_childof:
        return default


def call_once[T](func: Callable[[], T]) -> Callable[[], T]:
    """Returns a wrapper that ensures the wrapped function is called only once.

    Creates a wrapper around the provided function that caches the result of the
    first call. Subsequent calls return the cached result without executing
    the original function again.

    Args:
        func: The function to be wrapped. Must take no arguments.

    Returns:
        A wrapped version of the function that executes at most once.
    """
    sentinel: Any = object()
    output = sentinel

    @functools.wraps(func)
    def wrapper() -> T:
        nonlocal output
        if output is sentinel:
            output = func()
        return output

    return wrapper


type AsyncFunc[**P, T] = Callable[P, Coroutine[Any, Any, T]]
type AsAsyncFactory[**P, T] = Callable[
    Concatenate[Callable[P, T], P], Coroutine[Any, Any, T]
]

if TYPE_CHECKING:
    asyncio.to_thread = typing.cast(AsAsyncFactory, asyncio.to_thread)


@overload
def as_async[**P, T](
    func: None = None,
    /,
    *,
    cast: AsAsyncFactory[P, T] = asyncio.to_thread,
) -> Callable[[Callable[P, T]], AsyncFunc[P, T]]: ...


@overload
def as_async[**P, T](
    func: AsyncFunc[P, T],
    /,
) -> AsyncFunc[P, T]: ...


@overload
def as_async[**P, T](
    func: Callable[P, T],
    /,
) -> AsyncFunc[P, T]: ...


def as_async[**P, T](
    func: Callable[P, T] | AsyncFunc[P, T] | None = None,
    /,
    *,
    cast: AsAsyncFactory[P, T] = asyncio.to_thread,
) -> AsyncFunc[P, T] | Callable[[Callable[P, T]], AsyncFunc[P, T]]:
    """Convert a synchronous function to an asynchronous one.

    If the function is already asynchronous, returns it unchanged.
    Otherwise, wraps it using the specified casting method (defaults to asyncio.to_thread).

    Can be used as a decorator with or without arguments.

    Args:
        func: The function to convert to asynchronous. If None, returns a decorator.
        cast: A factory function that converts a synchronous function to asynchronous.
            Defaults to asyncio.to_thread, which runs the function in a separate thread.

    Returns:
        An asynchronous version of the input function, or a decorator that produces one.

    Examples:
        ```python
        # Basic usage as a decorator
        @as_async
        def read_file(path):
            with open(path) as f:
                return f.read()

        # With custom executor
        @as_async(cast=my_custom_executor)
        def process_data(data):
            return expensive_calculation(data)

        # Direct usage
        async_read = as_async(read_file)
        ```
    """

    def outer(func: Callable[P, T] | AsyncFunc[P, T]) -> AsyncFunc[P, T]:
        if inspect.iscoroutinefunction(func):
            return func
        elif TYPE_CHECKING:
            func = typing.cast(Callable[P, T], func)

        @functools.wraps(func)
        async def _inner(*args: P.args, **kwargs: P.kwargs) -> T:
            return await cast(func, *args, **kwargs)

        return _inner

    if func is None:
        return outer
    return outer(func)


def cache[**P, T](f: Callable[P, T]) -> Callable[P, T]:
    """Simple wrapper around functools.cache to preserve function signature.

    Provides memoization for the wrapped function, caching return values based on arguments.
    This is a thin wrapper over functools.cache that preserves proper type annotations.

    Args:
        f: The function to cache.

    Returns:
        A memoized version of the function with proper type annotations.

    Examples:
        ```python
        @cache
        def fibonacci(n):
            if n <= 1:
                return n
            return fibonacci(n-1) + fibonacci(n-2)
        ```
    """
    return typing.cast(Callable[P, T], functools.cache(f))


@overload
def make_noop[T](
    *, returns: T = None, asyncio: Literal[False] = False
) -> Callable[..., T]: ...


@overload
def make_noop[T](
    *, returns: T = None, asyncio: Literal[True]
) -> Callable[..., Coroutine[Any, Any, T]]: ...


def make_noop[T](
    *, returns: T = None, asyncio: bool = False
) -> Callable[..., T] | Callable[..., Coroutine[Any, Any, T]]:
    """Creates a no-operation function that accepts any arguments and returns a fixed value.

        Useful for creating placeholders, stubs, or disabling functionality temporarily.

        Args:
            returns: The value the function should return. Defaults to None.
            asyncio: Whether to create an async function. Defaults to False.

        Returns:
            A function that ignores all arguments and returns the specified value,
            either synchronously or asynchronously based on the asyncio parameter.

        Examples:
            ```python
            # Synchronous no-op
    @overload
    def make_noop[T](
        *, returns: T = None, asyncio: Literal[True]
    ) -> Callable[..., Coroutine[Any, Any, T]]: ...

            log_function = make_noop()

            # No-op with custom return value
            get_user = make_noop(returns={"id": 0, "name": "Guest"})

            # Async no-op
            async_operation = make_noop(asyncio=True, returns={"status": "success"})
            ```
    """

    def _noop(*args: Any, **kwargs: Any) -> T:
        del args, kwargs
        return returns

    return _noop if not asyncio else as_async(_noop)


def return_param[T](param: T) -> T:
    """Returns the provided parameter without modification.

    This function is a simple utility that returns the input parameter as-is.
    It can be useful in functional programming patterns where you need to pass
    a function that simply returns its input.

    Args:
        param: The parameter to return.

    Returns:
        The same parameter that was passed in.

    Example:
        ```python
        value = return_param(42)  # Returns 42
        ```
    """
    return param


def do_with[**P, T](
    context_manager: AbstractContextManager,
    func: Callable[P, T],
    *args: P.args,
    **kwargs: P.kwargs,
) -> T:
    """Executes a function within the context of a context manager.

    Allows for functional-style usage of context managers by automatically
    entering the context, executing the function, and exiting the context.

    Args:
        context_manager: The context manager to use.
        func: The function to execute within the context.
        *args: Positional arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        The result of calling the function with the specified arguments.

    Examples:
        ```python
        # Execute in a transaction
        result = do_with(
            db.transaction(),
            create_user,
            username="johndoe",
            email="john@example.com"
        )
        ```
    """
    with context_manager:
        return func(*args, **kwargs)


async def asyncdo_with[**P, T](
    context_manager: AbstractContextManager | AbstractAsyncContextManager,
    func: Callable[P, T] | AsyncFunc[P, T],
    *args: P.args,
    **kwargs: P.kwargs,
) -> T:
    """Executes a function within an async or sync context manager.

    Asynchronous version of do_with. Works with both synchronous and
    asynchronous context managers and functions.

    Args:
        context_manager: The context manager to use. Can be synchronous or asynchronous.
        func: The function to execute within the context. Can be synchronous or asynchronous.
        *args: Positional arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        The result of calling the function with the specified arguments.

    Examples:
        ```python
        # With async context manager and function
        result = await asyncdo_with(
            async_db.transaction(),
            async_create_user,
            username="johndoe"
        )

        # With sync context manager and async function
        result = await asyncdo_with(
            lock_manager(),
            async_process_data,
            data=payload
        )
        ```
    """
    if not is_async_context(context_manager):
        context_manager = AsyncContextWrapper(context_manager)

    async with context_manager:
        return await as_async(func)(*args, **kwargs)  # pyright: ignore[reportReturnType]


@final
class FrozenCoroutine[T]:
    """A coroutine wrapper that ensures the wrapped coroutine is executed at most once.

    When awaited multiple times, the coroutine is executed only on the first await.
    Subsequent awaits return the cached result without re-executing the coroutine.
    Thread-safe through the use of an asyncio.Lock.

    Attributes:
        _coro: The wrapped coroutine.
        _lock: Lock to ensure thread safety.
        _value: Cached result after first execution, or sentinel if not yet executed.

    Examples:
        ```python
        # Direct usage
        async def fetch_data():
            print("Fetching data...")
            return await api.get_data()

        frozen = FrozenCoroutine(fetch_data())

        # First await executes the coroutine
        result1 = await frozen  # Prints "Fetching data..."

        # Second await returns cached result
        result2 = await frozen  # No print, returns same result
        ```
    """

    _sentinel: Any = object()

    def __init__(self, coro: Coroutine[Any, Any, T]) -> None:
        """Initialize with a coroutine to be executed at most once.

        Args:
            coro: The coroutine to wrap.
        """
        self._coro = coro
        self._lock = asyncio.Lock()
        self._value = self._sentinel

    async def _await(self) -> T:
        """Internal method that handles the actual awaiting logic.

        Ensures the coroutine is executed at most once and returns
        the cached result for subsequent calls.

        Returns:
            The result of the coroutine execution.
        """
        async with self._lock:
            if self._value is not self._sentinel:
                return self._value
            self._value = await self._coro
            return self._value

    def __await__(self):
        return self._await().__await__()

    @classmethod
    def decorate[**P](
        cls, func: Callable[P, Coroutine[Any, Any, T]]
    ) -> Callable[P, FrozenCoroutine[T]]:
        """Decorator that wraps a coroutine-returning function to ensure
        each returned coroutine is executed at most once.

        Args:
            func: A function that returns a coroutine.

        Returns:
            A function that returns a FrozenCoroutine wrapping the original
            function's coroutine.

        Examples:
            ```python
            @FrozenCoroutine.decorate
            async def fetch_user(user_id):
                print(f"Fetching user {user_id}")
                return await api.get_user(user_id)

            # Creates a FrozenCoroutine
            user_coro = fetch_user(123)

            # First await executes
            user1 = await user_coro  # Prints "Fetching user 123"

            # Second await returns cached result
            user2 = await user_coro  # No print, returns same result
            ```
        """

        @functools.wraps(func)
        def _wrapper(*args: P.args, **kwargs: P.kwargs) -> FrozenCoroutine[T]:
            return FrozenCoroutine(func(*args, **kwargs))

        return _wrapper


def as_datetime(value: date, tz: tzinfo | None = None) -> datetime:
    return datetime(value.year, value.month, value.day, tzinfo=tz)


def join_into_datetime(
    dt: date, tm: time, tz: tzinfo | None = None
) -> datetime:
    return as_datetime(dt, tz).replace(
        hour=tm.hour,
        minute=tm.minute,
        second=tm.second,
        microsecond=tm.microsecond,
    )


async def as_async_iterable[T](iterable: Iterable[T]) -> AsyncIterable[T]:
    for item in iterable:
        yield item


@contextmanager
def raise_insteadof(
    insteadof: type[Exception], exc: type[Exception] = Exception, *args: Any
) -> Generator[None, None, None]:
    """Replaces an exception with another within a context.

    This context manager catches exceptions of type `insteadof` and raises a new
    exception of type `exc` instead, optionally passing arguments to the new exception.

    Args:
        insteadof: The exception type to catch.
        exc: The exception type to raise instead. Defaults to `Exception`.
        *args: Arguments to pass to the new exception.

    Raises:
        exc: If `insteadof` is raised, it is replaced with an instance of `exc`.

    Example:
        ```python
        try:
            with raise_insteadof(KeyError, ValueError, "Invalid key!"):
                raise KeyError("Missing key")
        except ValueError as e:
            print(e)  # Outputs: "Invalid key!"
        ```
    """
    try:
        yield
    except insteadof:
        raise exc(*args) from None


@dataclass
class Retry:
    """
    A utility class that provides retry logic for functions.
    This class allows you to retry a function multiple times in case of an exception. It supports both synchronous
    and asynchronous functions. You can configure the number of retries, the delay between retries, and an optional
    backoff multiplier for exponential delay growth.
    Attributes:
        signal: The exception type(s) that triggers the retry logic.
        count: The number of retries to attempt before giving up. Default is 3.
        delay: The initial delay (in seconds) between retries. Default is 0.
        backoff: The multiplier for the delay between retries (exponential backoff). Default is 1 (no backoff).
    Example:
        ```python
        retry = Retry(signal=ConnectionError, count=5, delay=1, backoff=2)
        @retry
        def unreliable_function():
            # Function implementation that might raise ConnectionError
            pass
        ```
    """

    signal: type[Exception] | tuple[type[Exception], ...]
    count: int = 3
    delay: float = 0  # seconds between retries
    backoff: float = 1  # multiplier for delay

    def get_signal(self) -> tuple[type[Exception], ...]:
        return (
            self.signal if isinstance(self.signal, tuple) else (self.signal,)
        )

    def __call__[**P, T](self, func: Callable[P, T]) -> Callable[P, T]:
        """
        Decorator that retries a function call on failure.
        This method wraps the provided function, retrying it on failure for a specified number of attempts. If the
        function raises the exception specified by `signal`, it will retry the function call up to the `count`
        number of times, with a delay between each retry and optional exponential backoff.
        Args:
            func: The function to be wrapped with retry logic.
        Returns:
            A wrapped function that will retry on failure.
        Example:
            ```python
            @retry
            def fetch_data():
                # Function that might raise a ConnectionError
                pass
            ```
        """

        @functools.wraps(func)
        def retrier(*args: P.args, **kwargs: P.kwargs) -> T:
            fails = []
            current_delay = self.delay
            signal = self.get_signal()
            for attempt in range(self.count):
                try:
                    return func(*args, **kwargs)
                except signal as e:
                    fails.append(e)
                    if attempt < self.count - 1 and current_delay > 0:
                        sleep(current_delay)
                        current_delay *= self.backoff
            raise ErrorGroup(
                "Failed retry operation",
                (RetryError(f"Exceeded max retries: {self.count}"), *fails),
            )

        return retrier

    def acall[**P, T](
        self, func: Callable[P, Coroutine[Any, Any, T]]
    ) -> Callable[P, Coroutine[Any, Any, T]]:
        """
        Asynchronous version of the retry decorator for functions that return coroutines.
        This method wraps the provided asynchronous function, retrying it on failure for a specified number of
        attempts. If the function raises the exception specified by `signal`, it will retry the function call
        up to the `count` number of times, with a delay between each retry and optional exponential backoff.
        Args:
            func: The asynchronous function to be wrapped with retry logic.
        Returns:
            A wrapped asynchronous function that will retry on failure.
        Example:
            ```python
            @retry.acall
            async def fetch_data():
                # Async function that might raise a ConnectionError
                pass
            ```
        """

        @functools.wraps(func)
        async def retrier(*args: P.args, **kwargs: P.kwargs) -> T:
            fails = []
            current_delay = self.delay
            signal = self.get_signal()
            for attempt in range(self.count):
                try:
                    return await func(*args, **kwargs)
                except signal as e:
                    fails.append(e)
                    if attempt < self.count - 1 and current_delay > 0:
                        await asyncio.sleep(current_delay)
                        current_delay *= self.backoff
            raise ErrorGroup(
                "Failed retry operation",
                (RetryError(f"Exceeded max retries: {self.count}"), *fails),
            )

        return retrier

    def map[S, T](
        self,
        predicate: Callable[[S], T],
        collection: Iterable[S],
        strategy: Literal["threshold", "temperature"] = "threshold",
    ) -> Iterable[T]:
        """
        Applies the retry logic to each item in a collection.
        This method attempts to apply the given predicate function to each item in the collection. If an exception
        occurs during the execution of the predicate, it will retry the operation up to the `count` number of times,
        with a delay between retries. You can control the retry strategy with the `strategy` parameter.
        Args:
            predicate: The function to apply to each item in the collection.
            collection: The collection of items to iterate over and apply the predicate to.
            strategy: The retry strategy to use. "threshold" retries a fixed number of times, while "temperature"
                      decreases the retry count with each successful operation. Default is "threshold".
        Returns:
            An iterable of the results of the predicate applied to each item in the collection.
        Example:
            ```python
            retry.map(fetch_data, [item1, item2])
            ```
        """
        count = 0
        predicate = self(predicate)
        signal = self.get_signal()
        for item in collection:
            try:
                yield predicate(item)
            except signal as err:
                if count >= self.count:
                    raise ErrorGroup(
                        "Failed retry operation",
                        (
                            RetryError(f"Exceeded max retries: {self.count}"),
                            err,
                        ),
                    ) from err
                count += 1
            else:
                if strategy == "temperature":
                    count = max(0, count - 1)

    async def amap[S, T](
        self,
        predicate: Callable[[S], Coroutine[Any, Any, T]],
        collection: Collection[S],
        strategy: Literal["threshold", "temperature"] = "threshold",
    ) -> AsyncIterable[T]:
        """
        Asynchronous version of `map` for a collection of items, using coroutines for the predicate.
        This method attempts to apply the given asynchronous predicate function to each item in the collection.
        If an exception occurs during the execution of the predicate, it will retry the operation up to the `count`
        number of times, with a delay between retries. The retry strategy can be controlled using the `strategy`
        parameter.
        Args:
            predicate: The asynchronous function to apply to each item in the collection.
            collection: The collection of items to iterate over and apply the predicate to.
            strategy: The retry strategy to use. "threshold" retries a fixed number of times, while "temperature"
                      decreases the retry count with each successful operation. Default is "threshold".
        Returns:
            An asynchronous iterable of the results of the predicate applied to each item in the collection.
        Example:
            ```python
            async for result in retry.amap(fetch_data, [item1, item2]):
                print(result)
            ```
        """
        count = 0
        signal = self.get_signal()
        predicate = self.acall(predicate)
        for item in collection:
            try:
                yield await predicate(item)
            except signal as err:
                if count >= self.count:
                    raise ErrorGroup(
                        "Failed retry operation",
                        (
                            RetryError(f"Exceeded max retries: {self.count}"),
                            err,
                        ),
                    ) from err
                count += 1
            else:
                if strategy == "temperature":
                    count = max(0, count - 1)

    async def agenmap[S, T](
        self,
        predicate: Callable[[S], Coroutine[Any, Any, T]],
        collection: AsyncGenerator[S],
        strategy: Literal["threshold", "temperature"] = "threshold",
    ) -> AsyncIterable[T]:
        """
        Asynchronously applies retry logic to each item generated by the given asynchronous generator.
        This method applies the given asynchronous predicate function to each item generated by the asynchronous
        generator. If an exception occurs during the execution of the predicate, it will retry the operation up to
        the `count` number of times, with a delay between retries. The retry strategy can be controlled using the
        `strategy` parameter.
        Args:
            predicate: The asynchronous function to apply to each item from the generator.
            collection: The asynchronous generator of items to iterate over and apply the predicate to.
            strategy: The retry strategy to use. "threshold" retries a fixed number of times, while "temperature"
                        decreases the retry count with each successful operation. Default is "threshold".
        Returns:
            An asynchronous iterable of the results of the predicate applied to each item from the generator.
        Example:
            ```python
            async for result in retry.agenmap(fetch_data, async_item_generator()):
                print(result)
            ```
        """
        count = 0
        signal = self.get_signal()
        predicate = self.acall(predicate)
        async for item in collection:
            try:
                yield await predicate(item)
            except signal as err:
                if count >= self.count:
                    raise ErrorGroup(
                        "Failed retry operation",
                        (
                            RetryError(f"Exceeded max retries: {self.count}"),
                            err,
                        ),
                    ) from err
                count += 1
            else:
                if strategy == "temperature":
                    count = max(0, count - 1)


UNSET = object()
_index_pattern = re.compile(r"\[([0-9]+)\]")


def walk_object(obj: Any, path: str) -> Any:
    """Safely retrieves a value from an object using a dot-separated path.
    This function allows you to access nested attributes, dictionary keys, or sequence indices
    in a safe manner, returning None if any part of the path is not found.
    Args:
        obj: The object to traverse.
    Returns:
        The value at the specified path, or None if the path does not exist.
    Example:
        ```python
        class User:
            def __init__(self, name, age):
                self.name = name
                self.age = age
        user = User("Alice", 30)
        age = walk_object(user, "age")  # Returns 30
        nested_dict = {"user": {"name": "Bob", "details": {"age": 25}}}
        name = walk_object(nested_dict, "user.name")  # Returns "Bob"
        invalid = walk_object(nested_dict, "user.details.address")  # Returns None
        nested_list = [1, 2, [3, 4, 5]]
        value = walk_object(nested_list, "[2].[1]")  # Returns 4
        ```
    """
    parts = path.split(".")
    value = obj
    for part in parts:
        if v := _index_pattern.match(part):
            idx = int(v.group(1))
            if TYPE_CHECKING:
                assert isinstance(value, list | tuple), (
                    "Expected a list or tuple"
                )
            value = value[idx] if len(value) > idx else UNSET
        elif isinstance(value, dict):
            value = value.get(part, UNSET)
        else:
            value = getattr(value, part, UNSET)
        if value in (None, UNSET):
            break
    return value if value is not UNSET else None


def isinstance_or_cast[T, Arg, U](
    expects: type[T], onmiss: Callable[[Arg], U]
) -> Callable[[Arg | T], T | U]:
    """
    Returns a decorator that checks if the value is an instance of the given type.
    If it is, it returns the value, otherwise it calls the given callable.
    """

    @functools.wraps(onmiss)
    def _check(value: Any) -> T | U:
        if isinstance(value, expects):
            return value
        return onmiss(value)

    return _check


class Caster[U, T]:
    __slots__ = (
        "_caster",
        "_name",
        "_safe_casted",
    )

    def __init__(
        self,
        caster: Callable[[U], T],
        name: str | None = None,
        safe_casted: bool = False,
    ) -> None:
        self._caster = caster
        self._name = cast(
            str, name or getattr(caster, "__name__", type(self).__name__)
        )
        self._safe_casted = safe_casted

    def __call__(self, value: U) -> T:
        """Casts the value using the provided caster function."""
        return self._caster(value)

    def __name__(self) -> str:
        return self._name

    def join[S](self, caster: Callable[[T], S]) -> Caster[U, S]:
        if self._safe_casted:
            raise ValueError("Cannot join with a safe-casted Caster")

        def _join(value: U) -> S:
            return caster(self._caster(value))

        return Caster(
            _join,
            name=f"{self._name}.join({getattr(caster, '__name__', type(caster).__name__)})",
        )

    cast = join  # Alias for join method for compatibility with _JoinedCast

    def strict(self, value: U) -> T:
        """Casts the value and raises an error if the result is None."""
        result = self._caster(value)
        if result is None:
            raise InvalidCast(
                sentence(
                    f"Received falsy value {result} from {value} during cast"
                ),
                result,
            )
        return result

    def safe[S](
        self,
        value: U,
        *childof: type[Exception],
        default: T | S = None,
    ) -> T | S:
        """Casts the value and returns None if the result is None, otherwise returns the result."""
        return safe_cast(
            self,
            value,
            *childof,
            default=default,
        )

    optional = (
        safe  # Alias for safe method for compatibility with maybe_result
    )

    def safe_cast(
        self,
        child_of: Collection[type[Exception]] = (),
        extend_child_of: bool = True,
    ):
        if extend_child_of:
            child_of = [TypeError, ValueError, *child_of]

        def _safe_cast(value: U) -> T | None:
            return safe_cast(self._caster, value, *child_of, default=None)

        return Caster(
            _safe_cast,
            name=f"{self._name}.safe_cast",
            safe_casted=True,
        )

    def or_[S](
        self, caster: Callable[[U], S], *childof: type[Exception]
    ) -> Caster[U, T | S]:
        """Returns a new caster that tries the original caster first, then the provided caster if the first fails."""

        if self._safe_casted:
            raise ValueError("Cannot join with a safe-casted Caster")

        if not childof:
            childof = (TypeError, ValueError)

        def _or(value: U) -> T | S:
            try:
                return self._caster(value)
            except childof:
                return caster(value)

        return Caster(
            _or,
            name=f"{self._name}.or_({getattr(caster, '__name__', type(caster).__name__)})",
        )

    @staticmethod
    def isinstance_or_cast[Arg](
        expects: type[T], onmiss: Callable[[Arg], U]
    ) -> Caster[Arg | T, T | U]:
        wrapped = isinstance_or_cast(expects, onmiss)
        return Caster(wrapped)

    def with_rule(
        self, rule: Callable[[T], bool], rulename: str | None = None
    ) -> Caster[U, T]:
        """Returns a new caster that applies the given rule to the result."""
        if self._safe_casted:
            raise ValueError("Cannot apply rule to a safe-casted Caster")

        if rulename is None:
            if isinstance(rule, LambdaType) and rule.__name__ == "<lambda>":
                raise ValueError(
                    "Rule name must be provided for lambda functions"
                )

            rulename = rule.__name__

        def _with_rule(value: U) -> T:
            result = self._caster(value)
            if not rule(result):
                raise InvalidCast(
                    sentence(
                        f"result {result} does not satisfy the rule {squote(rulename)}"
                    ),
                    result,
                )
            return result

        return Caster(_with_rule, name=f"{self._name}.with_rule({rulename})")


def _extract_return_type(
    wrapper: Callable[[Any], Any],
    return_type: type[Any] | None,
) -> type[Any] | None:
    if return_type is not None:
        return return_type
    elif isinstance(wrapper, MethodType):
        return getattr(wrapper.__func__, "__annotations__", {}).get(
            "return", None
        )
    elif isinstance(wrapper, FunctionType):
        return getattr(wrapper, "__annotations__", {}).get("return", None)
    elif callable(wrapper) and not isinstance(wrapper, type):
        annotated = wrapper.__call__
        return getattr(annotated, "__annotations__", {}).get("return", None)
    elif isinstance(wrapper, type):  # pyright: ignore[reportUnnecessaryIsInstance]
        return wrapper
    else:
        return Any  # pyright: ignore[reportUnreachable]


def wrap_result_with[**P, T, U](
    wrapper: Callable[[T], U],
    return_type: type[U] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, U]]:
    """
    Decorator factory that wraps the result of a function with a specified wrapper.
    This decorator modifies the return value of the decorated function by passing it
    through the provided `wrapper` callable. Optionally, it can update the function's
    return type annotation.
    Args:
        wrapper (Callable[[T], U]): A callable that takes the original return value
            and returns the wrapped value.
        return_type (type[U] | None, optional): The type to set as the return annotation
            for the decorated function. If None, attempts to infer from the wrapper.
    Returns:
        Callable[[Callable[P, T]], Callable[P, U]]: A decorator that wraps the result
        of the target function with `wrapper`.
    Example:
        >>> @wrap_result_with(str)
        ... def get_number() -> int:
        ...     return 42
        >>> get_number()
        '42'
    """

    def _wrap(func: Callable[P, T]) -> Callable[P, U]:
        func.__annotations__["return"] = _extract_return_type(
            wrapper, return_type
        )

        @functools.wraps(func)
        def __wrap(*args: P.args, **kwargs: P.kwargs) -> U:
            result = func(*args, **kwargs)
            return wrapper(result)

        __wrap.__annotations__ = func.__annotations__

        return __wrap

    return _wrap


def awrap_result_with[**P, T, U](
    wrapper: Callable[[T], Coroutine[Any, Any, U]],
    return_type: type[U] | None = None,
) -> Callable[
    [Callable[P, Coroutine[Any, Any, T]]], Callable[P, Coroutine[Any, Any, U]]
]:
    """
    Decorator factory that wraps the result of an asynchronous function with a specified wrapper.
    This decorator modifies the return value of the decorated asynchronous function by passing it
    through the provided `wrapper` callable, which must return an awaitable. Optionally, it can update the function's
    return type annotation.
    Args:
        wrapper (Callable[[T], Awaitable[U]]): A callable that takes the original return value
            and returns an awaitable that resolves to the wrapped value.
        return_type (type[U] | None, optional): The type to set as the return annotation
            for the decorated function. If None, attempts to infer from the wrapper.
    Returns:
        Callable[[Callable[P, T]], Callable[P, Coroutine[Any, Any, U]]]:
            A decorator that wraps the result of the target asynchronous function with `wrapper`.
    Example:
        >>> @awrap_result_with(lambda x: asyncio.sleep(0.1, result=str(x)))
        ... async def get_number() -> int:
        ...     return 42
        >>> await get_number()
        '42'
    """

    def _wrap(
        func: Callable[P, Coroutine[Any, Any, T]],
    ) -> Callable[P, Coroutine[Any, Any, U]]:
        func.__annotations__["return"] = _extract_return_type(
            wrapper, return_type
        )

        @functools.wraps(func)
        async def __wrap(*args: P.args, **kwargs: P.kwargs) -> U:
            result = await func(*args, **kwargs)
            return await wrapper(result)

        __wrap.__annotations__ = func.__annotations__

        return __wrap

    return _wrap
