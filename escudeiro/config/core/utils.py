from collections.abc import Callable
from enum import Enum
from functools import partial
from types import NoneType
from typing import Any, Literal, NamedTuple, TypeVar

from escudeiro.exc import (
    InvalidCast,
    MissingName,
)
from escudeiro.misc.functions import Caster
from escudeiro.misc.pathx import autopath, is_valid_path
from escudeiro.misc.strings import as_boolean, is_none

valid_path = Caster(autopath).with_rule(is_valid_path)


S = TypeVar("S")


LiteralType = type(Literal["Any"])


class ArgTuple(NamedTuple):
    arg: str
    cast: type


@partial(Caster.isinstance_or_cast, NoneType)
def null_cast(val: str):
    if not is_none(val):
        raise InvalidCast("Null values should match ('null', 'none', '')")
    return None


_cast_map: dict[Callable, Callable[[str], Any]] = {
    str: str,
    bool: Caster(as_boolean).strict,
    int: int,
    bytes: str.encode,
    NoneType: null_cast,
}


def _try_cast(cast: type, val: str) -> Any:
    caster = _cast_map.get(cast)
    if caster is None:
        if issubclass(cast, Enum):
            caster = cast
        else:
            raise InvalidCast("Unknown type used for Literal")
    try:
        return caster(val)
    except Exception:
        return val


def literal_cast(literal_decl: Any):
    """
    Converts a value to one of the literals defined in the provided literal declaration.

    Args:
        literal_decl (Any): The literal declaration, typically a `Literal` type annotation.

    Returns:
        Callable[[str], Any]: A casting function that checks if the value matches any of the literals defined
            in the declaration. If a match is found, it returns the value as is. Otherwise, it raises an `InvalidCast`
            exception.

    Raises:
        TypeError: If the provided literal declaration is not an instance of `Literal`.
        InvalidCast: If the value received does not match any argument from the literal declaration.

    Examples:
        >>> literal_cast(Literal["Any"])("Any")
        'Any'
        >>> literal_cast(Literal[1, "two", 3.0])("3.0")
        3.0
        >>> literal_cast(Literal[1, "two", 3.0])("four")
        Traceback (most recent call last):
            ...
        InvalidCast: Value received does not match any argument from literal: (1, 'two', 3.0)
    """
    if not isinstance(literal_decl, LiteralType):
        raise TypeError
    arg_map = tuple(ArgTuple(arg, type(arg)) for arg in literal_decl.__args__)  # pyright: ignore[reportAttributeAccessIssue]

    def _cast(val: str) -> Any:
        for arg, cast in arg_map:
            if _try_cast(cast, val) == arg:
                return arg
        else:
            raise InvalidCast(
                "Value received does not match any argument from literal",
                literal_decl.__args__,  # pyright: ignore[reportAttributeAccessIssue]
            )

    return _cast


def none_is_missing[T, U](
    cast: Callable[[T], U | None],
) -> Callable[[T | None], U]:
    exc_message = f"Expected value to be castable to {cast.__name__}, but returned None instead"

    def _cast(val: T | None) -> U:
        if val is None:
            raise MissingName(exc_message)
        casted = cast(val)
        if casted is None:
            raise MissingName(exc_message)
        return casted

    return _cast
