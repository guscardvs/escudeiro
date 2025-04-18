# pyright: reportPrivateUsage=false
import asyncio
import contextlib
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import (
    AbstractAsyncContextManager,
    AbstractContextManager,
    nullcontext,
)
from types import TracebackType
from typing import Any, Self, final, override
from unittest.mock import AsyncMock, Mock

from escudeiro.lazyfields import (
    _UNSET,
    ALazyContainer,
    AsyncLazyField,
    LazyContainer,
    LazyField,
    asynclazyfield,
    lazyfield,
    mark_class,
)


@final
class MockContextManager(AbstractContextManager, AbstractAsyncContextManager):
    """Reusable mock context manager for both sync and async contexts."""

    def __init__(self) -> None:
        super().__init__()
        self.call_count = 0
        self.enter_calls = 0
        self.exit_calls = 0

    def __call__(self) -> Self:
        return self

    @override
    def __enter__(self):
        super().__enter__()
        self.call_count += 1
        self.enter_calls += 1
        return self

    @override
    async def __aenter__(self):
        await super().__aenter__()
        self.call_count += 1
        self.enter_calls += 1
        return self

    @override
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> None:
        self.exit_calls += 1
        return

    @override
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ):
        self.exit_calls += 1
        return


@final
class LazyFieldTestFixture:
    """Test fixture for LazyField tests to avoid class creation in each test."""

    def __init__(
        self,
        lock_factory: Callable[
            [], AbstractContextManager
        ] = contextlib.nullcontext,
        field_value: Any = "test",
    ):
        self.mock = Mock()
        self.lock_factory = lock_factory
        self.field_value = field_value
        self.sample_class = self.create_sample_class()

    def create_sample_class(self):
        mock = self.mock
        field_value = self.field_value
        lock_factory = self.lock_factory

        @mark_class(lock_factory)
        class Sample:
            @lazyfield(lock_factory=lock_factory)
            def field(self):
                mock()
                return field_value

        return Sample

    def create_instance(self):
        return self.sample_class()

    def get_container(self, instance: Any) -> LazyContainer:
        """Get the LazyContainer from an instance."""
        return getattr(instance, LazyField.make_private("field"))

    def assert_container_exists(self, instance: Any):
        """Assert that the container exists on the instance."""
        assert hasattr(instance, LazyField.make_private("field"))

    def assert_container_content(self, instance: Any, expected_content: Any):
        """Assert that the container has the expected content."""
        container = self.get_container(instance)
        assert container.content == expected_content

    def assert_container_content_is_unset(self, instance: Any):
        """Assert that the container content is _UNSET."""
        container = self.get_container(instance)
        assert container.content is _UNSET


def test_lazyfield_freezes_value():
    """Test that LazyField freezes the value for each instance."""

    class Sample:
        @LazyField
        def frozen(self) -> list:
            return []

    sample = Sample()
    sample_2 = Sample()

    assert sample.frozen is sample.frozen
    assert sample_2.frozen is not sample.frozen
    assert isinstance(sample.frozen, list)


def test_lazyfield_creates_hidden_container():
    """Test that LazyField creates a hidden container attribute."""
    fixture = LazyFieldTestFixture()
    sample = fixture.create_instance()

    # Access to trigger initialization
    sample.field

    fixture.assert_container_exists(sample)
    fixture.assert_container_content(sample, "test")

    # Test the lock type
    container = fixture.get_container(sample)
    assert isinstance(container.lock, nullcontext)


def test_lazyfield_calls_context_on_get():
    """Test that LazyField calls the context manager on get."""
    mock_cm = MockContextManager()
    fixture = LazyFieldTestFixture(lock_factory=mock_cm)

    sample = fixture.create_instance()

    # First access triggers initialization and calls enter
    sample.field
    # Additional accesses should also call enter
    sample.field
    sample.field

    # Create another instance to verify per-instance behavior
    sample_2 = fixture.create_instance()
    sample_2.field

    # Each get should call enter
    assert mock_cm.enter_calls > 0, (
        "Lazyfield should call enter on each __get__"
    )


