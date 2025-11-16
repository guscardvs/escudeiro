# pyright: reportMissingParameterType=false

import asyncio
import contextlib
import inspect
from collections.abc import AsyncIterable, Callable
from datetime import UTC, date, datetime, time
from decimal import Decimal
from functools import partial
from typing import Any, NoReturn, Self
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch

import pytest

from escudeiro.exc.errors import ErrorGroup, InvalidCast, RetryError
from escudeiro.misc import (
    Caster,
    FrozenCoroutine,
    Retry,
    as_async,
    as_async_iterable,
    as_datetime,
    asafe_cast,
    asyncdo_with,
    cache,
    call_once,
    do_with,
    isinstance_or_cast,
    join_into_datetime,
    make_noop,
    raise_insteadof,
    safe_cast,
    walk_object,
)
from escudeiro.misc.functions import awrap_result_with, wrap_result_with
from escudeiro.misc.iterx import filter_isinstance, next_or
from escudeiro.misc.strings import sentence, squote


class TestSafeCast:
    def test_successful_cast(self):
        result = safe_cast(int, "123")
        assert result == 123

    def test_failed_cast_default_exceptions(self):
        result = safe_cast(int, "abc")
        assert result is None

    def test_failed_cast_custom_exceptions(self):
        def custom_caster(value: int):
            if value < 0:
                raise ValueError("Cannot be negative")
            if value > 100:
                raise RuntimeError("Too large")
            return value

        result = safe_cast(custom_caster, -10, ValueError)
        assert result is None

        result = safe_cast(custom_caster, 200, RuntimeError)
        assert result is None

        # Should not catch exceptions not in the ignore list
        with pytest.raises(RuntimeError):
            _ = safe_cast(custom_caster, 200, ValueError)

    def test_custom_default_value(self):
        result = safe_cast(int, "abc", default=42)
        assert result == 42


class TestAsafeCast:
    async def test_successful_cast(self):
        async def async_int(value: Any):
            await asyncio.sleep(0.01)
            return int(value)

        result = await asafe_cast(async_int, "123")
        assert result == 123

    async def test_failed_cast_default_exceptions(self):
        async def async_int(value: Any):
            await asyncio.sleep(0.01)
            return int(value)

        result = await asafe_cast(async_int, "abc")
        assert result is None

    async def test_failed_cast_custom_exceptions(self):
        async def custom_caster(value: float):
            await asyncio.sleep(0.01)
            if value < 0:
                raise ValueError("Cannot be negative")
            if value > 100:
                raise RuntimeError("Too large")
            return value

        result = await asafe_cast(custom_caster, -10, ValueError)
        assert result is None

        result = await asafe_cast(custom_caster, 200, RuntimeError)
        assert result is None

        # Should not catch exceptions not in the ignore list
        with pytest.raises(RuntimeError):
            _ = await asafe_cast(custom_caster, 200, ValueError)

    async def test_custom_default_value(self):
        async def async_int(value: Any):
            await asyncio.sleep(0.01)
            return int(value)

        result = await asafe_cast(async_int, "abc", default=42)
        assert result == 42


class TestCallOnce:
    def test_function_called_once(self):
        mock_func = Mock(return_value=42)
        wrapped = call_once(mock_func)

        # First call
        result1 = wrapped()
        assert result1 == 42
        mock_func.assert_called_once()

        # Second call
        result2 = wrapped()
        assert result2 == 42
        mock_func.assert_called_once()  # Still only called once

    def test_exception_not_cached(self):
        # If the function raises an exception, it shouldn't be cached
        side_effects = [ValueError("Error"), 42]
        mock_func = Mock(side_effect=side_effects)
        wrapped = call_once(mock_func)

        # First call - should raise
        with pytest.raises(ValueError):
            wrapped()

        # Second call - should return 42
        result = wrapped()
        assert result == 42
        assert mock_func.call_count == 2


class TestAsAsync:
    def test_async_function_unchanged(self):
        async def async_func():
            return 42

        result = as_async(async_func)
        assert result is async_func
        assert inspect.iscoroutinefunction(result)

    def test_sync_function_converted(self):
        def sync_func():
            return 42

        result = as_async(sync_func)
        assert result is not sync_func
        assert inspect.iscoroutinefunction(result)

    async def test_converted_function_execution(self):
        def sync_func(x: float, y: float):
            return x + y

        async_func = as_async(sync_func)
        result = await async_func(3, 4)
        assert result == 7

    async def test_custom_cast_function(self):
        def sync_func(x: float):
            return x * 2

        async def custom_cast[T, U: float | int](
            func: Callable[[T], U], x: T
        ) -> float:
            await asyncio.sleep(0.01)
            return func(x) + 1

        async_func = as_async(cast=custom_cast)(sync_func)
        result = await async_func(5)
        assert result == 11  # (5 * 2) + 1

    def test_decorator_usage(self):
        # No arguments
        @as_async
        def func1(x: float):
            return x * 2

        assert inspect.iscoroutinefunction(func1)

        # With arguments
        async def custom_cast(func: Callable[[float], float], x: float):
            await asyncio.sleep(0.01)
            return func(x) + 1

        @as_async(cast=custom_cast)
        def func2(x: float):
            return x * 2

        assert inspect.iscoroutinefunction(func2)


