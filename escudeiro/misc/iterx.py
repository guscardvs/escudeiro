"""Utilities for working with iterables and sequences.

This module provides functions for common iteration patterns, sequence transformations,
and advanced iterator operations with strong type safety.
"""

from __future__ import annotations

import itertools
from collections import defaultdict
from collections.abc import (
    AsyncIterable,
    Callable,
    Collection,
    Coroutine,
    Hashable,
    Iterable,
    Iterator,
    Mapping,
    Sequence,
)
from typing import TYPE_CHECKING, Any, cast, overload

from escudeiro.misc.functions import as_async, safe_cast


def moving_window[T](
    iterable: Iterable[T],
    window_size: int,
    cast: Callable[[Iterator[T]], Sequence[T]] = tuple,
) -> Iterable[Sequence[T]]:
    """Returns an iterator yielding non-overlapping windows from an iterable.

    Creates a sliding window of fixed size that moves through the iterable
    one element at a time.

    Args:
        iterable: The input iterable to create windows from.
        window_size: The size of each window.
        cast: A function to convert each window iterator to a sequence type.
             Defaults to tuple.

    Returns:
        An iterable of windows, where each window is a sequence of length
        window_size or smaller (for the final window if iterable length is
        not a multiple of window_size).

    Examples:
        ```python
        # Get sliding windows of size 3 from a list
        list(moving_window([1, 2, 3, 4, 5], 3))
        # Output: [(1, 2, 3), (4, 5)]

        # Use different output sequence type
        list(moving_window([1, 2, 3, 4, 5], 2, list))
        # Output: [[1, 2], [3, 4], [5]]
        ```
    """
    iterator = iter(iterable)

    while True:
        window = cast(itertools.islice(iterator, window_size))
        if not window:
            break
        yield window


@overload
def aislice[T](
    iterable: AsyncIterable[T],
    stop: int | None = ...,
    /,
) -> AsyncIterable[T]: ...


@overload
def aislice[T](
    iterable: AsyncIterable[T],
    start: int | None,
    stop: int | None,
    step: int | None = ...,
    /,
) -> AsyncIterable[T]: ...


async def aislice[T](
    iterable: AsyncIterable[T], *args: int | None
) -> AsyncIterable[T]:
    """Async slice iterator.

    Examples:
        >>> async for item in aislice(stream, 5):  # First 5 items
        ...     process(item)
        >>> async for item in aislice(stream, 2, 10, 2):  # Items 2,4,6,8
        ...     process(item)
    """
    s = slice(*args)
    start, stop, step = s.start or 0, s.stop, s.step or 1

    if not all(isinstance(x, int) for x in (start, step) if x is not None):
        raise TypeError("Slice indices must be integers")
    if any(x < 0 for x in (start, stop, step) if x is not None):
        raise ValueError("Negative indices not supported")
    if s.step == 0:
        raise ValueError("Step cannot be zero")
    if stop is not None and start >= stop:
        return  # Early exit for empty slices
    it = aiter(iterable)

    # Skip initial elements
    for _ in range(start):
        try:
            _ = await anext(it)
        except StopAsyncIteration:
            return

    # Yield remaining elements
    while stop is None or start < stop:
        try:
            yield await anext(it)
            start += step
            # Skip step-1 elements
            for _ in range(step - 1):
                _ = await anext(it)
        except StopAsyncIteration:
            break


async def amoving_window[T](
    iterable: AsyncIterable[T],
    window_size: int,
) -> AsyncIterable[Sequence[T]]:
    """Returns an iterator yielding non-overlapping windows from an iterable.

    Creates a sliding window of fixed size that moves through the iterable
    one element at a time.

    Args:
        iterable: The input iterable to create windows from.
        window_size: The size of each window.

    Returns:
        An iterable of windows, where each window is a sequence of length
        window_size or smaller (for the final window if iterable length is
        not a multiple of window_size).
    """
    iterator = aiter(iterable)

    while True:
        window = [item async for item in aislice(iterator, window_size)]
        if not window:
            break
        yield window


async def amap[V, T](
    predicate: Callable[[V], T] | Callable[[V], Coroutine[Any, Any, T]],
    iterable: AsyncIterable[V],
) -> AsyncIterable[T]:
    predicate = cast(Callable[[V], Coroutine[Any, Any, T]], as_async(predicate))
    async for item in iterable:
        yield await predicate(item)


async def afilter[V](
    predicate: Callable[[V], bool] | Callable[[V], Coroutine[Any, Any, bool]],
    iterable: AsyncIterable[V],
) -> AsyncIterable[V]:
    predicate = cast(
        Callable[[V], Coroutine[Any, Any, bool]], as_async(predicate)
    )
    async for item in iterable:
        if await predicate(item):
            yield item


