# Iterables & Sequences Utilities

The `escudeiro.misc.iterx` module provides advanced utilities for working with iterables, sequences, and async iterables in Python. It includes functions for windowing, mapping, filtering, flattening, grouping, and more—supporting both synchronous and asynchronous workflows.

---

## Why?

Python's standard library offers many tools for iteration, but common patterns like sliding windows, async mapping/filtering, or flattening nested structures often require verbose or repetitive code. This module provides concise, type-safe, and feature-rich helpers for these scenarios.

---

## Features

- **Sliding windows** for sync and async iterables
- **Async mapping, filtering, reducing** and enumeration
- **Flattening** of nested sequences
- **Type-based filtering** (`isinstance`, `issubclass`)
- **Carry mapping** (preserve original values)
- **Safe next/anext with default**
- **Dictionary inversion and grouping**

---

## Usage

### Moving Window

```python
from escudeiro.misc.iterx import moving_window

list(moving_window([1, 2, 3, 4, 5], 3))
# Output: [(1, 2, 3), (4, 5)]
```

### Async Moving Window

```python
from escudeiro.misc.iterx import amoving_window, aislice
import asyncio

async def main():
    async def gen():
        for i in range(7):
            yield i
    async for window in amoving_window(gen(), 3):
        print(window)
# Output: [0, 1, 2], [3, 4, 5], [6]
```

### Async Map/Filter/Reduce

```python
from escudeiro.misc.iterx import amap, afilter, areduce

async def main():
    async def gen():
        for i in range(5):
            yield i
    # Map
    async for x in amap(lambda x: x * 2, gen()):
        print(x)
    # Filter
    async for x in afilter(lambda x: x % 2 == 0, gen()):
        print(x)
    # Reduce
    result = await areduce(lambda a, b: a + b, gen(), 0)
    print(result)
```

### Flatten Nested Sequences

```python
from escudeiro.misc.iterx import flatten

flatten([1, [2, 3], [4, [5, 6]]])
# Output: [1, 2, 3, 4, 5, 6]
```

### Filter by Type

```python
from escudeiro.misc.iterx import filter_isinstance

list(filter_isinstance(str, [1, "hello", 2, "world"]))
# Output: ["hello", "world"]
```

### Invert Dictionary

```python
from escudeiro.misc.iterx import invert_dict

invert_dict({'a': 1, 'b': 2})
# Output: {1: 'a', 2: 'b'}
```

---

## API Reference

### Windowing

#### `moving_window`

```python
def moving_window[T](
    iterable: Iterable[T],
    window_size: int,
    cast: Callable[[Iterator[T]], Sequence[T]] = tuple,
) -> Iterable[Sequence[T]]:
```
- Returns non-overlapping windows from an iterable.

#### `amoving_window`

```python
async def amoving_window[T](
    iterable: AsyncIterable[T],
    window_size: int,
) -> AsyncIterable[Sequence[T]]:
```
- Async version for async iterables.

#### `aislice`

```python
async def aislice[T](
    iterable: AsyncIterable[T],
    start: int | None = None,
    stop: int | None = None,
    step: int | None = None,
) -> AsyncIterable[T]:
```
- Async slice for async iterables.

---

### Mapping & Filtering

#### `amap`

```python
async def amap[V, T](
    predicate: Callable[[V], T] | Callable[[V], Coroutine[Any, Any, T]],
    iterable: AsyncIterable[V],
) -> AsyncIterable[T]:
```
- Async map.

#### `afilter`

```python
async def afilter[V](
    predicate: Callable[[V], bool] | Callable[[V], Coroutine[Any, Any, bool]],
    iterable: AsyncIterable[V],
) -> AsyncIterable[V]:
```
- Async filter.

#### `areduce`

```python
async def areduce[V, T](
    predicate: Callable[[T, V], T] | Callable[[T, V], Coroutine[Any, Any, T]],
    iterable: AsyncIterable[V],
    initial: T | object = _reduce_sentinel,
) -> T | V:
```
- Async reduce.

#### `aenumerate`

```python
async def aenumerate[T](
    iterable: AsyncIterable[T], start: int = 0
) -> AsyncIterable[tuple[int, T]]:
```
- Async enumerate.

#### `aany`, `aall`

```python
async def aany[T](iterable: AsyncIterable[T], predicate=bool) -> bool
async def aall[T](iterable: AsyncIterable[T], predicate=bool) -> bool
```
- Async any/all with predicate.

---

### Sequence Utilities

#### `flatten`

```python
def flatten(sequence: Sequence[Any]) -> Sequence[Any]:
```
- Flattens nested sequences.

#### `exclude_none`

```python
def exclude_none[SequenceT: SequenceTypes](sequence: SequenceT) -> SequenceT:
```
- Recursively removes `None` from sequences.

#### `next_or`, `anext_or`

```python
def next_or[T, D](iterable: Iterable[T], default: D = None) -> T | D
async def anext_or[T, D](iterable: AsyncIterable[T], default: D = None) -> T | D
```
- Safe next/anext with default.

---

### Carry Mapping

#### `carrymap`, `acarrymap`

```python
def carrymap[T, U](predicate: Callable[[T], U], iterable: Iterable[T]) -> Iterable[tuple[U, T]]
async def acarrymap[U, T](predicate: Callable[[T], Coroutine[Any, Any, U]], iterable: AsyncIterable[T]) -> AsyncIterable[tuple[U, T]]
```
- Map while preserving original values.

#### `astarmap`, `acarrystarmap`

```python
async def astarmap[*Ts, U](predicate: Callable[[*Ts], Coroutine[Any, Any, U]], iterable: AsyncIterable[tuple[*Ts]]) -> AsyncIterable[U]
async def acarrystarmap[*Ts, U](predicate: Callable[[*Ts], Coroutine[Any, Any, U]], iterable: AsyncIterable[tuple[*Ts]]) -> AsyncIterable[tuple[U, tuple[*Ts]]]
```
- Async star mapping.

---

### Type Filtering

#### `filter_isinstance`

```python
def filter_isinstance[T](bases: type[T] | tuple[type[T], ...], iterable: Iterable[Any]) -> filter[T]
```
- Filters by `isinstance`.

#### `filter_issubclass`

```python
def filter_issubclass[T](bases: type[T], iterable: Iterable[Any]) -> filter[T]
```
- Filters by `issubclass`.

---

### Dictionary Utilities

#### `invert_dict`

```python
def invert_dict[K: Hashable, V: Hashable](mapping: Mapping[K, V]) -> Mapping[V, K]
```
- Inverts keys and values.

#### `group_values`

```python
def group_values[K, V](vals: Collection[dict[K, V]], group_by_key: K) -> dict[K, list[dict[K, V]]]
```
- Groups a collection of dicts by a key.

---

## Notes

- Async utilities require Python 3.8+.
- Many functions are type-annotated for static analysis.
- Use `flatten` and `exclude_none` for deep sequence cleaning.

---

## See Also

- [itertools](https://docs.python.org/3/library/itertools.html)
- [collections.abc](https://docs.python.org/3/library/collections.abc.html)
- [asyncio](https://docs.python.org/3/library/asyncio.html)