class TestCache:
    def test_caching_behavior(self):
        call_count = 0

        @cache
        def fibonacci(n: int):
            nonlocal call_count
            call_count += 1
            if n <= 1:
                return n
            return fibonacci(n - 1) + fibonacci(n - 2)

        # First call, should calculate everything
        result1 = fibonacci(10)
        initial_call_count = call_count
        assert initial_call_count > 10  # Should have made recursive calls

        # Reset count
        call_count = 0

        # Second call, should use cache
        result2 = fibonacci(10)
        assert call_count == 0  # No additional calls
        assert result1 == result2


class TestMakeNoop:
    def test_sync_noop(self):
        noop = make_noop()
        assert noop() is None
        assert noop(1, 2, 3, key="value") is None

    def test_custom_return_value(self):
        noop = make_noop(returns=42)
        assert noop() == 42
        assert noop(1, 2, 3) == 42

    def test_async_noop(self):
        noop = make_noop(asyncio=True)
        assert inspect.iscoroutinefunction(noop)

    async def test_async_noop_execution(self):
        noop = make_noop(asyncio=True, returns={"status": "success"})
        result = await noop(1, 2, key="value")
        assert result == {"status": "success"}


class TestDoWith:
    def test_do_with_contextmanager(self):
        mock_enter = Mock()
        mock_exit = Mock()
        mock_func = Mock(return_value=42)

        @contextlib.contextmanager
        def test_context():
            mock_enter()
            try:
                yield
            finally:
                mock_exit()

        result = do_with(test_context(), mock_func, 1, 2, key="value")

        assert result == 42
        mock_enter.assert_called_once()
        mock_exit.assert_called_once()
        mock_func.assert_called_once_with(1, 2, key="value")

    def test_exception_handling(self):
        mock_enter = Mock()
        mock_exit = Mock()
        mock_func = Mock(side_effect=ValueError("Test error"))

        @contextlib.contextmanager
        def test_context():
            mock_enter()
            try:
                yield
            finally:
                mock_exit()

        with pytest.raises(ValueError, match="Test error"):
            do_with(test_context(), mock_func)

        mock_enter.assert_called_once()
        mock_exit.assert_called_once()
        mock_func.assert_called_once()


class TestAsyncDoWith:
    async def test_with_sync_context_and_func(self):
        mock_enter = Mock()
        mock_exit = Mock()
        mock_func = Mock(return_value=42)

        @contextlib.contextmanager
        def test_context():
            mock_enter()
            try:
                yield
            finally:
                mock_exit()

        result = await asyncdo_with(
            test_context(), mock_func, 1, 2, key="value"
        )

        assert result == 42
        mock_enter.assert_called_once()
        mock_exit.assert_called_once()
        mock_func.assert_called_once_with(1, 2, key="value")

    async def test_with_async_context_and_func(self):
        mock_enter = AsyncMock()
        mock_exit = AsyncMock()
        mock_func = AsyncMock(return_value=42)

        @contextlib.asynccontextmanager
        async def test_context():
            await mock_enter()
            try:
                yield
            finally:
                await mock_exit()

        result = await asyncdo_with(
            test_context(), mock_func, 1, 2, key="value"
        )

        assert result == 42
        mock_enter.assert_called_once()
        mock_exit.assert_called_once()
        mock_func.assert_called_once_with(1, 2, key="value")

    async def test_with_sync_context_and_async_func(self):
        mock_enter = Mock()
        mock_exit = Mock()
        mock_func = AsyncMock(return_value=42)

        @contextlib.contextmanager
        def test_context():
            mock_enter()
            try:
                yield
            finally:
                mock_exit()

        result = await asyncdo_with(
            test_context(), mock_func, 1, 2, key="value"
        )

        assert result == 42
        mock_enter.assert_called_once()
        mock_exit.assert_called_once()
        mock_func.assert_called_once_with(1, 2, key="value")

    async def test_exception_handling(self):
        mock_enter = AsyncMock()
        mock_exit = AsyncMock()
        mock_func = AsyncMock(side_effect=ValueError("Test error"))

        @contextlib.asynccontextmanager
        async def test_context():
            await mock_enter()
            try:
                yield
            finally:
                await mock_exit()

        with pytest.raises(ValueError, match="Test error"):
            await asyncdo_with(test_context(), mock_func)

        mock_enter.assert_called_once()
        mock_exit.assert_called_once()
        mock_func.assert_called_once()


