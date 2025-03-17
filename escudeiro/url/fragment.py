from typing import Self

from escudeiro_pyrs import url

from escudeiro.url.mixins import Wrapped


class Fragment(Wrapped[url.Fragment]):
    def __init__(self, fragment_str: str) -> None:
        super().__init__(url.Fragment(fragment_str))

    def encode(self) -> str:
        return self._internal.encode()

    def set(self, fragment_str: str) -> Self:
        self._internal.set(fragment_str)
        return self

    def copy(self) -> Self:
        fragment = object.__new__(type(self))
        fragment._internal = self._internal.copy()
        return fragment
