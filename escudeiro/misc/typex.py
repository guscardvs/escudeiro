from collections.abc import Hashable
from types import GenericAlias, UnionType
from typing import (
    Annotated,
    Any,
    ForwardRef,
    Literal,
    TypeAliasType,
    TypeVar,
    Union,  # pyright:ignore[reportDeprecated]
    cast,
    get_args,
    get_origin,
)

from typing_extensions import TypeIs

from escudeiro.misc.iterx import flatten


def is_hashable(
    annotation: Any, *, unresolved_ok: bool = False
) -> TypeIs[Hashable]:
    """Whether values of `annotation` can be hashed.

    `unresolved_ok` treats a ForwardRef/TypeVar (whose real type is not
    known yet) as hashable instead of unhashable."""
    if isinstance(annotation, TypeAliasType):
        annotation = annotation.__value__

    if not isinstance(annotation, GenericAlias) and isinstance(
        annotation, type
    ):
        return issubclass(annotation, Hashable)

    stack: list[GenericAlias | Any] = [annotation]
    cache: set[Any] = set()

    while stack:
        current = stack.pop()
        if current in cache:
            continue

        if origin := get_origin(current):
            if origin is Annotated:  # pyright: ignore[reportUnnecessaryComparison]
                stack.extend(flatten((get_args(current)[0],)))
            elif origin is Literal:
                pass
            elif origin in (Union, UnionType):  # pyright: ignore[reportDeprecated]
                stack.extend(flatten(get_args(current)))
            else:
                stack.extend(flatten((origin, *get_args(current))))
        elif unresolved_ok and isinstance(current, ForwardRef | TypeVar | str):
            pass
        elif current not in (Ellipsis, None) and (
            not isinstance(current, type) or not issubclass(current, Hashable)
        ):
            return False
        cache.add(current)
    return True


def is_instanceexact(obj: Any, annotation: Any) -> bool:
    """Check if `obj` is an instance of `annotation`, considering type aliases and unions.
    If `annotation` is a type alias, it resolves to its value.
    If `annotation` is a union, it checks if `obj` is an instance of any of the types in the union.

    This is different from `isinstance` because it does not consider subclasses.
    For example, `is_instanceexact(1, int)` returns `True`, but `isinstance(1, int)` would also return `True` for subclasses of `int`.
    """
    if isinstance(annotation, TypeAliasType):
        annotation = annotation.__value__

    if isinstance(annotation, UnionType):
        return any(is_instanceexact(obj, arg) for arg in get_args(annotation))
    if isinstance(annotation, GenericAlias):
        annotation = get_origin(annotation) or annotation.__origin__

    return type(obj) is annotation


def cast_notnone[T](value: T | None) -> T:
    return cast(T, value)


def assert_notnone[T](value: T | None) -> T:
    if value is None:
        raise ValueError("Value is None")
    return value