class TestFrozenCoroutine:
    async def test_single_execution(self):
        mock_coro = AsyncMock(return_value=42)

        async def test_coro():
            return await mock_coro()

        frozen = FrozenCoroutine(test_coro())
        result1 = await frozen
        result2 = await frozen

        assert result1 == 42
        assert result2 == 42
        mock_coro.assert_called_once()

    async def test_decorator(self):
        mock_func = AsyncMock(return_value=42)

        @FrozenCoroutine.decorate
        async def test_func(x: Any, y: Any):
            return await mock_func(x, y)

        coro = test_func(1, 2)
        assert isinstance(coro, FrozenCoroutine)

        result1 = await coro
        result2 = await coro

        assert result1 == 42
        assert result2 == 42
        mock_func.assert_called_once_with(1, 2)
        mock_func.assert_awaited_once()

    async def test_multiple_instances(self):
        call_count = 0

        async def test_coro(x: float):
            nonlocal call_count
            call_count += 1
            return x * 2

        # Each instance should execute once
        frozen1 = FrozenCoroutine(test_coro(10))
        frozen2 = FrozenCoroutine(test_coro(20))

        result1a = await frozen1
        result2a = await frozen2
        result1b = await frozen1
        result2b = await frozen2

        assert result1a == 20
        assert result1b == 20
        assert result2a == 40
        assert result2b == 40
        assert call_count == 2  # One for each unique instance


class TestDatetimeFunctions:
    def test_as_datetime(self):
        d = date(2023, 5, 15)

        # Without timezone
        dt1 = as_datetime(d)
        assert isinstance(dt1, datetime)
        assert dt1.year == 2023
        assert dt1.month == 5
        assert dt1.day == 15
        assert dt1.hour == 0
        assert dt1.minute == 0
        assert dt1.second == 0
        assert dt1.tzinfo is None

        # With timezone
        tz = UTC
        dt2 = as_datetime(d, tz)
        assert dt2.tzinfo is tz

    def test_join_into_datetime(self):
        d = date(2023, 5, 15)
        t = time(14, 30, 45, 123456)

        # Without timezone
        dt1 = join_into_datetime(d, t)
        assert isinstance(dt1, datetime)
        assert dt1.year == 2023
        assert dt1.month == 5
        assert dt1.day == 15
        assert dt1.hour == 14
        assert dt1.minute == 30
        assert dt1.second == 45
        assert dt1.microsecond == 123456
        assert dt1.tzinfo is None

        # With timezone
        tz = UTC
        dt2 = join_into_datetime(d, t, tz)
        assert dt2.tzinfo is tz


class TestAsAsyncIterable:
    async def test_conversion(self):
        original = [1, 2, 3, 4, 5]
        async_iterable = as_async_iterable(original)

        assert isinstance(async_iterable, AsyncIterable)

        result = []
        async for item in async_iterable:
            result.append(item)

        assert result == original


class TestRaiseInsteadof:
    def test_exception_replacement(self):
        with pytest.raises(ValueError, match="Custom message"):
            with raise_insteadof(KeyError, ValueError, "Custom message"):
                raise KeyError("Original error")

    def test_non_matching_exceptions_pass_through(self):
        with pytest.raises(ValueError, match="Original error"):
            with raise_insteadof(KeyError, RuntimeError, "Custom message"):
                raise ValueError("Original error")

    def test_no_exception(self):
        # Should not raise or modify anything if no exception occurs
        with raise_insteadof(KeyError, ValueError, "Custom message"):
            x = 1 + 1
        assert x == 2


