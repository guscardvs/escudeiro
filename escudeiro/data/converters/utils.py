from collections.abc import Mapping
from typing import Any

from escudeiro.escudeiro_pyrs import squire


def asdict(obj: Any, by_alias: bool = False):
    return squire.deserialize_mapping(
        squire.make_mapping(obj, by_alias=by_alias), by_alias=by_alias
    )


def fromdict[T](into: type[T], mapping: Mapping[str, Any]) -> T:
    return into.__squire_serialize__(mapping)  # pyright: ignore[reportAttributeAccessIssue]
