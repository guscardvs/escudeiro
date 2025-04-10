from collections.abc import Generator, Sequence
from dataclasses import MISSING as dc_MISSING
from dataclasses import Field, fields
from typing import Any, cast, override

from escudeiro.config.adapter.interface import FieldResolverStrategy
from escudeiro.config.interface import MISSING
from escudeiro.data import data


@data
class DataclassResolverStrategy(FieldResolverStrategy[Field]):
    field: Field

    @override
    def cast(self) -> type:
        return cast(type, self.field.type)

    @override
    def names(self) -> Sequence[str]:
        return (self.field.name,)

    @override
    def init_name(self) -> str:
        return self.field.name

    @override
    def default(self) -> Any | type[MISSING]:
        if self.field.default not in (None, Ellipsis, dc_MISSING):
            return self.field.default
        return (
            MISSING
            if self.field.default_factory in (None, dc_MISSING)
            else self.field.default_factory
        )

    @override
    @classmethod
    def iterfield(cls, config_class: type) -> Generator[Field, Any, Any]:
        _ = cls
        yield from fields(config_class)
