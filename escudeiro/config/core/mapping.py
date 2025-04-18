import os
from collections.abc import Iterator, MutableMapping
from typing import override

from escudeiro.data import data, field
from escudeiro.exc import KeyAlreadyRead


@data
class EnvMapping(MutableMapping[str, str]):
    mapping: MutableMapping[str, str] = os.environ
    already_read: set[str] = field(default_factory=set)

    @override
    def __getitem__(self, key: str, /) -> str:
        val = self.mapping[key]
        self.already_read.add(key)
        return val

    @override
    def __setitem__(self, key: str, value: str, /) -> None:
        if key in self.already_read:
            raise KeyAlreadyRead(f"{key} already read, cannot change its value")
        self.mapping[key] = value

    @override
    def __delitem__(self, key: str, /) -> None:
        if key in self.already_read:
            raise KeyAlreadyRead(f"{key} already read, cannot delete it")
        del self.mapping[key]

    @override
    def __iter__(self) -> Iterator[str]:
        yield from self.mapping

    @override
    def __len__(self) -> int:
        return len(self.mapping)


DEFAULT_MAPPING = EnvMapping()
