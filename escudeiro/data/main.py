import dataclasses
import sys
from collections.abc import Callable, Generator, Mapping, Sequence
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import (
    Any,
    ForwardRef,
    NoReturn,
    Union,  # pyright:ignore[reportDeprecated]
    dataclass_transform,
    get_args,
    overload,
)

from typing_extensions import TypeIs, evaluate_forward_ref

from escudeiro.data.converters import fromdict, squire
from escudeiro.data.schema import (
    DictSchema,
    HasStr,
    HasToString,
    Items,
    ListSchema,
    Schema,
    str_cast,
)
from escudeiro.data.slots import slot
from escudeiro.misc.typex import is_hashable

from .field_ import Field, FieldInfo, field
from .methods import ArgumentType, MethodBuilder, MethodType
from .resolver import FieldsBuilder
from .utils.functions import disassemble_type, indent, remove_left_underscores
from .utils.functions import frozen as freeze
from .utils.typedef import (
    MISSING,
    UNINITIALIZED,
    Descriptor,
    InitOptions,
)

FieldMap = dict[str, Field]


def __dataclass_transform__[T](
    *,
    eq_default: bool,
    order_default: bool,
    kw_only_default: bool,
    frozen_default: bool,
    field_descriptors: tuple[type | Callable[..., Any], ...],
) -> Callable[[T], T]:
    return lambda a: a


@overload
def data[T](
    maybe_cls: None = None,
    /,
    *,
    frozen: bool = True,
    init: bool = True,
    kw_only: bool = False,
    slots: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = True,
    hash: bool | None = None,
    pydantic: bool = False,
    dataclass_fields: bool = False,
    field_class: type[Field] = Field,
    alias_generator: Callable[[str], str] = str,
) -> Callable[[type[T]], type[T]]: ...


@overload
def data[T](
    maybe_cls: type[T],
    /,
    *,
    frozen: bool = True,
    init: bool = True,
    kw_only: bool = False,
    slots: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = True,
    hash: bool | None = None,
    pydantic: bool = False,
    dataclass_fields: bool = False,
    field_class: type[Field] = Field,
    alias_generator: Callable[[str], str] = str,
) -> type[T]: ...


@dataclass_transform(
    order_default=True,
    frozen_default=True,
    kw_only_default=False,
    field_specifiers=(FieldInfo, field),
)
@__dataclass_transform__(  # Support for both formats of dataclass transform
    eq_default=True,
    order_default=True,
    frozen_default=True,
    kw_only_default=False,
    field_descriptors=(FieldInfo, field),
)
def data[T](
    maybe_cls: type[T] | None = None,
    /,
    *,
    frozen: bool = True,
    init: bool = True,
    kw_only: bool = False,
    slots: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = True,
    hash: bool | None = None,
    pydantic: bool = False,
    dataclass_fields: bool = False,
    field_class: type[Field] = Field,
    alias_generator: Callable[[str], str] = str,
) -> Callable[[type[T]], type[T]] | type[T]:
    """
    Decorator function that adds functionality to a data class.

    :param maybe_cls: Optional[type[T]], a type argument that needs to be
    wrapped in the FieldsBuilder.
    :param frozen: bool, whether to create an immutable class or not.
    :param kw_only: bool, whether all params should be kw_only or not.
    :param slots: bool, whether to generate a class using __slots__ or not.
    :param repr: bool, whether to generate a __repr__ method or not.
    :param eq: bool, whether to generate an __eq__ method or not.
    :param order: bool, whether to generate rich comparison methods or not.
    :param hash: bool, whether to generate a __hash__ method or not.
    :param pydantic: bool, whether to generate a __get_validator__ method or
    not to facilitate integration with pydantic.
    :param dataclass_fields: bool, whether to add __dataclass_fields__ with the
    dataclass format. This way, the class becomes a drop-in replacement for dataclasses.
    :param alias_generator: Callable[[str], str], automatic alias using the callable passed
    as parameter.
    **Warning**: dataclass_fields with pydantic=False will fail when trying to use with
    pydantic.

    :return: A callable object that wraps the maybe_cls type argument in a
    class that implements the specified features.
    :rtype: typing.Union[Callable[[type[T]], type[T]], type[T]]
    """

    def wrap(cls: type[T]) -> type[T]:
        fields = (
            FieldsBuilder(
                cls, kw_only, field_class, dataclass_fields, alias_generator
            )
            .from_annotations()
            .build()
        )
        field_map = {field.name: field for field in fields}
        return build_cls(
            cls,
            field_map,
            frozen=frozen,
            kw_only=kw_only,
            slots=slots,
            repr=repr,
            eq=eq,
            order=order,
            hash=hash,
            pydantic=pydantic,
            dataclass_fields=dataclass_fields,
            init=init,
        )

    return wrap(maybe_cls) if maybe_cls is not None else wrap