# Test map functionality
class TestRetryMap:
    def test_map_all_successful(self):
        """Test map with all successful operations."""

        def process(item):
            return item * 2

        retry = Retry(signal=ValueError)

        results = []
        for result in retry.map(process, [1, 2, 3]):
            results.append(result)

        assert results == [2, 4, 6]

    def test_map_retries_exhausted(self):
        """Test map where retries for each item are exhausted.

        The always_fail function always raises an error, and after exhausting the retry attempts,
        an ErrorGroup with a RetryError and the underlying exceptions is expected.
        """

        def always_fail(item):
            raise ValueError(f"Failed processing {item}")

        retry = Retry(signal=ValueError, count=2)

        with pytest.raises(ErrorGroup) as excinfo:
            # Collecting results will trigger the retries and eventual failure
            _ = list(retry.map(always_fail, [1, 2, 3]))

        error_group = excinfo.value
        assert any(
            isinstance(err, RetryError) for err in error_group.exceptions
        ), "Expected at least one RetryError in the ErrorGroup"

    def test_map_with_retries(self):
        """Test map with some retries needed."""
        counter = 0

        def process(item):
            nonlocal counter
            if item == 2 and counter < 2:
                counter += 1
                raise ValueError("Failed processing")
            return item * 2

        retry = Retry(signal=ValueError, count=3)

        results = []
        for result in retry.map(process, [1, 2, 3]):
            results.append(result)

        assert results == [2, 4, 6]
        assert counter == 2  # Process was retried twice for item 2

    def test_map_temperature_strategy(self):
        """Test map with temperature strategy that reduces retry count after success."""
        failure_counts = {2: 0, 4: 0}

        def process(item):
            if item in [2, 4] and failure_counts[item] < 2:
                failure_counts[item] += 1
                raise ValueError(f"Failed processing {item}")
            return item * 2

        retry = Retry(signal=ValueError, count=3)

        results = []
        for result in retry.map(
            process, list(range(1, 6)), strategy="temperature"
        ):
            results.append(result)

        assert results == [2, 4, 6, 8, 10]
        assert failure_counts[2] == 2
        assert failure_counts[4] == 2


# Test Retry call functionality
class TestRetry:
    def test_retry_works_for_successful_execution(self):
        sentinel = object()
        mock = Mock(return_value=sentinel)
        retrier = Retry(signal=ValueError)

        assert retrier(mock)() is sentinel
        mock.assert_called_once()

    def test_retry_works_for_retries(self):
        sentinel = object()
        counter = 0
        retrier = Retry(signal=ValueError)

        @retrier
        def _testfunc():
            nonlocal counter
            counter += 1
            if counter < 2:
                raise ValueError
            return sentinel

        assert _testfunc() is sentinel
        assert counter == 2

    @patch("escudeiro.misc.functions.sleep")
    def test_retry_sleeps_work_as_expected(self, mock: MagicMock):
        retrier = Retry(signal=ValueError, delay=3)
        counter = 0

        @retrier
        def _testfunc():
            nonlocal counter
            if counter == 0:
                counter += 1
                raise ValueError
            return counter

        assert _testfunc() == 1
        assert counter == 1
        mock.assert_called_once_with(3)

    @patch("escudeiro.misc.functions.sleep")
    def test_retry_does_proper_backoff_as_expected(self, mock: MagicMock):
        retrier = Retry(signal=ValueError, delay=3, backoff=2)
        counter = 0

        @retrier
        def _testfunc():
            nonlocal counter
            if counter < 2:
                counter += 1
                raise ValueError
            return counter

        assert _testfunc() == 2
        assert counter == 2
        mock.assert_has_calls((call(3), call(6)))

    def test_retry_eventually_fails_with_all_expected_exceptions(self):
        counts = 4
        retrier = Retry(signal=ValueError, count=counts)
        counter = 0

        @retrier
        def _testfunc() -> NoReturn:
            nonlocal counter
            counter += 1
            raise ValueError

        with pytest.raises(
            ErrorGroup, match="Failed retry operation"
        ) as exc_info:
            _testfunc()

        assert tuple(
            filter_isinstance(ValueError, exc_info.value.exceptions[1:])
        )
        assert (
            next_or(exc_info.value.exceptions[0].args)
            == f"Exceeded max retries: {counts}"
        )
        assert counter == counts

    def test_retry_does_not_interfere_with_unhandled_exceptions(self):
        retrier = Retry(signal=ValueError)

        counter = 0

        @retrier
        def _testfunc():
            nonlocal counter
            counter += 1
            raise KeyError("this is a test.")

        with pytest.raises(KeyError, match="this is a test."):
            _testfunc()

        assert counter == 1


