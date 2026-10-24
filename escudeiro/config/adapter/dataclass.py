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
        default = self.field.default
        if default is not dc_MISSING and default is not Ellipsis:
            return default
        if self.field.default_factory is not dc_MISSING:
            return self.field.default_factory()
        return MISSING

    @override
    @classmethod
    def iterfield(cls, config_class: type) -> Generator[Field, Any, Any]:
        _ = cls
        yield from (item for item in fields(config_class) if item.init)