def build_cls(cls: type, field_map: FieldMap, **opts: Any) -> Any:
    hash = opts["hash"]
    frozen = opts["frozen"]
    slots = opts["slots"]
    clsdict = (
        _get_clsdict(cls, field_map)
        | _get_cls_metadata(cls, opts)
        | _get_init(
            cls,
            field_map,
            {
                "frozen": frozen,
                "slots": slots,
                "init": opts["init"],
            },
        )
        | get_parse_dict(cls, field_map)
        | get_squire_serialize(cls, field_map)
    )

    if slots:
        clsdict |= _get_slots_metadata(cls, field_map)
    if opts["repr"]:
        clsdict |= _get_repr(cls, field_map)
    if opts["eq"]:
        clsdict |= _get_eq(cls, field_map)
        clsdict |= _get_ne(cls)
    if opts["order"]:
        clsdict |= _get_order(cls, field_map)
    if hash or (hash is None and frozen):
        clsdict |= _get_hash(cls, field_map, bool(hash))
    if opts["pydantic"]:
        clsdict |= _get_pydantic_handlers(cls, field_map)
    if opts["dataclass_fields"]:
        clsdict |= _make_dataclass_fields(field_map)
    maybe_freeze = freeze if frozen else lambda a: a
    return maybe_freeze(
        type(cls)(
            cls.__name__,
            cls.__bases__,
            clsdict,
        )
    )


def _get_clsdict(cls: type, field_map: FieldMap):
    return {
        key: value
        for key, value in cls.__dict__.items()
        if key not in (tuple(field_map) + ("__dict__", "__weakref__"))
    } | {"__squire_attrs__": field_map}


def _get_slots_metadata(
    cls: type,
    field_map: FieldMap,
) -> Mapping[str, Any]:
    inherited_slots: dict[str, Any] = {}
    for base_cls in cls.mro()[1:-1]:
        inherited_slots |= {
            name: getattr(base_cls, name)
            for name in getattr(base_cls, "__slots__", ())
        }
    reused_slots = {
        slot: descriptor
        for slot, descriptor in inherited_slots.items()
        if slot in field_map
    }
    slot_names = tuple(
        field for field in field_map if field not in reused_slots
    )
    for value in cls.__dict__.values():
        if (
            _is_descriptor_type(value)
            and value.private_name not in slot_names
            and value.private_name not in inherited_slots
            and value.private_name not in reused_slots
        ):
            slot_names += (value.private_name,)
        if (slots := slot.get_slots(value)) is not None:
            for extra in slots:
                if extra not in slot_names + tuple(reused_slots) + tuple(
                    inherited_slots
                ):
                    slot_names += (extra,)

    return inherited_slots | reused_slots | {"__slots__": tuple(slot_names)}


def _is_descriptor_type(
    obj: Any,
) -> TypeIs[Descriptor]:
    return hasattr(obj, "private_name") and hasattr(obj, "__get__")


def _get_cls_metadata(cls: type, opts: dict[str, Any]):
    return {
        "__qualname__": cls.__qualname__,
        "__source__": cls,
        "__build_opts__": opts,
    }


def _make_setattr(frozen: bool):
    def _setattr(field: str, arg: Any):
        return (
            f"_setattr(self, '{field}', {arg})"
            if frozen
            else f"self.{field} = {arg}"
        )

    return _setattr


