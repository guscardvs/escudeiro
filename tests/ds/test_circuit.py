# pyright: reportPrivateUsage=false
import asyncio
from functools import partial
from unittest.mock import Mock

import pytest

from escudeiro.ds import CircuitBreaker, with_circuit_breaker


@pytest.fixture
def circuit_breaker():
    """Fixture providing a fresh CircuitBreaker instance for each test."""
    return CircuitBreaker()


async def test_successful_execution(circuit_breaker: CircuitBreaker):
    """Test that successful function execution works normally."""

    async def test_func():
        return "success"

    result = await circuit_breaker.execute(test_func)
    assert result == "success"
    assert not circuit_breaker.is_frozen


async def test_freezes_on_exception(circuit_breaker: CircuitBreaker):
    """Test that the circuit breaker freezes when an exception occurs."""
    # Override freeze function to be immediate for testing
    circuit_breaker.freeze_function = partial(asyncio.sleep, 0.01)

    error_mock = Mock()
    circuit_breaker.on_error = error_mock

    # Function that raises an exception
    async def failing_func():
        raise ValueError("Test error")

    # Function that doesn't raise an exception
    async def success_func():
        return "success"

    async def check():
        # Verify circuit breaker state
        assert circuit_breaker.is_frozen
        assert circuit_breaker._freeze_future is not None
        error_mock.assert_called_once()

    # First call should raise and trigger freeze
    with pytest.raises(ValueError, match="Test error"):
        _ = await asyncio.gather(circuit_breaker.execute(failing_func), check())

    # Wait for unfreeze
    assert circuit_breaker._freeze_future is not None
    await circuit_breaker._freeze_future

    # After unfreeze, successful calls should work
    result = await circuit_breaker.execute(success_func)
    assert result == "success"
    assert not circuit_breaker.is_frozen


async def test_multiple_concurrent_executions(circuit_breaker: CircuitBreaker):
    """Test that multiple concurrent executions handle freezing correctly."""
    circuit_breaker.freeze_function = partial(asyncio.sleep, 0.1)

    # Create a failing function
    call_count = 0

    async def test_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("First call error")
        return f"Call {call_count}"

    # Start multiple tasks
    tasks = [circuit_breaker.execute(test_func) for _ in range(5)]
    results = []
    # First task should raise, others should wait and retry
    for future in asyncio.as_completed(tasks):
        try:
            result = await future
            results.append(result)
        except ValueError:
            results.append("error")

    # We should have one error and 4 successful retry calls
    assert "error" in results
    assert all(r.startswith("Call") for r in results if r != "error")
    assert call_count == 6  # 1 initial + 5 retries


async def test_decorator_functionality():
    """Test that the decorator properly wraps the function with circuit breaker logic."""
    cb = CircuitBreaker()
    cb.freeze_function = partial(asyncio.sleep, 0.01)

    execution_count = 0

    @with_circuit_breaker(cb)
    async def test_func(should_fail: bool = False):
        nonlocal execution_count
        execution_count += 1
        if should_fail:
            raise ValueError("Decorator test error")
        return "decorator success"

    # Test successful execution
    result = await test_func()
    assert result == "decorator success"
    assert execution_count == 1

    async def check():
        await asyncio.sleep(0.01)
        assert cb.is_frozen
        assert execution_count == 2

        # Wait for unfreeze
        assert cb._freeze_future is not None
        await cb._freeze_future

        # Test execution after unfreeze
        result = await test_func()
        assert result == "decorator success"

    # Test failing execution
    for task in asyncio.as_completed((test_func(should_fail=True), check())):
        try:
            await task
        except ValueError:
            pass
    # failing call + its retry after the freeze + the call made by check()
    assert execution_count == 4


async def test_custom_freeze_function(circuit_breaker: CircuitBreaker):
    """Test that a custom freeze function works correctly."""
    freeze_called = False

    async def custom_freeze():
        nonlocal freeze_called
        freeze_called = True
        await asyncio.sleep(0.01)

    circuit_breaker.freeze_function = custom_freeze

    async def failing_func():
        raise RuntimeError("Custom freeze test")

    async def check():
        assert circuit_breaker.is_frozen
        assert circuit_breaker._freeze_future is not None
        await circuit_breaker._freeze_future

        assert freeze_called
        assert not circuit_breaker.is_frozen

    # Trigger freeze
    with pytest.raises(RuntimeError):
        _ = await asyncio.gather(circuit_breaker.execute(failing_func), check())


