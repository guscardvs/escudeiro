from collections.abc import Generator, Sequence
from typing import Any, override

from escudeiro.config.adapter.interface import FieldResolverStrategy
from escudeiro.config.interface import MISSING
from escudeiro.data import data, get_fields
from escudeiro.data.field_ import Field
from escudeiro.data.utils.typedef import MISSING as NOTHING


@data
class SquireResolverStrategy(FieldResolverStrategy[Field]):
    field: Field

    @override
    def cast(self) -> type:
        return self.field.declared_type

    @override
    def names(self) -> Sequence[str]:
        return self.field.name, self.field.alias

    @override
    def init_name(self) -> str:
        return self.field.alias or self.field.name

    @override
    def default(self) -> Any | type[MISSING]:
        default = self.field.default
        if default is NOTHING:
            return MISSING
        return default() if self.field.has_default_factory else default

    @override
    @classmethod
    def iterfield(cls, config_class: type) -> Generator[Field, Any, Any]:
        _ = cls
        yield from get_fields(config_class).values()