def test_lazyfield_calls_context_on_write():
    """Test that LazyField calls the context manager on write and delete."""
    mock_cm = MockContextManager()
    fixture = LazyFieldTestFixture(lock_factory=mock_cm)

    sample = fixture.create_instance()

    initial_calls = mock_cm.enter_calls
    sample.field = "World"
    assert mock_cm.enter_calls > initial_calls, "Should call enter on __set__"

    initial_calls = mock_cm.enter_calls
    del sample.field
    assert mock_cm.enter_calls > initial_calls, (
        "Should call enter on __delete__"
    )


def test_lazyfield_sets_container_content_to_unset_on_delete():
    """Test that LazyField sets container content to _UNSET on delete."""
    fixture = LazyFieldTestFixture()
    sample = fixture.create_instance()

    # Initialize
    sample.field
    fixture.assert_container_content(sample, "test")

    # Delete
    del sample.field
    fixture.assert_container_content_is_unset(sample)


def test_get_after_del_resets_function_state():
    """Test that getting after deleting resets the function state."""
    fixture = LazyFieldTestFixture()
    sample = fixture.create_instance()

    # First access
    sample.field
    # Second access shouldn't call the function again
    sample.field
    assert fixture.mock.call_count == 1

    # Delete and access again
    del sample.field
    sample.field

    # Function should be called again
    assert fixture.mock.call_count == 2


def test_lazyfield_is_only_computed_on_call():
    """Test that LazyField is only computed when accessed."""
    fixture = LazyFieldTestFixture()
    sample = fixture.create_instance()

    # Should not be called until accessed
    assert fixture.mock.call_count == 0

    # Access triggers computation
    sample.field
    assert fixture.mock.call_count == 1


def test_lazyfield_set_forces_value_into_field():
    """Test that setting LazyField forces a value into the field."""
    sentinel = object()
    fixture = LazyFieldTestFixture()
    sample = fixture.create_instance()

    # Set value
    sample.field = sentinel

    # Value should be set without calling function
    assert sample.field is sentinel
    assert fixture.mock.call_count == 0

    # Container should exist
    fixture.assert_container_exists(sample)


def test_lazyfield_with_different_lock_factories():
    """Test LazyField with different lock factories."""
    lock_types = [nullcontext, MockContextManager()]

    for lock in lock_types:
        fixture = LazyFieldTestFixture(lock_factory=lock)
        sample = fixture.create_instance()

        sample.field
        container = fixture.get_container(sample)

        if isinstance(lock, type) and issubclass(lock, nullcontext):  # pyright: ignore[reportUnnecessaryIsInstance]
            assert isinstance(container.lock, nullcontext)
        else:
            assert container.lock is lock


def test_lazyfield_with_inheritance():
    """Test that LazyField works with inheritance."""

    class Base:
        @lazyfield
        def field(self):
            return "base"

    class Child(Base):
        @lazyfield
        def field(self):
            return "child"

    base = Base()
    child = Child()

    assert base.field == "base"
    assert child.field == "child"


def test_lazyfield_with_property_descriptor_protocol():
    """Test that LazyField follows the property descriptor protocol."""

    class Sample:
        @lazyfield
        def field(self):
            return "test"

    # Descriptor protocol should work on class
    descriptor = Sample.__dict__["field"]
    assert isinstance(descriptor, LazyField)

    # __get__ with instance=None should return the descriptor itself
    assert descriptor.__get__(None, Sample) is descriptor