async def test_custom_error_handler(circuit_breaker: CircuitBreaker):
    """Test that a custom error handler is called when an exception occurs."""
    handled_exceptions = []

    def custom_handler(exc: Exception):
        handled_exceptions.append(exc)

    circuit_breaker.on_error = custom_handler
    circuit_breaker.freeze_function = partial(asyncio.sleep, 0.01)

    # Function that raises an exception
    async def failing_func():
        raise KeyError("Custom handler test")

    # Trigger error handler
    with pytest.raises(KeyError):
        await circuit_breaker.execute(failing_func)

    assert len(handled_exceptions) == 1
    assert isinstance(handled_exceptions[0], KeyError)
    assert str(handled_exceptions[0]) == "'Custom handler test'"


async def test_freeze_function_exception(circuit_breaker: CircuitBreaker):
    """A failing freeze function surfaces once and never wedges the breaker."""

    async def failing_freeze():
        raise RuntimeError("Freeze function failed")

    circuit_breaker.freeze_function = failing_freeze
    calls = 0

    async def test_func():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ValueError("Initial error")
        return "ok"

    async def check():
        assert circuit_breaker.is_frozen
        # Wait for the freeze future to complete (with exception)
        assert circuit_breaker._freeze_future is not None
        await circuit_breaker._freeze_future

    # First execution triggers freeze, whose failure reaches its callers
    with pytest.raises(RuntimeError, match="Freeze function failed"):
        _ = await asyncio.gather(circuit_breaker.execute(test_func), check())

    # ... but the breaker is not stuck frozen: later calls really run func
    assert not circuit_breaker.is_frozen
    assert await circuit_breaker.execute(test_func) == "ok"
    assert await circuit_breaker.execute(test_func) == "ok"
    assert calls == 3  # was: 1, every later call re-raised the stale error


async def test_cancelled_waiter_does_not_cancel_the_others():
    cb = CircuitBreaker(freeze_function=partial(asyncio.sleep, 0.2))
    calls = 0

    async def f():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("x")
        return "ok"

    first = asyncio.create_task(cb.execute(f))
    await asyncio.sleep(0.02)  # first failed, breaker frozen
    assert cb.is_frozen
    b = asyncio.create_task(cb.execute(f))
    c = asyncio.create_task(cb.execute(f))
    await asyncio.sleep(0.02)
    _ = c.cancel()
    results = await asyncio.gather(first, b, c, return_exceptions=True)
    assert results[0] == "ok" and results[1] == "ok"
    assert isinstance(results[2], asyncio.CancelledError)


async def test_cancelled_unfreeze_task_releases_waiters():
    cb = CircuitBreaker(freeze_function=partial(asyncio.sleep, 30))

    async def f():
        raise RuntimeError("x")

    waiter = asyncio.create_task(cb.execute(f))
    await asyncio.sleep(0.02)
    assert cb.is_frozen
    assert cb._unfreeze_task is not None  # strong reference is kept
    _ = cb._unfreeze_task.cancel()

    # waiters are resolved (cancelled), not left hanging; breaker unfrozen
    done, pending = await asyncio.wait([waiter], timeout=1)
    assert not pending
    assert waiter.cancelled()
    assert not cb.is_frozen
    assert cb._freeze_future is not None and cb._freeze_future.done()


async def test_reentry_during_frozen_state(circuit_breaker: CircuitBreaker):
    """Test reentry behavior when circuit is already frozen."""
    circuit_breaker.freeze_function = partial(asyncio.sleep, 0.1)

    # First trigger a freeze
    async def failing_func():
        raise ValueError("Freeze trigger")

    # Create a test function that tracks calls
    call_count = 0

    async def test_func():
        nonlocal call_count
        call_count += 1
        return f"Call {call_count}"

    async def check():
        assert circuit_breaker.is_frozen

        # Start multiple concurrent calls during frozen state
        tasks = []
        for _ in range(3):
            tasks.append(
                asyncio.create_task(circuit_breaker.execute(test_func))
            )

        # Allow the circuit breaker to unfreeze
        await asyncio.sleep(0.2)

        # All tasks should complete successfully
        results = await asyncio.gather(*tasks)

        # All calls should have occurred after unfreezing
        assert call_count == 3
        assert all(r.startswith("Call") for r in results)
        assert not circuit_breaker.is_frozen

    # Trigger initial freeze
    with pytest.raises(ValueError):
        _ = await asyncio.gather(circuit_breaker.execute(failing_func), check())
