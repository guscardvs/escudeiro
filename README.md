# Escudeiro

**The squire to your Python projects.**

Escudeiro is a modern, extensible toolkit for Python that brings together advanced data modeling, configuration, utilities, and high-performance Rust-powered extensions. It is designed for developers who want robust, ergonomic, and efficient solutions for building complex Python applications.

---

## Features

- **Slots-first, Descriptor-friendly Data Classes**  
  Escudeiro’s `data` module is an attrs-like, slots-first data modeling system. It natively supports Python `__slots__`, advanced descriptors (like lazy fields and lazymethods), and is designed for extensibility.  
  - Out-of-the-box support for lazy fields, slotted descriptors, and custom field types.
  - Integrates seamlessly with async and sync lazy evaluation.
  - Serialization/deserialization to dict/JSON, schema generation, and type variable resolution.

- **Configuration Management**  
  Flexible configuration loading from environment variables, files, and mappings, with type-safe casting and validation.

- **Utilities & Helpers**  
  A rich set of helpers for type casting, lazy evaluation, async utilities, string manipulation, and more.

- **Autodiscovery**  
  Dynamic and static discovery of modules and objects at runtime, supporting plugin-like architectures.

- **Rust-powered Performance**  
  Performance-critical components are implemented in Rust (via PyO3), including file tree management and string utilities.

---

## Installation

```bash
pip install escudeiro
```
Requires Python 3.12+.

## Quick Start

### Data modeling and descriptors:

```python
from escudeiro.data import data, field
from escudeiro.lazyfields import lazyfield

@data
class User:
    name: str = field()
    age: int = field(default=0)

    @lazyfield
    def expensive_computation(self):
        print("Computing...")
        return self.age * 2

user = User(name="Alice", age=21)
print(user.expensive_computation)  # "Computing..." then 42
print(user.expensive_computation)  # 42 (cached)
```

### Asynchronous lazy evaluation:

```python
from escudeiro.lazyfields import asynclazyfield
import asyncio

@data
class Resource:
    @asynclazyfield
    async def load(self):
        await asyncio.sleep(1)
        return "loaded"

async def main():
    r = Resource()
    print(await r.load())  # "loaded"

asyncio.run(main())
```

### File tree management with Rust:

```python
from escudeiro.filetree import FileTree

tree = FileTree(base_dir="my_project")
vt = tree.virtual
vt.create_text_file("README.md", content="# My Project")
tree.write()
```

## Integrations

- Optional support for [Pydantic](https://pydantic-docs.helpmanual.io/) for data validation and settings management.
- Optional support for [msgspec](https://msgspec.readthedocs.io/en/latest/) for high-performance serialization/deserialization.

Install with:

```bash
pip install escudeiro[pydantic,msgspec]
```

## License
This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.

## Contributing
We welcome contributions! Please open an issue or submit a pull request on GitHub.

## Changelog
See the [CHANGELOG](CHANGELOG.md) for a detailed list of changes and updates.

## Author
Escudeiro is developed and maintained by me.