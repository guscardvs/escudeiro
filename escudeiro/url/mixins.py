from __future__ import annotations

from typing import Protocol, Self, override

from escudeiro.data import data


class Wrappable(Protocol):
    def compare(self, other: Self) -> bool: ...
    def encode(self) -> str: ...


@data(frozen=False)
class Wrapped[T: Wrappable]:
    internal: T

    @classmethod
    def from_internal(cls, internal: T) -> Self:
        self = object.__new__(cls)
        self.internal = internal
        return self

    @override
    def __eq__(self, other: Self | T | str | object) -> bool:
        if self is other:
            return True
        if isinstance(other, str):
            return self.internal.encode() == other
        if isinstance(other, type(self)):
            return self.internal.compare(other.internal)
        return False

    @override
    def __str__(self):
        return self.internal.encode()

    @override
    def __repr__(self):
        return f"{self.__class__.__name__}({self.internal!r})"