_reduce_sentinel = object()


@overload
async def areduce[T](
    predicate: Callable[[T, T], T] | Callable[[T, T], Coroutine[Any, Any, T]],
    iterable: AsyncIterable[T],
    initial: object = _reduce_sentinel,
) -> T: ...


@overload
async def areduce[T](
    predicate: Callable[[T, T], T] | Callable[[T, T], Coroutine[Any, Any, T]],
    iterable: AsyncIterable[T],
    initial: T,
) -> T: ...


@overload
async def areduce[V, T](
    predicate: Callable[[V, T], T] | Callable[[V, T], Coroutine[Any, Any, T]],
    iterable: AsyncIterable[T],
    initial: V,
) -> T: ...


async def areduce[V, T](
    predicate: Callable[[T, V], T]
    | Callable[[T, V], Coroutine[Any, Any, T]]
    | Callable[[V, V], V]
    | Callable[[V, V], Coroutine[Any, Any, V]],
    iterable: AsyncIterable[V],
    initial: T | V | object = _reduce_sentinel,
) -> T | V:
    iterable = aiter(iterable)
    predicate = cast(
        Callable[[T | V, V], Coroutine[Any, Any, T]], as_async(predicate)
    )

    if initial is _reduce_sentinel:
        try:
            value = await anext(iterable)
        except StopAsyncIteration:
            raise TypeError(
                "reduce() of empty iterable with no initial value"
            ) from None
    else:
        value = cast(T | V, initial)
    async for item in iterable:
        value = await predicate(value, item)
    return value


async def aenumerate[T](
    iterable: AsyncIterable[T], start: int = 0
) -> AsyncIterable[tuple[int, T]]:
    """Return an async iterator that yields tuples of (index, value)."""
    index = start
    async for item in iterable:
        yield index, item
        index += 1


async def aany[T](
    iterable: AsyncIterable[T],
    predicate: Callable[[T], bool]
    | Callable[[T], Coroutine[Any, Any, bool]] = bool,
) -> bool:
    """Return True if any item in the async iterable satisfies the predicate."""
    return (await anext_or(afilter(predicate, iterable))) is not None


async def aall[T](
    iterable: AsyncIterable[T],
    predicate: Callable[[T], bool]
    | Callable[[T], Coroutine[Any, Any, bool]] = bool,
) -> bool:
    """Return True if all items in the async iterable satisfy the predicate."""

    async def _not_predicate(x: T) -> bool:
        return not await as_async(predicate)(x)

    return not await aany(iterable, _not_predicate)


async def acarrymap[U, T](
    predicate: Callable[[T], Coroutine[Any, Any, U]], iterable: AsyncIterable[T]
) -> AsyncIterable[tuple[U, T]]:
    """Return an async iterator that yields tuples of (result, arg)
    where the result is the result of applying the predicate to the arg."""
    async for arg in iterable:
        yield await predicate(arg), arg


async def astarmap[*Ts, U](
    predicate: Callable[[*Ts], Coroutine[Any, Any, U]],
    iterable: AsyncIterable[tuple[*Ts]],
) -> AsyncIterable[U]:
    """Return an async iterator that yields the result
    where the result is the result of applying the predicate to the args."""
    async for args in iterable:
        yield await predicate(*args)


async def acarrystarmap[*Ts, U](
    predicate: Callable[[*Ts], Coroutine[Any, Any, U]],
    iterable: AsyncIterable[tuple[*Ts]],
) -> AsyncIterable[tuple[U, tuple[*Ts]]]:
    """Return an async iterator that yields tuples of (result, args)
    where the result is the result of applying the predicate to the args."""
    async for args in iterable:
        yield await predicate(*args), args


def flatten(sequence: Sequence[Any]) -> Sequence[Any]:
    """Flattens nested sequences into a single-level sequence.

    Recursively flattens nested sequences (lists, tuples, etc.) while
    preserving the outer sequence type. Strings and bytes objects are
    treated as atomic units and not flattened.

    Args:
        sequence: The nested sequence to flatten.

    Returns:
        A flattened sequence of the same type as the input sequence.
        If the original type cannot be preserved, returns a list.

    Examples:
        ```python
        flatten([1, [2, 3], [4, [5, 6]]])
        # Output: [1, 2, 3, 4, 5, 6]

        flatten((1, [2, 3], (4, 5)))
        # Output: (1, 2, 3, 4, 5)
        ```
    """
    flattened: list[Any] = []
    stack: list[tuple[Sequence[Any], int]] = [(sequence, 0)]

    while stack:
        curseq, index = stack.pop()
        while index < len(curseq):
            item = curseq[index]
            index += 1
            if isinstance(item, Sequence) and not isinstance(item, str | bytes):
                stack.append((curseq, index))
                curseq, index = item, 0
            else:
                flattened.append(item)

    return safe_cast(type(sequence), flattened, Exception, default=flattened)


