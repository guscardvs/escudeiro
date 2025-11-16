from collections.abc import Callable, Sequence
from types import EllipsisType
from typing import Any, ClassVar, Self, overload, override

from .utils.factory import factory, is_factory
from .utils.typedef import MISSING, DisassembledType, TypeNode

type BoolOrCallable = bool | Callable[[Any], Any]


class Field:
    __slots__: ClassVar[Sequence[str]] = (
        "name",
        "annotation",
        "kw_only",
        "default",
        "alias",
        "eq",
        "order",
        "init",
        "hash",
        "repr",
        "asdict_",
        "fromdict",
        "inherited",
        "ref",
    )

    def __init__(
        self,
        name: str,
        annotation: DisassembledType,
        kw_only: bool,
        default: Any,
        alias: str,
        eq: BoolOrCallable,
        order: BoolOrCallable,
        init: bool,
        hash: BoolOrCallable,
        repr: bool | Callable[[Any], str],
        asdict_: Callable[[Any], Any] | None,
        fromdict: Callable[[Any], Any] | None,
        inherited: bool = False,
        ref: Callable[[Any], Any] | None = None,
    ) -> None:
        self.name: str = name
        self.annotation: DisassembledType = annotation
        self.kw_only: bool = kw_only
        self.default: Any = default
        self.alias: str = alias
        self.eq: BoolOrCallable = eq
        self.order: BoolOrCallable = order
        self.init: bool = init
        self.hash: BoolOrCallable = hash
        self.repr: BoolOrCallable = repr
        self.asdict_: Callable[[Any], Any] | None = asdict_
        self.fromdict: Callable[[Any], Any] | None = fromdict
        self.inherited: bool = inherited
        self.ref: Callable[[Any], Any] | None = ref

    @property
    def argname(self):
        return self.alias or self.name

    @property
    def has_alias(self) -> bool:
        return self.alias != self.name

    @property
    def origin(self) -> type | None:
        return self.annotation.origin

    @property
    def args(self) -> Sequence[type]:
        return self.annotation.args

    @property
    def declared_type(self) -> type:
        return self.annotation.type_  # pyright: ignore[reportReturnType]

    @property
    def has_type_vars(self) -> bool:
        return bool(self.annotation.type_vars)

    @property
    def node(self) -> TypeNode:
        return self.annotation.typenode

    @property
    def field_type(self) -> type:
        return self.origin or self.declared_type

    @property
    def has_default(self) -> bool:
        return self.default is not MISSING and not is_factory(self.default)

    @property
    def has_default_factory(self) -> bool:
        return is_factory(self.default)

    @property
    def allow_none(self) -> bool:
        return None in self.args

    @override
    def __repr__(self) -> str:
        default_name = (
            self.default.__name__ if self.has_default_factory else self.default
        )
        return "Field(" + (
            ", ".join(
                (
                    f"name={self.name}",
                    f"annotation={self.annotation}",
                    f"default={default_name}",
                    f"kw_only={self.kw_only}",
                    f"alias={self.alias}",
                    f"eq={self.eq}",
                    f"order={self.order}",
                    f"init={self.init}",
                    f"hash={self.hash}",
                    f"repr={self.repr}",
                    f"asdict_={self.asdict_}",
                    f"fromdict={self.fromdict}",
                    f"transform={self.ref}",
                    f"inherited={self.inherited}",
                )
            )
            + ")"
        )

    def asdict(self):
        return {key: getattr(self, key) for key in self.__slots__}

    def duplicate(self, **overload: Any):
        return type(self)(**self.asdict() | overload)

    def inherit(self) -> Self:
        return self.duplicate(inherited=True)


class FieldInfo:
    __slots__: ClassVar[Sequence[str]] = (
        "default",
        "kw_only",
        "alias",
        "eq",
        "order",
        "init",
        "hash",
        "repr",
        "asdict_",
        "fromdict",
        "ref",
    )

    def __init__(
        self,
        default: Any,
        alias: str,
        kw_only: bool,
        eq: BoolOrCallable,
        order: BoolOrCallable,
        init: bool,
        hash: BoolOrCallable,
        repr: bool | Callable[[Any], str],
        asdict_: Callable[[Any], Any] | None,
        fromdict: Callable[[Any], Any] | None,
        ref: Callable[[Any], Any] | None = None,
    ) -> None:
        self.default: Any = default
        self.kw_only: bool = kw_only
        self.alias: str = alias
        self.eq: BoolOrCallable = eq
        self.order: BoolOrCallable = order
        self.init: bool = init
        self.hash: BoolOrCallable = hash
        self.repr: bool | Callable[[Any], str] = repr
        self.asdict_: Callable[[Any], Any] | None = asdict_
        self.fromdict: Callable[[Any], Any] | None = fromdict
        self.ref: Callable[[Any], Any] | None = ref

    def asdict(self):
        return {key: getattr(self, key) for key in self.__slots__}

    def duplicate(self, **overload: Any):
        return FieldInfo(**self.asdict() | overload)

    def build[F: Field](self, field_cls: type[F], **extras: Any) -> F:
        return field_cls(**self.asdict() | extras)


