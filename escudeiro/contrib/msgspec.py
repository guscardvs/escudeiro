from collections.abc import Callable, Mapping
from typing import Any, Literal, overload

import msgspec

from escudeiro.lazyfields import lazy
from escudeiro.misc import filter_isinstance, next_or, strings


class SquireStruct(msgspec.Struct):
    @overload
    def __init_subclass__(
        cls,
        *,
        tag: None | bool | str | int | Callable[[str], str | int] = None,
        tag_field: None | str = None,
        rename: None
        | Literal["lower", "upper", "camel", "pascal", "kebab"]
        | Callable[[str], str | None]
        | Mapping[str, str] = None,
        omit_defaults: bool = False,
        forbid_unknown_fields: bool = False,
        frozen: bool = False,
        eq: bool = True,
        order: bool = False,
        kw_only: bool = False,
        repr_omit_defaults: bool = False,
        array_like: bool = False,
        gc: bool = True,
        weakref: bool = False,
        dict: bool = False,
        cache_hash: bool = False,
    ) -> None: ...

    @overload
    def __init_subclass__(cls, **kwargs: Any) -> None: ...

    def __init_subclass__(cls, **kwargs: Any) -> None:
        if next_or(filter_isinstance(lazy, cls.__dict__.values())):
            raise TypeError(
                f"msgspec.Struct {cls.__name__} doesn't support lazyfields"
            )
        return super().__init_subclass__(**kwargs)


class PascalStruct(SquireStruct, rename=strings.to_pascal):
    pass


class CamelStruct(SquireStruct, rename=strings.to_camel):
    pass
