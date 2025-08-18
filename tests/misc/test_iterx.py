import asyncio
from collections.abc import AsyncGenerator, Collection, Sequence
from contextlib import aclosing

import pytest

from escudeiro.misc import (
    aall,
    aany,
    acarrymap,
    acarrystarmap,
    aenumerate,
    afilter,
    aislice,
    amap,
    amoving_window,
    anext_or,
    areduce,
    astarmap,
    carrymap,
    exclude_none,
    filter_isinstance,
    filter_issubclass,
    flatten,
    group_values,
    invert_dict,
    moving_window,
    next_or,
)


# Helper for async tests
async def async_generator[T](items: Collection[T]) -> AsyncGenerator[T]:
    for item in items:
        yield item


class TestMovingWindow:
    def test_complete_windows(self):
        result = list(moving_window([1, 2, 3, 4, 5, 6], 2))
        assert result == [(1, 2), (3, 4), (5, 6)]

    def test_incomplete_final_window(self):
        result = list(moving_window([1, 2, 3, 4, 5], 2))
        assert result == [(1, 2), (3, 4), (5,)]

    def test_empty_iterable(self):
        result = list(moving_window([], 3))
        assert result == []

    def test_window_size_larger_than_iterable(self):
        result = list(moving_window([1, 2], 5))
        assert result == [(1, 2)]

    def test_custom_cast_function(self):
        result = list(moving_window([1, 2, 3, 4], 2, list))
        assert result == [[1, 2], [3, 4]]


class TestAislice:
    async def test_stop_only(self):
        result = [
            x async for x in aislice(async_generator([1, 2, 3, 4, 5]), 3)
        ]
        assert result == [1, 2, 3]

    async def test_start_stop(self):
        result = [
            x async for x in aislice(async_generator([1, 2, 3, 4, 5]), 1, 4)
        ]
        assert result == [2, 3, 4]

    async def test_start_stop_step(self):
        result = [
            x async for x in aislice(async_generator([1, 2, 3, 4, 5]), 0, 5, 2)
        ]
        assert result == [1, 3, 5]

    async def test_empty_source(self):
        result = [x async for x in aislice(async_generator([]), 3)]
        assert result == []

    async def test_negative_indices_raises(self):
        with pytest.raises(ValueError):
            _ = [x async for x in aislice(async_generator([1, 2, 3]), -1, 5)]

    async def test_zero_step_raises(self):
        with pytest.raises(ValueError):
            _ = [x async for x in aislice(async_generator([1, 2, 3]), 0, 5, 0)]

    async def test_non_int_indices_raises(self):
        with pytest.raises(TypeError):
            _ = [x async for x in aislice(async_generator([1, 2, 3]), 0.5, 5)]  # pyright: ignore[reportArgumentType]


class TestAMovingWindow:
    async def test_complete_windows(self):
        result = [
            x async for x in amoving_window(async_generator([1, 2, 3, 4]), 2)
        ]
        assert result == [[1, 2], [3, 4]]

    async def test_incomplete_final_window(self):
        result = [
            x
            async for x in amoving_window(async_generator([1, 2, 3, 4, 5]), 2)
        ]
        assert result == [[1, 2], [3, 4], [5]]

    async def test_empty_iterable(self):
        result = [x async for x in amoving_window(async_generator([]), 3)]
        assert result == []


class TestAmap:
    async def test_sync_function(self):
        result = [
            x async for x in amap(lambda x: x * 2, async_generator([1, 2, 3]))
        ]
        assert result == [2, 4, 6]

    async def test_async_function(self):
        async def async_double(x: float):
            await asyncio.sleep(0.01)
            return x * 2

        result = [
            x async for x in amap(async_double, async_generator([1, 2, 3]))
        ]
        assert result == [2, 4, 6]

    async def test_empty_iterable(self):
        result = [x async for x in amap(lambda x: x * 2, async_generator([]))]
        assert result == []


