import sys
from typing import cast

import msgspec
import pytest
from msgspec import inspect

from escudeiro.contrib.msgspec import (
    CamelStruct,
    MsgspecTransformer,
    MsgspecTransformRegistry,
    PascalStruct,
)
from escudeiro.lazyfields import lazyfield


def _get_field(model: type[msgspec.Struct], name: str) -> inspect.Field:
    return next(
        item
        for item in cast(inspect.StructType, inspect.type_info(model)).fields
        if item.name == name
    )


@pytest.mark.skipif(
    sys.version_info >= (3, 14), reason="Incompatible with Python 3.14+"
)
def test_model_aliases_are_automatically_created_as_camel():
    class Person(PascalStruct):
        my_personal_name: str
        type_: str
        id_: int

    class AnotherPerson(CamelStruct):
        my_personal_name: str
        type_: str
        id_: int

    assert (
        _get_field(Person, "my_personal_name").encode_name == "MyPersonalName"
    )
    assert _get_field(Person, "type_").encode_name == "Type"
    assert _get_field(Person, "id_").encode_name == "Id"

    assert (
        _get_field(AnotherPerson, "my_personal_name").encode_name
        == "myPersonalName"
    )
    assert _get_field(AnotherPerson, "type_").encode_name == "type"
    assert _get_field(AnotherPerson, "id_").encode_name == "id"


@pytest.mark.skipif(
    sys.version_info >= (3, 14), reason="Incompatible with Python 3.14+"
)
def test_struct_support_lazyfields():
    with pytest.raises(
        TypeError, match="msgspec.Struct Person doesn't support lazyfields"
    ):

        class Person(PascalStruct):
            name: str
            surname: str

            @lazyfield
            def full_name(self):
                return f"{self.name} {self.surname}"

        _ = Person


@pytest.mark.skipif(
    sys.version_info >= (3, 14), reason="Incompatible with Python 3.14+"
)
def test_msgspec_transformer_caches_decode():
    class Person(msgspec.Struct):
        name: str
        age: int

    transformer = MsgspecTransformer(Person)

    # Call the transformer to ensure it works
    person_instance = transformer()({"name": "John", "age": 30})
    assert isinstance(person_instance, Person)
    assert person_instance.name == "John"
    assert person_instance.age == 30


@pytest.mark.skipif(
    sys.version_info >= (3, 14), reason="Incompatible with Python 3.14+"
)
def test_msgspec_transform_registry_registers_transformer():
    class Person(msgspec.Struct):
        name: str
        age: int

    registry = MsgspecTransformRegistry()

    registered_transformer = registry.require_decoder(Person)

    # Use the transformer to decode a message
    person_instance = registry.require_decoder(Person)(
        {"name": "Alice", "age": 25}
    )
    assert isinstance(person_instance, Person)
    assert person_instance.name == "Alice"
    assert person_instance.age == 25
    assert registry.lookup(Person) is registered_transformer
