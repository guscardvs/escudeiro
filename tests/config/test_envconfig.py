import itertools
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
    environ = EnvMapping({"CONFIG_DOTFILE": str(PARENT_DIR / ".envconfig")})

    env_config = EnvConfig(DotFile("invalid", Env.LOCAL), mapping=environ)
    assert env_config.dotfile
    assert env_config.dotfile.filename == PARENT_DIR / ".envconfig"
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


def test_env_orders_by_weight():
    ordered = [Env.LOCAL, Env.TEST, Env.DEV, Env.QA, Env.PRD, Env.ALWAYS]

    for low, high in itertools.combinations(ordered, 2):
        assert low < high
        assert low <= high
        assert high > low
        assert high >= low
        assert not high < low
        assert not low > high
    assert Env.DEV >= Env.DEV
    assert Env.DEV <= Env.DEV
    assert sorted(reversed(ordered)) == ordered


def test_env_compared_with_foreign_types_is_not_ordered():
    with pytest.raises(TypeError):
        _ = Env.DEV < 3  # pyright: ignore[reportOperatorIssue]


def _dotfiles(tmp_path: Path, *names: str) -> dict[str, Path]:
    paths = {}
    for name in names:
        paths[name] = tmp_path / f".env.{name}"
        paths[name].write_text(f"WHO={name}\n")
    return paths


def _who(env: str, tmp_path: Path, *dotfiles: DotFile) -> str:
    env_config = EnvConfig(*dotfiles, mapping=EnvMapping({"CONFIG_ENV": env}))
    return env_config("WHO")


def test_exact_dotfile_wins_over_cascading_ones(tmp_path: Path):
    files = _dotfiles(tmp_path, "local", "dev", "prd")

    assert (
        _who(
            "dev",
            tmp_path,
            DotFile(files["local"], Env.LOCAL, cascade=True),
            DotFile(files["dev"], Env.DEV),
            DotFile(files["prd"], Env.PRD, cascade=True),
        )
        == "dev"
    )


def test_cascading_dotfile_applies_to_lower_envs_only(tmp_path: Path):
    files = _dotfiles(tmp_path, "dev")
    dotfile = DotFile(files["dev"], Env.DEV, cascade=True)

    assert _who("local", tmp_path, dotfile) == "dev"
    assert _who("test", tmp_path, dotfile) == "dev"
    with pytest.raises(MissingName):
        _who("qa", tmp_path, dotfile)
    with pytest.raises(MissingName):
        _who("prd", tmp_path, dotfile)


def test_closest_cascading_dotfile_applies(tmp_path: Path):
    files = _dotfiles(tmp_path, "dev", "prd")
    dotfiles = (
        DotFile(files["prd"], Env.PRD, cascade=True),
        DotFile(files["dev"], Env.DEV, cascade=True),
    )

    assert _who("test", tmp_path, *dotfiles) == "dev"
    assert _who("qa", tmp_path, *dotfiles) == "prd"


def test_always_dotfile_applies_to_every_env(tmp_path: Path):
    files = _dotfiles(tmp_path, "always")
    dotfile = DotFile(files["always"], Env.ALWAYS, cascade=True)

    for env in ("local", "test", "dev", "qa", "prd"):
        assert _who(env, tmp_path, dotfile) == "always"


@pytest.mark.parametrize("strict", [True, False])
def test_typo_in_config_env_raises_and_names_the_variable(strict: bool):
    environ = EnvMapping({"CONFIG_ENV": "prod"})

    with pytest.raises(InvalidCast, match="CONFIG_ENV") as exc_info:
        _ = EnvConfig(mapping=environ, strict=strict)

    assert "prod" not in str(exc_info.value)


@pytest.mark.parametrize("strict", [True, False])
def test_typo_in_config_env_does_not_fall_back_to_default_env(strict: bool):
    environ = EnvMapping({"CONFIG_ENV": "prod"})
    with pytest.raises(InvalidCast, match="CONFIG_ENV"):
        _ = EnvConfig(mapping=environ, strict=strict, default_env=Env.LOCAL)


def test_absent_config_env_falls_back_to_default_env():
    for strict in (True, False):
        env_config = EnvConfig(
            mapping=EnvMapping({}), strict=strict, default_env=Env.DEV
        )
        assert env_config.env is Env.DEV


def test_empty_config_env_counts_as_absent():
    environ = EnvMapping({"CONFIG_ENV": ""})

    assert EnvConfig(mapping=environ, default_env=Env.QA).env is Env.QA
    assert EnvConfig(mapping=environ, strict=False).env is None


def test_strict_missing_config_env_names_the_variable():
    with pytest.raises(MissingName, match="CONFIG_ENV") as exc_info:
        _ = EnvConfig(mapping=EnvMapping({}))

    assert "bound method" not in str(exc_info.value)


def test_custom_env_var_is_named_in_errors():
    with pytest.raises(MissingName, match="MY_ENV"):
        _ = EnvConfig(mapping=EnvMapping({}), env_var="MY_ENV")


def test_config_dotfile_does_not_defeat_ignore_default(tmp_path: Path):
    dotfile = tmp_path / ".override"
    dotfile.write_text("NAME=from-override\n")
    environ = EnvMapping({"CONFIG_ENV": "prd", "CONFIG_DOTFILE": str(dotfile)})
    env_config = EnvConfig(
        mapping=environ, ignore_default_rule=lambda env: env is Env.PRD
    )

    assert env_config.env is Env.PRD
    assert env_config.ignore_default
    assert env_config("NAME") == "from-override"
    with pytest.raises(MissingName):
        env_config("NOPE", str, "default")


def test_config_dotfile_without_config_env_still_loads(tmp_path: Path):
    dotfile = tmp_path / ".override"
    dotfile.write_text("NAME=from-override\n")
    environ = EnvMapping({"CONFIG_DOTFILE": str(dotfile)})

    env_config = EnvConfig(mapping=environ)

    assert env_config.env is Env.ALWAYS
    assert env_config("NAME") == "from-override"


def test_config_dotfile_pointing_nowhere_raises(tmp_path: Path):
    environ = EnvMapping({"CONFIG_DOTFILE": str(tmp_path / "nope")})

    with pytest.raises(InvalidCast, match="CONFIG_DOTFILE"):
        _ = EnvConfig(mapping=environ, strict=False)
