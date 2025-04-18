import ast
import os
import re
from collections.abc import Callable, Iterable, Iterator, Sequence
from io import BytesIO
from pathlib import Path
from token import COMMENT
from tokenize import TokenError, tokenize
from typing import Any, Literal

from escudeiro.data import data
from escudeiro.misc import filter_isinstance, lazymethod

from .base import (
    AutoDiscoveryHelper,
    PathConverter,
    StrOrPath,
    smart_import,
    sort_files_by_dependency,
)

type CacheMap = dict[str, Any]
type ModName = str
type ObjectName = str
type Contents = str
type WantsToReturn = bool | None
type Validator = Callable[
    [CacheMap, Contents, ModName], Iterator[tuple[ObjectName, WantsToReturn]]
]


@data(frozen=False)
class StaticAutoDiscovery:
    """
    Performs static analysis to discover and load modules based on predefined criteria.

    This class facilitates the discovery of modules within a specified directory (`root`) or its
    subdirectories (`look_on`), applying static analysis techniques to identify and load modules
    that meet the criteria defined by the provided validator function.

    Attributes:
        _internal (AutoDiscoveryHelper): Helper instance for managing directory traversal and path conversion.
        _validator (Validator): Function to validate modules based on cached information and contents.
        _rounds (int): Number of rounds for discovery, limiting the depth of exploration in the directory structure.
        _cache (CacheMap): Dictionary to store discovered module objects for reuse and reference.

    Methods:
        load() -> Iterable[tuple[str, Any]]:
            Lazily loads modules that pass the validation criteria defined by `_validator`.

        load_asdict() -> dict[str, Any]:
            Loads discovered modules into a dictionary format.

    Example Usage:
        validator = static.instance_of(MyBaseClass)
        discovery = StaticAutoDiscovery(
            validator,
            root=Path("/path/to/directory"),
            exclude=["excluded_module.py"],
            exts=["py"],
            rounds=2
        )
        for name, obj in discovery.load():
            print(f"Loaded module: {name}")
    """

    _validator: Validator
    _internal: AutoDiscoveryHelper
    _rounds: int
    _cache: CacheMap
    _returned: dict[str, bool]

    def __init__(
        self,
        validator: Validator,
        root: Path,
        look_on: Path | None = None,
        exclude: Sequence[StrOrPath] = (),
        exts: Sequence[str] = (),
        converter: PathConverter = Path.as_posix,
        rounds: int = 1,
        include: Sequence[StrOrPath] = (),
    ):
        self._validator = validator
        self._rounds = rounds
        self._internal = AutoDiscoveryHelper(
            root,
            look_on,
            exclude,
            exts,
            converter,
            include,
        )
        self._cache = {}
        self._returned = {}

    @lazymethod
    def load(self) -> Iterable[tuple[str, Any]]:
        """
        Lazily loads modules from the target directory based on validation criteria.

        Returns:
            Iterable[tuple[str, Any]]: Generator yielding tuples of module names and their corresponding objects.
        """
        for _ in range(self._rounds):
            files = list(self._internal.iterdir(self._internal.target_path))
            for path in sort_files_by_dependency(
                [os.path.splitext(item)[0] for item in files], files
            ):
                module = self._parse_module(path)
                resolver = self._internal.get_resolver()
                modname = resolver(path)
                for name, wants in self._validator(
                    self._cache, module, modname
                ):
                    for item in self._import_module([name], path):
                        if wants in (True, None):
                            self._returned[name] = True
                            yield item

    def __iter__(self):
        yield from self.load()

    def load_asdict(self) -> dict[str, Any]:
        return dict(self.load())

    def _parse_module(self, path: Path) -> str:
        """
        Parses the contents of a module file.

        Args:
            path (Path): Path to the module file.

        Returns:
            str: Contents of the module as a string.
        """
        with path.open("r", encoding="utf-8") as stream:
            return stream.read()

    def _import_module(
        self, names: Sequence[str], path: Path
    ) -> Iterable[tuple[str, Any]]:
        """
        Imports specific modules identified by `names` from a given `path`.

        Args:
            names (Sequence[str]): Names of modules to import.
            path (Path): Path to the module file.

        Yields:
            Iterable[tuple[str, Any]]: Generator yielding tuples of imported module names and their corresponding objects.
        """
        names = [item for item in names if not self._returned.get(item)]
        resolver = self._internal.get_resolver()
        modname = resolver(path)
        mod = smart_import(modname, resolver)
        if any(name == modname for name in names):
            yield modname, mod
        for vname, obj in mod.__dict__.items():
            if vname in names:
                self._cache[vname] = obj
                yield vname, obj


class NOT_FOUND:
    """
    Placeholder class to indicate that a requested module or object was not found.
    """

    pass


def static_autoload_validator(comment: str = "# static: autoload"):
    """
    Returns a function to validate modules containing a specific autoload comment.

    Args:
        comment (str, optional): The comment string to search for in module contents. Defaults to "# static: autoload".

    Returns:
        Callable[[CacheMap, str, str], Iterator[str]]: Function that yields module names containing the specified comment.
    """

    def check(
        cachemap: CacheMap, module_contents: str, modname: str
    ) -> Iterator[tuple[ObjectName, WantsToReturn]]:
        _ = cachemap
        contents = BytesIO(module_contents.encode("utf-8"))
        try:
            return next(
                (
                    iter(((modname, True),))
                    for item in tokenize(contents.readline)
                    if item.type == COMMENT and comment in item.string
                ),
                iter(()),
            )
        except TokenError:
            return iter(())

    return check


