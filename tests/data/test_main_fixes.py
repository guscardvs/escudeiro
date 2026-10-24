# ruff: noqa: UP045, UP007
from collections.abc import Callable
from enum import Enum, IntEnum
from types import ModuleType
from typing import Any, Generic, Optional, TypeVar

import pytest

from escudeiro.data import (
    UNINITIALIZED,
    asdict,
    data,
    field,
    fromdict,
    get_fields,
)
from escudeiro.misc import StrEnum
from escudeiro.misc.typex import is_hashable

LoadModule = Callable[[str], ModuleType]


# ---- hash / eq consistency -------------------------------------------------


def test_frozen_class_with_future_annotations_is_hashable(
    load_module: LoadModule,
):
    module = load_module(
        """
        from __future__ import annotations

        from escudeiro.data import data

        @data(frozen=True)
        class A:
            x: int
            y: str = "a"
        """
    )

    assert hash(module.A(1)) == hash(module.A(1))
    assert {module.A(1): 1}[module.A(1)] == 1


def test_unresolved_forward_ref_is_hashed_and_fails_only_on_call():
    @data
    class Holder:
        value: "Whatever"  # pyright: ignore[reportUndefinedVariable]  # noqa: F821

    assert hash(Holder(1)) == hash(Holder(1))
    with pytest.raises(TypeError):
        _ = hash(Holder([]))


def test_typevar_field_is_hashed():
    t = TypeVar("t")

    @data
    class Box(Generic[t]):
        item: t

    assert hash(Box(1)) == hash(Box(1))


def test_typing_list_is_unhashable_like_builtin_list():
    from typing import List  # noqa: UP035

    assert not is_hashable(List[int])  # noqa: UP006
    assert not is_hashable(Optional[List[int]])  # noqa: UP006
    assert is_hashable(Optional[int])
    assert not is_hashable(list["Later"])  # pyright: ignore[reportUndefinedVariable]  # noqa: F821
    assert is_hashable(TypeVar("t"), unresolved_ok=True)
    assert not is_hashable(TypeVar("t"))

    with pytest.raises(TypeError, match="field type is not hashable"):

        @data(hash=True)
        class A:
            x: List[int]  # noqa: UP006

    @data
    class B:
        x: List[int]  # noqa: UP006
        y: int

    assert hash(B([1], 2)) == hash(B([2], 2))  # list is left out of the hash


def test_hash_ignores_fields_left_out_of_eq():
    @data
    class E:
        a: int
        b: int = field(eq=False)

    assert E(1, 2) == E(1, 3)
    assert hash(E(1, 2)) == hash(E(1, 3))
    assert hash(E(1, 2)) != hash(E(2, 2))


def test_class_without_fields_compares_equal_and_hashes_to_a_constant():
    @data
    class Empty:
        pass

    @data
    class Other:
        pass

    assert Empty() == Empty()
    assert Empty() != Other()
    assert hash(Empty()) == hash(Empty())
    assert len({Empty(), Empty()}) == 1


def test_class_with_only_eq_false_fields_is_equal_and_hashable():
    @data
    class Ignored:
        a: int = field(eq=False)

    assert Ignored(1) == Ignored(2)
    assert hash(Ignored(1)) == hash(Ignored(2))


# ---- keyword-only ----------------------------------------------------------


def test_class_wide_kw_only_makes_every_field_keyword_only():
    @data(kw_only=True)
    class K:
        a: int
        b: int = 2

    assert K(a=1) == K(a=1, b=2)
    with pytest.raises(TypeError):
        _ = K(5)  # pyright: ignore[reportCallIssue]


def test_class_wide_kw_only_allows_required_after_default():
    @data(kw_only=True)
    class K:
        a: int = 1
        b: int

    assert K(b=3).b == 3


def test_field_level_kw_only_keeps_other_fields_positional():
    @data
    class P:
        a: int
        b: int = field(kw_only=True)

    assert P(1, b=2).b == 2
    with pytest.raises(TypeError):
        _ = P(1, 2)  # pyright: ignore[reportCallIssue]


# ---- schema generation -----------------------------------------------------


class PlainEnum(Enum):
    RED = "red"
    BLUE = "blue"


class Level(IntEnum):
    LOW = 1
    HIGH = 2


class Mode(StrEnum):
    FAST = "fast"


class Mixed(Enum):
    A = 1
    B = "b"


def _schema_of(cls: type) -> dict[str, Any]:
    schema: dict[str, Any] = {}
    cls.__modify_schema__(schema)  # pyright: ignore[reportAttributeAccessIssue]
    return schema


def test_schema_required_matches_property_keys():
    @data(pydantic=True)
    class S:
        my_field: int
        other_field: str
        optional_one: int = 1

    schema = _schema_of(S)

    assert schema["required"] == ["myField", "otherField"]
    assert set(schema["required"]) <= set(schema["properties"])


