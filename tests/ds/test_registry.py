from collections.abc import Callable
from enum import Enum
from typing import Any

import pytest

from escudeiro.ds.registry import CallableRegistry, Registry, TransformRegistry
from escudeiro.exc.errors import AlreadySet, MissingName
from escudeiro.misc import ValueEnum


# Dummy enum for testing
class Color(ValueEnum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


def test_registry_register_and_lookup():
    reg = Registry(with_enum=Color)
    reg.register(Color.RED, 1)
    reg.register(Color.GREEN, 2)
    assert reg.lookup(Color.RED) == 1
    assert reg.lookup(Color.GREEN) == 2
    assert reg[Color.RED] == 1
    assert reg[Color.GREEN] == 2


def test_registry_missing_key_raises_keyerror():
    reg = Registry(with_enum=Color)
    reg.register(Color.RED, 1)
    with pytest.raises(MissingName):
        reg.lookup(Color.BLUE)


def test_registry_validate_success():
    reg = Registry(with_enum=Color)
    for color in Color:
        reg.register(color, color.value)
    reg.validate()  # Should not raise


def test_registry_validate_missing_keys():
    reg = Registry(with_enum=Color)
    reg.register(Color.RED, 1)
    with pytest.raises(MissingName) as excinfo:
        reg.validate()
    assert "Missing keys in registry" in str(excinfo.value)
    for missing in ["green", "blue"]:
        assert missing in str(excinfo.value)


def test_registry_len_and_iter():
    reg = Registry(with_enum=Color)
    reg.register(Color.RED, 1)
    reg.register(Color.GREEN, 2)
    keys = list(reg)
    assert set(keys) == {Color.RED, Color.GREEN}
    assert len(reg) == 2


def test_registry_prefix_and_post_init():
    reg = CallableRegistry(
        with_enum=Color, prefix="", use_enum_name_as_prefix=True
    )
    reg.__post_init__()
    assert reg.prefix == "color_"


def test_registry_custom_prefix():
    reg = CallableRegistry(
        with_enum=Color, prefix="my_", use_enum_name_as_prefix=True
    )
    reg.__post_init__()
    assert reg.prefix == "my_"


def test_callable_registry_registers_function():
    class FuncEnum(Enum):
        FOO = "foo"
        BAR = "bar"

    calls = {}

    def foo():
        calls["foo"] = True
        return "foo"

    def bar():
        calls["bar"] = True
        return "bar"

    reg = CallableRegistry(
        with_enum=FuncEnum, prefix="", use_enum_name_as_prefix=False
    )
    reg.register(FuncEnum.FOO, foo)
    reg.register(FuncEnum.BAR, bar)
    assert reg.lookup(FuncEnum.FOO)() == "foo"
    assert reg.lookup(FuncEnum.BAR)() == "bar"


def test_callable_registry_decorator_usage():
    class FuncEnum(Enum):
        FOO = "foo"
        BAR = "bar"

    reg = CallableRegistry[FuncEnum, Callable[[], str]](
        with_enum=FuncEnum, prefix="", use_enum_name_as_prefix=False
    )

    @reg
    def foo():
        return "foo"

    @reg
    def bar():
        return "bar"

    assert reg.lookup(FuncEnum.FOO)() == "foo"
    assert reg.lookup(FuncEnum.BAR)() == "bar"


def test_registry_checks_for_collision():
    reg = Registry(with_enum=Color)
    reg.register(Color.RED, 1)
    with pytest.raises(AlreadySet):
        reg.register(Color.RED, 2)  # Should raise AlreadySet error
    with pytest.raises(MissingName):
        reg.lookup(Color.BLUE)  # Should raise MissingName error


def test_transform_registry_register_and_lookup():
    registry = TransformRegistry()

    class Example:
        def __init__(self, value: Any) -> None:
            self.value = value

    def example_transformer(value: Any) -> Example:
        return Example(value)

    registry.register(Example, example_transformer)

    transformer = registry.lookup(Example)
    assert isinstance(transformer, Callable)
    example_instance = transformer("test")
    assert isinstance(example_instance, Example)
    assert example_instance.value == "test"


def test_transform_registry_raises_missing_name():
    registry = TransformRegistry()

    class Example:
        pass

    with pytest.raises(MissingName):
        _ = registry.lookup(Example)  # Should raise MissingName error


def test_transform_registry_raises_already_set():
    registry = TransformRegistry()

    class Example:
        pass

    def example_transformer(value: Any) -> Example:
        return Example()

    registry.register(Example, example_transformer)

    with pytest.raises(AlreadySet):
        registry.register(
            Example, example_transformer
        )  # Should raise AlreadySet error


def test_transform_registry_registers_multiple_transformers():
    registry = TransformRegistry()

    class ExampleA:
        def __init__(self, value: Any) -> None:
            self.value = value

    class ExampleB:
        def __init__(self, value: Any) -> None:
            self.value = value

    def example_a_transformer(value: Any) -> ExampleA:
        return ExampleA(value)

    def example_b_transformer(value: Any) -> ExampleB:
        return ExampleB(value)

    registry.register(ExampleA, example_a_transformer)
    registry.register(ExampleB, example_b_transformer)

    a_transformer = registry.lookup(ExampleA)
    b_transformer = registry.lookup(ExampleB)

    assert isinstance(a_transformer("test_a"), ExampleA)
    assert isinstance(b_transformer("test_b"), ExampleB)
