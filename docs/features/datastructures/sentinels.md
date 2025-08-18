# Sentinels

The `sentinels` module provides a mechanism for creating unique, singleton-like objects and enum-like values for use as special markers in Python code. Sentinels are useful for representing missing values, statuses, or other unique tokens that should not collide with regular data.

---

## Why?

Sentinels are commonly used to indicate special states such as "missing", "pending", or "completed" in APIs, data structures, and function arguments. Using unique objects instead of regular values (like `None` or strings) avoids ambiguity and bugs.

Instead of manually creating singleton objects or using enums, the `@sentinel` decorator automates the creation of unique, immutable sentinel instances or enum-like classes.

---

## Features

- **Single unique sentinel objects** (e.g., `MISSING`)
- **Enum-like sentinel classes** (e.g., `STATUS.PENDING`, `STATUS.COMPLETED`)
- **Guaranteed uniqueness** (instances are singletons per name/module)
- **Pickle support** (sentinels can be serialized and deserialized)
- **Automatic registry** for all sentinels
- **Simple, type-safe API**

---

## Usage

### Single Sentinel

```python
from escudeiro.ds.sentinels import sentinel

@sentinel
class MISSING:
    pass

assert repr(MISSING) == "MISSING"
assert MISSING is sentinel(MISSING)  # Uniqueness guaranteed
```

### Enum-like Sentinels

```python
from escudeiro.ds.sentinels import sentinel

@sentinel
class STATUS:
    PENDING = 1
    COMPLETED = 2
    CANCELLED = "cancelled"

assert repr(STATUS.PENDING) == "1"
assert repr(STATUS.COMPLETED) == "2"
assert repr(STATUS.CANCELLED) == "'cancelled'"
assert STATUS.PENDING == 1
assert STATUS.COMPLETED == 2
assert STATUS.CANCELLED == "cancelled"
```

### Uniqueness

```python
@sentinel
class A:
    pass

@sentinel
class B:
    pass

assert A is not B

@sentinel
class STATUS_A:
    PENDING = 1

@sentinel
class STATUS_B:
    PENDING = 1

assert STATUS_A.PENDING is not STATUS_B.PENDING
```

### Pickling Support

```python
import pickle
from escudeiro.ds.sentinels import sentinel

@sentinel
class MISSING:
    pass

pickled = pickle.dumps(MISSING)
unpickled = pickle.loads(pickled)
assert unpickled is MISSING
```

### Registry

All sentinels are registered in an internal registry:

```python
from escudeiro.ds.sentinels import _registry, sentinel

@sentinel
class FIRST_CALL:
    pass

assert "your_module:FIRST_CALL" in _registry
assert _registry["your_module:FIRST_CALL"] is FIRST_CALL
```

---

## API Reference

### `sentinel`

```python
def sentinel[T](cls: type[T]) -> T
```

- **Description:** Decorator for creating unique sentinel objects or enum-like sentinel classes.
- **Parameters:**
  - `cls`: The class to decorate.
- **Returns:** A unique sentinel instance (if class is empty) or a new type with sentinel members.

---

## Notes

- Sentinel instances are always unique per name and module.
- Enum-like sentinels allow for value comparison and identity checks.
- Callable and dunder members are ignored when creating enum-like sentinels.
- Use sentinels for missing values, statuses, or any special marker.

---

## See Also

- [Python enums](https://docs.python.org/3/library/enum.html)
- [Singleton pattern](https://en.wikipedia.org/wiki/Singleton_pattern)
- [Pickle documentation](https://docs.python.org/3/library/pickle.html)