def _get_init(cls: type, field_map: FieldMap, opts: InitOptions):
    method_name = "__init__"
    if not opts["init"]:
        method_name = MethodBuilder.make_squire_name(method_name)
    builder = MethodBuilder(
        method_name,
        {
            "attr_dict": field_map,
            "MISSING": MISSING,
            "_setattr": object.__setattr__,
            "UNINITIALIZED": UNINITIALIZED,
        },
    )
    _setattr = _make_setattr(opts["frozen"])
    if hasattr(cls, "__pre_init__"):
        _ = builder.add_scriptline("self.__pre_init__()")
    if not opts["slots"]:
        _ = builder.add_scriptline("_inst_dict = self.__dict__")
    for f in field_map.values():
        field_name = f.name
        arg_name = remove_left_underscores(f.alias)
        if not f.init:
            if f.has_default:
                _ = builder.add_scriptline(
                    _setattr(field_name, f"attr_dict['{field_name}'].default")
                )
            elif f.has_default_factory:
                factory_name = f"__attr_factory_{field_name}"
                _ = builder.add_scriptline(
                    _setattr(field_name, f"{factory_name}()")
                ).add_glob(factory_name, f.default)
            elif f.ref:
                _ = builder.add_scriptline(
                    _setattr(
                        field_name,
                        f"attr_dict['{field_name}'].ref(self)",
                    )
                )
            else:
                _ = builder.add_scriptline(
                    _setattr(field_name, "UNINITIALIZED")
                )
            continue
        if f.has_default:
            arg = f"{arg_name}=attr_dict['{field_name}'].default"

            _ = builder.add_scriptline(_setattr(field_name, arg_name))
        elif f.has_default_factory:
            arg = f"{arg_name}=MISSING"

            init_factory_name = f"__attr_factory_{field_name}"
            for line in (
                f"if {arg_name} is not MISSING:",
                f"    {_setattr(field_name, arg_name)}",
                "else:",
                f"    {_setattr(field_name, f'{init_factory_name}()')}",
            ):
                _ = builder.add_scriptline(line)
            _ = builder.add_glob(init_factory_name, f.default)
        elif f.ref:
            arg = f"{arg_name}=MISSING"
            init_transform_name = f"__attr_transform_{field_name}"
            for line in (
                f"if {arg_name} is not MISSING:",
                f"    {_setattr(field_name, arg_name)}",
                "else:",
                f"    {_setattr(field_name, f'{init_transform_name}(self)')}",
            ):
                _ = builder.add_scriptline(line)
            _ = builder.add_glob(init_transform_name, f.ref)
        else:
            _ = builder.add_scriptline(_setattr(field_name, arg_name))
            arg = arg_name
        _ = builder.add_arg(
            arg,
            ArgumentType.KEYWORD if f.kw_only else ArgumentType.POSITIONAL,
        )
        _ = builder.add_annotation(arg_name, f.declared_type)
    if hasattr(cls, "__post_init__"):
        _ = builder.add_scriptline("self.__post_init__()")
    return builder.build(cls)


def _get_repr(cls: type, field_map: FieldMap):
    fields = []
    globs = {}
    for f in field_map.values():
        if f.repr is False:
            continue
        elif f.repr is True:
            fields.append(f"{f.name}={{self.{f.name}!r}}")
        else:
            field_repr_call = f"__repr_{f.name}"
            globs[field_repr_call] = f.repr
            fields.append(f"{f.name}={{{field_repr_call}(self.{f.name})!r}}")
    fieldstr = ", ".join(fields)
    returnline = f"return f'{cls.__name__}({fieldstr})'"
    return (
        MethodBuilder("__repr__", globs)
        .add_annotation("return", str)
        .add_scriptline(returnline)
        .build(cls)
    )


_othername = "other"


def _get_eq(cls: type, field_map: FieldMap):
    fields_to_compare = {
        name: f for name, f in field_map.items() if f.eq is not False
    }
    builder = MethodBuilder("__eq__").add_arg(
        _othername, ArgumentType.POSITIONAL
    )
    if fields_to_compare:
        return _build_field_comparison(builder, fields_to_compare, cls)
    returnline = "return _object_eq(self, other)"
    return (
        builder.add_glob("_object_eq", object.__eq__)
        .add_annotation("return", bool)
        .add_scriptline(returnline)
        .build(cls)
    )


def _build_field_comparison(
    builder: MethodBuilder, fields_to_compare: FieldMap, cls: type
):
    _ = builder.add_scriptline("if type(other) is type(self):")
    args = []
    for f in fields_to_compare.values():
        arg = f"{{target}}.{f.name}"
        if f.eq is not True:
            glob_name = f"_parser_{f.name}"
            arg = f"{glob_name}({arg})"
            _ = builder.add_glob(glob_name, f.eq)
        args.append(arg)

    fieldstr = "(" + ", ".join(args) + ",)"
    return (
        builder.add_scriptlines(
            indent(
                f"return {fieldstr.format(target='self')} "
                + f"== {fieldstr.format(target=_othername)}",
            ),
            "else:",
            indent("return NotImplemented"),
        )
        .add_annotation("return", bool)
        .build(cls)
    )