# Test Retry acall functionality
class TestRetryACall:
    async def test_retry_works_for_successful_execution(self):
        sentinel = object()
        mock = AsyncMock(return_value=sentinel)
        retrier = Retry(signal=ValueError)

        assert await retrier.acall(mock)() is sentinel
        mock.assert_called_once()

    async def test_retry_works_for_retries(self):
        sentinel = object()
        counter = 0
        retrier = Retry(signal=ValueError)

        @retrier.acall
        async def _testfunc():
            nonlocal counter
            counter += 1
            if counter < 2:
                raise ValueError
            return sentinel

        assert await _testfunc() is sentinel
        assert counter == 2

    @patch("asyncio.sleep")
    async def test_retry_sleeps_work_as_expected(self, mock: AsyncMock):
        retrier = Retry(signal=ValueError, delay=3)
        counter = 0

        @retrier.acall
        async def _testfunc():
            nonlocal counter
            if counter == 0:
                counter += 1
                raise ValueError
            return counter

        assert await _testfunc() == 1
        assert counter == 1
        mock.assert_called_once_with(3)

    @patch("asyncio.sleep")
    async def test_retry_does_proper_backoff_as_expected(
        self, mock: MagicMock
    ):
        retrier = Retry(signal=ValueError, delay=3, backoff=2)
        counter = 0

        @retrier.acall
        async def _testfunc():
            nonlocal counter
            if counter < 2:
                counter += 1
                raise ValueError
            return counter

        assert await _testfunc() == 2
        assert counter == 2
        mock.assert_has_calls((call(3), call(6)))

    async def test_retry_eventually_fails_with_all_expected_exceptions(self):
        counts = 4
        retrier = Retry(signal=ValueError, count=counts)
        counter = 0

        @retrier.acall
        async def _testfunc() -> NoReturn:
            nonlocal counter
            counter += 1
            raise ValueError

        with pytest.raises(
            ErrorGroup, match="Failed retry operation"
        ) as exc_info:
            await _testfunc()

        assert tuple(
            filter_isinstance(ValueError, exc_info.value.exceptions[1:])
        )
        assert (
            next_or(exc_info.value.exceptions[0].args)
            == f"Exceeded max retries: {counts}"
        )
        assert counter == counts

    async def test_retry_acall_does_not_interfere_with_unhandled_exceptions(
        self,
    ):
        retrier = Retry(signal=ValueError)

        counter = 0

        @retrier.acall
        async def _testfunc():
            nonlocal counter
            counter += 1
            raise KeyError("this is a test.")

        with pytest.raises(KeyError, match="this is a test."):
            await _testfunc()

        assert counter == 1


# Test amap functionality
class TestRetryAMap:
    async def test_amap_all_successful(self):
        """Test amap with all successful operations."""

        async def process(item):
            return item * 2

        retry = Retry(signal=ValueError)

        results = []
        async for result in retry.amap(process, [1, 2, 3]):
            results.append(result)

        assert results == [2, 4, 6]

    async def test_amap_retries_exhausted(self):
        """Test amap where an item's async predicate fails more than retry.count times."""

        async def failing_process(_: int):
            raise ValueError("processing failed")

        # Set retry count to 3 for this test
        retry = Retry(signal=ValueError, count=3)

        with pytest.raises(ErrorGroup) as exc_info:
            async for _ in retry.amap(failing_process, [42]):
                pass
        # Assert that one of the error messages indicates that max retries were exceeded.
        error_messages = [str(e) for e in exc_info.value.exceptions]
        assert any("Exceeded max retries:" in msg for msg in error_messages)

    async def test_amap_with_retries(self):
        """Test amap with some retries needed."""
        counter = 0

        async def process(item):
            nonlocal counter
            if item == 2 and counter < 2:
                counter += 1
                raise ValueError("Failed processing")
            return item * 2

        retry = Retry(signal=ValueError, count=3)

        results = []
        async for result in retry.amap(process, [1, 2, 3]):
            results.append(result)

        assert results == [2, 4, 6]
        assert counter == 2  # Process was retried twice for item 2

    async def test_amap_temperature_strategy(self):
        """Test amap with temperature strategy that reduces retry count after success."""
        failure_counts = {2: 0, 4: 0}

        async def process(item):
            if item in [2, 4] and failure_counts[item] < 2:
                failure_counts[item] += 1
                raise ValueError(f"Failed processing {item}")
            return item * 2

        retry = Retry(signal=ValueError, count=3)

        results = []
        async for result in retry.amap(
            process, list(range(1, 6)), strategy="temperature"
        ):
            results.append(result)

        assert results == [2, 4, 6, 8, 10]
        assert failure_counts[2] == 2
        assert failure_counts[4] == 2