def test_lazyfield_concurrent_access():
    """Test that AsyncLazyField handles concurrent access correctly."""

    @final
    @mark_class(threading.Lock)
    class SlowSample:
        call_count = 0

        @lazyfield(lock_factory=threading.Lock)
        def field(self):
            self.call_count += 1
            time.sleep(0.1)  # Simulate slow computation
            return f"result-{self.call_count}"

    sample = SlowSample()

    # Concurrent access should only compute once
    with ThreadPoolExecutor() as executor:
        results = tuple(executor.map(lambda _: sample.field, range(3)))

    # All results should be the same
    assert all(r == results[0] for r in results), results
    assert sample.call_count == 1


class MockAsyncContextManager(contextlib.AbstractAsyncContextManager):
    """Reusable mock async context manager for testing."""

    def __init__(self) -> None:
        super().__init__()
        self.call_count: int = 0
        self.enter_calls: int = 0
        self.exit_calls: int = 0

    def __call__(self) -> Self:
        return self

    @override
    async def __aenter__(self):
        await super().__aenter__()
        self.call_count += 1
        self.enter_calls += 1
        return self

    @override
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ):
        self.exit_calls += 1
        return


@final
class AsyncLazyFieldTestFixture:
    """Test fixture for AsyncLazyField tests to avoid class creation in each test."""

    def __init__(
        self,
        lock_factory: Callable[[], AbstractAsyncContextManager] = nullcontext,
        field_value: Any = "test",
    ):
        self.mock = AsyncMock()
        self.lock_factory = lock_factory or contextlib.nullcontext
        self.field_value = field_value
        self.sample_class = self.create_sample_class()

    def create_sample_class(self):
        mock = self.mock
        field_value = self.field_value
        lock_factory = self.lock_factory

        @mark_class(actx_factory=lock_factory)
        class Sample:
            @asynclazyfield(lock_factory=lock_factory)
            async def field(self):
                await mock()
                return field_value

        return Sample

    def create_instance(self):
        return self.sample_class()

    def get_container(self, instance: Any) -> ALazyContainer:
        """Get the AlazyContainer from an instance."""
        return getattr(instance, AsyncLazyField.make_private("field"))

    def assert_container_exists(self, instance: Any):
        """Assert that the container exists on the instance."""
        assert hasattr(instance, AsyncLazyField.make_private("field"))

    async def assert_container_content(
        self, instance: Any, expected_content: Any
    ):
        """Assert that the container has the expected content."""
        container = self.get_container(instance)
        content = await container.acquire()
        assert content == expected_content

    async def assert_container_content_is_unset(self, instance: Any):
        """Assert that the container content is _UNSET."""
        container = self.get_container(instance)
        content = await container.acquire()
        assert content is _UNSET


async def test_asynclazyfield_freezes_value():
    """Test that AsyncLazyField freezes the value for each instance."""

    class Sample:
        @asynclazyfield
        async def frozen(self) -> list:
            return []

    sample = Sample()
    sample_2 = Sample()

    result1 = await sample.frozen()
    result2 = await sample.frozen()
    result3 = await sample_2.frozen()

    assert result1 is result2
    assert result2 is not result3
    assert isinstance(result1, list)


async def test_asynclazyfield_creates_hidden_container():
    """Test that AsyncLazyField creates a hidden container attribute."""
    fixture = AsyncLazyFieldTestFixture()
    sample = fixture.create_instance()

    # Access to trigger initialization
    await sample.field()

    fixture.assert_container_exists(sample)
    await fixture.assert_container_content(sample, "test")

    # Test the lock type
    container = fixture.get_container(sample)
    assert isinstance(container.lock, contextlib.nullcontext)


async def test_asynclazyfield_calls_context_on_get():
    """Test that AsyncLazyField calls the context manager on get."""
    mock_cm = MockAsyncContextManager()
    fixture = AsyncLazyFieldTestFixture(lock_factory=mock_cm)

    sample = fixture.create_instance()
    # First access triggers initialization and calls enter
    await sample.field()
    initial_enter_calls = mock_cm.enter_calls

    # Additional accesses should also call enter
    await sample.field()
    await sample.field()

    # Create another instance to verify per-instance behavior
    sample_2 = fixture.create_instance()
    await sample_2.field()

    # Each get should call enter
    assert mock_cm.enter_calls > initial_enter_calls, (
        "AsyncLazyField should call enter on each __get__"
    )


