import contextlib
import sys
import types
import typing
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from dataclasses import is_dataclass
from types import NoneType
from typing import (
    Any,
    ForwardRef,
    TypeVar,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

from escudeiro.config.core.config import Config
from escudeiro.config.core.utils import LiteralType, literal_cast, null_cast
from escudeiro.config.interface import MISSING, ConfigLike, default_cast
from escudeiro.data import data, factory
from escudeiro.data.utils.functions import disassemble_type
from escudeiro.data.utils.typedef import DisassembledType
from escudeiro.exc import InvalidCast, MissingName
from escudeiro.misc import (
    Caster,
    as_boolean,
    exclamation,
    jsonx,
    make_lex_separator,
)

from .dataclass import DataclassResolverStrategy
from .interface import FieldResolverStrategy
from .squire import SquireResolverStrategy

DEFAULT_CONFIG = Config()

T = TypeVar("T")


_sequences = (list, tuple, set, frozenset)
_bool_cast = Caster(Caster(as_boolean).strict, name="bool")


def _defaults_allowed(config: ConfigLike, name: str) -> bool:
    """Ask the config whether a missing name may fall back to a default.

    EnvConfig drops defaults in some environments (`ignore_default_rule`);
    a probe default goes through `config.get`, so that decision stays there
    and the real default is never cast or altered by the config.
    """
    probe = object()
    try:
        return config.get(name, default_cast, probe) is probe
    except MissingName:
        return False


def _try_each(
    *names: str,
    default: Callable[[], Any],
    cast: Any,
    config: ConfigLike,
):
    for name in names:
        with suppress(MissingName):
            return config(name, cast)
    if _defaults_allowed(config, names[0]):
        value = default()
        if value is not MISSING:
            return value
    raise MissingName(
        exclamation(f"{', '.join(names)} not found and no default was given")
    )


def _is_union(annotation: Any) -> bool:
    return get_origin(annotation) in (typing.Union, types.UnionType)  # pyright: ignore[reportDeprecated]


def _first_match(casts: Sequence[Callable[[str], Any]]) -> Callable[[str], Any]:
    def _cast(val: str) -> Any:
        for caster in casts:
            try:
                return caster(val)
            except Exception:
                continue
        raise InvalidCast("Value does not match any member of the union")

    return _cast


def _resolve_union(annotation: Any) -> tuple[Any, bool]:
    """Union members are tried in order, `None` (null, none, '') last."""
    args = get_args(annotation)
    members = [_resolve_cast(arg) for arg in args if arg is not NoneType]
    if any(is_config for _, is_config in members):
        if len(members) == 1:
            return members[0]
        raise InvalidCast("Unions of configuration classes are not supported")
    casts = [member for member, _ in members]
    if NoneType in args:
        casts.append(null_cast)
    return (casts[0] if len(casts) == 1 else _first_match(casts)), False


def _resolve_cast(outer_type: Any) -> tuple[Any, bool]:
    while isinstance(outer_type, typing.TypeAliasType):
        outer_type = outer_type.__value__
    origin = get_origin(outer_type)
    if _is_union(outer_type):
        return _resolve_union(outer_type)
    if outer_type is bool:
        return _bool_cast, False
    if isinstance(outer_type, typing.cast(Any, LiteralType)):
        return literal_cast(outer_type), False
    with contextlib.suppress(ValueError):
        _ = AdapterConfigFactory.get_strategy_class(
            disassemble_type(outer_type)
        )
        return outer_type, True
    if origin is None:
        return (
            make_lex_separator(outer_type)
            if outer_type in _sequences
            else outer_type
        ), False
    if origin in _sequences:
        args = get_args(outer_type)
        element, is_config = _resolve_cast(args[0]) if args else (str, False)
        if is_config:
            raise InvalidCast(
                "Collections of configuration classes are not supported"
            )
        return make_lex_separator(origin, cast(Any, element)), False
    return (
        _loads if dict in (origin, outer_type) else origin,  # type:ignore
        False,
    )


def _loads(val: Any) -> Any:
    return jsonx.loads(val) if isinstance(val, str) else val


@data
class AdapterConfigFactory:
    """
    Factory for creating configuration instances based on model classes.
    """

    config: ConfigLike = DEFAULT_CONFIG

    @staticmethod
    def get_strategy_class(
        config_class: DisassembledType,
    ) -> type[FieldResolverStrategy]:
        """
        Get the appropriate strategy class for resolving fields in the configuration class.

        Args:
            config_class (type): The configuration class to resolve.

        Returns:
            type[FieldResolverStrategy]: The strategy class for resolving fields.
        """
        klass = config_class.origin or config_class.type_
        try:
            from pydantic import BaseModel

            base_model_cls: list[type] = [BaseModel]
            if sys.version_info < (3, 14):
                from pydantic import v1

                base_model_cls.append(v1.BaseModel)
        except ImportError:
            base_model_cls = []
        if hasattr(klass, "__squire_attrs__"):
            return SquireResolverStrategy
        elif is_dataclass(klass):
            return DataclassResolverStrategy
        elif (
            base_model_cls
            and isinstance(klass, type)
            and issubclass(klass, tuple(base_model_cls))
        ):
            from .pydantic import PydanticResolverStrategy

            return PydanticResolverStrategy
        elif hasattr(klass, "__attrs_attrs__"):
            from .attrs import AttrsResolverStrategy

            return AttrsResolverStrategy
        raise ValueError("Unknown class definition")

    def load(
        self,
        model_cls: type[T],
        __prefix__: str = "",
        __sep__: str = "__",
        *,
        presets: dict[str, Any] | None = None,
        **defaults: Any,
    ) -> T:
        """
        Load a configuration instance based on a model class.

        Args:
            model_cls (type[T]): The model class representing the configuration.
            __prefix__ (str): Optional prefix for configuration fields.
            __set__(str): Optional prefix to separate fields of nested models. Default is "__"
            presets (Optional[dict[str, Any]]): Optional preset values for fields.
            **defaults (Any): Default values for fields.

        Returns:
            T: The loaded configuration instance.
        """
        presets = presets or {}
        strategy_class = self.get_strategy_class(disassemble_type(model_cls))
        resolvers = tuple(
            resolver
            for field in strategy_class.iterfield(model_cls)
            if (resolver := strategy_class(field)).init_name() not in presets
        )
        result = {
            resolver.init_name(): self._get_value(
                model_cls,
                resolver,
                __prefix__,
                __sep__,
                defaults,
            )
            for resolver in resolvers
        }
        return model_cls(**result | presets)

    def maker(
        self,
        model_cls: type[T],
        __prefix__: str = "",
        __sep__: str = "__",
        *,
        presets: dict[str, Any] | None = None,
        **defaults: Any,
    ) -> Callable[[], T]:
        """
        Create a factory function for loading configuration instances.

        Args:
            model_cls (type[T]): The model class representing the configuration.
            __prefix__ (str): Optional prefix for configuration fields.
            presets (Optional[dict[str, Any]]): Optional preset values for fields.
            **defaults (Any): Default values for fields.

        Returns:
            Callable[[], T]: The factory function for loading configuration instances.
        """

        @factory
        def load():
            return self.load(
                model_cls, __prefix__, __sep__, presets=presets, **defaults
            )

        return load

    def _annotation(
        self, model_cls: type, resolver: FieldResolverStrategy
    ) -> Any:
        annotation = resolver.cast()
        if not isinstance(annotation, (str, ForwardRef)):
            return annotation
        name = resolver.names()[0]
        try:
            return get_type_hints(model_cls)[name]
        except Exception as e:
            raise InvalidCast(
                exclamation(
                    f"Could not resolve the annotation of {model_cls.__qualname__}.{name}"
                )
            ) from e

    def _get_value(
        self,
        model_cls: type,
        resolver: FieldResolverStrategy,
        prefix: str,
        sep: str,
        defaults: Mapping[str, Any],
    ):
        names = self.resolve_names(model_cls, resolver, prefix)
        cast, _is_config = _resolve_cast(self._annotation(model_cls, resolver))
        if _is_config:
            return self.load(
                cast,
                f"{next(iter(names))}{sep}",
                sep,
                **defaults,
            )

        def default() -> Any:
            for name in names:
                if (value := defaults.get(name, MISSING)) is not MISSING:
                    return value
            return resolver.default()

        return _try_each(*names, default=default, cast=cast, config=self.config)

    def resolve_names(
        self, model_cls: type, resolver: FieldResolverStrategy, prefix: str
    ) -> Sequence[str]:
        names = resolver.names()
        prefix = prefix or getattr(model_cls, "__prefix__", "")
        without_prefix = cast(
            Sequence[str], getattr(model_cls, "__without_prefix__", ())
        )
        if not prefix or set(names).intersection(without_prefix):
            return (*names, *map(str.upper, names))

        processed_names = []
        for name in names:
            _prefix = f"{prefix}_" if not prefix.endswith("_") else prefix
            processed = f"{_prefix}{name}".lower()
            processed_names.extend((processed, processed.upper()))

        return tuple(processed_names)
