from collections.abc import Generator, Sequence
from typing import Any, override

from attr._make import Factory  # pyright: ignore[reportPrivateImportUsage]
from attrs import NOTHING, Attribute, fields

from escudeiro.config.adapter.interface import FieldResolverStrategy
from escudeiro.config.interface import MISSING
from escudeiro.data import data
from escudeiro.exc import InvalidCast
from escudeiro.misc import strings


@data
class AttrsResolverStrategy(FieldResolverStrategy[Attribute]):
    field: Attribute

    @override
    def cast(self) -> type:
        if field_type := self.field.type:
            return field_type
        raise InvalidCast(
            strings.exclamation(f"Field {self.field.name} has no valid type")
        )

    @override
    def names(self) -> Sequence[str]:
        return tuple(
            item
            for item in (self.field.name, self.field.alias)
            if item is not None
        )

    @override
    def init_name(self) -> str:
        return self.field.alias or self.field.name

    @override
    def default(self) -> Any | type[MISSING]:
        default = self.field.default
        if default is None or default in (Ellipsis, NOTHING):
            return MISSING
        return default.factory() if isinstance(default, Factory) else default

    @override
    @classmethod
    def iterfield(cls, config_class: type) -> Generator[Attribute, Any, Any]:
        _ = cls
        yield from fields(config_class)
