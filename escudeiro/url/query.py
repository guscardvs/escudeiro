from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import Self

from escudeiro.escudeiro_pyrs import url
from escudeiro.url.mixins import Wrapped


class Query(Wrapped[url.Query]):
    def __init__(self, querystr: str) -> None:
        super().__init__(url.Query(querystr))

    def add(
        self, args: Mapping[str, str] | None = None, /, **params: str
    ) -> Self:
        if args:
            self.internal.add_map(args)
        if params:
            self.internal.add_map(params)
        return self

    def set(
        self, args: Mapping[str, str] | None = None, /, **params: str
    ) -> Self:
        if args:
            self.internal.set_map(args)
        if params:
            self.internal.set_map(params)
        return self

    def copy(self) -> Self:
        query = object.__new__(type(self))
        query.internal = self.internal.copy()
        return query

    def encode(self) -> str:
        return self.internal.encode()

    def omit_empty_equal(self) -> str:
        return self.internal.omit_empty_equal()

    def sort(self) -> Self:
        self.internal.sort()
        return self

    def first(self) -> Mapping[str, str]:
        return self.internal.first()

    @property
    def params(self) -> Mapping[str, Collection[str]]:
        return self.internal.params

    def __setitem__(self, key: str, value: str) -> None:
        _ = self.add({key: value})

    def __getitem__(self, key: str) -> Collection[str]:
        return self.params[key]

    def remove(self, *keys: str) -> Self:
        for key in keys:
            self.internal.remove(key)
        return self
