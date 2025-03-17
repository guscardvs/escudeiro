from __future__ import annotations

from typing import Final, Protocol, Self, override


class Wrappable(Protocol):
    def compare(self, other: Self) -> bool: ...
    def encode(self) -> str: ...


class Wrapped[T: Wrappable]:
    __slots__: Final[tuple[str, ...]] = ("_internal",)

    def __init__(self, internal: T) -> None:
        self._internal: T = internal

    def set_internal(self, internal: T) -> None:
        self._internal = internal

    def get_internal(self) -> T:
        return self._internal

    @classmethod
    def from_internal(cls, internal: T) -> Self:
        self = object.__new__(cls)
        self._internal = internal
        return self

    @override
    def __eq__(self, other: Self | T | str | object) -> bool:
        if self is other:
            return True
        if isinstance(other, str):
            return self._internal.encode() == other
        if isinstance(other, type(self)):
            return self._internal.compare(other.get_internal())
        return False

    @override
    def __str__(self):
        return self._internal.encode()

    @override
    def __repr__(self):
        return f"{self.__class__.__name__}({self._internal!r})"
