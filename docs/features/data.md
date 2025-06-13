# Data Classes

The `data` module provides a powerful decorator and utilities for defining Python data classes, inspired by both `dataclasses` and `attrs`. It offers a familiar, type-safe API with advanced features such as slots, frozen instances, custom field types, and optional Pydantic integration.

---

## Why?

Python's `dataclasses` and the `attrs` library make it easy to define classes for storing data, but sometimes you need more flexibility, better performance, or extra features like per-field customization, slots, or integration with other libraries.

The `data` module aims to combine the best of both worlds, providing a modern, extensible, and ergonomic API for defining data classes. It has also drop in support for dataclasses so, you can take:

```python
from dataclasses import dataclass, field
@dataclass
class Point:
    x: int
    y: int = field(default=0)
```

and have it work with `escudeiro.data`:

```python
from escudeiro.data import data
from dataclasses import field

@data(frozen=False)
class Point:
    x: int
    y: int = field(default=0)
```

and it will work the same way, but with the added benefits of slots, frozen instances, and more.

---

## Features

- **Familiar API**: Similar to `dataclasses` and `attrs`
- **Type-safe**: Full type hinting and static analysis support
- **Slots support**: Reduce memory usage and speed up attribute access
- **Frozen classes**: Make instances immutable
- **Custom fields**: Use `field()` and `private()` for fine-grained control
- **Pydantic compatibility**: Optional handlers for Pydantic models
- **Dataclass fields compatibility**: Optionally generate `__dataclass_fields__` and understands `dataclasses.field()` implementation
- **Descriptor-friendly**: Supports lazy fields, lazy methods, and custom descriptors that use private fields in a slots-friendly way.
- **Hooks and helpers**: For advanced customization and introspection

---

## Usage

### Basic Data Class

```python
from escudeiro.data import data, field

@data
class Point:
    x: int
    y: int = field(default=0)

p = Point(1)
print(p.x, p.y)  # 1 0
```

### Frozen and Slots

```python
from escudeiro.data import data

@data(frozen=True, slots=True)
class Config:
    name: str
    value: int
```

### Private Fields

```python
from escudeiro.data import data, private

@data
class User:
    name: str
    _token: str = private()
```

### Pydantic Integration

```python
from escudeiro.data import data

@data(pydantic=True)
class Model:
    id: int
    name: str
```

### Custom Field Options

```python
from escudeiro.data import data, field

@data
class Item:
    id: int = field(default_factory=int, repr=False)
    name: str
```

### Descriptors and slots

Given that the `data` module uses slots by default, it automatically looks for a .private_field
in the descriptors defined to add it to the slots collection and allow the descriptor to work correctly without conflicts.

```python
from escudeiro.data import data
from escudeiro.lazyfields import lazyfield

@data
class Computation:
    value: int

    @lazyfield
    def double(self):
        print("Computing double...")
        return self.value * 2
c = Computation(value=10)
print(c.double)  # "Computing double..." then 20
```

If the descript requires extra slot entries, you can use the `slot` decorator to add them:

```python
from escudeiro.data import data, slot

@slot('_my_value', '_another_value')
class MyDescriptor:
    def __get__(self, instance, owner):
        if instance is None:
            return self
        if not hasattr(instance, '_my_value'):
            instance._my_value = self.compute(instance)
        if not hasattr(instance, '_another_value'):
            instance._another_value = self.compute_another(instance)
        return (
            instance._my_value,
            instance._another_value
        )

@data
class MyClass:
    value: int
    example = MyDescriptor()
```

---

## API Reference

### `@data`

```python
@overload
def data[T](
    maybe_cls: None = None,
    /,
    *,
    frozen: bool = True,
    init: bool = True,
    kw_only: bool = False,
    slots: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = True,
    hash: bool | None = None,
    pydantic: bool = False,
    dataclass_fields: bool = False,
    field_class: type[Field] = Field,
    alias_generator: Callable[[str], str] = str,
) -> Callable[[type[T]], type[T]]: ...

@overload
def data[T](
    maybe_cls: type[T],
    /,
    *,
    frozen: bool = True,
    init: bool = True,
    kw_only: bool = False,
    slots: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = True,
    hash: bool | None = None,
    pydantic: bool = False,
    dataclass_fields: bool = False,
    field_class: type[Field] = Field,
    alias_generator: Callable[[str], str] = str,
) -> type[T]: ...
```

- **Description:** Decorator for defining a data class.
- **Parameters:**
  - `frozen`: Make instances immutable (default: `True`)
  - `init`: Generate `__init__` (default: `True`)
  - `kw_only`: All fields keyword-only (default: `False`)
  - `slots`: Use `__slots__` (default: `True`)
  - `repr`: Generate `__repr__` (default: `True`)
  - `eq`: Generate `__eq__` (default: `True`)
  - `order`: Generate ordering methods (default: `True`)
  - `hash`: Generate `__hash__` (default: `None`)
  - `pydantic`: Add Pydantic handlers (default: `False`)
  - `dataclass_fields`: Add `__dataclass_fields__` (default: `False`)
  - `field_class`: Custom field class (default: `Field`)
  - `alias_generator`: Function to generate field aliases (default: `str`)

---

### Fields

#### `field`

```python
def field(
    *,
    default: Any = UNINITIALIZED,
    default_factory: Callable[[], Any] = UNINITIALIZED,
    repr: bool = True,
    eq: bool = True,
    order: bool = True,
    hash: bool | None = None,
    init: bool = True,
    kw_only: bool = False,
    metadata: dict[str, Any] = {},
    alias: str | None = None,
)
```

- **Description:** Define a field with custom options.
- **Parameters:** Similar to `dataclasses.field`.

#### `private`

```python
def private(
    *,
    default: Any = UNINITIALIZED,
    default_factory: Callable[[], Any] = UNINITIALIZED,
)
```

- **Description:** Define a private field (not included in `__repr__`, `__eq__`, etc).

---

### Helpers

- `asdict(obj)`: Convert to dict.
- `asjson(obj)`: Convert to JSON.
- `fromdict(cls, data)`: Create instance from dict.
- `fromjson(cls, data)`: Create instance from JSON.
- `get_fields(cls)`: Get field definitions.
- `call_init(obj)`: Call `__post_init__` hooks.
- `update_refs(obj)`: Update references.
- `resolve_typevars(cls)`: Resolve type variables.

---

## Notes

- The `data` decorator is compatible with most `dataclasses` and `attrs` patterns.
- Use `field()` for advanced field options, or `private()` for hidden fields.
- Set `pydantic=True` for Pydantic model compatibility.
- Set `dataclass_fields=True` to expose `__dataclass_fields__` for interoperability.

---

## See Also

- [Python dataclasses](https://docs.python.org/3/library/dataclasses.html)
- [attrs](https://www.attrs.org/en/stable/)
- [Pydantic](https://docs.pydantic.dev/)
