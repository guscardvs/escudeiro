from collections.abc import Callable
from enum import Enum
from typing import Any, Protocol

from escudeiro.data import data, private
from escudeiro.exc.errors import AlreadySet, MissingName
from escudeiro.misc import to_snake


@data(frozen=False)
class Registry[T: Enum, S]:
    """A generic registry that maps enum keys to values.
    This registry allows for registering values with enum keys, validating
    that all enum keys are present, and looking up values by their keys.
    It can be used with any enum type and any value type, including callables.
    Args:
        T (Enum): The enum type to use as keys in the registry.
        S: The type of values to be stored in the registry.
    Attributes:
        with_enum (type[T]): The enum type used for keys.
        registry (dict[T, S]): A dictionary mapping enum keys to values.
    Methods:
        register(key: T, value: S) -> S: Registers a value with a key.
        validate() -> None: Validates that all enum keys are present in the registry.
        lookup(key: T) -> S: Looks up a value by its key.
        __getitem__(key: T) -> S: Allows dictionary-like access to the registry.
        __iter__() -> Iterator[str]: Iterates over the registry keys.
        __len__() -> int: Returns the number of items in the registry.
    """

    with_enum: type[T]
    registry: dict[T, S] = private(initial_factory=dict)

    def register(self, key: T, value: S) -> S:
        if key in self.registry:
            raise AlreadySet(f"Key '{key.value}' is already registered.")
        self.registry[key] = value
        return value

    def validate(self):
        """Validates the keys in the registry are exhaustive."""

        missing_keys = set(self.with_enum).difference(self.registry)
        if missing_keys:
            raise MissingName(
                f"Missing keys in registry: {', '.join(map(str, missing_keys))}"
            )

    def lookup(self, key: T) -> S:
        """Looks up a value by key."""
        if key not in self.registry:
            raise MissingName(f"Key '{key.value}' not found in registry.")
        return self.registry[key]

    def __getitem__(self, key: T) -> S:
        """Allows for dictionary-like access."""
        return self.lookup(key)

    def __iter__(self):
        """Iterates over the registry keys."""
        return iter(map(str, self.registry))

    def __len__(self):
        """Returns the number of items in the registry."""
        return len(self.registry)


@data(frozen=False)
class CallableRegistry[T: Enum, S: Callable](Registry[T, S]):
    """A registry for callables that maps enum keys to callable values.
    This registry allows for registering functions with enum keys, validating
    that all enum keys are present, and looking up functions by their keys.
    Args:
        T (Enum): The enum type to use as keys in the registry.
        S: The type of callable values to be stored in the registry.
    Attributes:
        with_enum (type[T]): The enum type used for keys.
        registry (dict[T, S]): A dictionary mapping enum keys to callable values.
        prefix (str): A prefix to be added to the function names when registering.
        use_enum_name_as_prefix (bool): Whether to use the enum name as a prefix.
    Methods:
        register(key: T, value: S) -> S: Registers a callable with a key.
        validate() -> None: Validates that all enum keys are present in the registry.
        lookup(key: T) -> S: Looks up a callable by its key.
        __getitem__(key: T) -> S: Allows dictionary-like access to the registry.
        __iter__() -> Iterator[str]: Iterates over the registry keys.
        __len__() -> int: Returns the number of items in the registry.
    """

    prefix: str = ""
    use_enum_name_as_prefix: bool = True

    def __post_init__(self):
        if self.use_enum_name_as_prefix and not self.prefix:
            self.prefix = to_snake(self.with_enum.__name__) + "_"

    def __call__(self, func: S) -> S:
        return self.register(
            self.with_enum(func.__name__.removeprefix(self.prefix)), func
        )


class Transformer[T](Protocol):
    def __call__(self, value: Any) -> T: ...


@data(frozen=False)
class TransformRegistry:
    registry: dict[type, Transformer] = private(initial_factory=dict)

    def register[T](self, cls: type[T], transformer: Transformer[T]) -> None:
        if cls in self.registry:
            raise AlreadySet(
                f"Transformer for {cls.__name__} is already registered."
            )
        self.registry[cls] = transformer

    def lookup[T](self, cls: type[T]) -> Transformer[T]:
        if cls not in self.registry:
            raise MissingName(f"No transformer registered for {cls.__name__}.")
        return self.registry[cls]

    def require[T](
        self, cls: type[T], transformer_factory: Callable[[], Transformer[T]]
    ) -> Transformer[T]:
        if cls not in self.registry:
            self.register(cls, transformer_factory())
        return self.registry[cls]

    def __getitem__[T](self, cls: type[T]) -> Transformer[T]:
        return self.lookup(cls)
