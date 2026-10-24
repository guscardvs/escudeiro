from pathlib import Path
from typing import final

import pytest
from hypothesis import given
from hypothesis.strategies import text

from escudeiro import config
from escudeiro.config import AdapterConfigFactory, CachedFactory, EnvConfig
from escudeiro.config.core.config import InvalidDotenv
from escudeiro.exc import FailedFileOperation, InvalidCast, MissingName
from escudeiro.misc.functions import Caster


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


SECRET = "s3cr3t-value"


def test_reprs_do_not_leak_the_mapping():
    mapping = config.EnvMapping({"DB_PASSWORD": SECRET})
    cfg = config.Config(mapping=mapping)
    env_cfg = EnvConfig(
        mapping=config.EnvMapping({"DB_PASSWORD": SECRET}), strict=False
    )

    for obj in (
        mapping,
        cfg,
        env_cfg,
        AdapterConfigFactory(cfg),
        CachedFactory(cfg),
        AdapterConfigFactory(env_cfg),
    ):
        assert SECRET not in repr(obj)
        assert "DB_PASSWORD" not in repr(obj)


def test_default_mapping_repr_does_not_leak_os_environ(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("DB_PASSWORD", SECRET)

    assert SECRET not in repr(config.Config())
    assert SECRET not in repr(config.DEFAULT_MAPPING)
    assert SECRET not in repr(AdapterConfigFactory())


def test_invalid_cast_message_names_variable_and_cast_only():
    cfg = config.Config(mapping=config.EnvMapping({"PASSWORD": SECRET}))

    with pytest.raises(InvalidCast) as exc_info:
        cfg("PASSWORD", int)

    message = str(exc_info.value)
    assert SECRET not in message
    assert "PASSWORD" in message
    assert "int" in message


def test_invalid_cast_message_names_caster_not_a_bound_method():
    cfg = config.Config(mapping=config.EnvMapping({"PORT": "x"}))

    with pytest.raises(InvalidCast, match="PORT") as exc_info:
        cfg("PORT", Caster(int).with_rule(lambda v: v > 0, "positive"))

    assert "bound method" not in str(exc_info.value)
    assert "int.with_rule(positive)" in str(exc_info.value)


def _env_file(tmp_path: Path, content: str | bytes) -> Path:
    filename = tmp_path / ".env"
    if isinstance(content, str):
        content = content.encode()
    filename.write_bytes(content)
    return filename


def test_dotenv_skips_utf8_bom(tmp_path: Path):
    filename = _env_file(tmp_path, b"\xef\xbb\xbfFIRST=1\nSECOND=2\n")
    cfg = config.Config(filename)

    assert cfg("FIRST") == "1"
    assert cfg("SECOND") == "2"


def test_dotenv_reads_utf8_whatever_the_locale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import builtins

    from escudeiro.config.core import config as config_module

    seen: list[object] = []

    def spy(*args: object, **kwargs: object):
        seen.append(kwargs.get("encoding"))
        return builtins.open(*args, **kwargs)  # pyright: ignore

    monkeypatch.setattr(config_module, "open", spy, raising=False)

    cfg = config.Config(_env_file(tmp_path, "NAME=caf\u00e9\n"))

    assert cfg("NAME") == "caf\u00e9"
    assert seen == ["utf-8-sig"]


def test_dotenv_export_prefix_is_stripped(tmp_path: Path):
    filename = _env_file(tmp_path, "export A=1\nexport\tB=2\nexportC=3\n")
    cfg = config.Config(filename)

    assert (cfg("A"), cfg("B"), cfg("exportC")) == ("1", "2", "3")
    with pytest.raises(MissingName):
        cfg("export A")


def test_dotenv_line_without_equals_reports_file_and_line(tmp_path: Path):
    filename = _env_file(tmp_path, "A=1\n\n# comment\nnot a pair\n")

    with pytest.raises(InvalidDotenv) as exc_info:
        _ = config.Config(filename)

    assert f"{filename}:4" in str(exc_info.value)
    assert "not a pair" not in str(exc_info.value)


def test_dotenv_empty_name_is_rejected(tmp_path: Path):
    with pytest.raises(InvalidDotenv, match=":1"):
        _ = config.Config(_env_file(tmp_path, "=1\n"))


def test_dotenv_invalid_utf8_is_a_typed_error(tmp_path: Path):
    with pytest.raises(InvalidDotenv):
        _ = config.Config(_env_file(tmp_path, b"A=\xff\xfe\n"))


def test_dotenv_blank_lines_and_comments_are_skipped(tmp_path: Path):
    cfg = config.Config(_env_file(tmp_path, "\n   \n# x\n  # y\nA = 1\n"))

    assert cfg("A") == "1"


def test_missing_env_file_is_ignored_unless_strict(tmp_path: Path):
    missing = tmp_path / "missing.env"

    assert config.Config(missing).file_values == {}
    with pytest.raises(FailedFileOperation, match="missing.env"):
        _ = config.Config(missing, strict=True)
