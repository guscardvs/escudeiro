from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import (
    Any,
    ForwardRef,
    NamedTuple,
    Protocol,
    Self,
    TypedDict,
    override,
)


class DisassembledType(NamedTuple):
    type_: type | ForwardRef
    origin: type | None
    args: Sequence[type]
    type_vars: Sequence["TypeNode"]
    typenode: "TypeNode"


@dataclass
class TypeNode:
    type_: Any
    args: list["TypeNode"] = field(default_factory=list)

    @override
    def __hash__(self) -> int:
        return id(self)


class MISSING:
    pass


class InitOptions(TypedDict):
    slots: bool
    frozen: bool
    init: bool


class UNINITIALIZED:
    pass


class Descriptor(Protocol):
    private_name: str

    def __get__(self, instance: Any | None, owner: type[Any]) -> Self | Any: ...