def make_unresolved_ref(cls: type, field: Field):
    def _unresolved_ref(_: Any) -> NoReturn:
        raise TypeError(
            "Trying to use class with unresolved ForwardRef for"
            + f" {cls.__qualname__}.{field.name}",
        )

    return _unresolved_ref


def get_parse_dict(cls: type, field_map: FieldMap):
    namespace = {}
    args = []
    alias_args = []
    builder = (
        MethodBuilder(
            "__parse_dict__",
            {
                "deserialize": squire.deserialize,
                "deserialize_mapping": squire.deserialize_mapping,
            },
        )
        .add_arg("alias", ArgumentType.POSITIONAL)
        .add_annotation("alias", bool)
        .add_annotation("return", Mapping[str, Any])
    )
    mod_globalns = sys.modules[cls.__module__].__dict__
    for name, f in field_map.items():
        field_type = f.origin or f.declared_type
        result, resolved = _resolve_forward_ref(
            field_type, cls, f, mod_globalns
        )
        if not resolved:
            _ = builder.add_glob(f"_asdict_{f.name}", result)
            arg = f"'{{name}}': _asdict_{f.name}(self.{name})"
        else:
            arg = _create_argument_for_field(f, field_type, builder.add_glob)
        args.append(arg.format(name=name))
        alias_args.append(arg.format(name=f.alias))
    namespace |= builder.add_scriptline(
        "\n    ".join(
            (
                "if alias:",
                f"    return {{{', '.join(alias_args)}}}",
                f"return {{{', '.join(args)}}}",
            )
        )
    ).build(cls)

    return namespace | MethodBuilder(
        "__iter__", {"todict": squire.deserialize}
    ).add_scriptline("yield from todict(self).items()").build(cls)


def _resolve_forward_ref(
    field_type: Any,
    cls: type,
    field: Field,
    mod_globalns: dict[str, Any],
) -> tuple[Any, bool]:
    if not isinstance(field_type, ForwardRef) or field.asdict_:
        return field_type, True
    try:
        parsed = evaluate_forward_ref(
            field_type,
            globals=mod_globalns,
            locals={cls.__name__: cls},
            type_params=None,
        )
    except NameError:
        return make_unresolved_ref(cls, field), False
    return (
        (disassemble_type(parsed), True)
        if parsed is not None
        else (
            make_unresolved_ref(cls, field),
            False,
        )
    )


def _create_argument_for_field(
    f: Field,
    field_type: type | ForwardRef,
    add_glob: Callable[[str, Callable], Any],
):
    if f.asdict_:
        add_glob(f"_asdict_{f.name}", f.asdict_)
        return f"'{{name}}': _asdict_{f.name}(self.{f.name})"
    elif hasattr(field_type, "__parse_dict__"):
        return f"'{{name}}': self.{f.name}.__parse_dict__(alias)"
    elif not isinstance(field_type, type):
        return f"'{{name}}': self.{f.name}"
    elif issubclass(field_type, list | tuple | set | dict):
        add_glob(f"field_type_{f.name}", field_type)
        return _get_parse_dict_sequence_arg(f)
    else:
        return f"'{{name}}': self.{f.name}"


def _get_parse_dict_sequence_arg(f: Field) -> str:
    field_type = f.origin or f.declared_type
    if not f.args:
        return f"'{{name}}': self.{f.name}"
    elif (
        len(f.args) > 1
        and issubclass(field_type, tuple)
        and (len(f.args) != 2 or f.args[1] is not Ellipsis)  # pyright: ignore[reportUnnecessaryComparison]
    ):
        idx_to_parse = [
            idx
            for idx, item in enumerate(f.args)
            if hasattr(item, "__parse_dict__")
        ]
        if not idx_to_parse:
            return f"'{{name}}': self.{f.name}"
        tuple_args = ", ".join(
            f"self.{f.name}[{idx}]"
            if idx not in idx_to_parse
            else f"self.{f.name}[{idx}].__parse_dict__(alias)"
            for idx, _ in enumerate(f.args)
        )
        return f"'{{name}}': ({tuple_args})"
    elif len(f.args) == 1 or issubclass(field_type, tuple):
        (element_type, *_) = f.args
        if hasattr(element_type, "__parse_dict__"):
            return (
                f"'{{name}}': field_type_{f.name}(x.__parse_dict__(alias)"
                f" for x in self.{f.name})"
            )
        return f"'{{name}}': deserialize(self.{f.name}, alias)"
    elif issubclass(field_type, Mapping):
        return f"'{{name}}': deserialize_mapping(self.{f.name}, alias)"
    else:
        return f"'{{name}}': deserialize(self.{f.name}, alias)"


