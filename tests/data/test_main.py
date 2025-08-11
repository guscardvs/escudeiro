import dataclasses
import pathlib
from collections.abc import Callable, Hashable, Sequence
from typing import Any, final, get_type_hints, override
from unittest.mock import Mock

import pytest

from escudeiro.data import (
    UNINITIALIZED,
    asdict,
    data,
    factory,
    field,
    fromdict,
)
from escudeiro.data.field_ import private
from escudeiro.data.helpers import call_init, init_hooks, squire_method
from escudeiro.data.methods import MethodBuilder
from escudeiro.misc import next_or


@data
class Person:
    name: str
    age: int


def test_instantiation_runs_without_errors():
    _ = Person("John Doe", 46)


def test_no_slots_class_is_also_valid():
    @data(slots=False)
    class NoSlots:
        x: int

    ns = NoSlots(1)

    assert {"x": 1} == ns.__dict__


def test_frozen_works_correctly():
    person = Person("John Doe", 46)

    with pytest.raises(AttributeError):
        person.name = "Jane Doe"  # pyright: ignore[reportAttributeAccessIssue]


def test_frozen_can_be_disabled():
    @data(frozen=False)
    class NotFrozen:
        x: int

    nf = NotFrozen(1)

    nf.x = 2

    assert nf.x == 2


def test_repr_returns_the_expected_string():
    @data
    class Another:
        email: str
        name: str = field(repr=str.title)
        password: str = field(repr=False)

    person = Person("Jane Doe", 30)
    another = Another("test@example.com", "valerica", "Very Important Secret")

    assert repr(person) == "Person(name='Jane Doe', age=30)"
    assert repr(another) == "Another(email='test@example.com', name='Valerica')"


def test_defaults_work_as_expected():
    @data
    class WithDefault:
        x: int = 4

    wd = WithDefault()

    assert wd.x == 4


def test_defaults_work_with_factory():
    def make_factory():
        val = 0

        def fac() -> int:
            nonlocal val
            val += 1
            return val

        return fac

    @data
    class WithFactory:
        x: int = field(default=factory(make_factory()))

    wf = WithFactory()
    wf2 = WithFactory()

    assert wf.x == 1
    assert wf2.x == 2


def test_exceptions_are_detected_and_handled():
    @data
    class E(Exception):
        msg: str
        other: int

    with pytest.raises(E) as ei:
        raise E("yolo", 42)

    e = ei.value

    assert ("yolo", 42) == e.args
    assert "yolo" == e.msg
    assert 42 == e.other


def test_mro_uses_the_rightmost_parent_attribute():
    @data
    class A:
        x: int = 10

        def xx(self) -> int:
            return 10

    @data
    class B(A):
        y: int = 20

    @data
    class C(A):
        x: int = 50

        @override
        def xx(self):
            return 50

    @data
    class D(B, C):
        pass

    d = D()

    assert d.x == d.xx()
    assert d.y == 20


def test_eq_validates_equality_correctly():
    @data
    class A:
        x: int

    a = A(1)
    a2 = A(1)
    assert a == a2


def test_eq_validates_inequality_correctly():  # sourcery skip: de-morgan
    @data(frozen=False, slots=False)
    class A:
        x: int

    eq_mock = Mock()
    eq_mock.return_value = True

    a = A(1)
    a.__eq__ = eq_mock
    a2 = A(1)

    assert not (a != a2)
    assert eq_mock.call_count == 1


def test_info_allows_opt_out_of_equality():
    @data
    class A:
        x: int
        y: int
        z: int = field(eq=False)

    assert A(1, 2, 3) == A(1, 2, 4)
    assert A(1, 2, 3) != A(1, 3, 3) != A(2, 2, 3)


def test_attrs_allow_addition_of_descriptors_on_slotted_classes():
    @final
    class AccessCounter:
        def __init__(self, func: Callable) -> None:
            self.func = func
            self.public_name = func.__name__
            self.private_name = f"_access_counter_{func.__name__}"

        def __set_name__(self, owner: type, name: str):
            self.public_name = name
            self.private_name = f"_access_counter_{name}"

        def __get__(self, instance: Any | None, owner: type):
            if not instance:
                return self
            value = getattr(instance, self.private_name, 0)
            result = self.func(instance)
            object.__setattr__(instance, self.private_name, value + 1)
            return result, value

    @data
    class MyCls:
        @AccessCounter
        def a(self):
            return "Hello"

    instance = MyCls()

    assert MyCls.a.private_name in MyCls.__slots__  # pyright: ignore[reportAttributeAccessIssue]
    assert instance.a == ("Hello", 0)
    assert instance.a == ("Hello", 1)
    assert instance.a == ("Hello", 2)


