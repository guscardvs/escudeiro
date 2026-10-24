"""Utilities for lazy method evaluation with argument-sensitive caching.

This module provides a decorator class for lazily evaluating instance methods,
optionally caching results based on their argument signature. It supports different
caching strategies depending on the method’s parameter types.
"""

import enum
from collections.abc import Callable, Hashable, Sequence
from functools import wraps
from inspect import Parameter, signature
from typing import (
    Any,
    ClassVar,
    Concatenate,
    Self,
    cast,
    overload,
)

from escudeiro.misc.typex import is_hashable

_MISSING: Any = object()


def _typed(value: Any) -> Any:
    """Key form of a value that keeps `1`, `True` and `1.0` apart."""
    if isinstance(value, tuple):
        return (tuple, tuple(_typed(item) for item in value))
    return (type(value), value)


class MethodType(enum.Enum):
    SELF_ONLY = 0
    HASHABLE_ARGS = 1
    UNKNOWN_OR_UNHASHABLE = 2


class lazymethod[SelfT, T, **P]:
    __slots__ = (
        "_func",
        "public_name",
        "private_name",
        "_method_type",
        "_container",
        "_pos_map",
        "_default_map",
        "_var_positional",
        "_var_keyword",
        "_named",
    )

    format_: ClassVar[str] = "_lazymethod_{method_name}_"

    def __init__(self, func: Callable[Concatenate[SelfT, P], T]) -> None:
        self._func = func
        self._method_type = self._determine_method_type(func)
        self._container = self._get_container()
        self.public_name = func.__name__
        self.private_name = self.format_.format(method_name=func.__name__)
        self._var_positional: str | None = None
        self._var_keyword: str | None = None
        self._named: frozenset[str] = frozenset()
        self._pos_map, self._default_map = self._make_signature_maps(
            func, self._method_type
        )

    def _make_signature_maps(
        self, func: Callable, method_type: MethodType
    ) -> tuple[dict[int, str], dict[str, Any]]:
        if method_type is MethodType.SELF_ONLY:
            return {}, {}
        sig = signature(func)
        pos_map = {}
        default_map = {}

        pos = 0
        named: set[str] = set()
        for param in tuple(sig.parameters.values())[1:]:
            if param.kind is Parameter.VAR_POSITIONAL:
                self._var_positional = param.name
            elif param.kind is Parameter.VAR_KEYWORD:
                self._var_keyword = param.name
            else:
                named.add(param.name)
                if param.kind is not Parameter.KEYWORD_ONLY:
                    pos += 1
                    pos_map[pos] = param.name
                if param.default is not Parameter.empty:
                    default_map[param.name] = param.default

        self._named = frozenset(named)
        return pos_map, default_map

    def _determine_method_type(self, func: Callable) -> MethodType:
        sig = signature(func)
        if len(sig.parameters) == 1:
            return MethodType.SELF_ONLY
        elif all(
            param.annotation is not param.empty
            and self.is_hashable(param.annotation)
            for param in tuple(sig.parameters.values())[1:]
        ):
            return MethodType.HASHABLE_ARGS
        else:
            return MethodType.UNKNOWN_OR_UNHASHABLE

    @staticmethod
    def is_hashable(annotation: Any) -> bool:
        return is_hashable(annotation)

    def _get_container(
        self,
    ) -> type[dict[Hashable, T]] | type[list[tuple[Any, T]]] | None:
        match self._method_type:
            case MethodType.SELF_ONLY:
                return None
            case MethodType.HASHABLE_ARGS:
                return dict
            case MethodType.UNKNOWN_OR_UNHASHABLE:
                return list

    def __set_name__(self, owner: type[SelfT], name: str) -> None:
        self.public_name = name
        self.private_name = self.format_.format(method_name=name)

    @classmethod
    def get_private(cls, name: str) -> str:
        return cls.format_.format(method_name=name)

    @overload
    def __get__(self, instance: None, owner: type[SelfT]) -> Self: ...

    @overload
    def __get__(
        self, instance: SelfT, owner: type[SelfT]
    ) -> Callable[P, T]: ...

    def __get__(
        self, instance: SelfT | None, owner: type[SelfT]
    ) -> Callable[P, T] | Self:
        if instance is None:
            return self
        return self._call(instance)

    def _call(self, instance: SelfT) -> Callable[P, T]:
        @wraps(self._func)
        def _callable(*args: P.args, **kwargs: P.kwargs) -> T:
            value = self._get(
                instance,
                self.private_name,
                args,
                kwargs,
            )
            if value is not _MISSING:
                return value
            return self._set(instance, *args, **kwargs)

        return _callable

    def _set(self, instance: SelfT, *args: P.args, **kwargs: P.kwargs) -> T:
        value = self._func(instance, *args, **kwargs)
        if self._container is None:
            object.__setattr__(instance, self.private_name, value)
        elif self._container is dict:
            kwargs_only = self._signature_to_kwargs(args, kwargs)
            container = cast(
                dict[Hashable, T],
                getattr(instance, self.private_name, self._container()),
            )
            container[self._key(kwargs_only, frozenset)] = value
            object.__setattr__(instance, self.private_name, container)
        elif self._container is list:
            kwargs_only = self._signature_to_kwargs(args, kwargs)
            container = cast(
                list[tuple[Any, T]],
                getattr(instance, self.private_name, self._container()),
            )
            container.append((self._key(kwargs_only, tuple), value))
            object.__setattr__(instance, self.private_name, container)
        return value

    def _get(
        self,
        instance: SelfT,
        name: str,
        args: Sequence[Any],
        kwargs: dict[str, Any],
    ) -> T | Any:
        if self._container is None:
            return getattr(instance, name, _MISSING)
        container = getattr(instance, name, None)
        if container is None:
            return _MISSING
        kwargs_only = self._signature_to_kwargs(args, kwargs)
        if self._container is dict:
            return container.get(self._key(kwargs_only, frozenset), _MISSING)
        key = self._key(kwargs_only, tuple)
        for item in container:
            if item[0] == key:
                return item[1]
        return _MISSING

    @staticmethod
    def _key(kwargs_only: dict[str, Any], kind: type) -> Any:
        return kind((k, _typed(v)) for k, v in kwargs_only.items())

    def _signature_to_kwargs(
        self, args: Sequence[Any], kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        result = kwargs.copy()
        named = len(self._pos_map)
        for pos, arg in enumerate(args[:named], 1):
            result[self._pos_map[pos]] = arg
        if self._var_positional is not None:
            result[self._var_positional] = tuple(args[named:])
        for name, value in self._default_map.items():
            if name not in result:
                result[name] = value
        if self._var_keyword is not None:
            extra = {k: result.pop(k) for k in kwargs if k not in self._named}
            result[self._var_keyword] = tuple(sorted(extra.items()))
        return {k: result[k] for k in sorted(result)}

    @classmethod
    def is_initialized(cls, instance: SelfT, name: str) -> bool:
        return hasattr(instance, cls.format_.format(method_name=name))
