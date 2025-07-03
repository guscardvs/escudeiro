import dataclasses
from collections.abc import Callable, Collection, Sequence
from types import MemberDescriptorType
from typing import ClassVar, cast, final, get_origin

from .field_ import Field, FieldInfo, default_field_info
from .utils.factory import factory
from .utils.functions import disassemble_type
from .utils.typedef import MISSING


@final
class FieldsBuilder:
    __slots__ = (
        "cls",
        "kw_only",
        "field_names",
        "parent_fields",
        "fields",
        "field_class",
        "dataclass_fields",
        "alias_generator",
    )

    def __init__(
        self,
        cls: type,
        kw_only: bool,
        field_class: type[Field],
        dataclass_fields: bool,
        alias_generator: Callable[[str], str],
    ):
        self.cls = cls
        self.kw_only = kw_only
        self.field_names: set[str] = set()
        self.parent_fields: list[Field] = []
        self.fields: list[Field] = []
        self.field_class = field_class
        self.dataclass_fields = dataclass_fields
        self.alias_generator = alias_generator

    def build(self) -> Sequence[Field]:
        self._add_parent_fields()
        fields = self.parent_fields + self.fields
        _validate_fields_order(fields)
        return fields

    def _add_parent_fields(self):
        unfiltered_parent_fields = []
        for parent in reversed(self.cls.mro()[1:-1]):
            unfiltered_parent_fields.extend(
                field.inherit()
                for field in cast(
                    Sequence[Field],
                    getattr(parent, "__squire_attrs__", {}).values(),
                )
                if field.name not in self.field_names and not field.inherited
            )
        seen = set()
        for field in reversed(unfiltered_parent_fields):
            if field.name in seen:
                continue
            self.parent_fields.insert(0, field)
            seen.add(field.name)
        self.field_names.update(seen)

    def add_field(self, key: str, annotation: type):
        default = getattr(self.cls, key, MISSING)
        if isinstance(default, MemberDescriptorType):
            return self
        info = default_field_info.duplicate(default=default)
        if isinstance(default, FieldInfo):
            info = default
        elif isinstance(default, dataclasses.Field) and self.dataclass_fields:
            info = self._field_from_dc(default)
        field = info.build(
            self.field_class,
            name=key,
            annotation=disassemble_type(annotation),
            alias=info.alias or self.alias_generator(key),
        )
        self.fields.append(field)
        self.field_names.add(field.name)
        return self

    def from_annotations(self):
        if not hasattr(self.cls, "__annotations__"):
            return self
        for key, val in self.cls.__annotations__.items():
            if get_origin(val) is not ClassVar:
                _ = self.add_field(key, val)
        return self

    def _field_from_dc(self, field: dataclasses.Field) -> FieldInfo:
        kwargs: dict = default_field_info.asdict() | {
            "init": field.init,
            "hash": field.hash,
            "eq": field.compare,
            "order": field.compare,
            "repr": field.repr,
        }
        if field.default_factory is not dataclasses.MISSING:
            kwargs["default"] = factory(field.default_factory)
        elif field.default is not dataclasses.MISSING:
            kwargs["default"] = field.default
        else:
            kwargs["default"] = MISSING
        if kw_only := getattr(field, "kw_only", default_field_info.kw_only):
            kwargs["kw_only"] = kw_only
        return FieldInfo(**kwargs)


def _validate_fields_order(fields: Collection[Field]):
    had_default = False
    last_default_field = ""
    for field in fields:
        if field.kw_only:
            continue
        if had_default and field.default is MISSING and field.ref is None:
            raise ValueError(
                f"Non default field {field.name!r}"
                + " after field with default"
                + f" {last_default_field!r} without kw_only flag"
            )
        if not had_default and field.default is not MISSING:
            last_default_field = field.name
            had_default = True
