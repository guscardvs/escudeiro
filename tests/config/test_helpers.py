from enum import Enum
from pathlib import Path
from typing import Any, Literal

import pytest

from escudeiro.config import Config, EnvMapping
from escudeiro.config.core.utils import (
    boolean_cast,
    literal_cast,
    none_is_missing,
    valid_path,
)
from escudeiro.exc import InvalidCast, InvalidEnv, MissingName
from escudeiro.misc.pathx import is_valid_path
from escudeiro.misc.strings import squote


def test_boolean_returns_valid_bool():
    mapping = EnvMapping(
        {"first": "true", "second": "False", "third": "1", "fourth": "0"}
    )
    cfg = Config(mapping=mapping)

    assert cfg("first", boolean_cast)
    assert not cfg("second", boolean_cast)
    assert cfg("third", boolean_cast)
    assert not cfg("fourth", boolean_cast)
    assert boolean_cast.strict(True) is True
    assert boolean_cast.strict(False) is False


def test_boolean_raises_invalid_cast():
    """test boolean raises invalid cast if
    no boolean definition matches"""
    mapping = EnvMapping({"key": "value"})
    cfg = Config(mapping=mapping)

    with pytest.raises(InvalidCast):
        _ = cfg("key", boolean_cast.strict)


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
        _ = cfg("key", none_is_missing(boolean_cast.optional))