SequenceTypes = list | dict | set | tuple


def exclude_none[SequenceT: SequenceTypes](sequence: SequenceT) -> SequenceT:
    """Recursively filters out `None` values from sequences and their nested elements.

    Args:
        sequence: The sequence to filter. Must be a dict, list, set, or tuple.

    Returns:
        Filtered sequence with `None` values removed, preserving the original
        sequence type.

    Notes:
        - Tuple typing will not be preserved due to Python's immutability of tuples.
        - For dictionaries, only values are checked for None; keys are always preserved.

    Examples:
        ```python
        # Remove None from list
        exclude_none([1, None, 2, [3, None, 4]])
        # Output: [1, 2, [3, 4]]

        # Remove None from dictionary
        exclude_none({"a": 1, "b": None, "c": {"d": None, "e": 2}})
        # Output: {"a": 1, "c": {"e": 2}}
        ```
    """
    outer_acc: SequenceT = (
        type(sequence)() if not isinstance(sequence, tuple) else []
    )
    stack: list[tuple[SequenceT, SequenceT]] = [(sequence, outer_acc)]

    while stack:
        curr, acc = stack.pop()

        if isinstance(curr, dict):
            if TYPE_CHECKING:
                acc = cast(dict, acc)
            for key, value in curr.items():
                if value is None:
                    continue
                if isinstance(value, SequenceTypes):
                    new_acc = (
                        type(value)() if not isinstance(value, tuple) else []
                    )
                    acc[key] = new_acc
                    stack.append((value, new_acc))  # pyright: ignore[reportArgumentType]
                else:
                    acc[key] = value
        else:
            temp_acc = []
            for item in curr:
                if item is None:
                    continue
                if isinstance(item, SequenceTypes):
                    new_acc = (
                        type(item)() if not isinstance(item, tuple) else []
                    )
                    temp_acc.append(new_acc)
                    stack.append((item, new_acc))  # pyright: ignore[reportArgumentType]
                else:
                    temp_acc.append(item)
            if isinstance(curr, list | tuple):
                _ = acc.extend(temp_acc)  # pyright: ignore[reportAttributeAccessIssue]
            else:
                _ = acc.update(temp_acc)  # pyright: ignore[reportAttributeAccessIssue]

    return outer_acc


def next_or[T, D](iterable: Iterable[T], default: D = None) -> T | D:
    """Returns the first element from an iterable or a default value if empty.

    A convenience wrapper around the built-in `next` function with a default value.

    Args:
        iterable: The iterable to get the first element from.
        default: The value to return if the iterable is empty. Defaults to None.

    Returns:
        The first element of the iterable or the default value if the iterable is empty.

    Examples:
        ```python
        next_or([1, 2, 3])  # Returns 1
        next_or([], "empty")  # Returns "empty"
        ```
    """
    return next(iter(iterable), default)


async def anext_or[T, D](
    iterable: AsyncIterable[T], default: D = None
) -> T | D:
    """Returns the first element from an iterable or a default value if empty.

    A convenience wrapper around the built-in `anext` function with a default value.

    Args:
        iterable: The iterable to get the first element from.
        default: The value to return if the iterable is empty. Defaults to None.

    Returns:
        The first element of the iterable or the default value if the iterable is empty.

    Examples:
        ```python
        await anext_or([1, 2, 3])  # Returns 1
        await anext_or([], "empty")  # Returns "empty"
        ```
    """
    return await anext(aiter(iterable), default)


def carrymap[T, U](
    predicate: Callable[[T], U], iterable: Iterable[T]
) -> Iterable[tuple[U, T]]:
    """Maps elements with a function while preserving the original values.

    Applies a function to each element in an iterable and yields tuples of
    (result, original), where result is the transformed value and original
    is the original input element.

    Args:
        predicate: A function to apply to each element in the iterable.
        iterable: The input iterable.

    Returns:
        An iterator yielding tuples of (transformed_value, original_value).

    Examples:
        ```python
        # Transform elements while keeping originals
        list(carrymap(str.upper, ["a", "b", "c"]))
        # Output: [("A", "a"), ("B", "b"), ("C", "c")]

        # Calculate lengths while preserving strings
        list(carrymap(len, ["apple", "banana", "cherry"]))
        # Output: [(5, "apple"), (6, "banana"), (6, "cherry")]
        ```
    """
    for arg in iterable:
        yield predicate(arg), arg