# Test agenmap functionality
class TestRetryAgenMap:
    async def test_agenmap_all_successful(self):
        """Test agenmap with all successful operations."""

        async def process(item):
            return item * 2

        async def generator():
            for i in [1, 2, 3]:
                yield i

        retry = Retry(signal=ValueError)

        results = []
        async for result in retry.agenmap(process, generator()):
            results.append(result)

        assert results == [2, 4, 6]

    async def test_agenmap_with_retries(self):
        """Test agenmap with some retries needed."""
        counter = 0

        async def process(item):
            nonlocal counter
            if item == 2 and counter < 2:
                counter += 1
                raise ValueError("Failed processing")
            return item * 2

        async def generator():
            for i in [1, 2, 3]:
                yield i

        retry = Retry(signal=ValueError, count=3)

        results = []
        async for result in retry.agenmap(process, generator()):
            results.append(result)

        assert results == [2, 4, 6]
        assert counter == 2  # Process was retried twice for item 2

    async def test_agenmap_exceeds_max_retries(self):
        """Test agenmap when max retries are exceeded."""

        async def process(item):
            if item == 2:
                raise ValueError("Failed processing")
            return item * 2

        async def generator():
            for i in [1, 2, 3]:
                yield i

        retry = Retry(signal=ValueError, count=2)

        with pytest.raises(ErrorGroup):
            results = []
            async for result in retry.agenmap(process, generator()):
                results.append(result)

    async def test_agenmap_temperature_strategy(self):
        """Test agenmap with temperature strategy that reduces retry count after success."""
        failure_counts = {2: 0, 4: 0}

        async def process(item):
            if item in [2, 4] and failure_counts[item] < 2:
                failure_counts[item] += 1
                raise ValueError(f"Failed processing {item}")
            return item * 2

        async def generator():
            for i in [1, 2, 3, 4, 5]:
                yield i

        retry = Retry(signal=ValueError, count=3)

        results = []
        async for result in retry.agenmap(
            process, generator(), strategy="temperature"
        ):
            results.append(result)

        assert results == [2, 4, 6, 8, 10]
        assert failure_counts[2] == 2
        assert failure_counts[4] == 2


# ...existing code...


class TestWalkObject:
    def test_walk_object_with_dict(self):
        data = {"a": {"b": {"c": 42}}}
        assert walk_object(data, "a.b.c") == 42

    def test_walk_object_with_missing_key(self):
        data = {"a": {"b": {}}}
        assert walk_object(data, "a.b.c") is None

    def test_walk_object_with_object_attributes(self):
        class Dummy:
            def __init__(self):
                self.x = 10
                self.child = type("Child", (), {"y": 20})()

        obj = Dummy()
        assert walk_object(obj, "x") == 10
        assert walk_object(obj, "child.y") == 20

    def test_walk_object_with_list_index(self):
        data = [1, 2, [3, 4, 5]]
        assert walk_object(data, "[2].[1]") == 4

    def test_walk_object_with_tuple_index(self):
        data = (1, 2, (3, 4, 5))
        assert walk_object(data, "[2].[2]") == 5

    def test_walk_object_with_dict_and_list(self):
        data = {"a": [0, {"b": 99}]}
        assert walk_object(data, "a.[1].b") == 99

    def test_walk_object_returns_none_for_out_of_range_index(self):
        data = [1, 2]
        assert walk_object(data, "[5]") is None

    def test_walk_object_returns_none_for_missing_attribute(self):
        class Dummy:
            pass

        obj = Dummy()
        assert walk_object(obj, "not_found") is None

    def test_walk_object_returns_none_for_none_in_path(self):
        data = {"a": None}
        assert walk_object(data, "a.b") is None

    def test_walk_object_with_mixed_path(self):
        class Dummy:
            def __init__(self):
                self.x = [{"y": 123}]

        obj = Dummy()
        assert walk_object(obj, "x.[0].y") == 123


class TestIsInstanceOrCast:
    def test_isinstance_or_cast_isinstance_success(self):
        value = 42

        @partial(isinstance_or_cast, int)
        def caster(value: str) -> int:
            return int(value)

        result = caster(value)

        assert result is value  # Should return the original value

    def test_isinstance_or_cast_runs_caster_on_failure(self):
        value = "42"
        caster = MagicMock(return_value=42)

        result = isinstance_or_cast(int, caster)(value)

        assert result == 42
        assert caster.call_count == 1
        caster.assert_called_once_with(value)


