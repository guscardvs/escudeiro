import pathlib
from collections.abc import Collection
from typing import Self

from escudeiro.escudeiro_pyrs import url
from escudeiro.url.mixins import Wrapped


class Path(Wrapped[url.Path]):
    def __init__(self, pathstr: str) -> None:
        super().__init__(url.Path(pathstr))

    def encode(self) -> str:
        return self.internal.encode()

    def add(self, path: str | pathlib.Path) -> Self:
        if isinstance(path, str):
            self.internal.add(path)
        else:
            self.internal.add_path(path)
        return self

    def set(self, path: str | pathlib.Path) -> Self:
        self.internal.clear()
        return self.add(path)

    @property
    def isdir(self) -> bool:
        return self.internal.is_dir()

    @property
    def isfile(self) -> bool:
        return not self.isdir

    def normalize(self) -> Self:
        self.internal.normalize()
        return self

    def copy(self) -> Self:
        instance = object.__new__(type(self))
        instance.internal = self.internal.copy()
        return instance

    @property
    def segments(self) -> Collection[str]:
        return self.internal.segments
