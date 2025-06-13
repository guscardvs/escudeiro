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