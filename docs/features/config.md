# Config

The `config` module provides a flexible, extensible configuration system for Python applications, inspired by and compatible with [Starlette's Config](https://www.starlette.io/config/). It supports environment variables, `.env` files, type casting, and advanced features like environment-specific overrides and adapter-based extensibility.

---

## Why?

Managing configuration in Python projects often involves juggling environment variables, `.env` files, and type conversions. The `config` module streamlines this process, offering a unified API for loading, casting, and managing configuration values, while remaining compatible with Starlette's conventions.

```python
from escudeiro.config import Config

config = Config(".env")
DEBUG = config("DEBUG", cast=bool, default=False)
DATABASE_URL = config("DATABASE_URL")
```

---

## Features

- **Starlette-compatible API** for easy migration and interoperability
- **Environment variable and `.env` file support**
- **Type casting** with robust error handling
- **Environment-specific configuration** via `EnvConfig` and `DotFile`
- **Extensible adapters** for dataclasses, attrs, Pydantic, and more
- **Manual and automatic value overrides**
- **Thread-safe lazy loading**

---

## Usage

### Basic Configuration

```python
from escudeiro.config import Config

config = Config(".env")
SECRET_KEY = config("SECRET_KEY")
TIMEOUT = config("TIMEOUT", cast=int, default=30)
```

### Environment-Specific Configuration

```python
from escudeiro.config import EnvConfig, Env, DotFile

config = EnvConfig(DotFile(".env.production", Env.PROD))
API_URL = config("API_URL")
```

### Using Adapters

Adapters allow you to load configuration into dataclasses, attrs, or Pydantic models.

```python
from escudeiro.config.adapter import AdapterConfigFactory
from dataclases import dataclass
from escudeiro.data import data

@data
class PoolConfig:
    size: int
    timeout: int
    max_retries: int

@dataclass # Also supports escudeiro.data.data, attrs.define and pydantic.BaseModel
class DBConfig:
    host: str
    port: int
    user: str
    password: str
    pool: PoolConfig

factory = AdapterConfigFactory()
db_config = factory.load(DBConfig, __prefix__="db")
# will search for environment variables like DB_HOST, DB_PORT, etc.
# for pool it will search for DB_POOL__SIZE, DB_POOL__TIMEOUT, etc.
# the types defined in DBConfig will be automatically casted using the declared types
# or using boolean_cast for boolean values.
```

---

## Type Casting Helpers

The `escudeiro.config.core.utils` module provides a set of robust helpers for type casting and validation, which are used internally by the config system and can be leveraged in your own code for advanced scenarios.

### Key Helpers

- **`boolean_cast`**: Converts strings like `"true"`, `"1"`, `"false"`, `"0"` to booleans, with strict error handling via `maybe_result`.
- **`valid_path`**: Casts a string to a `Path` and checks if it exists, raising if not.
- **`literal_cast`**: Casts a string to a value from a `Literal` type annotation, raising if the value is not allowed.
- **`none_is_missing`**: Ensures that a cast never returns `None`, raising `MissingName` if it does.
- **`null_cast`**: Casts strings like `"null"`, `"none"`, or `""` to Python `None`.

These helpers are used by the config system to provide safe, extensible, and customizable type casting for environment variables and `.env` values. You can use them directly for custom validation or casting logic in your own configuration workflows.

---

## Examples

Here are some practical examples of using the helpers from `escudeiro.config.core.utils`:

```python
from escudeiro.config.core.utils import boolean_cast, valid_path, literal_cast, maybe_result

# Boolean casting
DEBUG = boolean_cast("true")  # True
ENABLED = boolean_cast("0")   # False

# Path validation
config_path = valid_path("/etc/myapp/config.yaml")  # Raises if file does not exist

# Literal casting
from typing import Literal
env = literal_cast("prod", Literal["dev", "prod", "test"])  # "prod"

# Using maybe_result for strict/optional casting
strict_bool = maybe_result(boolean_cast).strict()
optional_bool = maybe_result(boolean_cast).optional()

strict_bool("yes")  # Raises if not a valid boolean
optional_bool("maybe")  # Returns None instead of raising

# Chaining casts with joined_cast
from escudeiro.config.core.utils import joined_cast
cast_to_int_then_str = joined_cast(int).cast(str)
result = cast_to_int_then_str("42")  # "42" as a string after int conversion

# Using with_rule to enforce a custom rule
from escudeiro.config.core.utils import with_rule
positive_int = joined_cast(int).cast(with_rule(lambda x: x > 0))
value = positive_int("10")  # 10
```

These examples demonstrate how you can compose and use the helpers for robust configuration parsing and validation.

## API Reference

### `Config`

```python
class Config:
    def __init__(self, env_file: str | Path | None = None, mapping: Mapping[str, str] = DEFAULT_MAPPING)
    def __call__(self, name: str, cast: Callable = default_cast, default: Any = MISSING) -> Any
    def get(self, name: str, cast: Callable = default_cast, default: Any = MISSING) -> Any
```

- **Description:** Loads configuration from environment variables and `.env` files.
- **Parameters:**
  - `env_file`: Path to a dotenv file.
  - `mapping`: Optional mapping to override environment variables.

### `EnvConfig`

```python
class EnvConfig(Config):
    def __init__(self, env: Env, env_file: str | Path | None = None, ...)
    def get(self, name: str, cast: Callable = default_cast, default: Any = MISSING) -> Any
    @property
    def dotfile(self) -> DotFile | None
```

- **Description:** Extends `Config` to support environment-specific overrides.

### `DotFile`

```python
class DotFile:
    filename: str | Path
    env: Env
    cascade: bool = False
```

- **Description:** Represents a configuration file for a specific environment.

### Adapters

- `AdapterConfigFactory`: Base for creating config adapters.
- `CachedFactory`: Caches adapter instances for efficiency.

---

## Utilities

- `default_cast`: Default type casting function.
- `MISSING`: Sentinel for missing values.
- `EnvMapping`: Mapping for environment variables.
- `get_config`: Function to retrieve config managed by contextvars inside escudeiro.
- `set_config`: Function to set config values managed by contextvars inside escudeiro. It raises `AlreadySet` if the config was already changed once.
- `get_env`: Function to retrive the environment set in the contextvars.

---

## Notes

- The API is compatible with Starlette's `Config`, so you can migrate with minimal changes.
- Use `EnvConfig` and `DotFile` for advanced, multi-environment setups.
- Adapters make it easy to bind configuration to structured types.

---

## See Also

- [Starlette Config](https://www.starlette.io/config/)
- [python-dotenv](https://pypi.org/project/python-dotenv/)
- [escudeiro.lazyfields](./lazyfields.md)
