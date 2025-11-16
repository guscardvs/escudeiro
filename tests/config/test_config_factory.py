import dataclasses
import sys
from enum import Enum
from types import SimpleNamespace
from typing import Any, Literal

import pytest
from attrs import asdict, define
from pydantic import BaseModel

from escudeiro import config
from escudeiro.config.adapter.attrs import AttrsResolverStrategy
from escudeiro.config.adapter.cache import CachedFactory as MemoFactory
from escudeiro.config.adapter.dataclass import DataclassResolverStrategy
from escudeiro.config.adapter.factory import AdapterConfigFactory
from escudeiro.config.adapter.pydantic import PydanticResolverStrategy
from escudeiro.config.adapter.squire import SquireResolverStrategy
from escudeiro.data import data
from escudeiro.data.converters import asdict as squire_asdict
from escudeiro.data.utils.functions import disassemble_type
from escudeiro.exc import InvalidCast
from escudeiro.misc import jsonx

if sys.version_info < (3, 14):
    from pydantic import v1
else:
    v1 = SimpleNamespace(BaseModel=BaseModel)


@dataclasses.dataclass(frozen=True)
class PersonConfig:
    name: str
    emails: tuple[str, ...]
    counts: set[int]
    meta: dict[str, Any]
    account: Literal["admin", "user"]


class AnotherConfig(BaseModel):
    name: str
    emails: tuple[str, ...]
    counts: set[int]
    meta: dict[str, Any]
    account: Literal["admin", "user"]


class AnotherV1Config(v1.BaseModel):
    name: str
    emails: tuple[str, ...]
    counts: set[int]
    meta: dict[str, Any]
    account: Literal["admin", "user"]


@define
class OtherConfig:
    name: str
    emails: tuple[str, ...]
    counts: set[int]
    meta: dict[str, Any]
    account: Literal["admin", "user"]


@data
class Another:
    name: str
    emails: tuple[str, ...]
    counts: set[int]
    meta: dict[str, Any]
    account: Literal["admin", "user"]


factory = AdapterConfigFactory()


def test_adapter_factory_identifies_strategy_correctly():
    assert (
        factory.get_strategy_class(disassemble_type(PersonConfig))
        is DataclassResolverStrategy
    )
    assert (
        factory.get_strategy_class(disassemble_type(AnotherConfig))
        is PydanticResolverStrategy
    )
    assert (
        factory.get_strategy_class(disassemble_type(AnotherV1Config))
        is PydanticResolverStrategy
    )
    assert (
        factory.get_strategy_class(disassemble_type(PersonConfig))
        is DataclassResolverStrategy
    )
    assert (
        factory.get_strategy_class(disassemble_type(OtherConfig))
        is AttrsResolverStrategy
    )
    assert (
        factory.get_strategy_class(disassemble_type(Another))
        is SquireResolverStrategy
    )


def test_adapter_parses_correctly_on_from_config():
    mapping = config.EnvMapping(
        {
            "NAME": "John Doe",
            "emails": "person@example.com,  john.doe@hi.com,doejohn@test.com",
            "COUNTS": "6,2, 7, 1",
            "ACCOUNT": "admin",
        }
    )
    cfg = config.Config(mapping=mapping)
    factory = config.AdapterConfigFactory(cfg)
    presets = {"meta": {"spouse": "Jane Doe"}}

    person_config = factory.load(PersonConfig, presets=presets)
    another_config = factory.load(AnotherConfig, presets=presets)
    another_v1_config = factory.load(AnotherV1Config, presets=presets)
    other_config = factory.load(OtherConfig, presets=presets)
    another = factory.load(Another, presets=presets)

    assert person_config.name == "John Doe"
    assert person_config.emails == (
        "person@example.com",
        "john.doe@hi.com",
        "doejohn@test.com",
    )
    assert person_config.counts == {6, 2, 7, 1}
    assert person_config.meta == {"spouse": "Jane Doe"}
    assert (
        dataclasses.asdict(person_config)
        == asdict(other_config)
        == (
            another_v1_config.dict()
            if sys.version_info < (3, 14)
            else another_config.model_dump()
        )
        == another_config.model_dump()
        == squire_asdict(another)
    )


def test_adapter_uses_json_loads_if_receives_dict_as_param():
    mapping = config.EnvMapping(
        {
            "NAME": "John Doe",
            "emails": "person@example.com,  john.doe@hi.com,doejohn@test.com",
            "COUNTS": "6,2, 7, 1",
            "meta": jsonx.dumps({"hello": "world"}),
            "account": "user",
        }
    )
    cfg = config.Config(mapping=mapping)
    factory = config.AdapterConfigFactory(cfg)
    person_config = factory.load(PersonConfig)
    assert person_config.meta == {"hello": "world"}


