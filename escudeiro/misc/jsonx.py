"""Small wrapper module around orjson to have a similar interface to builtins.json"""

from collections.abc import Callable
from typing import Any, BinaryIO, TextIO

import orjson

loads: Callable[[str | bytes | bytearray | memoryview], Any] = orjson.loads


def dumps(
    val: Any,
    *,
    default: Callable[[Any], Any] | None = None,
    option: int | None = None,
) -> str:
    return orjson.dumps(val, default=default, option=option).decode("utf-8")


def load(fdes: BinaryIO | TextIO) -> Any:
    return loads(fdes.read())


def dump(
    obj: Any,
    fdes: BinaryIO,
    *,
    default: Callable[[Any], Any] | None = None,
    indent: bool = False,
) -> None:
    indent_flag = orjson.OPT_INDENT_2 if indent else None
    _ = fdes.write(orjson.dumps(obj, default=default, option=indent_flag))
