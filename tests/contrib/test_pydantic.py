from typing import NamedTuple

import pytest
from pydantic import ValidationError

from escudeiro.contrib.pydantic import Model, MutableModel
from escudeiro.lazyfields import lazyfield


def test_model_aliases_are_automatically_created_as_camel():
    class Person(Model):
        my_personal_name: str
        type_: str
        id_: int

    assert Person.model_fields["my_personal_name"].alias == "myPersonalName"
    assert Person.model_fields["type_"].alias == "type"
    assert Person.model_fields["id_"].alias == "id"


def test_model_is_frozen():
    class Person(Model):
        name: str

    person = Person(name="Hello")

    with pytest.raises(ValidationError):
        person.name = "world"


def test_model_supports_lazyfields():
    call_count = 0

    class Person(Model):
        name: str
        surname: str

        @lazyfield
        def full_name(self):
            nonlocal call_count
            call_count += 1
            return f"{self.name} {self.surname}"

    person = Person(name="John", surname="Doe")
    assert person.full_name == "John Doe"

    del person.full_name
    person.full_name = "Jane Doe"

    assert person.full_name == "Jane Doe"
    assert call_count == 1


def test_model_populates_by_alias_and_name():
    class Person(Model):
        id_: int
        type_: str

    person = Person(id=1, type_="2")  # pyright: ignore[reportCallIssue]

    assert person.id_ == 1
    assert person.type_ == "2"


def test_model_supports_from_attributes():
    class PersonTuple(NamedTuple):
        name: str
        email: str

    person_tuple = PersonTuple("John Doe", "test@example.com")

    class Person(Model):
        name: str
        email: str

    person = Person.model_validate(person_tuple)

    assert person.name == person_tuple.name
    assert person.email == person_tuple.email


def test_mutable_model_is_not_frozen():
    class Person(MutableModel):
        name: str

    person = Person(name="John Doe")

    person.name = "Jane Doe"

    assert person.name == "Jane Doe"