def _dict_get(
    mapping: Mapping,
    name: str,
    alias: str,
    sentinel: Any,
    default: Any,
    dict_get: Callable[[Mapping, str, Any], Any],
):
    val = dict_get(mapping, alias, sentinel)
    if val is not sentinel:
        return val
    val = dict_get(mapping, name, sentinel)
    if val is not sentinel:
        return val
    if default is not sentinel:
        return default
    raise KeyError(
        f"Key '{name}' or alias '{alias}' not found in mapping: {mapping!r}"
        + " and no default value provided.",
    )


def get_squire_serialize(cls: type, field_map: FieldMap):
    args = []
    builder = (
        MethodBuilder(
            "__squire_serialize__",
            {
                "dict_get": _dict_get,
                "sentinel": object(),
                "_dict_get": dict.get,
            },
        )
        .add_arg("mapping", ArgumentType.POSITIONAL)
        .add_annotation("return", cls)
        .add_annotation("mapping", Mapping[str, Any])
        .set_type(MethodType.CLASS)
    )
    for f in field_map.values():
        field_type = f.origin or f.declared_type
        _ = builder.add_glob(f"_field_type_{f.name}", field_type)
        default_line = "sentinel"
        if f.has_default:
            _ = builder.add_glob(f"_field_type_{f.name}_default", f.default)
            default_line = f"_field_type_{f.name}_default"
        elif f.has_default_factory:
            _ = builder.add_glob(
                f"_field_type_{f.name}_default_factory", f.default
            )
            default_line = f"_field_type_{f.name}_default_factory()"
        get_line = f"dict_get(mapping, {f.name!r}, {f.alias!r}, sentinel, {default_line}, _dict_get)"
        if f.fromdict:
            _ = builder.add_glob(f"_field_type_{f.name}", f.fromdict)
            arg = f"_field_type_{f.name}({get_line})"
        elif hasattr(field_type, "__squire_serialize__"):
            arg = f"_field_type_{f.name}.__squire_serialize__({get_line})"
        elif field_type in (date, datetime):
            arg = f"_field_type_{f.name}.fromisoformat({get_line})"
        elif not isinstance(field_type, type):  # pyright: ignore[reportUnnecessaryIsInstance]
            arg = f"({get_line})"
        elif issubclass(field_type, list | tuple | set | dict):
            arg, globs = _get_gserialize_sequence_arg(f, get_line)
            _ = builder.merge_globs(globs)
        else:
            arg = f"_field_type_{f.name}({get_line})"
        args.append(f"{f.alias}={arg}")
    _ = builder.add_scriptline(f"return cls({', '.join(args)})")
    return builder.build(cls)


def _get_gserialize_sequence_arg(
    field: Field,
    get_line: str,
) -> tuple[str, Mapping[str, Any]]:
    field_type = field.origin or field.declared_type
    globs = {}
    returnline = get_line
    if not field.args:
        pass
    elif (
        len(field.args) > 1
        and issubclass(field_type, tuple)
        and (len(field.args) != 2 or field.args[1] is not Ellipsis)  # pyright: ignore[reportUnnecessaryComparison]
    ):
        if idx_to_parse := [
            idx
            for idx, item in enumerate(field.args)
            if hasattr(item, "__squire_serialize__")
        ]:
            for idx in idx_to_parse:
                globs[f"_elem_type_{field.name}_{idx}"] = field.args[idx]
            tuple_args = ", ".join(
                f"{get_line}[{idx}]"
                if idx not in idx_to_parse
                else f"_elem_type_{field.name}_{idx}."
                + f"__squire_serialize__({get_line}[{idx}])"
                for idx, _ in enumerate(field.args)
            )
            returnline = f"({tuple_args})"
    elif len(field.args) == 1 or issubclass(field_type, tuple):
        (element_type, *_) = field.args
        if hasattr(element_type, "__squire_serialize__"):
            globs[f"_elem_type_{field.name}"] = element_type
            returnline = (
                f"_field_type_{field.name}("
                + f"_elem_type_{field.name}.__squire_serialize__(x)"
                + f" for x in {get_line})"
            )
        else:
            returnline = f"_field_type_{field.name}({get_line})"
    return returnline, globs