def test_alias_support_works_correctly():
    @data
    class A:
        x: int = field(alias="xVal")

    a = A(xVal=2)

    assert a.x == 2


def test_post_and_pre_init_work_correctly():
    val = 0

    @data
    class A:
        def __pre_init__(self):
            nonlocal val
            val += 1

        def __post_init__(self):
            nonlocal val
            val += 1

    _ = A()

    assert val == 2


def test_define_compares_correctly_with_parser():
    @data
    class Person:
        name: str = field(eq=str.lower)

    @data
    class A:
        x: int = field(eq=lambda val: val % 3)

    assert Person("John") == Person("john") != Person("jane")
    assert A(3) == A(6) != A(7)


def test_define_creates_ordering_correctly():
    @data
    class A:
        x: int
        y: int
        z: int

    @data(order=False)
    class Unorderable:
        x: int

    a1 = A(1, 2, 3)
    a2 = A(2, 3, 4)
    a3 = A(2, 4, 5)

    items = [a3, a1, a2]
    expected = [a1, a2, a3]

    for item in sorted(items):
        assert item is expected.pop(0)

    for item in ["__lt__", "__gt__", "__le__", "__ge__"]:
        assert hasattr(A, item)

    with pytest.raises(TypeError):
        _ = Unorderable(1) > Unorderable(2)  # pyright: ignore[reportOperatorIssue]


def test_define_creates_ordering_only_for_direct_instances():
    @data
    class A:
        x: int

    class B(A):
        pass

    with pytest.raises(TypeError):
        _ = A(1) < B(1)

    assert B(2) > B(1)  # ordering is inherited but not contravariant


def test_define_creates_hashable_classes():
    @data
    class A:
        x: int

    @data
    class B:
        x: int = field(eq=lambda val: val % 3)

    @data
    class C:
        x: int = field(hash=lambda val: val * 3)
        y: int = field(hash=False)

    @data
    class D:
        x: int = field(hash=lambda val: val / 3, eq=lambda val: val * 3)

    sentinel = object()

    assert isinstance(A(1), Hashable)
    assert {A(1): sentinel}[A(1)] is sentinel
    assert hash(A(2)) != hash(A(1)) == hash(A(1))
    assert hash(B(3)) == hash(B(6)) != hash(B(7))
    assert A(1) is not A(2)
    assert hash(C(3, 2)) == hash(C(3, 1))
    assert hash(D(3)) == hash((D, 3 / 3))


def test_define_does_not_create_hashable_when_it_shouldnt():
    @data(hash=False)
    class A:
        x: int

    @data(frozen=False)
    class B:
        x: int

    with pytest.raises(TypeError):
        _ = hash(A(1))
    with pytest.raises(TypeError):
        _ = hash(B(1))

    class C:
        x: list[int]  # pyright: ignore[reportUninitializedInstanceVariable]

    with pytest.raises(TypeError) as exc_info:
        _ = data(hash=True)(C)

    assert exc_info.value.args == (
        f"field type is not hashable: {list[int]!r} (field 'x' in C)",
    )
    assert not issubclass(data(C), Hashable), (
        "should not complain if class does not want explicitly hash"
    )