def filter_isinstance[T](
    bases: type[T] | tuple[type[T], ...], iterable: Iterable[Any]
) -> filter[T]:
    """Filters an iterable to include only instances of specified types.

    Creates a filter object that yields only elements from the iterable
    that are instances of the given type or types.

    Args:
        bases: A type or tuple of types to check against.
        iterable: The iterable to filter.

    Returns:
        A filter object yielding only elements that are instances of the specified types.

    Examples:
        ```python
        # Filter to keep only strings
        list(filter_isinstance(str, [1, "hello", 2, "world"]))
        # Output: ["hello", "world"]

        # Filter to keep strings or numbers
        list(filter_isinstance((str, int), [1, "hello", [], 2, {}, "world"]))
        # Output: [1, "hello", 2, "world"]
        ```
    """

    def _predicate(item: Any) -> bool:
        return isinstance(item, bases)

    return filter(_predicate, iterable)


def filter_issubclass[T](bases: type[T], iterable: Iterable[Any]) -> filter[T]:
    """Filters an iterable to include only types that are subclasses of specified types.

    Creates a filter object that yields only elements from the iterable
    that are types (classes) and are subclasses of the given type or types.

    Args:
        bases: A type or tuple of types to check against.
        iterable: The iterable to filter. Elements should be types (classes).

    Returns:
        A filter object yielding only types that are subclasses of the specified types.

    Examples:
        ```python
        # Filter to keep only exception subclasses
        classes = [ValueError, str, TypeError, list, OSError]
        list(filter_issubclass(Exception, classes))
        # Output: [ValueError, TypeError, OSError]

        # Filter to keep only sequence subclasses
        list(filter_issubclass(Sequence, [list, dict, tuple, set]))
        # Output: [list, tuple]
        ```
    """

    def _predicate(item: Any) -> bool:
        return isinstance(item, type) and issubclass(item, bases)

    return filter(_predicate, iterable)


def invert_dict[K: Hashable, V: Hashable](
    mapping: Mapping[K, V],
) -> Mapping[V, K]:
    """
    Inverts the given mapping by swapping its keys and values.

    This function creates a new mapping where each value from the input
    becomes a key, and each key becomes the corresponding value. It is
    intended for mappings with unique values to avoid data loss. If the
    input mapping contains duplicate values, only one of the corresponding
    keys will be retained in the inverted mapping.

    Args:
        mapping: A mapping (such as a dict) where both keys and values are hashable.

    Returns:
        A new mapping with keys and values swapped.

    Raises:
        TypeError: If the values in the original mapping are not hashable,
                   since they are used as keys in the inverted mapping.

    Examples:
        >>> invert_dict({'a': 1, 'b': 2})
        {1: 'a', 2: 'b'}

        >>> invert_dict({1: 'x', 2: 'x'})
        { 'x': 2 }  # Note: The key 1 is overwritten by 2 because values were duplicated.
    """
    return {value: key for key, value in mapping.items()}


def group_values[K, V](
    vals: Collection[dict[K, V]], group_by_key: K
) -> dict[K, list[dict[K, V]]]:
    """
    Groups a collection of dictionaries by a specified key.

    This function iterates over a collection of dictionaries and aggregates them into a new
    dictionary. Each key in the returned dictionary corresponds to a unique value found under
    the specified group_by_key in the input dictionaries, and the associated value is a list
    of dictionaries that have that same key value.

    Args:
        vals: A collection of dictionaries. Each dictionary is expected to contain the key
              specified by group_by_key.
        group_by_key: The key used to group the dictionaries. The value for this key must be
                      hashable and present in every dictionary within the collection.

    Returns:
        A dictionary mapping each unique value (found under group_by_key) to a list of dictionaries
        that share that value.

    Raises:
        KeyError: If any dictionary in vals does not contain the specified group_by_key.

    Examples:
        >>> data = [
        ...     {'category': 'A', 'value': 1},
        ...     {'category': 'B', 'value': 2},
        ...     {'category': 'A', 'value': 3},
        ... ]
        >>> group_values(data, 'category')
        {'A': [{'category': 'A', 'value': 1}, {'category': 'A', 'value': 3}],
         'B': [{'category': 'B', 'value': 2}]}
    """
    result = defaultdict(list)
    for item in vals:
        result[item[group_by_key]].append(item)
    return dict(result)
