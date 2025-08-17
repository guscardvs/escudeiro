# Type Utilities

The `typex` module provides advanced utilities for working with Python type annotations, focusing on type introspection and validation. It is especially useful for generic types, unions, and annotated types, supporting complex type analysis in a type-safe manner.

---

## Why?

Type annotations in Python can be complex, especially when dealing with generics, unions, and custom type aliases. Determining properties like hashability across nested or composite types is non-trivial. The `typex` module simplifies this process by providing utilities that deeply inspect and validate type annotations.

Consider the following scenario:

```python
from typing import List, Dict, Any
from escudeiro.misc.typex import is_hashable

print(is_hashable(int))  # True
print(is_hashable(List[int]))  # False
print(is_hashable(Dict[str, int]))  # False
```

---

## Features

- **Deep type introspection** for generics, unions, and annotated types
- **Hashability checks** for complex/nested type annotations
- **Support for `TypeAliasType`, `Annotated`, and standard typing constructs**
- **Type-safe and compatible with static type checkers**

---

## Usage

### Checking Hashability of Types

```python
from escudeiro.misc.typex import is_hashable

print(is_hashable(int))  # True
print(is_hashable(list))  # False
print(is_hashable(tuple))  # True
print(is_hashable(list[int]))  # False
print(is_hashable(tuple[int, ...]))  # True
```

### Handling Type Aliases and Annotated Types

```python
from typing import Annotated, TypeAlias

MyAlias: TypeAlias = int
MyAnnotated = Annotated[int, "meta"]

print(is_hashable(MyAlias))      # True
print(is_hashable(MyAnnotated))  # True
```

### Exact instance checking

```python
class Parent:
  pass

class Child(Parent):
    pass

isinstance(Child(), Parent) # true
isinstance(Child(), Child) # true
is_instanceexact(Child(), Child) # true
is_instanceexact(Child(), Parent) # false
```

### Casting shortcuts

```python

value: int | None = 1

cast_notnone(value) # type casts value to int for the linter.
assert_notnone(value) # also type casts, but if value is none raises ValueError.
# assert_notnone raises ValueError because python assert can be skipped by optimized mode.
```

---

## API Reference

### `is_hashable`

```python
def is_hashable(annotation: Any) -> TypeIs[Hashable]:
    ...
```

- **Description:** Determines if a type annotation (including generics, unions, and annotated types) is hashable.
- **Parameters:**
  - `annotation`: The type annotation to check.
- **Returns:** `True` if the type is hashable, `False` otherwise.

### `is_instanceexact`

```python
def is_instanceexact(obj: Any, annotation: Any) -> bool:
    ...
```

- **Description:** Checks if an object is an instance of a specific type, considering inheritance.
  - It supports annotations and unions.
- **Parameters:**
  - `obj`: The object to check.
  - `annotation`: The type annotation to check against.
- **Returns:** `True` if the object is an instance of the specified type, `False` otherwise.

### `cast_notnone`

```python
def cast_notnone[T](value: T | None) -> T:
    ...
```

- **Description:** Casts a value to a non-None type for type checking.
- **Parameters:**
  - `value`: The value to cast.
- **Returns:** Returns typing.cast(T, value)

### `assert_notnone`

```python
def assert_notnone[T](value: T | None) -> T:
    ...
```

- **Description:** Asserts that a value is not None, raising a ValueError if it is.
- **Parameters:**
  - `value`: The value to check.
- **Returns:** The value if it is not None.

---

## Implementation Notes

- Handles `TypeAliasType` by resolving to the underlying type.
- Recursively inspects generic arguments and union members.
- Supports `Annotated` types by checking the base type.
- Uses a stack and cache to avoid infinite recursion and redundant checks.

---

## See Also

- [Python typing — Type hints](https://docs.python.org/3/library/typing.html)
- [collections.abc.Hashable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Hashable)
- [PEP 593 – Flexible function and variable annotations](https://peps.python.org/pep-0593/)
