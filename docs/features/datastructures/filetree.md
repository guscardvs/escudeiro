# FileTree & VirtualFileTree

The `filetree` and `virtual` modules provide a flexible, Pythonic API for representing, manipulating, and writing file and directory trees in memory or on disk. They support both real and virtual filesystems, making them ideal for code generation, testing, and complex file operations.

---

## Why?

Managing complex directory structures and file operations in Python often leads to repetitive, error-prone code. The `FileTree` and `VirtualFileTree` classes abstract these patterns, allowing you to build, merge, and validate file trees with ease—without touching the disk until you want to.

```python
from escudeiro.ds.filetree import FileTree

with FileTree("/tmp/myproject") as tree:
    tree.virtual.create_py_file("main", content="print('Hello')")
    tree.virtual.create_dir("subdir")
    tree.virtual.create_text_file("README.md", content="# My Project")
# Files are written to disk on exit
```

---

## Features

- **In-memory virtual file trees** (`VirtualFileTree`)
- **Disk-backed file trees** (`FileTree`)
- **Easy file and directory creation** (including Python files, text files, and `__init__.py`)
- **Context manager support** for atomic writes
- **Merging and composition** of trees
- **Validation** for permissions and conflicts
- **Type-safe and dataclass-friendly**

---

## Usage

### Creating a Virtual File Tree

```python
from escudeiro.ds.filetree.virtual import VirtualFileTree

vt = VirtualFileTree.from_basename("myproject")
vt.create_py_file("main", content="print('Hello')")
vt.create_dir("subdir")
vt.create_text_file("README.md", content="# My Project")
```

### Writing to Disk with FileTree

```python
from escudeiro.ds.filetree import FileTree

with FileTree("/tmp/myproject") as tree:
    tree.merge(vt)  # Merge a VirtualFileTree
    # Or create files directly:
    tree.virtual.create_init_file("subdir")
# Files are written to disk on exit
```

### Using Context Managers

```python
with FileTree("/tmp/demo") as tree:
    with tree.virtual.virtual_context("nested") as vt:
        vt.create_text_file("file.txt", content="data")
    # Changes are merged automatically
```

### Merging Trees

```python
tree1 = VirtualFileTree.from_basename("pkg1")
tree1.create_py_file("a")

tree2 = VirtualFileTree.from_basename("pkg2")
tree2.create_py_file("b")

tree1.merge(tree2)  # pkg2 becomes a subfolder of pkg1
```

---

## API Reference

### FileTree

```python
class FileTree:
    def __init__(self, base_dir: Path)
    def merge(self, tree: FileTree | VirtualFileTree, *path: str) -> None
    def write(self) -> None
    def validate(self) -> None
    def __enter__(self) -> Self
    def __exit__(self, *exc_info)
    @property
    def virtual(self) -> VirtualFileTree
```

- **Description:** Represents a file tree rooted at a real directory. Supports merging, validation, and atomic writes.

### VirtualFileTree

```python
class VirtualFileTree:
    def __init__(self, root: FsNode)
    @classmethod
    def from_basename(cls, name: str) -> Self
    def create_py_file(self, filename, *path, private=False, dunder=False, content="", append=False)
    def create_text_file(self, filename, *path, content="", encoding="utf-8", append=False)
    def create_init_file(self, *path, content="", append=False)
    def create_dir(self, dirname, *path)
    def merge(self, vt: VirtualFileTree, *path: str) -> None
    def virtual_context(self, dirname: str, *path: str)
    def get_path(self, pathname: str, *path: str) -> FsNode
    def __parse_dict__(self, by_alias: bool) -> dict
```

- **Description:** Represents an in-memory file tree. Supports file and directory creation, merging, and context management.

---

### Utilities

- `merge(tree, *path)`: Merge another tree at the given path.
- `virtual_context(dirname, *path)`: Context manager for isolated modifications.
- `validate()`: Checks for permission and path conflicts before writing.
- `__parse_dict__()`: Returns a nested dictionary representation of the tree.

---

## Notes

- Use `VirtualFileTree` for in-memory operations and composition.
- Use `FileTree` to write to disk, with context manager support for atomicity.
- Merging trees will raise on conflicts (e.g., file/folder name clashes).
- All file and directory creation methods accept arbitrary subpaths.

---

## See Also

- [Python pathlib](https://docs.python.org/3/library/pathlib.html)
- [contextlib](https://docs.python.org/3/library/contextlib.html)
- [dataclasses](https://docs.python.org/3/library/dataclasses.html)
 