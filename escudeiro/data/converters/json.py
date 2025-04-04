from typing import Any

import orjson

from .utils import asdict, fromdict


def asjson(
    obj: Any,
    *,
    by_alias: bool = True,
) -> str:
    if not hasattr(obj, "__squire_attrs__"):
        raise TypeError("Unable to parse classes not defined with `define`")

    return orjson.dumps(asdict(obj, by_alias=by_alias)).decode()


def fromjson[T](
    into: type[T],
    json_str: str,
) -> T:
    val = orjson.loads(json_str)
    return fromdict(into, val)