class TestAfilter:
    async def test_sync_predicate(self):
        result = [
            x
            async for x in afilter(
                lambda x: x % 2 == 0, async_generator([1, 2, 3, 4])
            )
        ]
        assert result == [2, 4]

    async def test_async_predicate(self):
        async def is_even(x: float):
            await asyncio.sleep(0.01)
            return x % 2 == 0

        result = [
            x async for x in afilter(is_even, async_generator([1, 2, 3, 4]))
        ]
        assert result == [2, 4]

    async def test_all_filtered(self):
        result = [
            x
            async for x in afilter(
                lambda x: x > 10, async_generator([1, 2, 3])
            )
        ]
        assert result == []

    async def test_none_filtered(self):
        result = [
            x
            async for x in afilter(
                lambda x: x <= 10, async_generator([1, 2, 3])
            )
        ]
        assert result == [1, 2, 3]


class TestAreduce:
    async def test_sync_function(self):
        result = await areduce(
            lambda x, y: x + y, async_generator([1, 2, 3, 4])
        )
        assert result == 10

    async def test_with_initial(self):
        result = await areduce(
            lambda x, y: x + y, async_generator([1, 2, 3]), 10
        )
        assert result == 16

    async def test_async_function(self):
        async def async_add(x: float, y: float) -> float:
            await asyncio.sleep(0.01)
            return x + y

        result = await areduce(async_add, async_generator([1, 2, 3]))
        assert result == 6

    async def test_empty_iterable_with_initial(self):
        result = await areduce(lambda x, y: x + y, async_generator([]), 5)
        assert result == 5

    async def test_empty_iterable_without_initial_raises(self):
        with pytest.raises(TypeError):
            await areduce(lambda x, y: x + y, async_generator([]))

    async def test_single_item(self):
        result = await areduce(lambda x, y: x + y, async_generator([42]))
        assert result == 42


class TestAenumerate:
    async def test_default_start(self):
        result = [
            x async for x in aenumerate(async_generator(["a", "b", "c"]))
        ]
        assert result == [(0, "a"), (1, "b"), (2, "c")]

    async def test_custom_start(self):
        result = [
            x async for x in aenumerate(async_generator(["a", "b", "c"]), 10)
        ]
        assert result == [(10, "a"), (11, "b"), (12, "c")]

    async def test_empty_iterable(self):
        result = [x async for x in aenumerate(async_generator([]))]
        assert result == []


class TestAny:
    async def test_true_case(self):
        async with aclosing(
            async_generator([False, False, True, False])
        ) as gen:
            result = await aany(gen)
        assert result is True

    async def test_false_case(self):
        async with aclosing(async_generator([False, False, False])) as gen:
            result = await aany(gen)
        assert result is False

    async def test_empty_iterable(self):
        async with aclosing(async_generator([])) as gen:
            result = await aany(gen)
        assert result is False

    async def test_custom_predicate(self):
        async with aclosing(async_generator([1, 2, 3, 4])) as gen:
            result = await aany(gen, lambda x: x > 3)
        assert result is True

    async def test_async_predicate(self):
        async def is_greater_than_three(x: float):
            await asyncio.sleep(0.01)
            return x > 3

        async with aclosing(async_generator([1, 2, 3, 4])) as gen:
            result = await aany(gen, is_greater_than_three)
        assert result is True


class TestAll:
    async def test_true_case(self):
        async with aclosing(async_generator([True, True, True])) as gen:
            result = await aall(gen)
        assert result is True

    async def test_false_case(self):
        async with aclosing(async_generator([True, False, True])) as gen:
            result = await aall(gen)
        assert result is False

    async def test_empty_iterable(self):
        async with aclosing(async_generator([])) as gen:
            result = await aall(gen)
        assert result is True

    async def test_custom_predicate(self):
        async with aclosing(async_generator([2, 4, 6, 8])) as gen:
            result = await aall(gen, lambda x: x % 2 == 0)
        assert result is True

    async def test_async_predicate(self):
        async def is_even(x: float):
            await asyncio.sleep(0.01)
            return x % 2 == 0

        async with aclosing(async_generator([2, 4, 5, 6])) as gen:
            result = await aall(gen, is_even)
        assert result is False


