from collections.abc import Callable
from enum import Enum

import pytest

from escudeiro.ds.registry import CallableRegistry, Registry
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