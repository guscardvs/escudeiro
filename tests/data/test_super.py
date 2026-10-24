from typing import override

from escudeiro.data import data


def test_super_in_post_init_reaches_the_parent():
    calls: list[str] = []

    @data(frozen=False)
    class Parent:
        x: int

        def __post_init__(self):
            calls.append("parent")

    @data(frozen=False)
    class Child(Parent):
        y: int = 0

        def __post_init__(self):
            super().__post_init__()
            calls.append("child")

    _ = Child(1)

    assert calls == ["parent", "child"]


def test_super_in_user_defined_dunders():
    @data
    class Parent:
        x: int

        @override
        def __repr__(self) -> str:
            return f"Parent<{self.x}>"

    @data(slots=False)
    class Child(Parent):
        @override
        def __repr__(self) -> str:
            return "Child:" + super().__repr__()

    assert repr(Child(1)) == "Child:Parent<1>"


def test_super_in_classmethod_property_and_staticmethod_free_functions():
    @data
    class Parent:
        x: int

        @classmethod
        def kind(cls) -> str:
            return "parent"

        @property
        def label(self) -> str:
            return "parent-label"

    @data
    class Child(Parent):
        @classmethod
        @override
        def kind(cls) -> str:
            return "child+" + super().kind()

        @property
        @override
        def label(self) -> str:
            return "child+" + super().label

        @staticmethod
        def helper() -> str:
            return "helper"

        def refers_to_own_class(self) -> type:
            return __class__  # pyright: ignore[reportUndefinedVariable]

    child = Child(1)

    assert Child.kind() == "child+parent"
    assert child.label == "child+parent-label"
    assert Child.helper() == "helper"
    assert child.refers_to_own_class() is Child


def test_super_works_through_several_data_levels():
    @data(frozen=False, slots=False)
    class A:
        def __post_init__(self):
            self.trail = ["A"]  # pyright: ignore[reportUninitializedInstanceVariable]

    @data(frozen=False, slots=False)
    class B(A):
        def __post_init__(self):
            super().__post_init__()
            self.trail.append("B")

    @data(frozen=False, slots=False)
    class C(B):
        def __post_init__(self):
            super().__post_init__()
            self.trail.append("C")

    assert C().trail == ["A", "B", "C"]