class TestAcarrymap:
    async def test_sync_function(self):
        async def async_double(x: float):
            await asyncio.sleep(0.01)
            return x * 2

        result = [
            x
            async for x in acarrymap(async_double, async_generator([1, 2, 3]))
        ]
        assert result == [(2, 1), (4, 2), (6, 3)]

    async def test_empty_iterable(self):
        async def async_double(x: float):
            await asyncio.sleep(0.01)
            return x * 2

        result = [
            x async for x in acarrymap(async_double, async_generator([]))
        ]
        assert result == []


class TestAstarmap:
    async def test_basic_usage(self):
        async def add_multiply(a: float, b: float):
            await asyncio.sleep(0.01)
            return a + b, a * b

        data = [(1, 2), (3, 4), (5, 6)]
        result = [
            x async for x in astarmap(add_multiply, async_generator(data))
        ]
        assert result == [(3, 2), (7, 12), (11, 30)]

    async def test_empty_iterable(self):
        async def add_multiply(a: float, b: float):
            await asyncio.sleep(0.01)
            return a + b, a * b

        result = [x async for x in astarmap(add_multiply, async_generator([]))]
        assert result == []


class TestAcarrystarmap:
    async def test_basic_usage(self):
        async def add_multiply(a: float, b: float):
            await asyncio.sleep(0.01)
            return a + b, a * b

        data = [(1, 2), (3, 4), (5, 6)]
        result = [
            x async for x in acarrystarmap(add_multiply, async_generator(data))
        ]
        assert result == [
            ((3, 2), (1, 2)),
            ((7, 12), (3, 4)),
            ((11, 30), (5, 6)),
        ]

    async def test_empty_iterable(self):
        async def add_multiply(a: float, b: float):
            await asyncio.sleep(0.01)
            return a + b, a * b

        result = [
            x async for x in acarrystarmap(add_multiply, async_generator([]))
        ]
        assert result == []


class TestFlatten:
    def test_nested_list(self):
        result = flatten([1, [2, 3], [4, [5, 6]]])
        assert result == [1, 2, 3, 4, 5, 6]

    def test_nested_tuple(self):
        result = flatten((1, [2, 3], (4, 5)))
        assert isinstance(result, tuple)
        assert result == (1, 2, 3, 4, 5)

    def test_mixed_nesting(self):
        result = flatten([1, (2, 3), [4, (5, [6])]])
        assert result == [1, 2, 3, 4, 5, 6]

    def test_empty_sequence(self):
        result = flatten([])
        assert result == []

    def test_no_nesting(self):
        result = flatten([1, 2, 3])
        assert result == [1, 2, 3]

    def test_strings_not_flattened(self):
        result = flatten(["abc", ["def", "ghi"]])
        assert result == ["abc", "def", "ghi"]


class TestExcludeNone:
    def test_list_with_none(self):
        result = exclude_none([1, None, 2, None, 3])
        assert result == [1, 2, 3]

    def test_nested_list_with_none(self):
        result = exclude_none([1, [2, None, 3], None, 4])
        assert result == [1, [2, 3], 4]

    def test_dict_with_none(self):
        result = exclude_none({"a": 1, "b": None, "c": {"d": None, "e": 2}})
        assert result == {"a": 1, "c": {"e": 2}}

    def test_nested_mixed_types(self):
        result = exclude_none([1, {"a": None, "b": [1, None, 2]}, None])
        assert result == [1, {"b": [1, 2]}]

    def test_tuple_with_none(self):
        # Tuples are converted to lists in the implementation
        result = exclude_none((1, None, 2, (3, None, 4)))
        assert isinstance(result, list)
        assert result == [1, 2, [3, 4]]

    def test_set_with_none(self):
        # Order isn't guaranteed with sets, so just check membership
        result = exclude_none({1, None, 2, 3})
        assert None not in result
        assert 1 in result and 2 in result and 3 in result


class TestNextOr:
    def test_non_empty_iterable(self):
        result = next_or([1, 2, 3])
        assert result == 1

    def test_empty_iterable_default_none(self):
        result = next_or([])
        assert result is None

    def test_empty_iterable_custom_default(self):
        result = next_or([], "default")
        assert result == "default"

    def test_generator(self):
        def gen():
            yield 42

        result = next_or(gen())
        assert result == 42