def static_child_of(*bases: type) -> Validator:
    """
    Returns a function to check if a class is a child of specified base classes using AST analysis.

    Args:
        *bases (type): Variable-length argument list of base class types to check against.

    Returns:
        Callable[[CacheMap, str, str], Iterator[str]]: Function that yields class names that are children of specified base classes.
    """

    def check(
        cachemap: CacheMap, module_contents: str, modname: str
    ) -> Iterator[tuple[ObjectName, WantsToReturn]]:
        try:
            module_ast = ast.parse(module_contents, filename=modname)
        except SyntaxError:
            return None

        for node in ast.walk(module_ast):
            possible_bases = set(base.__name__ for base in bases) | set(
                cachemap.keys()
            )
            if isinstance(node, ast.ClassDef):
                class_name = node.name

                # Skip if the class matches any of the base classes themselves
                if any(
                    modname == base.__module__ and class_name == base.__name__
                    for base in bases
                ):
                    continue

                curbases = [
                    base.id for base in node.bases if isinstance(base, ast.Name)
                ]

                # Check if any base class in the class definition matches the criteria
                if any(item in curbases for item in possible_bases):
                    yield class_name, True

    return check


def static_instance_of(
    *bases: type,
) -> Validator:
    return static_chain_validate(
        "last",
        static_child_of(*bases),
        _static_instance_of(*bases),
    )


def _static_instance_of(
    *bases: type,
) -> Validator:
    """
    Returns a function to validate instances of specified types using AST analysis.

    Args:
        *bases (type): Variable-length argument list of types to validate against.

    Returns:
        Callable[[CacheMap, str, str], Iterator[str]]: Function that yields names of instances
        that match the specified types.
    """

    def check(
        cachemap: CacheMap, module_contents: str, modname: str
    ) -> Iterator[tuple[ObjectName, WantsToReturn]]:
        try:
            module_ast = ast.parse(module_contents, filename=modname)
        except SyntaxError:
            return None

        for node in filter_isinstance(ast.Assign, ast.walk(module_ast)):
            possible_bases = set(base.__name__ for base in bases) | {
                name
                for name, item in cachemap.items()
                if isinstance(item, type)
            }
            walked = list(ast.walk(node.value))
            tuple_assign = next(
                filter_isinstance(ast.Tuple, walked),
                None,
            )
            if tuple_assign is not None:
                for idx, item in enumerate(tuple_assign.elts):
                    if isinstance(item, ast.Call):
                        name = next(
                            filter_isinstance(ast.Name, ast.walk(item)), None
                        )
                        if name and name.id in possible_bases:
                            tuple_target = next(
                                filter_isinstance(ast.Tuple, node.targets), None
                            )
                            if tuple_target is None:
                                return

                            if len(tuple_target.elts) == 1 and isinstance(
                                item_name := node.targets[0], ast.Name
                            ):
                                yield (item_name.id, True)
                            elif idx < len(tuple_target.elts) and isinstance(
                                item_name := tuple_target.elts[idx], ast.Name
                            ):
                                yield (item_name.id, True)

            else:
                next_call = next(
                    filter_isinstance(ast.Call, walked),
                    None,
                )
                if next_call is None:
                    continue
                name = next(
                    filter_isinstance(ast.Name, ast.walk(next_call.func)), None
                )
                if not name:
                    continue
                if name.id in possible_bases:
                    target = next(
                        filter_isinstance(
                            ast.Name,
                            (
                                node
                                for target in node.targets
                                for node in ast.walk(target)
                            ),
                        ),
                        None,
                    )
                    if target is not None:
                        yield target.id, True

    return check


def static_chain_validate(
    mode: Literal["any", "last"], *validators: Validator
) -> Validator:
    """
    Chains multiple validators into a single function with specified validation mode.

    Args:
        mode (Literal['any', 'last']): Mode specifying whether 'any' or 'last' validators must pass.
        *validators (Validator): Variable-length argument list of validator functions.

    Returns:
        Validator: Composite validator function that applies validators based on the mode.
    """

    if mode not in ("any", "last"):
        raise ValueError(f"Invalid mode '{mode}'. Expected 'any' or 'all'.")  # pyright: ignore[reportUnreachable]

    def composite_validator(
        cachemap: CacheMap, module_contents: str, modname: str
    ) -> Iterator[tuple[ObjectName, WantsToReturn]]:
        if mode == "any":
            for validator in validators:
                result = validator(cachemap, module_contents, modname)
                for item, wants in result:
                    yield (item, True if wants is None else wants)
            return None
        elif mode == "last":
            for validator in validators[:-1]:
                for item, _ in validator(cachemap, module_contents, modname):
                    yield (item, False)
            yield from validators[-1](cachemap, module_contents, modname)

    return composite_validator


def static_modulename_validator(
    module_name_filter: str | re.Pattern,
) -> Validator:
    """
    Returns a validator function that acts as a no-operation (noop) validator
    for modules matching the specified name filter.

    Args:
        module_name_filter (str): Filter to match module names (e.g., 'models.py' or 'models/').

    Returns:
        Validator: Validator function that returns an empty iterator for modules matching the filter.
    """

    def validate_module(
        cachemap: CacheMap, module_contents: str, modname: str
    ) -> Iterator[tuple[ObjectName, WantsToReturn]]:
        _ = cachemap, module_contents
        # Check if the module name matches the filter
        if re.search(module_name_filter, modname):
            return iter(
                [(modname, True)]
            )  # Return an empty iterator if module matches filter
        else:
            # Return None if module doesn't match the filter (no validation performed)
            return iter([])

    return validate_module