class TestCaster:
    def test_caster_with_default_call(self):
        caster = Caster(int)
        value = "123"
        result = caster(value)
        assert result == 123

    def test_caster_with_join(self):
        caster = Caster(int).join(float)
        value = "123"

        result = caster(value)

        assert result == 123.0

    def test_caster_with_strict(self):
        @Caster
        def caster(value: str) -> int | None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        value = "123.456"

        with pytest.raises(InvalidCast) as exc_info:
            _ = caster.strict(value)

        assert (
            exc_info.value.args[0]
            == f"Received falsy value None from {value} during cast."
        )

    def test_caster_with_strict_success(self):
        @Caster
        def caster(value: str) -> int | None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        value = "123"

        result = caster.strict(value)

        assert result == 123

    def test_with_caster_safe(self):
        value = "abc"
        result = Caster(int).safe(value)

        assert result is None

    def test_with_caster_safe_success(self):
        value = "123"
        result = Caster(int).safe(value)

        assert result == 123

    def test_with_caster_safe_custom_default(self):
        value = "abc"
        result = Caster(int).safe(value, default=42)

        assert result == 42

    def test_caster_with_safe_custom_exceptions(self):
        class CustomException(Exception):
            pass

        @Caster
        def caster(value: str) -> int | None:
            try:
                return int(value)
            except ValueError as err:
                raise CustomException("Custom error during cast") from err

        value = "abc"
        result = caster.safe(value, CustomException, default=42)

        assert result == 42

    def test_caster_with_safe_custom_exceptions_no_match(self):
        class CustomException(Exception):
            pass

        @Caster
        def caster(value: str) -> int | None:
            try:
                return int(value)
            except CustomException:
                return None

        value = "abc"
        result = caster.safe(value, ValueError, default=42)

        assert result == 42

    def test_caster_or_success(self):
        caster = Caster[str, int](int).or_(float)
        value = "123.456"
        result = caster(value)

        assert result == 123.456

    def test_caster_or_failure(self):
        caster = Caster[str, int](int).or_(float)
        value = "abc"

        with pytest.raises(ValueError) as exc_info:
            _ = caster(value)

        assert (
            str(exc_info.value) == "could not convert string to float: 'abc'"
        )

    def test_caster_isinstance_or_cast_success(self):
        class Custom:
            def __init__(self, value: int):
                self.value = value

            @classmethod
            def cast(cls, value: str) -> Self:
                return cls(int(value))

        value = Custom(42)
        caster = Caster.isinstance_or_cast(Custom, Custom.cast)

        assert caster(value) is value

    def test_caster_isinstance_or_cast_failure(self):
        class Custom:
            def __init__(self, value: int):
                self.value = value

            @classmethod
            def cast(cls, value: str) -> Self:
                return cls(int(value))

        value = "123"
        caster = Caster.isinstance_or_cast(Custom, Custom.cast)

        result = caster(value)

        assert isinstance(result, Custom)
        assert result.value == 123

    def test_with_rule_success_no_rulename(self):
        @Caster
        def caster(value: str) -> int:
            return int(value)

        value = "123"

        def rule(x):
            return x < 124

        result = caster.with_rule(rule)(value)

        assert result == 123

    def test_with_rule_fail_no_rulename(self):
        @Caster
        def caster(value: str) -> int:
            return int(value)

        def rule(x):
            return x < 100

        value = "123"
        with pytest.raises(InvalidCast) as exc_info:
            _ = caster.with_rule(rule)(value)

        assert exc_info.value.args == (
            sentence(
                f"result {123} does not satisfy the rule {squote(rule.__name__)}"
            ),
            123,
        )

    def test_with_rule_fail_with_unnamed_lambda(self):
        @Caster
        def caster(value: str) -> int:
            return int(value)

        value = "123"
        with pytest.raises(
            ValueError, match="Rule name must be provided for lambda functions"
        ):
            _ = caster.with_rule(lambda x: x < 100)(value)

    def test_with_rule_success_with_rulename(self):
        @Caster
        def caster(value: str) -> int:
            return int(value)

        value = "123"
        result = caster.with_rule(
            lambda x: x < 124, "Value must be less than 124"
        )(value)

        assert result == 123

    def test_with_rule_fail_with_rulename(self):
        @Caster
        def caster(value: str) -> int:
            return int(value)

        def rule(x):
            return x < 100

        rulename = "Value must be less than 100"
        value = "123"
        with pytest.raises(InvalidCast) as exc_info:
            _ = caster.with_rule(rule, rulename)(value)

        assert exc_info.value.args == (
            sentence(
                f"result 123 does not satisfy the rule {squote(rulename)}"
            ),
            123,
        )

    def test_with_rule_fail_for_named_lambda(self):
        @Caster
        def caster(value: str) -> int:
            return int(value)

        value = "123"
        rulename = "Value must be less than 100"

        with pytest.raises(InvalidCast) as exc_info:
            _ = caster.with_rule(lambda x: x < 100, rulename)(value)

        assert exc_info.value.args == (
            sentence(
                f"result 123 does not satisfy the rule {squote(rulename)}"
            ),
            123,
        )

    def test_cannot_add_pipeline_for_safe_casted(self):
        # test join
        @Caster
        def example_func(val: str):
            return int(val)

        def as_float(val: Any | None) -> float:
            if val is None:
                return 0
            else:
                return float(val)

        with pytest.raises(ValueError) as join_excinfo:
            _ = example_func.safe_cast().join(as_float)
        with pytest.raises(ValueError) as or_excinfo:
            _ = example_func.safe_cast().or_(as_float)
        with pytest.raises(ValueError) as with_rule_excinfo:
            _ = example_func.safe_cast().with_rule(
                lambda val: as_float(val) > 0, "Must be positive"
            )

        assert (
            next_or(join_excinfo.value.args)
            == "Cannot join with a safe-casted Caster"
        )
        assert (
            next_or(or_excinfo.value.args)
            == "Cannot join with a safe-casted Caster"
        )
        assert (
            next_or(with_rule_excinfo.value.args)
            == "Cannot apply rule to a safe-casted Caster"
        )


