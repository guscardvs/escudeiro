from typing import Literal

import orjson as json

from escudeiro.data import data, field
from escudeiro.data.converters.json import asjson, fromjson
from escudeiro.data.converters.utils import asdict, fromdict
from escudeiro.data.utils.factory import Factory, factory


@data
class ExampleClass:
    x: int
    y: str = field(alias="y_alias")


def test_as_dict():
    mapping = {"x": 1, "y": "hello"}
    parsed = fromdict(ExampleClass, mapping)
    assert asdict(parsed, by_alias=False) == {"x": 1, "y": "hello"}

    mapping = {"x": 1, "y": [1, 2, 3]}
    parsed = asdict(fromdict(ExampleClass, mapping))
    assert isinstance(parsed, dict)
    assert parsed == {"x": 1, "y": "[1, 2, 3]"}

    mapping = {"x": 1, "y": (1, 2, 3)}
    parsed = asdict(fromdict(ExampleClass, mapping))
    assert isinstance(parsed, dict)
    assert parsed == {"x": 1, "y": "(1, 2, 3)"}

    mapping = {"x": 1, "y": {1, 2, 3}}
    parsed = asdict(fromdict(ExampleClass, mapping))
    assert isinstance(parsed, dict)
    assert parsed == {"x": 1, "y": "{1, 2, 3}"}

    mapping = {"x": 1, "y": {"a": 1, "b": 2}}
    parsed = asdict(fromdict(ExampleClass, mapping))
    assert isinstance(parsed, dict)
    assert parsed == {"x": 1, "y": "{'a': 1, 'b': 2}"}


def test_unwrap_deeply_nested_mapping():
    """
    Test that unwrap properly unwraps a deeply nested mapping.
    """

    @data
    class D:
        d: str

    @data
    class C:
        c: tuple[D, ...]

    @data
    class B:
        b: C

    @data
    class A:
        a: B

    mapping = {"a": {"b": {"c": ({"d": "value"}, {"d": "another"})}}}

    unwrapped = asdict(A(B(C((D("value"), D("another"))))))

    assert unwrapped == mapping


def test_as_json():
    item = ExampleClass(1, "hello")
    assert asjson(item) == json.dumps({"x": 1, "y_alias": "hello"}).decode()
    assert (
        asjson(item, by_alias=False)
        == json.dumps({"x": 1, "y": "hello"}).decode()
    )


def test_nested_as_json():
    @data
    class Metadata:
        y: str = field(alias="meta")

    @data
    class B:
        x: int

    @data
    class A:
        a: B
        metadata: Metadata

    obj = A(B(1), Metadata("another"))

    assert (
        asjson(obj)
        == json.dumps({"a": {"x": 1}, "metadata": {"meta": "another"}}).decode()
    )

    assert (
        asjson(obj, by_alias=False)
        == json.dumps({"a": {"x": 1}, "metadata": {"y": "another"}}).decode()
    )


def test_fromjson():
    json_data = '{"x": 1, "y": "hello"}'
    assert fromjson(ExampleClass, json_data) == ExampleClass(1, "hello")

    @data
    class Metadata:
        y: str = field(alias="meta")

    @data
    class B:
        x: int

    @data
    class A:
        a: B
        metadata: Metadata

    obj = A(B(1), Metadata("another"))

    assert (
        fromjson(
            A,
            json.dumps({"a": {"x": 1}, "metadata": {"y": "another"}}).decode(),
        )
        == obj
    )


def test_factory_properly_returns_factory_parameter_on_nesting():
    @factory
    def func() -> Literal["Hello"]:
        return "Hello"

    other = factory(func)

    assert other is func and isinstance(func, Factory)