def test_boolean_cast_works_correctly():
    @data
    class CustomConfig:
        is_valid: bool

    assert (
        not config.AdapterConfigFactory(
            config.Config(mapping=config.EnvMapping({"IS_VALID": "False"}))
        )
        .load(CustomConfig)
        .is_valid
    )
    assert (
        not config.AdapterConfigFactory(
            config.Config(mapping=config.EnvMapping({"IS_VALID": "false"}))
        )
        .load(CustomConfig)
        .is_valid
    )
    assert (
        not config.AdapterConfigFactory(
            config.Config(mapping=config.EnvMapping({"IS_VALID": ""}))
        )
        .load(CustomConfig)
        .is_valid
    )
    assert (
        not config.AdapterConfigFactory(
            config.Config(mapping=config.EnvMapping({"IS_VALID": "0"}))
        )
        .load(CustomConfig)
        .is_valid
    )
    assert (
        not config.AdapterConfigFactory(
            config.Config(mapping=config.EnvMapping({"IS_VALID": "invalid"}))
        )
        .load(CustomConfig)
        .is_valid
    )
    assert (
        config.AdapterConfigFactory(
            config.Config(mapping=config.EnvMapping({"IS_VALID": "True"}))
        )
        .load(CustomConfig)
        .is_valid
    )
    assert (
        config.AdapterConfigFactory(
            config.Config(mapping=config.EnvMapping({"IS_VALID": "true"}))
        )
        .load(CustomConfig)
        .is_valid
    )
    assert (
        config.AdapterConfigFactory(
            config.Config(mapping=config.EnvMapping({"IS_VALID": "1"}))
        )
        .load(CustomConfig)
        .is_valid
    )


type LiteralValue = Literal["a", "b"]


def test_literal_cast_works_correctly():
    class Option(Enum):
        VALUE = "value"

    @data
    class Test:
        options: Literal[1, "Other", b"Another", Option.VALUE, False]

    @data
    class Defaults:
        value: LiteralValue = "b"

    assert (
        config.AdapterConfigFactory(
            config.Config(mapping=config.EnvMapping({"OPTIONS": "1"}))
        )
        .load(Test)
        .options
        == 1
    )
    assert (
        config.AdapterConfigFactory(
            config.Config(mapping=config.EnvMapping({"OPTIONS": "Other"}))
        )
        .load(Test)
        .options
        == "Other"
    )
    assert (
        config.AdapterConfigFactory(
            config.Config(mapping=config.EnvMapping({"OPTIONS": "Another"}))
        )
        .load(Test)
        .options
        == b"Another"
    )
    assert (
        config.AdapterConfigFactory(
            config.Config(mapping=config.EnvMapping({"OPTIONS": "value"}))
        )
        .load(Test)
        .options
        is Option.VALUE
    )
    assert (
        config.AdapterConfigFactory(
            config.Config(mapping=config.EnvMapping({"OPTIONS": "false"}))
        )
        .load(Test)
        .options
        is False
    )
    assert (
        config.AdapterConfigFactory(
            config.Config(mapping=config.EnvMapping({}))
        )
        .load(Defaults)
        .value
        == "b"
    )

    with pytest.raises(InvalidCast):
        assert config.AdapterConfigFactory(
            config.Config(mapping=config.EnvMapping({"OPTIONS": "invalid"}))
        ).load(Test)


def test_config_factory_support_for_nested_classes():
    @data
    class Test:
        name: str

    @data
    class Another:
        test: Test
        name: str

    cfg = config.Config(
        mapping=config.EnvMapping(
            {
                "NAME": "name",
                "TEST__NAME": "test_name",
                "ANOTHER_NAME": "another_name",
                "ANOTHER_TEST__NAME": "another_test_name",
            }
        )
    )

    factory = config.AdapterConfigFactory(cfg)

    assert factory.load(Another) == Another(Test("test_name"), "name")
    assert factory.load(Another, "another") == Another(
        Test("another_test_name"), "another_name"
    )


def test_memo_factory_does_not_reload_matching_calls():
    @data
    class Person:
        name: str
        email: str
        age: int

    cfg = config.Config(
        mapping=config.EnvMapping(
            {
                "PERSON_NAME": "John Doe",
                "PERSON_EMAIL": "johndoe@example.com",
                "PERSON_AGE": "30",
            }
        )
    )
    memo_factory = MemoFactory(cfg)

    assert memo_factory.load(Person, __prefix__="person") is memo_factory.load(
        Person, __prefix__="person"
    )


def test_memo_factory_reloads_for_different_prefix():
    @data
    class Person:
        name: str
        email: str
        age: int

    cfg = config.Config(
        mapping=config.EnvMapping(
            {
                "PERSON_NAME": "John Doe",
                "PERSON_EMAIL": "johndoe@example.com",
                "PERSON_AGE": "30",
                "NAME": "Doe John",
                "EMAIL": "doejohn@example.com",
                "AGE": "15",
            }
        )
    )
    memo_factory = MemoFactory(cfg)

    assert memo_factory.load(Person, __prefix__="person") != memo_factory.load(
        Person
    )


def test_memo_factory_reloads_for_different_types():
    @data
    class Person:
        name: str
        email: str
        age: int

    @data
    class Product:
        name: str
        category: str

    cfg = config.Config(
        mapping=config.EnvMapping(
            {
                "NAME": "John Doe",
                "EMAIL": "johndoe@example.com",
                "AGE": "30",
                "CATEGORY": "cleaning",
            }
        )
    )
    memo_factory = MemoFactory(cfg)

    person = memo_factory.load(Person)
    product = memo_factory.load(Product)

    assert isinstance(person, Person)
    assert person.name == "John Doe"
    assert person.email == "johndoe@example.com"
    assert person.age == 30
    assert isinstance(product, Product)
    assert product.name == "John Doe"
    assert product.category == "cleaning"


def test_memo_factory_primary_is_loaded_if_prefix_is_empty():
    @data
    class Person:
        name: str
        email: str
        age: int

    cfg = config.Config(
        mapping=config.EnvMapping(
            {
                "PERSON_NAME": "John Doe",
                "PERSON_EMAIL": "johndoe@example.com",
                "PERSON_AGE": "30",
            }
        )
    )
    memo_factory = MemoFactory(cfg)

    assert memo_factory.load(
        Person, __prefix__="person", __primary__=True
    ) is memo_factory.load(Person)