def test_define_does_not_overwrite_methods_but_creates_squire_alternatives():
    @data
    class A:
        z: int = False

    @data
    class B:
        a: int
        b: int

        def __init__(self, a: int, b: int):
            squire_method("init", self, a, b)

        @override
        def __repr__(self):
            return f"B(a={self.a}, b={self.b})"

        @override
        def __eq__(self, other: Any):
            if other.__class__ is self.__class__:
                return (self.a, self.b) == (other.a, other.b)
            else:
                return NotImplemented

        @override
        def __ne__(self, other: Any):
            result = self.__eq__(other)

            return NotImplemented if result is NotImplemented else not result

        def __lt__(self, other: Any):
            if other.__class__ is self.__class__:
                return (self.a, self.b) < (other.a, other.b)
            else:
                return NotImplemented

        def __le__(self, other: Any):
            if other.__class__ is self.__class__:
                return (self.a, self.b) <= (other.a, other.b)
            else:
                return NotImplemented

        def __gt__(self, other: Any):
            if other.__class__ is self.__class__:
                return (self.a, self.b) > (other.a, other.b)
            else:
                return NotImplemented

        def __ge__(self, other: Any):
            if other.__class__ is self.__class__:
                return (self.a, self.b) >= (other.a, other.b)
            else:
                return NotImplemented

        @override
        def __hash__(self):
            return hash((self.__class__, self.a, self.b))

    methods = [
        "__init__",
        "__repr__",
        "__eq__",
        "__hash__",
        "__ne__",
        "__lt__",
        "__le__",
        "__gt__",
        "__ge__",
    ]

    for method in methods:
        smethod = "_".join(("__squire", method.lstrip("_")))
        assert hasattr(A, method) and not hasattr(A, smethod)
        assert hasattr(B, smethod)


type Validator = Callable[[Any], bool]


def test_defines_correctly_classes_with_non_types_as_hints():
    @data
    class Whatever:
        validator: Validator
        root: pathlib.Path
        look_on: pathlib.Path | None = None
        exclude: Sequence[str | pathlib.Path] = ()

    _ = Whatever


def test_init_false_does_sets_values_with_proper_initial_values():
    @data
    class Whatever:
        name: str
        email: str = field(init=False)
        age: int = field(init=False, default=18)
        friend: list[str] = field(init=False, default_factory=list)

    whatever = Whatever("hello")

    assert whatever.email is UNINITIALIZED
    assert whatever.age == 18
    assert whatever.friend == []

    assert "email" not in get_type_hints(Whatever.__init__)

    whatever.email = "world"  # pyright: ignore[reportAttributeAccessIssue]
    assert whatever.email == "world"

    with pytest.raises(AttributeError):
        whatever.email = "Hello"  # pyright: ignore[reportAttributeAccessIssue]


def test_define_init_does_not_add_init_function():
    @data(init=False, frozen=False)
    class Whatever:
        name: str

    assert Whatever.__init__ is object.__init__
    assert hasattr(Whatever, MethodBuilder.make_squire_name("__init__"))

    whatever = Whatever()
    call_init(whatever, name="Hello")

    assert whatever.name == "Hello"


def test_init_hooks():
    @data(init=False, frozen=False)
    class TestObject:
        pre_init_called: bool = field(init=False)
        post_init_called: bool = field(init=False)

        def __pre_init__(self):
            self.pre_init_called = True

        def __post_init__(self):
            self.post_init_called = True

    pre_callback_called = False
    post_callback_called = False

    def pre_callback(_):
        nonlocal pre_callback_called
        pre_callback_called = True

    def post_callback(_):
        nonlocal post_callback_called
        post_callback_called = True

    obj = TestObject()

    with init_hooks(
        obj,
        pre_callbacks=[pre_callback],
        post_callbacks=[post_callback],
    ):
        assert hasattr(obj, "pre_init_called")  # pre-init should be called
        assert not hasattr(
            obj, "post_init_called"
        )  # post-init should not be called
        assert pre_callback_called is True  # Pre-callback should be called
        assert (
            post_callback_called is False
        )  # Post-callback should not be called

    assert hasattr(
        obj, "post_init_called"
    )  # post-init should be called after the context

    pre_callback_called = False
    post_callback_called = False

    del obj.post_init_called, obj.pre_init_called

    with init_hooks(obj):
        assert hasattr(obj, "pre_init_called")  # pre-init should be called
        assert not hasattr(
            obj, "post_init_called"
        )  # post-init should not be called

    assert hasattr(
        obj, "post_init_called"
    )  # post-init should be called after the context


def test_init_hooks_ignores_hooks_if_hooks_dont_exist():
    @data
    class Test:
        pass

    obj = Test()

    with init_hooks(obj):
        pass  # no exceptions should be raised


