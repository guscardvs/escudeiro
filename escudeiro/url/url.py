from collections.abc import Mapping
from typing import Self

from escudeiro.escudeiro_pyrs import url
from escudeiro.url.fragment import Fragment
from escudeiro.url.mixins import Wrapped
from escudeiro.url.netloc import Netloc
from escudeiro.url.path import Path
from escudeiro.url.query import Query


class URL(Wrapped[url.URL]):
    def __init__(self, val: str) -> None:
        super().__init__(url.URL(val))

    @property
    def scheme(self) -> str:
        return self.internal.scheme

    @scheme.setter
    def scheme(self, val: str) -> None:
        self.internal.scheme = val

    @property
    def netloc(self) -> Netloc:
        return Netloc.from_internal(self.internal.netloc)

    @netloc.setter
    def netloc(self, val: Netloc) -> None:
        self.internal.netloc = val.internal

    @property
    def path(self) -> Path:
        return Path.from_internal(self.internal.path)

    @path.setter
    def path(self, val: Path) -> None:
        self.internal.path = val.internal

    @property
    def query(self) -> Query:
        return Query.from_internal(self.internal.query)

    @query.setter
    def query(self, val: Query) -> None:
        self.internal.query = val.internal

    @property
    def fragment(self) -> Fragment:
        return Fragment.from_internal(self.internal.fragment)

    @fragment.setter
    def fragment(self, val: Fragment) -> None:
        self.internal.fragment = val.internal

    def copy(self) -> Self:
        new_instance = object.__new__(type(self))
        new_instance.internal = self.internal.copy()
        return new_instance

    def add(
        self,
        path: str | None = None,
        query: Mapping[str, str] | None = None,
        fragment: str | None = None,
        netloc: str | None = None,
        netloc_obj: Netloc | None = None,
        scheme: str | None = None,
    ) -> Self:
        self.internal.add(
            path,
            query,
            fragment,
            netloc,
            netloc_obj and netloc_obj.internal,
            scheme,
        )
        return self

    def set(
        self,
        path: str | None = None,
        query: Mapping[str, str] | None = None,
        fragment: str | None = None,
        netloc: str | None = None,
        netloc_obj: Netloc | None = None,
        scheme: str | None = None,
    ) -> Self:
        self.internal.set(
            path,
            query,
            fragment,
            netloc,
            netloc_obj and netloc_obj.internal,
            scheme,
        )
        return self

    @classmethod
    def from_netloc(
        cls,
        netloc: Netloc | None = None,
        username: str | None = None,
        password: str | None = None,
        host: str | None = None,
        port: int | None = None,
    ) -> Self:
        return cls.from_internal(
            url.URL.from_netloc(
                netloc and netloc.internal, username, password, host, port
            )
        )

    @classmethod
    def from_args(
        cls,
        path: str | None = None,
        query: Mapping[str, str] | None = None,
        fragment: str | None = None,
        netloc: str | None = None,
        netloc_obj: Netloc | None = None,
        scheme: str | None = None,
    ) -> Self:
        return cls.from_internal(
            url.URL.from_args(
                path,
                query,
                fragment,
                netloc,
                netloc_obj and netloc_obj.internal,
                scheme,
            )
        )

    def encode(self, append_empty_equal: bool = True) -> str:
        return self.internal.encode(append_empty_equal)

    def copy_add(
        self,
        path: str | None = None,
        query: Mapping[str, str] | None = None,
        fragment: str | None = None,
        netloc: str | None = None,
        netloc_obj: Netloc | None = None,
        scheme: str | None = None,
    ) -> Self:
        return self.copy().add(
            path,
            query,
            fragment,
            netloc,
            netloc_obj,
            scheme,
        )

    def copy_set(
        self,
        path: str | None = None,
        query: Mapping[str, str] | None = None,
        fragment: str | None = None,
        netloc: str | None = None,
        netloc_obj: Netloc | None = None,
        scheme: str | None = None,
    ) -> Self:
        return self.copy().set(
            path,
            query,
            fragment,
            netloc,
            netloc_obj,
            scheme,
        )
