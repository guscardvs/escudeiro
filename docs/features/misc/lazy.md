# Lazy Method Decorator (`lazymethod`)

The `lazymethod` decorator in `escudeiro.misc.lazy` provides argument-sensitive lazy evaluation and caching for instance methods. Unlike `lazyfields`, which cache a single value per field, `lazymethod` can cache results for different argument combinations, supporting both hashable and unhashable arguments.

---

## Why?

Consider the following pattern for caching expensive computations based on arguments:

```python
class MyClass:
    def expensive(self, x, y=1):
        if not hasattr(self, "_cache"):
            self._cache = {}
        key = (x, y)
        if key not in self._cache:
            print("Computing...")
            self._cache[key] = x + y
        return self._cache[key]
```

This approach is verbose and error-prone. `lazymethod` automates this, handling argument mapping, caching, and even unhashable arguments.

---

## Features

- **Argument-sensitive caching**: Caches results per argument signature.
- **Supports hashable and unhashable arguments**: Uses dict or list as needed.
- **No boilerplate**: Just decorate your method.
- **Automatic signature handling**: Deals with defaults and keyword arguments.
- **Type-safe**: Uses type hints for better safety.

---

## Usage

### Basic Usage

```python
from escudeiro.misc.lazy import lazymethod

class MyClass:
    @lazymethod
    def expensive(self, x, y=1):
        print("Computing...")
        return x + y

obj = MyClass()
print(obj.expensive(2, y=3))  # Prints "Computing..." then 5
print(obj.expensive(2, y=3))  # Prints 5 (no recomputation)
print(obj.expensive(4))       # Prints "Computing..." then 5
```

### Works with Unhashable Arguments

If your method uses unhashable arguments, `lazymethod` falls back to a list-based cache:

```python
class MyClass:
    @lazymethod
    def expensive(self, data: list):
        print("Computing...")
        return sum(data)

obj = MyClass()
print(obj.expensive([1, 2]))  # Prints "Computing..." then 3
print(obj.expensive([1, 2]))  # Prints 3 (no recomputation)
```

---

## API Reference

### `lazymethod`

```python
class lazymethod[SelfT, T, **P]:
    def __init__(self, func: Callable[Concatenate[SelfT, P], T]) -> None
```

- **Description:** Decorator for instance methods to cache results per argument signature.
- **Parameters:**
  - `func`: The method to decorate.

#### Method Types

- **SELF_ONLY**: No arguments except `self` (single cached value).
- **HASHABLE_ARGS**: All arguments are hashable (dict-based cache).
- **UNKNOWN_OR_UNHASHABLE**: Some arguments are unhashable (list-based cache).

#### Utilities

- `is_initialized(instance, name)`: Returns `True` if the cache exists for the method.

---

## Comparison: `lazymethod` vs `lazyfields`

| Feature                | `lazymethod` (`misc/lazy`)         | `lazyfields` (`lazyfields`)         |
|------------------------|------------------------------------|-------------------------------------|
| **Granularity**        | Per-method, per-argument           | Per-field, per-instance             |
| **Argument support**   | Caches per argument signature      | No arguments (property-like)        |
| **Async support**      | No                                 | Yes (`@asynclazyfield`)             |
| **Thread safety**      | No built-in locking                | Optional per-instance locking       |
| **Manual reset**       | No                                 | Yes (`dellazy`)                     |
| **Type safety**        | Yes                                | Yes                                 |
| **Use case**           | Methods with arguments             | Expensive properties/fields         |

---

## Notes

- Use `lazymethod` for methods whose results depend on arguments.
- Use `lazyfields` for properties or fields that should be computed once per instance.
- `lazymethod` does not provide thread safety or async support.

---

## See Also

- [escudeiro.lazyfields](../lazyfields.md)
- [Python descriptors](https://docs.python.org/3/howto/descriptor.html)
- [functools.lru_cache](https://docs.python.org/3/library/functools.html#functools.lru_cache)