def _get_ne(cls: type):
    return (
        MethodBuilder("__ne__")
        .add_arg(_othername, ArgumentType.POSITIONAL)
        .add_annotation("return", bool)
        .add_scriptlines(
            "result = self.__eq__(other)",
            "if result is NotImplemented:",
            indent("return NotImplemented"),
            "else:",
            indent("return not result"),
        )
        .build(cls)
    )


def _get_order(cls: type, field_map: FieldMap):
    payload: dict[str, Any] = {}

    for name, signal in [
        ("__lt__", "<"),
        ("__le__", "<="),
        ("__gt__", ">"),
        ("__ge__", ">="),
    ]:
        payload |= _make_comparator_builder(name, signal, field_map).build(cls)
    return payload


def _get_order_attr_tuple(fields: list[Field]) -> str:
    args = []
    for f in fields:
        arg = f"{{target}}.{f.name}"
        if f.order is not True:
            arg = f"_parser_{f.name}({arg})"
        args.append(arg)

    return f"({', '.join(args)},)"


def _make_comparator_builder(name: str, signal: str, field_map: FieldMap):
    fields = [f for f in field_map.values() if f.order is not False]

    if not fields:
        return (
            MethodBuilder(name, {f"_object_{name}": getattr(object, name)})
            .add_arg(_othername, ArgumentType.POSITIONAL)
            .add_annotation("return", bool)
            .add_scriptline(f"return _object_{name}(self, other)")
        )
    builder = MethodBuilder(
        name,
        {f"_parser_{f.name}": f.order for f in field_map.values()},
    )
    attr_tuple = _get_order_attr_tuple(fields)
    return (
        builder.add_arg(_othername, ArgumentType.POSITIONAL)
        .add_annotation("return", bool)
        .add_scriptlines(
            "if type(other) is type(self):",
            indent(
                "return "
                + f" {signal} ".join(
                    (
                        attr_tuple.format(target="self"),
                        attr_tuple.format(target="other"),
                    )
                ),
            ),
            "return NotImplemented",
        )
    )


def _get_hash(cls: type, fields_map: FieldMap, wants_hash: bool):
    builder = MethodBuilder("__hash__")
    args = ["type(self)"]
    for f in fields_map.values():
        if not f.hash:
            continue
        arg = f"self.{f.name}"
        if f.hash is not True:
            glob = f"_hash_{f.name}"
            arg = f"{glob}({arg})"
            _ = builder.add_glob(glob, f.hash)
        elif not isinstance(f.eq, bool):
            glob = f"_hash_{f.name}"
            arg = f"{glob}({arg})"
            _ = builder.add_glob(glob, f.eq)
        elif not is_hashable(f.declared_type):
            if not wants_hash:
                continue
            raise TypeError(
                f"field type is not hashable: {f.declared_type!r} (field '{f.name}' in {cls.__name__})"
            )
        args.append(arg)

    # if it only contains the class and no field qualifies for hashing
    if len(args) == 1:
        if not wants_hash:
            return {}
        raise TypeError("No hashable field found for class")

    return (
        builder.add_scriptline(f"return hash(({', '.join(args)}))")
        .add_annotation("return", int)
        .build(cls)
    )


