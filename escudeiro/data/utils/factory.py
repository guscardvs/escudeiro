import typing
from collections.abc import Callable
from typing import Self, final

from typing_extensions import TypeIs


@final
class Factory[**P, T]:
    __slots__ = ("func", "_initialized")

    def __new__(cls, func: Callable[P, T]) -> Self:
        if isinstance(func, cls):
            return func

        self = object.__new__(cls)
        return self

    def __init__(self, func: Callable[P, T]) -> None:
        if getattr(self, "_initialized", None):
            return

        self.func = func
        self._initialized = True

    def __name__(self):
        return self.func.__name__

    def __call__(self, *args: P.args, **kwds: P.kwargs) -> T:
        return self.func(*args, **kwds)


def factory[**P, T](func: Callable[P, T]) -> Factory[P, T]:
    return Factory(func)


def is_factory(obj: typing.Any) -> TypeIs[Factory]:
    return isinstance(obj, Factory)
