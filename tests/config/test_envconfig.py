from pathlib import Path

import pytest

from escudeiro.config import DotFile, Env, EnvConfig, EnvMapping
from escudeiro.exc import InvalidCast, MissingName

PARENT_DIR = curpath = Path(__file__).resolve().parent


def test_envconfig_returns_file_vals_if_in_expected_env():
    """EnvConfig should consider file_vals
    if env matches consider_file_on_env"""
    environ = EnvMapping({"CONFIG_ENV": Env.LOCAL.name})
    config = EnvConfig(
        DotFile(PARENT_DIR / ".envconfig", Env.LOCAL),
        mapping=environ,
    )

    assert config.env is Env.LOCAL
    assert config("NAME") == "teste"


def test_envconfig_does_not_find_value_if_not_in_expected_env():
    environ = EnvMapping({"CONFIG_ENV": Env.DEV.name})
    config = EnvConfig(
        DotFile(PARENT_DIR / ".envconfig", Env.LOCAL),
        mapping=environ,
    )

    with pytest.raises(MissingName):
        config("NAME")


def test_envconfig_raises_missing_name_if_no_env_is_found():
    with pytest.raises(MissingName):
        _ = EnvConfig(DotFile(PARENT_DIR / ".envconfig", Env.LOCAL))


def test_envconfig_raises_invalid_cast_if_env_val_is_invalid():
    environ = EnvMapping({"CONFIG_ENV": "invalid"})

    with pytest.raises(InvalidCast):
        _ = EnvConfig(
            DotFile(PARENT_DIR / ".envconfig", Env.LOCAL),
            mapping=environ,
        )


def test_envconfig_opens_config_dotfile_if_passed():
    environ = EnvMapping({"CONFIG_DOTFILE": "tests/config/.envconfig"})

    env_config = EnvConfig(DotFile("invalid", Env.LOCAL), mapping=environ)
    assert env_config.dotfile
    assert env_config.dotfile.filename == Path("tests/config/.envconfig")
    assert env_config.dotfile.env == Env.ALWAYS
    assert env_config("NAME") == "teste"


def test_env_config_uses_default_env_if_none_is_provided():
    environ = EnvMapping({"CONFIG_ENV": Env.DEV.name})
    config = EnvConfig(
        DotFile(PARENT_DIR / ".envconfig", Env.LOCAL), default_env=Env.LOCAL
    )
    with_env = EnvConfig(
        DotFile(PARENT_DIR / ".envconfig", Env.DEV),
        mapping=environ,
        default_env=Env.LOCAL,
    )

    assert config.env is Env.LOCAL
    assert with_env.env is Env.DEV
    assert (config("NAME"), with_env("NAME")) == ("teste", "teste")


def test_env_config_supports_envless_environment():
    config = EnvConfig(
        DotFile(PARENT_DIR / ".envconfig", Env.LOCAL),
        mapping=EnvMapping({}),
        strict=False,
    )

    assert config.env is None
