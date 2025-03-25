"""Utilities for working with iterables and sequences.

This module provides functions for common iteration patterns, sequence transformations,
and advanced iterator operations with strong type safety.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable, Iterable, Iterator, Sequence
from typing import TYPE_CHECKING, Any, cast

from escudeiro.misc.functions import safe_cast


def moving_window[T](
    iterable: Iterable[T],
    window_size: int,
    cast: Callable[[Iterator[T]], Sequence[T]] = tuple,
) -> Iterable[Sequence[T]]:
    """Returns an iterator yielding overlapping windows from an iterable.

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


def filter_isinstance[T](bases: type[T], iterable: Iterable[Any]) -> filter[T]:
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
