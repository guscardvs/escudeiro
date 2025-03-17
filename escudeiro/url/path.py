import pathlib
from collections.abc import Collection
from typing import Self

from escudeiro_pyrs import url

from escudeiro.url.mixins import Wrapped


class Path(Wrapped[url.Path]):
    def __init__(self, pathstr: str) -> None:
        super().__init__(url.Path(pathstr))

    def encode(self) -> str:
        return self._internal.encode()

    def add(self, path: str | pathlib.Path) -> Self:
        if isinstance(path, str):
            self._internal.add(path)
        else:
            self._internal.add_path(path)
        return self

    def set(self, path: str | pathlib.Path) -> Self:
        self._internal.clear()
        return self.add(path)

    @property
    def isdir(self) -> bool:
        return self._internal.is_dir()

    @property
    def isfile(self) -> bool:
        return not self.isdir

    def normalize(self) -> Self:
        self._internal.normalize()
        return self

    def copy(self) -> Self:
        instance = object.__new__(type(self))
        instance._internal = self._internal.copy()
        return instance

    @property
    def segments(self) -> Collection[str]:
        return self._internal.segments
