import inspect
import pathlib
from collections.abc import Callable, Iterable, Iterator, Sequence
from pathlib import Path
from typing import Any

from escudeiro.data import data
from escudeiro.lazyfields import lazyfield

from .base import AutoDiscoveryHelper, PathConverter, StrOrPath, smart_import

type Validator = Callable[[Any], bool]


@data(frozen=False)
class RuntimeAutoDiscovery:
    """
    Facilitates runtime discovery and loading of modules based on a validation function.

    This class enables the discovery and loading of modules within a specified directory (`root`)
    or its subdirectories (`look_on`), leveraging runtime inspection techniques to identify and
    load modules that meet the criteria defined by the provided validator function.

    Attributes:
        _internal (AutoDiscoveryHelper): Helper instance for managing directory traversal and path conversion.
        _validator (Validator): Function to validate modules or objects based on runtime inspection.

    Methods:
        load() -> Iterator[tuple[str, Any]]:
            Lazily loads modules that pass the validation criteria defined by `_validator`.

        load_asdict() -> dict[str, Any]:
            Loads discovered modules into a dictionary format.

    Example Usage:
        validator = lambda obj: inspect.isclass(obj) and issubclass(obj, MyBaseClass)
        discovery = RuntimeAutoDiscovery(
            validator,
            root=pathlib.Path("/path/to/directory"),
            exclude=["excluded_module.py"],
            exts=["py"],
        )
        for name, obj in discovery.load():
            print(f"Loaded module: {name}")
    """

    _validator: Validator
    _internal: AutoDiscoveryHelper

    def __init__(
        self,
        validator: Validator,
        root: pathlib.Path,
        look_on: Path | None = None,
        exclude: Sequence[StrOrPath] = (),
        exts: Sequence[str] = (),
        converter: PathConverter = Path.as_posix,
        include: Sequence[StrOrPath] = (),
    ):
        """
        Iterates over the members of the module specified by the given path.

        Args:
            path (Path): The path to the module to be loaded.

        Yields:
            Iterable[tuple[str, Any]]: An iterable of tuples containing member names
            and their corresponding objects if they pass the validation.
        """
        self._validator = validator
        self._internal = AutoDiscoveryHelper(
            root,
            look_on,
            exclude,
            exts,
            converter,
            include,
        )

    def _itermod(self, path: Path) -> Iterable[tuple[str, Any]]:
        """
        Iterates over the members of the module specified by the given path.

        Args:
            path (Path): The path to the module to be loaded.

        Yields:
            Iterable[tuple[str, Any]]: An iterable of tuples containing member names
            and their corresponding objects if they pass the validation.
        """
        resolver = self._internal.get_resolver()
        mod = smart_import(resolver(path), resolver)

        for name, obj in inspect.getmembers(mod):
            if self._validator(obj):
                yield (name, obj)

    def load(self) -> Iterator[tuple[str, Any]]:
        """
        Lazily loads modules that pass the validation criteria.

        Returns:
            Iterator[tuple[str, Any]]: Iterator yielding tuples of module names and their corresponding objects.
        """
        for file in self._internal.iterdir(self._internal.target_path):
            for name, obj in self._itermod(file):
                if self._validator(obj):
                    yield name, obj

    @lazyfield
    def asdict(self) -> dict[str, Any]:
        """
        Loads discovered modules into a dictionary format.

        Returns:
            dict[str, Any]: Dictionary mapping module names to their corresponding objects.
        """
        return dict(self.load())

    def __iter__(self):
        yield from self.load()


def runtime_child_of(parent_class: type) -> Callable[[Any], bool]:
    """
    Returns a function that checks if an object is a subclass (or instance) of `parent_class`.

    Args:
        parent_class (type): The class or type to check against.

    Returns:
        Callable[[Any], bool]: Function that checks if an object is a subclass or instance of `parent_class`.
    """

    def check(obj: Any) -> bool:
        return isinstance(obj, type) and issubclass(obj, parent_class)

    return check


def runtime_instance_of(*bases: type) -> Callable[[Any], bool]:
    """
    Returns a function that validates instances of specified types in runtime.

    Args:
        *bases (type): Variable-length argument list of types to validate against.

    Returns:
        Callable[[Any], bool]: Function that validates instances of specified types.
    """

    def check(obj: Any) -> bool:
        return isinstance(obj, bases)

    return check


def runtime_contains_attr(attr_name: str) -> Callable[[Any], bool]:
    """
    Returns a function that checks if an object contains an attribute `attr_name`.

    Args:
        attr_name (str): The attribute name to check for.

    Returns:
        Callable[[Any], bool]: Function that checks if an object contains the specified attribute.
    """

    def check(obj: Any) -> bool:
        return hasattr(obj, attr_name)

    return check


def runtime_attr_with_value(
    attr_name: str, attr_value: Any
) -> Callable[[Any], bool]:
    """
    Returns a function that checks if an object has an attribute `attr_name` with a specific `attr_value`.

    Args:
        attr_name (str): The attribute name to check for.
        attr_value (Any): The expected value of the attribute.

    Returns:
        Callable[[Any], bool]: Function that checks if the object has the specified attribute with the specified value.
    """

    def check(obj: Any) -> bool:
        return hasattr(obj, attr_name) and getattr(obj, attr_name) == attr_value

    return check


def runtime_chain_validate_all(*validators: Validator) -> Validator:
    """Combines multiple validator functions into a single validator that checks if all validators pass."""

    def check(obj: Any) -> bool:
        return all(validator(obj) for validator in validators)

    return check


def runtime_chain_validate_any(*validators: Validator) -> Validator:
    """Combines multiple validator functions into a single validator that checks if any validator passes."""

    def check(obj: Any) -> bool:
        return any(validator(obj) for validator in validators)

    return check
