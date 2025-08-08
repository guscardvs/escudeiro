from typing import Annotated, Any, Literal, override

import pytest

from escudeiro.misc.typex import (
    assert_notnone,
    cast_notnone,
    is_hashable,
    is_instanceexact,
)


class TestIsHashable:
    # ==== Types that SHOULD be hashable ====
    @pytest.mark.parametrize(
        "typ",
        [
            int,
            str,
            float,
            bool,
            type(None),
            int | None,
            int | str,
            tuple[int, str],
            Literal[1, 2, 3],
            Annotated[int, "metadata"],
            frozenset[str],
        ],
    )
    def test_hashable_types(self, typ: Any):
        assert is_hashable(typ), f"{typ} should be hashable"

    # ==== Types that SHOULD NOT be hashable ====
    @pytest.mark.parametrize(
        "typ",
        [
            list[int],
            set[str],
            dict[str, int],
            list[str] | None,
            str | list[str],
            tuple[int, list[int]],
            Annotated[list[int], "metadata"],
        ],
    )
    def test_unhashable_types(self, typ: Any):
        assert not is_hashable(typ), f"{typ} should NOT be hashable"

    # ==== Edge: recursive or nested generics ====
    @pytest.mark.parametrize(
        "typ",
        [
            int | list[str] | None,
            tuple[int, int] | list[int],
            Annotated[dict[str, int] | None, "meta"],
        ],
    )
    def test_complex_unhashable_cases(self, typ: Any):
        assert not is_hashable(typ), (
            f"{typ} should NOT be hashable (deep unhashable part)"
        )

    # ==== User-defined classes ====

    class HashableCustom:
        @override
        def __hash__(self):
            return 42

    class UnhashableCustom:
        __hash__ = None  # pyright: ignore[reportAssignmentType]

    def test_custom_class_hashable(self):
        assert is_hashable(self.HashableCustom)

    def test_custom_class_unhashable(self):
        assert not is_hashable(self.UnhashableCustom)

    # ==== Aliased types / runtime aliases ====
    MyFrozenSet = frozenset[int]
    MyList = list[str]
    type MyTuple = tuple[int]
    type MyDict = dict[str, Any]

    def test_alias_variable(self):
        assert is_hashable(self.MyFrozenSet)
        assert not is_hashable(self.MyList)

    def test_type_alias_type(self):
        assert is_hashable(self.MyTuple)
        assert not is_hashable(self.MyDict)

    # ==== Optional Ellipsis corner case ====
    def test_ellipsis_is_ignored(self):
        assert is_hashable(None | tuple[int, ...])


class TestIsInstanceexact:
    @pytest.mark.parametrize(
        "obj, annotation, expected",
        [
            (1, int, True),
            (1.0, float, True),
            ("test", str, True),
            (None, type(None), True),
            (1, int | str, True),
            (1.0, int | str, False),
            ("test", int | str, True),
            ([1, 2], list[int], True),
            (frozenset([1]), frozenset[int], True),
        ],
        ids=[
            "int_exact",
            "float_exact",
            "str_exact",
            "none_exact",
            "int_or_str_match_int",
            "int_or_str_mismatch_float",
            "int_or_str_match_str",
            "list_not_instanceexact",
            "frozenset_exact",
        ],
    )
    def test_is_instanceexact(self, obj: Any, annotation: Any, expected: bool):
        assert is_instanceexact(obj, annotation) == expected

    def test_does_not_match_for_subclasses(self):
        class Base:
            pass

        class Derived(Base):
            pass

        assert is_instanceexact(Derived(), Base) is False
        assert is_instanceexact(Base(), Base) is True
        assert is_instanceexact(Derived(), Derived) is True

    def test_union_type_handling(self):
        class CustomType:
            pass

        assert is_instanceexact(CustomType(), CustomType | int) is True
        assert is_instanceexact(1, CustomType | int) is True
        assert is_instanceexact("test", CustomType | int) is False


class TestAssertNotNone:
    def test_assert_notnone_with_value(self):
        assert assert_notnone(5) == 5
        assert assert_notnone("hello") == "hello"

    def test_assert_notnone_with_none(self):
        with pytest.raises(ValueError, match="Value is None"):
            assert_notnone(None)


class TestCastNotNone:
    def test_cast_notnone_with_value(self):
        assert cast_notnone(5) == 5
        assert cast_notnone("hello") == "hello"

    def test_cast_notnone_with_none(self):
        assert cast_notnone(None) is None, "cast_notnone does not raise, just casts"
    
