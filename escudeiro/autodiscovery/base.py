import ast
import importlib
import importlib.util
import os
import pathlib
import sys
import warnings
from collections import defaultdict
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from types import ModuleType

from escudeiro.data import data
from escudeiro.lazyfields import lazyfield
from escudeiro.misc import filter_isinstance, lazymethod

type PathConverter = Callable[[Path], str]
type StrOrPath = str | Path


def make_modulename_converter(
    root: pathlib.Path, path_converter: PathConverter
) -> PathConverter:
    root_path = path_converter(root)

    def converter(path: Path) -> str:
        pathstr = path_converter(path)
        if root_path in pathstr:
            pathstr = pathstr.replace(root_path, root.name, 1)
        # a package's __init__.py is the package itself, not a submodule
        pathstr = pathstr.removesuffix(".py").removesuffix("/__init__")
        return pathstr.replace("/", ".")

    return converter


@data(frozen=False)
class AutoDiscoveryHelper:
    """
    Helper class for auto-discovery of modules or files within a directory.

    Attributes:
        root (pathlib.Path): Root directory to start discovery.
        look_on (Path | None): Optional specific directory to look on.
        exclude (Sequence[StrOrPath]): List of paths or filenames to exclude.
        exts (Sequence[str]): List of file extensions to consider.
        converter (PathConverter): Function to convert paths to strings.
    """

    root: pathlib.Path
    look_on: Path | None = None
    exclude: Sequence[StrOrPath] = ()
    exts: Sequence[str] = ()
    converter: PathConverter = Path.as_posix
    include: Sequence[StrOrPath] = ()

    def __post_init__(self):
        self.exclude = ("__pycache__", *self.exclude)
        self.exts = (".py", *self.exts)

    @lazyfield
    def excludes(self) -> tuple[tuple[str, ...], tuple[Path, ...]]:
        str_exclude = tuple(filter_isinstance(str, self.exclude))
        path_exclude = tuple(filter_isinstance(pathlib.Path, self.exclude))
        return str_exclude, path_exclude

    @lazyfield
    def includes(self) -> tuple[tuple[str, ...], tuple[Path, ...]]:
        str_include = tuple(filter_isinstance(str, self.include))
        path_include = tuple(filter_isinstance(pathlib.Path, self.include))
        return str_include, path_include

    def should_lookup(self, path: Path) -> bool:
        str_exclude, path_exclude = self.excludes
        str_include, path_include = self.includes
        _, ext = os.path.splitext(path)

        if path.name in str_exclude or path in path_exclude:
            return False
        if path.is_dir():
            # include filters files only, so nested matches are still reached
            return True
        if path.is_file() and ext not in self.exts:
            return False
        if str_include or path_include:
            return (
                path.name in str_include
                or path in path_include
                or any(parent in path_include for parent in path.parents)
            )
        return True

    @property
    def target_path(self) -> Path:
        return self.look_on or self.root

    @lazymethod
    def get_resolver(self) -> PathConverter:
        return make_modulename_converter(self.root, self.converter)

    def iterdir(self, path: Path) -> Iterator[Path]:
        stack = [path]
        visited: set[str] = set()
        while stack:
            path = stack.pop()
            if not path.is_dir():
                yield path
                continue
            # symlink loops resolve to an already visited directory
            real = os.path.realpath(path)
            if real in visited:
                continue
            visited.add(real)
            dirs: list[Path] = []
            for item in sorted(filter(self.should_lookup, path.iterdir())):
                if item.is_dir():
                    dirs.append(item)
                else:
                    yield item
            stack.extend(reversed(dirs))


def _import_base(node: ast.ImportFrom, modname: str, file: Path) -> str | None:
    """Absolute name of the module a `from ... import` statement reads from."""
    if not node.level:
        return node.module
    package = modname.split(".")
    if file.name != "__init__.py":
        _ = package.pop()
    if node.level - 1 > len(package):
        return None
    package = package[: len(package) - (node.level - 1)]
    return ".".join([*package, *([node.module] if node.module else [])])


def sort_files_by_dependency(
    modnames: list[str], files: list[Path]
) -> Iterator[Path]:
    """
    Sorts Python files by their dependencies using AST analysis.

    Args:
        modnames (List[str]): List of module names corresponding to `files`.
        files (List[Path]): List of Path objects representing Python files to sort.

    Returns:
        List[Path]: Sorted list of Python files by dependency, least dependent first.
    """
    # Step 1: Parse each file and extract dependencies
    dependencies: defaultdict[str, dict[str, None]] = defaultdict(dict)
    for modname, file in zip(modnames, files):
        try:
            with file.open("r", encoding="utf-8") as f:
                module_ast = ast.parse(f.read(), filename=str(file))
        except SyntaxError:
            # Handle syntax errors in the files gracefully
            warnings.warn(f"SyntaxError: Unable to parse file {file}")
            continue
        for node in ast.walk(module_ast):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    dependencies[modname][alias.name] = None
            elif isinstance(node, ast.ImportFrom):
                base = _import_base(node, modname, file)
                if not base or base == "__future__":
                    continue
                dependencies[modname][base] = None
                for alias in node.names:
                    # `from pkg import sub` may import the submodule
                    dependencies[modname][f"{base}.{alias.name}"] = None

    # Step 2: Perform topological sorting based on dependencies
    sorted_names: list[str] = []
    visited: set[str] = set()

    def dfs(modname: str):
        if modname in visited:
            return
        visited.add(modname)
        for dep in dependencies[modname]:
            dfs(dep)
        sorted_names.append(modname)

    for modname in modnames:
        dfs(modname)

    # Map sorted module names back to files
    by_name: defaultdict[str, list[Path]] = defaultdict(list)
    for file, modname in zip(files, modnames):
        by_name[modname].append(file)
    for modname in sorted_names:
        yield from by_name.get(modname, ())


def _main_module_for(modfullname: str) -> ModuleType | None:
    """Return `__main__` if it is the script/module named `modfullname`."""
    main = sys.modules.get("__main__")
    main_file = getattr(main, "__file__", None)
    if main is None or not main_file:
        return None
    main_spec = getattr(main, "__spec__", None)
    if main_spec is not None and main_spec.name == modfullname:
        return main
    try:
        spec = importlib.util.find_spec(modfullname)
    except (ImportError, ValueError, AttributeError):
        return None
    origin = spec.origin if spec else None
    if origin and os.path.exists(origin) and os.path.exists(main_file):
        if os.path.samefile(origin, main_file):
            return main
    return None


def smart_import(
    modfullname: str, resolver: PathConverter | None = None
) -> ModuleType:
    """
    Smart import function that avoids duplicate imports by leveraging sys.modules.

    Args:
        modfullname (str): Full module name to import.
        resolver (Callable[[Path], str] | None): Unused, kept for backwards compatibility.

    Returns:
        ModuleType: Imported module.
    """
    _ = resolver
    if modfullname in sys.modules:
        return sys.modules[modfullname]
    if (main := _main_module_for(modfullname)) is not None:
        return main
    return importlib.import_module(modfullname)