def _get_pydantic_handlers(cls: type, fields_map: FieldMap):
    namespace = {}

    # Create Validation Function
    builder = MethodBuilder(
        "__pydantic_validate__", {"fromdict": fromdict}
    ).set_type(MethodType.CLASS)
    namespace |= (
        builder.add_arg("value", ArgumentType.POSITIONAL)
        .add_annotation("value", Any)
        .add_annotation("return", cls)
        .add_scriptlines(
            "if isinstance(value, cls):",
            indent("return value"),
            "try:",
            indent("return fromdict(cls, dict(value))"),
            "except (TypeError, ValueError) as e:",
            indent(
                f"raise TypeError(f'{cls.__name__} expected dict not"
                + " {type(value).__name__}')",
            ),
        )
        .build(cls)
    )

    # Write Get Validators
    namespace |= (
        MethodBuilder("__get_validators__")
        .set_type(MethodType.CLASS)
        .add_scriptline("yield cls.__pydantic_validate__ ")
        .add_annotation("return", Generator[Any, Any, Callable])
        .build(cls)
    )

    # Make modify schema
    builder = (
        MethodBuilder("__modify_schema__")
        .set_type(MethodType.CLASS)
        .add_arg("field_schema", ArgumentType.POSITIONAL)
    )

    cls_schema = Schema(
        cls.__name__,
        "object",
        [f.argname for f in fields_map.values() if f.default is MISSING],
        properties=_generate_schema_lines(fields_map),
    )
    return namespace | builder.add_scriptline(
        f"field_schema.update({cls_schema.to_string()})"
    ).build(cls)


def _generate_schema_lines(fields_map: FieldMap) -> dict[str, HasStr]:
    schemas: dict[str, HasStr] = {}
    for f in fields_map.values():
        field_type = f.field_type
        if current_map := getattr(field_type, "__squire_attrs__", None):
            required = [
                f.argname for f in current_map.values() if f.default is MISSING
            ]
            schemas[f.argname] = Schema(
                field_type.__name__,
                "object",
                required,
                properties=_generate_schema_lines(current_map),
            )
        else:
            schemas[f.argname] = _resolve_schematype(f.field_type, f.args)
    return schemas


def _resolve_schematype(field_type: type, args: Sequence[type]) -> HasToString:
    _type_map = {
        type(None): "null",
        bool: "boolean",
        str: "string",
        float: "number",
        int: "integer",
    }
    if val := _type_map.get(field_type):
        return DictSchema(val)
    if field_type in (list, set, tuple):
        extras = {}
        if args:
            extras["items"] = Items(
                *(_resolve_schematype(arg, get_args(arg)) for arg in args)
            )
        return DictSchema("array", **extras)
    if field_type is dict:
        extras = {}
        if args:
            keyt, valt = args
            if keyt is not str:
                raise TypeError(
                    f"Cannot generate schema for dict with key type {keyt}",
                    keyt,
                )
            extras["additional_properties"] = _resolve_schematype(
                valt, get_args(valt)
            )
        return DictSchema("object", **extras)
    if current_map := getattr(field_type, "__squire_attrs__", None):
        required = [
            f.argname for f in current_map.values() if f.default is MISSING
        ]
        return Schema(
            field_type.__name__,
            "object",
            required,
            properties=_generate_schema_lines(current_map),
        )
    if field_type is Union:  # pyright: ignore[reportDeprecated]
        choices = [_resolve_schematype(arg, get_args(arg)) for arg in args]
        return ListSchema("anyOf", *choices)
    if issubclass(field_type, Enum):
        # remove from parents cls, enum.Enum and object
        # uses only the first of the mro
        parent, *_ = field_type.mro()[1:-2]
        if parent:
            if ft := _type_map.get(parent):
                type_name = ft
            else:
                raise NotImplementedError
        else:
            type_name = "string"
        return Schema(
            field_type.__name__,
            type_name,
            enum=Items(*[f'"{item.value}"' for item in field_type]),
        )
    if issubclass(field_type, datetime):
        return DictSchema("string", format=str_cast("date-time"))
    if issubclass(field_type, date):
        return DictSchema("string", format=str_cast("date"))
    if issubclass(field_type, time):
        return DictSchema("string", format=str_cast("time"))
    if issubclass(field_type, timedelta):
        return DictSchema("number", format=str_cast("time-delta"))
    raise NotImplementedError


def _make_dataclass_fields(fields_map: FieldMap):
    dc_fields = {}
    for f in fields_map.values():
        kwargs: dict[str, Any] = {
            "compare": f.eq or f.order,
            "hash": bool(f.hash),
            "repr": bool(f.repr),
            "init": f.init,
        }
        if f.has_default:
            kwargs["default"] = f.default
        if f.has_default_factory:
            kwargs["default_factory"] = f.default

        dc_field: dataclasses.Field = dataclasses.field(**kwargs)
        dc_field.name = f.name
        dc_field.type = f.declared_type
        dc_field._field_type = dataclasses._FIELD  # pyright: ignore[reportAttributeAccessIssue]
        dc_fields[f.name] = dc_field
    return {"__dataclass_fields__": dc_fields}
