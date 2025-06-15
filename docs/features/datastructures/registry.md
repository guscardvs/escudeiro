# Registry

The `registry` module provides generic and callable registries for mapping enum keys to values or callables. These registries help organize, validate, and access mappings in a type-safe and extensible way, supporting both general values and function registration patterns.

---

## Why?

Consider the need to associate a set of enum keys with specific values or functions, ensuring that all enum members are handled and providing easy lookup and validation. Instead of manually managing dictionaries and boilerplate checks, the `registry` module offers a structured, reusable solution:

```python
from enum import Enum
from escudeiro.ds.registry import Registry

class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3

color_registry = Registry(with_enum=Color)
color_registry.register(Color.RED, "#ff0000")
color_registry.register(Color.GREEN, "#00ff00")
color_registry.register(Color.BLUE, "#0000ff")
```

---

## Features

- **Generic registry** for mapping enum keys to any value
- **Callable registry** for mapping enum keys to functions
- **Validation** to ensure all enum keys are registered
- **Dictionary-like access** and iteration
- **Automatic function registration** with prefix support

---

## Usage

### Basic Registry

```python
from enum import Enum
from escudeiro.ds.registry import Registry

class Status(Enum):
    OK = 1
    ERROR = 2

status_registry = Registry(with_enum=Status)
status_registry.register(Status.OK, "Everything is fine")
status_registry.register(Status.ERROR, "Something went wrong")

print(status_registry[Status.OK])  # "Everything is fine"
```

### Callable Registry

```python
from enum import Enum
from escudeiro.ds.registry import CallableRegistry

class Action(Enum):
    START = 1
    STOP = 2

actions = CallableRegistry(with_enum=Action)

@actions
def action_start():
    print("Started")

@actions
def action_stop():
    print("Stopped")

actions[Action.START]()  # Prints "Started"
```

### Validation

```python
# Raises MissingName if any enum key is not registered
status_registry.validate()
```

---

## API Reference

### `Registry`

```python
class Registry[T: Enum, S]:
    with_enum: type[T]
    registry: dict[T, S]

    def register(self, key: T, value: S) -> S
    def validate(self) -> None
    def lookup(self, key: T) -> S
    def __getitem__(self, key: T) -> S
    def __iter__(self) -> Iterator[str]
    def __len__(self) -> int
```

- **Description:** Generic registry mapping enum keys to values.
- **Parameters:**
  - `with_enum`: Enum type used as keys.
- **Methods:**
  - `register(key, value)`: Register a value for a key.
  - `validate()`: Ensure all enum keys are registered.
  - `lookup(key)`: Lookup value by key.
  - `__getitem__`, `__iter__`, `__len__`: Dict-like access.

### `CallableRegistry`

```python
class CallableRegistry[T: Enum, S: Callable](Registry[T, S]):
    prefix: str = ""
    use_enum_name_as_prefix: bool = True

    def __call__(self, func: S) -> S
```

- **Description:** Registry for mapping enum keys to callables (functions).
- **Parameters:**
  - `prefix`: Prefix for function names (optional).
  - `use_enum_name_as_prefix`: If true, uses enum name as prefix.
- **Methods:**
  - `__call__(func)`: Decorator to register a function.

---

## Utilities

- **Exceptions:**
  - `AlreadySet`: Raised if a key is registered twice.
  - `MissingName`: Raised if a key is missing or not found.

---

## Notes

- Use `validate()` to ensure all enum members are registered.
- `CallableRegistry` can be used as a decorator for function registration.
- Supports dictionary-like access and iteration over registered keys.

---

## See Also

- [Python Enum](https://docs.python.org/3/library/enum.html)
- [Python decorators](https://docs.python.org/3/glossary.html#term-decorator)
- [Type hints](https://docs.python.org/3/library/typing.html)
- [AutoRegistry](https://autoregistry.readthedocs.io/en/latest/?badge=latest%2F)