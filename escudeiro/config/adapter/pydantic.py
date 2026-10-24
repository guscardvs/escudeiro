import sys
from collections.abc import Generator, Sequence
from typing import Any, cast, override

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from escudeiro.config.adapter.interface import FieldResolverStrategy
from escudeiro.config.interface import MISSING
from escudeiro.data import data
from escudeiro.lazyfields import lazyfield

if sys.version_info < (3, 14):
    from pydantic import v1


@data
class FieldWrapper:
    name: str
    field_info: FieldInfo


@data
class PydanticResolverStrategy(FieldResolverStrategy[FieldWrapper]):
    field: FieldWrapper

    @lazyfield
    def field_info(self) -> FieldInfo:
        return self.field.field_info

    @override
    def cast(self) -> type:
        return cast(type, self.field_info.annotation)

    @override
    def names(self) -> Sequence[str]:
        return (self.field.name, self.field_info.alias or self.field.name)

    @override
    def init_name(self) -> str:
        return self.field.name

    @override
    def default(self) -> Any | type[MISSING]:
        default = self.field_info.default
        if default is not PydanticUndefined and default is not Ellipsis:
            return default
        if self.field_info.default_factory is not None:
            return self.field_info.default_factory()  # pyright: ignore[reportCallIssue]
        return MISSING

    @override
    @classmethod
    def iterfield(
        cls,
        config_class: "type[BaseModel | v1.BaseModel]",
    ) -> Generator[FieldWrapper, Any, Any]:
        if sys.version_info < (3, 14) and issubclass(
            config_class, v1.BaseModel
        ):
            yield from cls._as_v1_iterfield(config_class)
        else:
            yield from map(
                lambda item: FieldWrapper(*item),
                config_class.model_fields.items(),
            )

    @classmethod
    def _as_v1_iterfield(
        cls, config_class: "type[v1.BaseModel]"
    ) -> Generator[FieldWrapper, Any, Any]:
        for field in config_class.__fields__.values():
            field_info = FieldInfo(
                # outer_type_ drops Optional, the annotation keeps it
                annotation=field.annotation,
                # v1 keeps `None` as the default of required/factory fields
                default=(
                    PydanticUndefined
                    if field.required or field.default_factory
                    else field.default
                ),
                default_factory=field.default_factory,
                alias=field.alias,
            )
            fw = FieldWrapper(field.name, field_info)
            yield fw
