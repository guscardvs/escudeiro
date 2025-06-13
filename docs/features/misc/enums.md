# Enhanced String Enums

The `enumsx` module provides advanced enum base classes for Python, focused on string-based enums with rich aliasing and automatic value generation in various naming conventions (snake_case, camelCase, PascalCase, kebab-case). These utilities simplify enum usage, improve string conversions, and support flexible lookups.

---

## Why?

Standard Python enums are powerful but can be verbose when you need string-based values, aliases, or custom string representations. Consider the following:

```python
from enum import Enum

class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"

print(str(Color.RED))  # Prints 'Color.RED'
```

With `enumsx`, you can easily create enums with automatic string values, multiple aliases, and custom string output:

```python
from escudeiro.misc.enumsx import SnakeEnum

class Color(SnakeEnum):
    RED = ...
    LIGHT_BLUE = ...
    DARK_GREEN = ...
    
print(str(Color.LIGHT_BLUE))  # Prints 'light_blue'
print(Color("lightBlue"))     # Flexible lookup by alias
```

---

## Features

- **String-based enums** with enhanced aliasing
- **Automatic value generation** in snake_case, camelCase, PascalCase, or kebab-case
- **Custom string representations** (`str()` returns value or name)
- **Flexible lookup** by value, name, or alias
- **Type-safe and extensible**

---

## Usage

### Basic String Enum with Aliases

```python
from escudeiro.misc.enumsx import StrEnum

class Status(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"

print(Status.SUCCESS.get_aliases())  # ('success', 'SUCCESS', 'success', 'Success', 'Success', 'success')
print(Status("SUCCESS"))             # Status.SUCCESS (lookup by alias)
```

### Enum with Automatic snake_case Values

```python
from escudeiro.misc.enumsx import SnakeEnum

class Animal(SnakeEnum):
    RED_FOX = ...
    BLUE_WHALE = ...

print(Animal.RED_FOX.value)  # 'red_fox'
print(Animal("redFox"))      # Animal.RED_FOX (lookup by camelCase alias)
```

### Enum with camelCase, PascalCase, or kebab-case Values

```python
from escudeiro.misc.enumsx import CamelEnum, PascalEnum, KebabEnum

class Fruit(CamelEnum):
    GOLDEN_APPLE = ...
    BLOOD_ORANGE = ...

print(Fruit.GOLDEN_APPLE.value)  # 'goldenApple'

class Tool(PascalEnum):
    POWER_DRILL = ...
    HAND_SAW = ...

print(Tool.POWER_DRILL.value)    # 'PowerDrill'

class Device(KebabEnum):
    SMART_PHONE = ...
    LAPTOP_COMPUTER = ...

print(Device.SMART_PHONE.value)  # 'smart-phone'
```

### Custom String Representation

```python
from escudeiro.misc.enumsx import ValueEnum, NameEnum

class Mode(ValueEnum):
    AUTO = "auto"
    MANUAL = "manual"

print(str(Mode.AUTO))   # 'auto'

class Level(NameEnum):
    HIGH = "high"
    LOW = "low"

print(str(Level.HIGH))  # 'HIGH'
```

---

## API Reference

### Base Classes

#### `StrEnum`

- **Description:** String-based enum with alias support.
- **Methods:**
  - `get_aliases(self) -> Sequence[str]`: Returns all string aliases for the member (value, name, camel, pascal, kebab, etc.).
  - Flexible lookup: `EnumClass("alias")` returns the matching member.

#### `ValueEnum`

- **Description:** Like `StrEnum`, but `str(member)` returns the value.

#### `NameEnum`

- **Description:** Like `StrEnum`, but `str(member)` returns the name.

#### `SnakeEnum`, `CamelEnum`, `PascalEnum`, `KebabEnum`

- **Description:** Subclasses of `StrEnum` that auto-generate values in the respective naming convention.
- **Usage:** Use `...` as the value to auto-generate from the name.

---

## Utilities

- **Alias lookup:** All enums support lookup by any alias (name, value, camelCase, etc.).
- **Custom value generation:** Inherit from the appropriate base for your naming style.

---

## Notes

- If combining multiple enum utilities, inherit from `NameEnum` or `ValueEnum` first to control string output.
- Aliases are generated using the member name and value in various cases and styles.
- Use `get_aliases()` to inspect all possible lookup strings for a member.

---

## See Also

- [Python enum documentation](https://docs.python.org/3/library/enum.html)
- [String case conversion](https://pypi.org/project/stringcase/)