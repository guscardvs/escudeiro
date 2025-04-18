from pathlib import Path
from typing import final

import pytest
from hypothesis import given
from hypothesis.strategies import text

from escudeiro import config
from escudeiro.exc import InvalidCast, MissingName


@given(text(), text())
def test_config_call_success(key: str, value: str):
    """test config call returns valid string
    from mapping source when name exists"""
    mapping = config.EnvMapping({key: value})
    cfg = config.Config(mapping=mapping)

    val = cfg(key)

    assert isinstance(val, str)
    assert val == value


def test_config_call_name_not_found():
    """test config call raises `config.MissingName`
    if name does not exists in source mapping"""
    mapping = config.EnvMapping({})
    cfg = config.Config(mapping=mapping)

    with pytest.raises(MissingName):
        cfg("invalid")


def test_config_cast_returns_cast_type():
    """test config cast returns cast type
    when name exists"""

    @final
    class _Cast:
        def __init__(self, val: str) -> None:
            self.val = val

    key = "key"
    value = "val"
    mapping = config.EnvMapping({key: value})
    cfg = config.Config(mapping=mapping)

    casted = cfg(key, _Cast)

    assert isinstance(casted, _Cast)
    assert casted.val == value


def test_config_cast_fails_with_invalid_cast():
    """test config cast fails with invalid cast
    when cast raises TypeError or ValueError"""

    def _fail_cast(val: str):
        _ = val
        raise TypeError

    mapping = config.EnvMapping({"key": "value"})
    cfg = config.Config(mapping=mapping)

    with pytest.raises(InvalidCast):
        cfg("key", _fail_cast)


def test_env_mapping_raises_errors_correctly_on_read():
    mapping = config.EnvMapping({})
    mapping["my-name"] = "val"
    mapping["my-name"]

    with pytest.raises(KeyError):
        mapping["my-name"] = "error"
    with pytest.raises(KeyError):
        del mapping["my-name"]


def test_config_reads_from_env_file(tmp_path: Path):
    filename = tmp_path / ".envtestfile"
    with open(filename, "w") as buf:
        buf.writelines(
            map(
                lambda val: f"{val}\n",
                [
                    "TEST_VALUE_FOUND=world",  # Testing a normal key-value pair
                    "# FULLY_COMMENTED=error",  # Testing a comment (should be ignored)
                    "TEST_QUOTE_CAPTURE='123abc'",  # Testing single quotes around value
                    'TEST_QUOTE_CAPTURE_WITH_SPACES=" 321 "',  # Testing double quotes with spaces
                    "TEST_DOUBLE_QUOTE_CAPTURE=\"'123'\"",  # Testing double quotes around value
                    "TEST_COMMENT_IN_VALUE=abc # comment",  # Testing comment after value (should be ignored)
                    "TEST_QUOTED_COMMENT_CAPTURE='abc # comment'",  # Testing single quotes with quoted comment
                    "TEST_VALUE_WITH_HASH=abc#comment",  # Testing value with hash, comment should not be taken into consideration
                    "TEST_QUOTE_WITH_COMMENT_CAPTURE='abc' # \"comment\"",  # Testing single quotes with inline comment
                    "TEST_QUOTE_CAPTURE_WITH_MIXED_COMMENTS='abc # comment\"",  # Testing single quotes with mixed comment format
                    "TEST_EMPTY_VALUE=",  # Testing empty value
                ],
            )
        )
    cfg = config.Config(filename)
    assert cfg("TEST_VALUE_FOUND") == "world"
    assert cfg("TEST_QUOTE_CAPTURE") == "123abc"
    assert cfg("TEST_QUOTE_CAPTURE_WITH_SPACES") == " 321 "
    assert cfg("TEST_DOUBLE_QUOTE_CAPTURE") == "'123'"
    assert cfg("TEST_COMMENT_IN_VALUE") == "abc"
    assert cfg("TEST_QUOTED_COMMENT_CAPTURE") == "abc # comment"
    assert cfg("TEST_VALUE_WITH_HASH") == "abc#comment"
    assert cfg("TEST_QUOTE_WITH_COMMENT_CAPTURE") == "abc"
    assert cfg("TEST_QUOTE_CAPTURE_WITH_MIXED_COMMENTS") == "'abc"
    assert cfg("TEST_EMPTY_VALUE") == ""

    with pytest.raises(MissingName):
        cfg("FULLY_COMMENTED")