def test_define_is_drop_in_replacement_for_dataclass():
    @data(frozen=False, dataclass_fields=True)
    class Test:
        order_field: int
        name: str = dataclasses.field(init=False)
        email: str = dataclasses.field(hash=False)
        age: int = dataclasses.field(compare=False)
        password: str = dataclasses.field(default="MyPassword")
        friends: list[str] = dataclasses.field(default_factory=list)

    default_obj = Test(1, email="Hello", age=18)
    another = Test(0, email="World", age=19)

    assert default_obj.name is UNINITIALIZED
    assert default_obj.email == "Hello"
    assert default_obj.password == "MyPassword"
    assert default_obj.friends == []

    assert sorted([default_obj, another]) == [another, default_obj]


def test_define_creates_convertable_classes():
    @data
    class A:
        x: int
        y: int

    instance = A(1, 2)

    assert asdict(instance) == {"x": 1, "y": 2}
    assert fromdict(A, {"x": 3, "y": 4}) == A(3, 4)


def test_define_creates_convertable_classes_with_aliases():
    @data
    class A:
        x: int = field(alias="xVal")
        y: int = field(alias="yVal")

    instance = A(xVal=1, yVal=2)

    assert asdict(instance, by_alias=True) == {"xVal": 1, "yVal": 2}
    assert fromdict(A, {"xVal": 3, "yVal": 4}) == A(3, 4)


def test_define_respects_defaults_on_conversions():
    @data
    class A:
        x: int = 1
        y: int = 2

    instance = A()

    assert asdict(instance) == {"x": 1, "y": 2}
    assert fromdict(A, {"x": 3}) == A(3, 2)
    assert fromdict(A, {}) == A(1, 2)


def test_define_understands_mixed_alias_name_mappings():
    @data
    class A:
        x: int = field(alias="xVal")
        y: int = field(alias="yVal")

    instance = A(xVal=1, yVal=2)

    assert asdict(instance, by_alias=True) == {"xVal": 1, "yVal": 2}
    assert fromdict(A, {"xVal": 3, "yVal": 4}) == A(3, 4)
    assert fromdict(A, {"x": 5, "y": 6}) == A(5, 6)
    assert fromdict(A, {"xVal": 7, "y": 8}) == A(7, 8)
    assert fromdict(A, {"x": 9, "yVal": 10}) == A(9, 10)


def test_define_conversions_fail_if_key_missing_without_defaults():
    @data
    class A:
        x: int = field(alias="xVal")
        y: int = field(alias="yVal")

    with pytest.raises(KeyError) as exc_info:
        _ = fromdict(A, {"x": 1})
    assert (
        next_or(exc_info.value.args)
        == "Key 'y' or alias 'yVal' not found"
        + " in mapping: {'x': 1} and no default value provided."
    )

    with pytest.raises(KeyError) as exc_info:
        _ = fromdict(A, {})  
    assert (
        next_or(exc_info.value.args)
        == "Key 'x' or alias 'xVal' not found"
        + " in mapping: {} and no default value provided."
    )


def test_transforms_work_correctly():
    # Test that a transform function is applied correctly
    @data
    class A:
        x: int
        y: float = private(ref=lambda ainstance: ainstance.x * 2.0)

    a = A(3)

    assert a.y == 6.0

def test_transform_works_with_mutable():
    @data(frozen=False)
    class A:
        names: list[str]
        comma_separated:  str = private(
            ref=lambda ainstance: ", ".join(ainstance.names) if ainstance.names else ""
        )
    a = A(["Alice", "Bob", "Charlie"])
    assert a.comma_separated == "Alice, Bob, Charlie"

    

def test_squire_serialize_properly_handles_sequence_types():
    @data
    class B:
        z: int
    @data
    class A:
        x: int
        y: list[B] = field(default_factory=list)
        w: list[float] = field(default_factory=list)

    @data
    class C:
        a: int
        b: set[int] = field(default_factory=set)

    assert fromdict(A, {"x": 1, "y": [{"z": 2}, {"z": 3}], "w": [1.0, 2.0]}) == A(1, [B(2), B(3)], [1.0, 2.0])
    assert fromdict(C, {"a": 1, "b": [2, 3]}) == C(1, {2, 3})
