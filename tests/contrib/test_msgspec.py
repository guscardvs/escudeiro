from typing import cast

import msgspec
import pytest
from msgspec import inspect

from escudeiro.contrib.msgspec import CamelStruct, PascalStruct
from escudeiro.lazyfields import lazyfield


def _get_field(model: type[msgspec.Struct], name: str) -> inspect.Field:
    return next(
        item
        for item in cast(inspect.StructType, inspect.type_info(model)).fields
        if item.name == name
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
