from typing import Annotated, Any, Literal, override

import pytest

from escudeiro.misc.typex import is_hashable


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
