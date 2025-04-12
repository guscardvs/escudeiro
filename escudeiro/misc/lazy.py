import enum
from collections.abc import Callable, Hashable, Sequence
from functools import wraps
from inspect import signature
from typing import (
    Any,
    ClassVar,
    Concatenate,
    Self,
    cast,
    get_args,
    get_origin,
    overload,
)


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
    )

    format_: ClassVar[str] = "_lazymethod_{method_name}_"

    def __init__(self, func: Callable[Concatenate[SelfT, P], T]) -> None:
        self._func = func
        self._method_type = self._determine_method_type(func)
        self._container = self._get_container()
        self.public_name = func.__name__
        self.private_name = self.format_.format(method_name=func.__name__)

    def _determine_method_type(self, func: Callable) -> MethodType:
        sig = signature(func)
        if len(sig.parameters) == 1:
            return MethodType.SELF_ONLY
        elif all(
            param.annotation is not param.empty
            and self._is_hashable(param.annotation)
            for param in tuple(sig.parameters.values())[1:]
        ):
            return MethodType.HASHABLE_ARGS
        else:
            return MethodType.UNKNOWN_OR_UNHASHABLE

    def _is_hashable(self, annotation: Any) -> bool:
        if origin := get_origin(annotation):
            args = get_args(annotation)
            return self._is_hashable(origin) and all(
                self._is_hashable(arg) for arg in args
            )
        if isinstance(annotation, type):
            return issubclass(annotation, Hashable)
        return False

    def _get_container(
        self,
    ) -> type[dict[Hashable, T] | list[tuple[Any, T]]] | None:
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
            if (
                value := self._get(
                    instance,
                    self.private_name,
                    args,
                    kwargs,
                )
            ) is not None:
                return value
            return self._set(instance, *args, **kwargs)

        return _callable

    def _set(self, instance: SelfT, *args: P.args, **kwargs: P.kwargs) -> T:
        value = self._func(instance, *args, **kwargs)
        if self._container is None:
            object.__setattr__(instance, self.private_name, value)
        elif self._container is dict:
            container = cast(
                dict[Hashable, T],
                getattr(instance, self.private_name, self._container()),
            )
            container[(*args, tuple(kwargs.items()))] = value
            object.__setattr__(instance, self.private_name, container)
        elif self._container is list:
            container = cast(
                list[tuple[Any, T]],
                getattr(instance, self.private_name, self._container()),
            )
            container.append(((*args, tuple(kwargs.items())), value))
            object.__setattr__(instance, self.private_name, container)
        return value

    def _get(
        self,
        instance: SelfT,
        name: str,
        args: Sequence[Any],
        kwargs: dict[str, Any],
    ) -> T | None:
        if self._container is None:
            return getattr(instance, name, None)
        elif self._container is dict:
            container = getattr(instance, name, None)
            if container is None:
                return None
            return container.get((*args, tuple(kwargs.items())))
        elif self._container is list:
            container = getattr(instance, name, None)
            if container is None:
                return None
            for item in container:
                if item[0] == (*args, tuple(kwargs.items())):
                    return item[1]
            return None

    @classmethod
    def is_initialized(cls, instance: SelfT, name: str) -> bool:
        return hasattr(instance, cls.format_.format(method_name=name))
