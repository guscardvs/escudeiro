from typing import Self

from escudeiro_pyrs import url

from escudeiro.url.mixins import Wrapped


class Netloc(Wrapped[url.Netloc]):
    def __init__(self, netloc: str) -> None:
        super().__init__(url.Netloc(netloc))

    @property
    def username(self) -> str | None:
        return self._internal.username

    @property
    def password(self) -> str | None:
        return self._internal.password

    @property
    def port(self) -> int | None:
        return self._internal.port

    @port.setter
    def port(self, port: int) -> None:
        self._internal.port = port

    @property
    def host(self) -> str:
        return self._internal.host

    def encode(self) -> str:
        return self._internal.encode()

    def parse(self, netloc: str) -> Self:
        self._internal.parse(netloc)
        return self

    def set(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> Self:
        self._internal.set(host, port, username, password)
        return self

    def merge(self, other: Self) -> Self:
        new_instance = object.__new__(type(self))
        new_instance._internal = self._internal.merge(other._internal)
        return new_instance

    def merge_left(self, other: Self) -> Self:
        new_instance = object.__new__(type(self))
        new_instance._internal = self._internal.merge_left(other._internal)
        return new_instance

    def merge_inplace(self, other: Self) -> Self:
        self._internal.merge_inplace(other._internal)
        return self

    @classmethod
    def from_args(
        cls,
        host: str,
        username: str | None = None,
        password: str | None = None,
        port: int | None = None,
    ) -> Self:
        self = object.__new__(cls)
        self._internal = url.Netloc.from_args(
            host=host, port=port, username=username, password=password
        )
        return self

    def copy(self) -> Self:
        new_instance = object.__new__(type(self))
        new_instance._internal = self._internal.copy()
        return new_instance