class TestAnextOr:
    async def test_non_empty_iterable(self):
        result = await anext_or(async_generator([1, 2, 3]))
        assert result == 1

    async def test_empty_iterable_default_none(self):
        result = await anext_or(async_generator([]))
        assert result is None

    async def test_empty_iterable_custom_default(self):
        result = await anext_or(async_generator([]), "default")
        assert result == "default"


class TestCarrymap:
    def test_basic_mapping(self):
        result = list(carrymap(lambda x: x * 2, [1, 2, 3]))
        assert result == [(2, 1), (4, 2), (6, 3)]

    def test_with_strings(self):
        result = list(carrymap(str.upper, ["a", "b", "c"]))
        assert result == [("A", "a"), ("B", "b"), ("C", "c")]

    def test_empty_iterable(self):
        arr: list[int] = []
        result = list(carrymap(lambda x: x * 2, arr))
        assert result == []


class TestFilterIsinstance:
    def test_single_type(self):
        data = [1, "a", 2, "b", [], 3]
        result = list(filter_isinstance(str, data))
        assert result == ["a", "b"]

    def test_multiple_types(self):
        data = [1, "a", 2.0, [], {}, "b"]
        result = list(filter_isinstance((str, int), data))
        assert result == [1, "a", "b"]

    def test_empty_iterable(self):
        result = list(filter_isinstance(str, []))
        assert result == []

    def test_no_matching_items(self):
        data = [1, 2, 3, 4]
        result = list(filter_isinstance(str, data))
        assert result == []


class TestFilterIssubclass:
    def test_basic_filtering(self):
        classes = [ValueError, str, TypeError, list, OSError]
        result = list(filter_issubclass(Exception, classes))
        assert set(result) == {ValueError, TypeError, OSError}

    def test_multiple_base_classes(self):
        classes = [list, dict, tuple, set]
        result = list(filter_issubclass(Sequence, classes))
        assert set(result) == {list, tuple}

    def test_empty_iterable(self):
        result = list(filter_issubclass(Exception, []))
        assert result == []

    def test_non_type_objects_filtered_out(self):
        # Should filter out non-type objects like "not a class"
        mixed_data = [ValueError, "not a class", TypeError]
        result = list(filter_issubclass(Exception, mixed_data))
        assert set(result) == {ValueError, TypeError}


class TestInvertDict:
    def test_basic_inversion(self):
        original = {"a": 1, "b": 2, "c": 3}
        inverted = invert_dict(original)
        assert inverted == {1: "a", 2: "b", 3: "c"}

    def test_duplicate_values(self):
        # With duplicate values, last key-value pair wins
        original = {"a": 1, "b": 1, "c": 2}
        inverted = invert_dict(original)
        assert len(inverted) == 2
        assert inverted[1] in [
            "a",
            "b",
        ]  # Either a or b, depending on dict order
        assert inverted[2] == "c"

    def test_empty_dict(self):
        assert invert_dict({}) == {}


class TestGroupValues:
    def test_basic_grouping(self):
        data = [
            {"category": "A", "value": 1},
            {"category": "B", "value": 2},
            {"category": "A", "value": 3},
        ]
        result = group_values(data, "category")
        assert result == {
            "A": [
                {"category": "A", "value": 1},
                {"category": "A", "value": 3},
            ],
            "B": [{"category": "B", "value": 2}],
        }

    def test_single_group(self):
        data = [
            {"category": "A", "value": 1},
            {"category": "A", "value": 2},
        ]
        result = group_values(data, "category")
        assert result == {
            "A": [
                {"category": "A", "value": 1},
                {"category": "A", "value": 2},
            ],
        }

    def test_empty_collection(self):
        result = group_values([], "category")
        assert result == {}

    def test_missing_key_raises(self):
        data = [{"category": "A"}, {"type": "B"}]
        with pytest.raises(KeyError):
            _ = group_values(data, "category")
