from typing import Self

from escudeiro.escudeiro_pyrs import url
from escudeiro.url.mixins import Wrapped


class Netloc(Wrapped[url.Netloc]):
    def __init__(self, netloc: str) -> None:
        super().__init__(url.Netloc(netloc))

    @property
    def username(self) -> str | None:
        return self.internal.username

    @property
    def password(self) -> str | None:
        return self.internal.password

    @property
    def port(self) -> int | None:
        return self.internal.port

    @port.setter
    def port(self, port: int) -> None:
        self.internal.port = port

    @property
    def host(self) -> str:
        return self.internal.host

    def encode(self) -> str:
        return self.internal.encode()

    def parse(self, netloc: str) -> Self:
        self.internal.parse(netloc)
        return self

    def set(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> Self:
        self.internal.set(host, port, username, password)
        return self

    def merge(self, other: Self) -> Self:
        new_instance = object.__new__(type(self))
        new_instance.internal = self.internal.merge(other.internal)
        return new_instance

    def merge_left(self, other: Self) -> Self:
        new_instance = object.__new__(type(self))
        new_instance.internal = self.internal.merge_left(other.internal)
        return new_instance

    def merge_inplace(self, other: Self) -> Self:
        self.internal.merge_inplace(other.internal)
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
        self.internal = url.Netloc.from_args(
            host=host, port=port, username=username, password=password
        )
        return self

    def copy(self) -> Self:
        new_instance = object.__new__(type(self))
        new_instance.internal = self.internal.copy()
        return new_instance
