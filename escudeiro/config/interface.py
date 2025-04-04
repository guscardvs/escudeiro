from collections.abc import Callable
from typing import Any, Protocol, overload


class MISSING:
    pass


def default_cast(a: Any):
    return a


class ConfigLike(Protocol):
    def get(
        self,
        name: str,
        cast: Callable = default_cast,
        default: Any | type[MISSING] = MISSING,
    ) -> Any: ...

    @overload
    def __call__[T](
        self,
        name: str,
        cast: Callable[[Any], T] | type[T] = default_cast,
        default: type[MISSING] = MISSING,
    ) -> T: ...

    @overload
    def __call__[T](
        self,
        name: str,
        cast: Callable[[Any], T] | type[T] = default_cast,
        default: T = ...,
    ) -> T: ...

    def __call__[T](
        self,
        name: str,
        cast: Callable[[Any], T] | type[T] = default_cast,
        default: T | type[MISSING] = MISSING,
    ) -> T: ...