async def test_asynclazyfield_is_only_computed_on_call():
    """Test that AsyncLazyField is only computed when accessed."""
    fixture = AsyncLazyFieldTestFixture()
    sample = fixture.create_instance()

    # Should not be called until accessed
    assert fixture.mock.await_count == 0

    # Access triggers computation
    await sample.field()
    assert fixture.mock.await_count == 1


async def test_asynclazyfield_reset_with_none():
    """Test that resetting AsyncLazyField with None deletes the content."""
    fixture = AsyncLazyFieldTestFixture()
    sample = fixture.create_instance()

    # Initialize
    await sample.field()
    await fixture.assert_container_content(sample, "test")

    # Reset with None should delete
    descriptor = type(sample).__dict__["field"]
    await descriptor.reset(sample)

    await fixture.assert_container_content_is_unset(sample)


async def test_asynclazyfield_get_after_reset():
    """Test that getting after resetting recomputes the value."""
    fixture = AsyncLazyFieldTestFixture()
    sample = fixture.create_instance()

    # First access
    await sample.field()
    # Second access shouldn't call the function again
    await sample.field()
    assert fixture.mock.await_count == 1

    # Reset and access again
    descriptor = sample.__class__.__dict__["field"]
    await descriptor.reset(sample)
    await sample.field()

    # Function should be called again
    assert fixture.mock.await_count == 2


async def test_asynclazyfield_reset_with_value():
    """Test that resetting AsyncLazyField with a value sets the content."""
    fixture = AsyncLazyFieldTestFixture()
    sample = fixture.create_instance()

    # Initialize
    await sample.field()

    # Reset with value
    descriptor = sample.__class__.__dict__["field"]
    await descriptor.reset(sample, "new_value")

    # Should have new value without calling function
    result = await sample.field()
    assert result == "new_value"
    assert fixture.mock.await_count == 1  # Only the initial call


async def test_asynclazyfield_reset_on_uninitialized():
    """Test that resetting an uninitialized AsyncLazyField works correctly."""
    fixture = AsyncLazyFieldTestFixture()
    sample = fixture.create_instance()

    # Reset without initialization
    descriptor = sample.__class__.__dict__["field"]
    await descriptor.reset(sample, "direct_value")

    # Should have the value without calling function
    result = await sample.field()
    assert result == "direct_value"
    assert fixture.mock.await_count == 0


async def test_asynclazyfield_concurrent_access():
    """Test that AsyncLazyField handles concurrent access correctly."""

    @final
    @mark_class(actx_factory=asyncio.Lock)
    class SlowSample:
        call_count = 0

        @asynclazyfield(lock_factory=asyncio.Lock)
        async def field(self):
            self.call_count += 1
            await asyncio.sleep(0.1)  # Simulate slow computation
            return f"result-{self.call_count}"

    sample = SlowSample()

    # Concurrent access should only compute once
    results = await asyncio.gather(
        sample.field(), sample.field(), sample.field()
    )

    # All results should be the same
    assert all(r == results[0] for r in results), results
    assert sample.call_count == 1


async def test_asynclazyfield_with_different_lock_factories():
    """Test AsyncLazyField with different lock factories."""
    results = []

    class CustomLockManager(MockAsyncContextManager):
        @override
        async def __aenter__(self):
            result = await super().__aenter__()
            results.append("lock entered")
            return result

    lock_factory = CustomLockManager()
    fixture = AsyncLazyFieldTestFixture(lock_factory=lock_factory)
    sample = fixture.create_instance()

    await sample.field()
    assert "lock entered" in results
    assert lock_factory.enter_calls > 0


