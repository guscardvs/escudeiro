from enum import Enum
from pathlib import Path
from typing import Literal

import pytest

from escudeiro.config import Config, EnvMapping
from escudeiro.config.core.utils import (
    literal_cast,
    none_is_missing,
    valid_path,
)
from escudeiro.exc import InvalidCast, MissingName
from escudeiro.misc.functions import Caster
from escudeiro.misc.pathx import is_valid_path
from escudeiro.misc.strings import as_boolean, squote


def test_valid_path_returns_path_object(tmp_path: Path):
    filepath = tmp_path / "file.txt"
    filepath.touch()
    mapping = EnvMapping({"key": filepath.as_posix()})
    cfg = Config(mapping=mapping)

    val = cfg("key", valid_path)

    assert isinstance(val, Path)
    assert val == filepath


def test_valid_path_raises_file_not_found_error():
    """test valid_path raises FileNotFoundError
    if the path does not exist."""
    mapping = EnvMapping({"key": "./non_existent_file.txt"})
    cfg = Config(mapping=mapping)
    valpath = Path("./non_existent_file.txt")

    with pytest.raises(InvalidCast) as exc_info:
        _ = cfg("key", valid_path)

    assert isinstance(exc_info.value.__cause__, InvalidCast)
    assert exc_info.value.__cause__.args == (
        f"result {valpath!s} does not satisfy the rule {squote(is_valid_path.__name__)}.",
        valpath,
    )


def test_literal_cast_returns_valid_cast():
    class Test(Enum):
        VALUE = "value"

    literal_type = Literal[1, "other", b"another", Test.VALUE, None, False]
    caster = literal_cast(literal_type)
    mapping = EnvMapping(
        {
            "first": "other",
            "second": "another",
            "third": "1",
            "fourth": "value",
            "fifth": "null",
            "sixth": "false",
            "seventh": "invalid",
        }
    )
    cfg = Config(mapping=mapping)

    assert (
        cfg("first", caster),
        cfg("second", caster),
        cfg("third", caster),
        cfg("fourth", caster),
        cfg("fifth", caster),
        cfg("sixth", caster),
    ) == (
        "other",
        b"another",
        1,
        Test.VALUE,
        None,
        False,
    )

    with pytest.raises(InvalidCast) as exc_info:
        cfg("seventh", caster)

    assert exc_info.value.__cause__ is not None
    assert exc_info.value.__cause__.args == (
        "Value received does not match any argument from literal",
        literal_type.__args__,
    )


def test_none_is_missing():
    mapping = EnvMapping({"key": "null"})
    cfg = Config(mapping=mapping)

    with pytest.raises(MissingName):
        _ = cfg("key", none_is_missing(Caster(as_boolean).optional))