@overload
def field(
    *,
    default_factory: Callable[[], Any],
    alias: str = "",
    kw_only: bool = False,
    eq: BoolOrCallable = True,
    order: BoolOrCallable = True,
    init: bool = True,
    hash: BoolOrCallable = True,
    repr: bool | Callable[[Any], str] = True,
    asdict: Callable[[Any], Any] | None = None,
    fromdict: Callable[[Any], Any] | None = None,
) -> Any: ...


@overload
def field(
    *,
    default: Any,
    alias: str = "",
    kw_only: bool = False,
    eq: BoolOrCallable = True,
    order: BoolOrCallable = True,
    init: bool = True,
    hash: BoolOrCallable = True,
    repr: bool | Callable[[Any], str] = True,
    asdict: Callable[[Any], Any] | None = None,
    fromdict: Callable[[Any], Any] | None = None,
) -> Any: ...


@overload
def field(
    *,
    alias: str = "",
    kw_only: bool = False,
    eq: BoolOrCallable = True,
    order: BoolOrCallable = True,
    init: bool = True,
    hash: BoolOrCallable = True,
    repr: bool | Callable[[Any], str] = True,
    asdict: Callable[[Any], Any] | None = None,
    fromdict: Callable[[Any], Any] | None = None,
) -> Any: ...


def field(
    *,
    default: Any = ...,
    default_factory: Callable[[], Any] | EllipsisType = ...,
    alias: str = "",
    kw_only: bool = False,
    eq: BoolOrCallable = True,
    order: BoolOrCallable = True,
    init: bool = True,
    hash: BoolOrCallable = True,
    repr: bool | Callable[[Any], str] = True,
    asdict: Callable[[Any], Any] | None = None,
    fromdict: Callable[[Any], Any] | None = None,
) -> Any:  # sourcery skip: instance-method-first-arg-name
    """
    Declare metadata for a gyver-attrs field.

    :param default: The default value of the field.
    :param default_factory: A callable that returns the default value of the field.
    :param alias: The alternative name for the field.
    :param kw_only: Whether the field should be a keyword-only parameter in
    the generated constructor.
    :param eq: Whether the field should be used in the equality comparison of instances
    of the class.
               If a callable is passed, it will be used to compare the field values.
    :param order: Whether the field should be used in rich comparison ordering
    of instances of the class.
                 If a callable is passed, it will be used to compare the field values.
    """
    if not isinstance(default_factory, EllipsisType):
        default = factory(default_factory)
    return FieldInfo(
        default=default if default is not Ellipsis else MISSING,
        alias=alias,
        kw_only=kw_only,
        eq=eq,
        order=order,
        init=init,
        hash=hash,
        repr=repr,
        asdict_=asdict,
        fromdict=fromdict,
        ref=None,
    )


@overload
def private(
    *,
    initial_factory: Callable[[], Any],
    alias: str = "",
    kw_only: bool = False,
    eq: BoolOrCallable = True,
    order: BoolOrCallable = True,
    hash: BoolOrCallable = True,
    repr: bool | Callable[[Any], str] = True,
    asdict: Callable[[Any], Any] | None = None,
    fromdict: Callable[[Any], Any] | None = None,
): ...


@overload
def private(
    *,
    initial: Any,
    alias: str = "",
    kw_only: bool = False,
    eq: BoolOrCallable = True,
    order: BoolOrCallable = True,
    hash: BoolOrCallable = True,
    repr: bool | Callable[[Any], str] = True,
    asdict: Callable[[Any], Any] | None = None,
    fromdict: Callable[[Any], Any] | None = None,
    ref: Callable[[Any], Any] | None = None,
): ...


@overload
def private(
    *,
    ref: Callable[[Any], Any],
    alias: str = "",
    kw_only: bool = False,
    eq: BoolOrCallable = True,
    order: BoolOrCallable = True,
    hash: BoolOrCallable = True,
    repr: bool | Callable[[Any], str] = True,
    asdict: Callable[[Any], Any] | None = None,
    fromdict: Callable[[Any], Any] | None = None,
): ...


def private(
    *,
    initial: Any = ...,
    initial_factory: Callable[[], Any] | EllipsisType = ...,  # type: ignore
    alias: str = "",
    kw_only: bool = False,
    eq: BoolOrCallable = True,
    order: BoolOrCallable = True,
    hash: BoolOrCallable = True,
    repr: bool | Callable[[Any], str] = True,
    asdict: Callable[[Any], Any] | None = None,
    fromdict: Callable[[Any], Any] | None = None,
    ref: Callable[[Any], Any] | None = None,
) -> FieldInfo:
    """Declare metadata for a field not added to init.
    :param initial: The initial value of the field.
    :param initial_factory: A callable that returns the initial value of the field.
    Parameters are the same as in info."""
    if (
        isinstance(initial, EllipsisType)
        and isinstance(initial_factory, EllipsisType)
        and ref is None
    ):
        raise ValueError("No initial value provided")
    if not isinstance(initial_factory, EllipsisType):
        initial = factory(initial_factory)
    return FieldInfo(
        default=initial if initial is not Ellipsis else MISSING,
        alias=alias,
        kw_only=kw_only,
        eq=eq,
        order=order,
        init=False,
        hash=hash,
        repr=repr,
        asdict_=asdict,
        fromdict=fromdict,
        ref=ref,
    )


default_field_info: FieldInfo = field()
