# string annotations on purpose: every adapter has to resolve them
from __future__ import annotations

import dataclasses
import sys
from typing import Any

import attrs
import pytest
from pydantic import BaseModel, Field

from escudeiro import config
from escudeiro.config import Env, EnvConfig, EnvMapping
from escudeiro.data import data, field
from escudeiro.exc import InvalidCast, MissingName


@dataclasses.dataclass
class DC:
    name: str
    port: int | None = None
    flag: bool = False
    tags: list[bool] = dataclasses.field(default_factory=list)
    ids: frozenset[int] = frozenset()
    opt: str | None = None
    internal: list[int] = dataclasses.field(init=False, default_factory=list)


@attrs.define
class AT:
    name: str
    port: int | None = None
    flag: bool = False
    tags: list[bool] = attrs.Factory(list)
    ids: frozenset[int] = frozenset()
    opt: str | None = None


class PD(BaseModel):
    name: str
    port: int | None = None
    flag: bool = False
    tags: list[bool] = Field(default_factory=list)
    ids: frozenset[int] = frozenset()
    opt: str | None = None


@data
class SQ:
    name: str
    port: int | None = None
    flag: bool = False
    tags: list[bool] = field(default_factory=list)
    ids: frozenset[int] = frozenset()
    opt: str | None = None


classes: list[type] = [DC, AT, PD, SQ]
if sys.version_info < (3, 14):
    from pydantic import v1

    class PDV1(v1.BaseModel):
        name: str
        port: int | None = None
        flag: bool = False
        tags: list[bool] = v1.Field(default_factory=list)
        ids: frozenset[int] = frozenset()
        opt: str | None = None

    classes.append(PDV1)


def make_factory(**values: str) -> config.AdapterConfigFactory:
    mapping = EnvMapping({key.upper(): val for key, val in values.items()})
    return config.AdapterConfigFactory(config.Config(mapping=mapping))


def prd_factory(**values: str) -> config.AdapterConfigFactory:
    mapping = EnvMapping(
        {"CONFIG_ENV": "prd"}
        | {key.upper(): val for key, val in values.items()}
    )
    env_config = EnvConfig(
        mapping=mapping, ignore_default_rule=lambda env: env is Env.PRD
    )
    return config.AdapterConfigFactory(env_config)


parametrize_cls = pytest.mark.parametrize(
    "cls", classes, ids=lambda cls: cls.__name__
)


def load(factory: config.AdapterConfigFactory, cls: type, **kw: Any) -> Any:
    return factory.load(cls, **kw)


@parametrize_cls
def test_defaults_none_and_factories_apply_when_absent(cls: type):
    result = load(make_factory(name="n"), cls)

    assert result.name == "n"
    assert result.port is None
    assert result.flag is False
    assert result.tags == []
    assert result.ids == frozenset()
    assert result.opt is None


@parametrize_cls
def test_default_factory_is_called_not_returned(cls: type):
    first = load(make_factory(name="n"), cls)
    second = load(make_factory(name="n"), cls)

    assert first.tags == []
    assert first.tags is not second.tags


@parametrize_cls
def test_values_use_the_resolved_annotations(cls: type):
    result = load(
        make_factory(
            name="n",
            port="8080",
            flag="true",
            tags="true,false,0",
            ids="1,2,2",
            opt="x",
        ),
        cls,
    )

    assert result.port == 8080
    assert result.flag is True
    assert result.tags == [True, False, False]
    assert result.ids == frozenset({1, 2})
    assert result.opt == "x"


@parametrize_cls
def test_optional_accepts_null_values(cls: type):
    assert load(make_factory(name="n", port="null"), cls).port is None


@parametrize_cls
def test_optional_still_validates_the_value(cls: type):
    with pytest.raises(InvalidCast) as exc_info:
        load(make_factory(name="n", port="abc"), cls)

    assert "abc" not in str(exc_info.value)


@parametrize_cls
def test_required_field_raises_missing_name(cls: type):
    with pytest.raises(MissingName):
        load(make_factory(), cls)


@parametrize_cls
def test_falsy_default_given_to_load_is_used(cls: type):
    result = load(make_factory(name="n"), cls, port=0, flag=False)

    assert result.port == 0


@parametrize_cls
def test_env_value_wins_over_default_given_to_load(cls: type):
    assert load(make_factory(name="n", port="1"), cls, port=0).port == 1


@parametrize_cls
def test_defaults_are_ignored_where_the_config_ignores_them(cls: type):
    with pytest.raises(MissingName):
        load(prd_factory(name="n"), cls)

    everything = prd_factory(
        name="n", port="1", flag="1", tags="1", ids="1", opt="o"
    )
    assert load(everything, cls).port == 1


def test_defaults_are_honored_outside_ignoring_environments():
    mapping = EnvMapping({"CONFIG_ENV": "dev", "NAME": "n"})
    env_config = EnvConfig(
        mapping=mapping, ignore_default_rule=lambda env: env is Env.PRD
    )

    result = load(config.AdapterConfigFactory(env_config), DC)

    assert result.port is None


def test_non_init_fields_are_not_loaded():
    assert load(make_factory(name="n", internal="1"), DC).internal == []


@dataclasses.dataclass
class Unresolvable:
    value: DoesNotExist  # noqa: F821  # pyright: ignore


def test_unresolvable_annotation_names_the_field():
    with pytest.raises(InvalidCast) as exc_info:
        load(make_factory(value="1"), Unresolvable)

    assert "Unresolvable.value" in str(exc_info.value)


@dataclasses.dataclass
class Inner:
    value: int = 1
    other: str = "o"


@dataclasses.dataclass
class Outer:
    inner: Inner
    name: str = "outer"


def test_nested_models_receive_the_defaults():
    result = load(make_factory(), Outer, inner__value=5)

    assert result == Outer(Inner(5, "o"), "outer")


def test_nested_models_still_read_the_environment():
    assert load(make_factory(inner__value="7"), Outer).inner.value == 7
