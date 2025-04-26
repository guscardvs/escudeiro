from collections.abc import Hashable
from types import GenericAlias, UnionType
from typing import Annotated, Any, TypeAliasType, get_args, get_origin

from typing_extensions import TypeIs

from escudeiro.misc.iterx import flatten


def is_hashable(annotation: Any) -> TypeIs[Hashable]:
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
            if isinstance(current, GenericAlias | UnionType):
                stack.extend(flatten((origin, *get_args(current))))
            elif origin is Annotated:  # pyright: ignore[reportUnnecessaryComparison]
                stack.extend(flatten((get_args(current)[0],)))
        elif current not in (Ellipsis, None) and (
            not isinstance(current, type) or not issubclass(current, Hashable)
        ):
            return False
        cache.add(current)
    return True