def test_schema_ignores_non_init_fields_as_required():
    @data(pydantic=True)
    class S:
        a: int
        b: int = field(init=False)

    assert _schema_of(S)["required"] == ["a"]


def test_schema_supports_every_enum_flavour():
    @data(pydantic=True)
    class S:
        plain: PlainEnum
        level: Level
        mode: Mode

    props = _schema_of(S)["properties"]

    assert props["plain"]["type"] == "string"
    assert props["plain"]["enum"] == ["red", "blue"]
    assert props["level"]["type"] == "integer"
    assert props["level"]["enum"] == [1, 2]
    assert props["mode"]["type"] == "string"
    assert props["mode"]["enum"] == ["fast"]


def test_schema_rejects_enums_with_mixed_values():
    with pytest.raises(NotImplementedError, match="Mixed"):

        @data(pydantic=True)
        class S:
            mixed: Mixed


def test_schema_supports_nested_and_optional_containers():
    @data(pydantic=True)
    class S:
        matrix: list[list[int]]
        by_name: dict[str, list[int]]
        maybe: Optional[list[int]] = None
        union: list[int] | None = None
        fixed: tuple[int, ...] = ()

    props = _schema_of(S)["properties"]
    int_array = {"type": "array", "items": [{"type": "integer"}]}

    assert props["matrix"] == {"type": "array", "items": [int_array]}
    assert props["byName"] == {
        "type": "object",
        "additionalProperties": int_array,
    }
    assert props["maybe"] == {"anyOf": [int_array, {"type": "null"}]}
    assert props["union"] == {"anyOf": [int_array, {"type": "null"}]}
    assert props["fixed"] == int_array


def test_schema_describes_nested_models_with_aliased_required():
    @data
    class Child:
        child_name: str

    @data(pydantic=True)
    class S:
        child: Child
        children: list[Child]

    props = _schema_of(S)["properties"]

    assert props["child"]["required"] == ["childName"]
    assert props["children"]["items"][0]["required"] == ["childName"]


# ---- smaller defects -------------------------------------------------------


def test_frozen_without_slots_rejects_every_new_attribute():
    @data(slots=False)
    class F:
        x: int

    f = F(1)
    with pytest.raises(AttributeError):
        f.y = 2  # pyright: ignore[reportAttributeAccessIssue]
    with pytest.raises(AttributeError):
        f.z = 3  # pyright: ignore[reportAttributeAccessIssue]
    with pytest.raises(AttributeError):
        f.x = 5  # pyright: ignore[reportAttributeAccessIssue]
    assert f.__dict__ == {"x": 1}


def test_init_false_field_without_default_may_follow_a_default():
    @data
    class F:
        a: int = 1
        b: int = field(init=False)

    f = F()

    assert f.a == 1
    assert f.b is UNINITIALIZED


def test_non_default_after_default_still_fails():
    with pytest.raises(ValueError, match="after field with default"):

        @data
        class F:
            a: int = 1
            b: int


@pytest.mark.parametrize("alias", ["my-x", "1x", "a b", "class", "_"])
def test_invalid_alias_is_reported_clearly(alias: str):
    with pytest.raises(ValueError, match="Invalid alias"):

        @data
        class F:
            a: int = field(alias=alias)


def test_invalid_alias_is_fine_for_fields_outside_init():
    @data
    class F:
        a: int = field(init=False, alias="my-x", default=1)

    assert asdict(F(), by_alias=True) == {"my-x": 1}


def test_callable_repr_result_is_used_as_is():
    @data
    class F:
        secret: str = field(repr=lambda _: "***")
        name: str = field(repr=str.upper)

    assert repr(F("pw", "ann")) == "F(secret=***, name=ANN)"


def test_factory_name_is_a_string_and_field_repr_shows_it():
    def make_items() -> list[int]:
        return []

    @data
    class F:
        items: list[int] = field(default_factory=make_items)

    items_field = get_fields(F)["items"]

    assert items_field.default.__name__ == "make_items"
    assert "default=make_items" in repr(items_field)
    assert "bound method" not in repr(items_field)


def test_module_globals_do_not_shadow_generated_helpers(
    load_module: LoadModule,
):
    module = load_module(
        """
        from escudeiro.data import data, field

        sentinel = "shadow"
        deserialize = "shadow"
        deserialize_mapping = "shadow"
        MISSING = "shadow"
        UNINITIALIZED = "shadow"
        dict_get = "shadow"
        missing_key = "shadow"

        @data
        class A:
            x: int = 3
            y: list[int] = field(default_factory=list)
            z: int = field(init=False, default=1)
        """
    )

    assert fromdict(module.A, {}) == module.A(3)
    assert asdict(module.A(1, [1])) == {"x": 1, "y": [1], "z": 1}
