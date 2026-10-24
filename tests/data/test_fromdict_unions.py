# ruff: noqa: UP045, UP007
from datetime import date, datetime
from typing import Any, Optional, Union

import pytest

from escudeiro.data import asdict, data, field, fromdict, private


@data
class Inner:
    v: int


@data
class Holder:
    a: int | None = None
    b: Optional[Inner] = None
    c: Union[datetime, None] = None
    d: list[Inner] | None = None
    e: Optional[date] = None
    f: int | str | None = None


def test_optional_int_accepts_value_none_and_missing():
    assert fromdict(Holder, {"a": 1}).a == 1
    assert fromdict(Holder, {"a": None}).a is None
    assert fromdict(Holder, {}).a is None


def test_optional_converts_the_non_none_arm():
    holder = fromdict(
        Holder,
        {
            "b": {"v": 1},
            "c": "2020-01-02T03:04:05",
            "d": [{"v": 2}, {"v": 3}],
            "e": "2021-02-03",
        },
    )

    assert holder.b == Inner(1)
    assert holder.c == datetime(2020, 1, 2, 3, 4, 5)
    assert holder.d == [Inner(2), Inner(3)]
    assert holder.e == date(2021, 2, 3)


def test_optional_converters_let_none_through():
    holder = fromdict(Holder, {"b": None, "c": None, "d": None, "e": None})

    assert (holder.b, holder.c, holder.d, holder.e) == (None, None, None, None)


def test_unions_with_several_non_none_arms_pass_through():
    assert fromdict(Holder, {"f": "x"}).f == "x"
    assert fromdict(Holder, {"f": 3}).f == 3
    assert fromdict(Holder, {"f": None}).f is None


def test_optional_fields_round_trip_through_asdict():
    mapping: dict[str, Any] = {
        "a": 1,
        "b": {"v": 1},
        "c": datetime(2020, 1, 2),
        "d": [{"v": 2}],
        "e": date(2021, 2, 3),
        "f": "x",
    }

    holder = fromdict(
        Holder,
        mapping
        | {"c": mapping["c"].isoformat(), "e": mapping["e"].isoformat()},
    )

    assert asdict(holder) == mapping
    assert holder.__parse_dict__(False)["b"] == {"v": 1}  # pyright: ignore[reportAttributeAccessIssue]
    assert holder.__parse_dict__(False)["d"] == [{"v": 2}]  # pyright: ignore[reportAttributeAccessIssue]
    assert Holder().__parse_dict__(False)["b"] is None  # pyright: ignore[reportAttributeAccessIssue]


def test_defaults_are_used_as_they_are():
    @data
    class WithDefaults:
        inner: Inner = Inner(7)
        when: datetime = field(default_factory=lambda: datetime(2000, 1, 1))
        items: list[Inner] = field(default_factory=list)

    result = fromdict(WithDefaults, {})

    assert result.inner == Inner(7)
    assert result.when == datetime(2000, 1, 1)
    assert result.items == []


def test_default_factory_only_runs_when_the_key_is_missing():
    calls: list[int] = []

    def make() -> list[int]:
        calls.append(1)
        return []

    @data
    class WithFactory:
        items: list[int] = field(default_factory=make)

    assert fromdict(WithFactory, {"items": [1]}).items == [1]
    assert calls == []
    assert fromdict(WithFactory, {}).items == []
    assert calls == [1]


def test_non_init_fields_do_not_break_fromdict():
    @data(frozen=False)
    class WithPrivate:
        a: int
        cache: dict[str, int] = private(initial_factory=dict)
        late: str = field(init=False)
        derived: int = private(ref=lambda self: self.a * 2)

    original = WithPrivate(2)
    original.cache["k"] = 1
    mapping = asdict(original)

    assert "cache" in mapping  # asdict still emits them...
    restored = fromdict(WithPrivate, mapping)  # ...but fromdict skips them
    assert restored.a == 2
    assert restored.cache == {}
    assert restored.derived == 4


def test_private_named_field_round_trips():
    @data
    class Underscore:
        _x: int
        y: int = 2

    assert fromdict(Underscore, {"_x": 1}) == Underscore(x=1)


def test_frozen_class_with_a_default_none_optional_nested_model():
    @data
    class Wrapper:
        inner: Optional[Inner] = None

    assert fromdict(Wrapper, {"inner": {"v": 5}}) == Wrapper(Inner(5))
    assert fromdict(Wrapper, {}) == Wrapper()


def test_missing_required_key_still_names_the_key():
    with pytest.raises(KeyError, match="Key 'v' or alias 'v' not found"):
        _ = fromdict(Inner, {})