async def test_asynclazyfield_with_inheritance():
    """Test that AsyncLazyField works with inheritance."""

    class Base:
        @asynclazyfield
        async def field(self):
            return "base"

    class Child(Base):
        @asynclazyfield
        async def field(self):
            return "child"

    base = Base()
    child = Child()

    assert await base.field() == "base"
    assert await child.field() == "child"


async def test_asynclazyfield_descriptor_protocol():
    """Test that AsyncLazyField follows the descriptor protocol."""

    class Sample:
        @asynclazyfield
        async def field(self):
            return "test"

    # Descriptor protocol should work on class
    descriptor = Sample.__dict__["field"]
    assert isinstance(descriptor, AsyncLazyField)

    # __get__ with instance=None should return the descriptor itself
    assert descriptor.__get__(None, Sample) is descriptor


async def test_alazycontainer_operations():
    """Test AlazyContainer operations directly."""
    lock = MockAsyncContextManager()
    container = ALazyContainer("initial", lock)

    # Test acquire
    content = await container.acquire()
    assert content == "initial"
    assert lock.enter_calls == 1
    assert lock.exit_calls == 1

    # Test put
    await container.put("updated")
    content = await container.acquire()
    assert content == "updated"
    assert lock.enter_calls == 3
    assert lock.exit_calls == 3

    # Test delete
    await container.delete()
    content = await container.acquire()
    assert content is _UNSET
    assert lock.enter_calls == 5
    assert lock.exit_calls == 5


async def test_asynclazyfield_decorated_methods():
    """Test different ways of decorating with asynclazyfield."""

    # Test with direct decoration
    class Sample1:
        @asynclazyfield
        async def method1(self):
            return "method1"

    # Test with function call decoration
    class Sample2:
        @asynclazyfield()
        async def method2(self):
            return "method2"

    # Test with custom lock factory
    lock = MockAsyncContextManager()

    @mark_class(actx_factory=lock)
    class Sample3:
        @asynclazyfield(lock_factory=lambda: lock)
        async def method3(self):
            return "method3"

    s1 = Sample1()
    s2 = Sample2()
    s3 = Sample3()

    assert await s1.method1() == "method1"
    assert await s2.method2() == "method2"
    assert await s3.method3() == "method3"
    assert lock.enter_calls > 0


class TestComplexUseCases:
    """Test complex use cases with AsyncLazyField."""

    async def test_multiple_asynclazyfields_same_class(self):
        """Test multiple AsyncLazyFields on the same class."""
        mock1 = AsyncMock(return_value="value1")
        mock2 = AsyncMock(return_value="value2")

        class MultiFields:
            @asynclazyfield
            async def field1(self):
                await mock1()
                return "value1"

            @asynclazyfield
            async def field2(self):
                await mock2()
                return "value2"

        instance = MultiFields()

        assert await instance.field1() == "value1"
        assert await instance.field2() == "value2"

        # Verify each function was called exactly once
        assert mock1.await_count == 1
        assert mock2.await_count == 1

        # Access again - should use cached values
        assert await instance.field1() == "value1"
        assert await instance.field2() == "value2"

        assert mock1.await_count == 1
        assert mock2.await_count == 1

    async def test_asynclazyfield_depending_on_another(self):
        """Test an AsyncLazyField that depends on another AsyncLazyField."""
        first_mock = AsyncMock(return_value="first")
        second_mock = AsyncMock()

        class DependentFields:
            @asynclazyfield
            async def first(self):
                await first_mock()
                return "first"

            @asynclazyfield
            async def second(self):
                first_value = await self.first()
                await second_mock(first_value)
                return f"second-{first_value}"

        instance = DependentFields()

        # Access the dependent field
        result = await instance.second()

        assert result == "second-first"
        assert first_mock.await_count == 1
        second_mock.assert_called_once_with("first")

        # Access again - both should use cached values
        result = await instance.second()
        assert result == "second-first"
        assert first_mock.await_count == 1
        assert second_mock.call_count == 1