class TestWrapResultWith:
    def test_wrap_result_with_success(self):
        mock = MagicMock(return_value=42)

        @wrap_result_with(mock, MagicMock)
        def process(value: str) -> int:
            return int(value)

        result = process("123")

        assert result == 42
        mock.assert_called_once_with(123)
        assert process.__annotations__["return"] == MagicMock

    def test_wrap_result_with_success_with_valid_function(self):
        @wrap_result_with(Decimal)
        def process(value: str) -> int:
            return int(value)

        result = process("123")

        assert result == Decimal(123)
        assert process.__annotations__["return"] == Decimal

    def test_wrap_result_with_failure(self):
        mock = MagicMock(side_effect=ValueError("Invalid value"))

        @wrap_result_with(mock, MagicMock)
        def process(value: str) -> int:
            return int(value)

        with pytest.raises(ValueError, match="Invalid value"):
            process("123")

        mock.assert_called_once_with(123)
        assert process.__annotations__["return"] == MagicMock

    def test_wrap_result_introspects_correctly(self):
        @wrap_result_with(Decimal)
        def process(value: str) -> int:
            return int(value)

        def another_wrapper(value: str) -> Decimal:
            return Decimal(value)

        @wrap_result_with(another_wrapper)
        def process_with_function():
            return "123"

        class AnotherWrapper:
            def __call__(self, value: str) -> Decimal:
                return Decimal(value)

        @wrap_result_with(AnotherWrapper())
        def process_with_class():
            return "123"

        assert process.__annotations__["value"] is str, (
            "Parameter should not be wrapped"
        )
        assert process.__annotations__["return"] is Decimal, (
            "Should use the annotation from the type"
        )
        assert process_with_function.__annotations__["return"] is Decimal, (
            "Should use the annotation from the function annotation"
        )
        assert process_with_class.__annotations__["return"] is Decimal, (
            "Should use the annotation from the annotation of the method"
        )


class TestAWrapResultWith:
    async def test_awrap_result_with_success(self):
        mock = AsyncMock(return_value=42)

        @awrap_result_with(mock, AsyncMock)
        async def process(value: str) -> int:
            return int(value)

        result = await process("123")

        assert result == 42
        mock.assert_called_once_with(123)
        assert process.__annotations__["return"] == AsyncMock

    async def test_awrap_result_with_success_with_valid_function(self):
        @awrap_result_with(as_async(Decimal), Decimal)
        async def process(value: str) -> int:
            return int(value)

        result = await process("123")

        assert result == Decimal(123)
        assert process.__annotations__["return"] == Decimal

    async def test_awrap_result_with_failure(self):
        mock = AsyncMock(side_effect=ValueError("Invalid value"))

        @awrap_result_with(mock, AsyncMock)
        async def process(value: str) -> int:
            return int(value)

        with pytest.raises(ValueError, match="Invalid value"):
            await process("123")

        mock.assert_called_once_with(123)
        assert process.__annotations__["return"] == AsyncMock

    async def test_awrap_result_introspects_correctly(self):
        async def another_wrapper(value: str) -> Decimal:
            return Decimal(value)

        @awrap_result_with(another_wrapper)
        async def process_with_function() -> str:
            return "123"

        class AnotherWrapper:
            async def __call__(self, value: str) -> Decimal:
                return Decimal(value)

        @awrap_result_with(AnotherWrapper())
        async def process_with_class():
            return "123"

        assert process_with_function.__annotations__["return"] is Decimal, (
            "Should use the annotation from the function annotation"
        )
        assert process_with_class.__annotations__["return"] is Decimal, (
            "Should use the annotation from the annotation of the method"
        )
