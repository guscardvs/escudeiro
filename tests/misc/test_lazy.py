# pyright: reportUnusedParameter=false,reportMissingParameterType=false
from typing import Generic, TypeVar, override

import pytest

from escudeiro.misc.lazy import MethodType, lazymethod


def test_method_type_detection():
    """Test the internal _determine_method_type logic."""

    class Test:
        def __init__(self) -> None:
            self.counter = 0

        @lazymethod
        def self_only(self):
            self.counter += 1
            return f"self_only_{self.counter}"

        @lazymethod
        def hashable_args(self, a: str, b: int):
            self.counter += 1
            return f"hashable_{self.counter}"

        @lazymethod
        def unhashable_args(self, a: list):
            self.counter += 1
            return f"unhashable_{self.counter}"

        @lazymethod
        def unannotated_args(self, a):
            self.counter += 1
            return f"unannotated_{self.counter}"

    # Extract lazymethod instances
    self_only_method = Test.__dict__["self_only"]
    hashable_method = Test.__dict__["hashable_args"]
    unhashable_method = Test.__dict__["unhashable_args"]
    unannotated_method = Test.__dict__["unannotated_args"]

    # Check method types
    assert self_only_method._method_type == MethodType.SELF_ONLY
    assert hashable_method._method_type == MethodType.HASHABLE_ARGS
    assert unhashable_method._method_type == MethodType.UNKNOWN_OR_UNHASHABLE
    assert unannotated_method._method_type == MethodType.UNKNOWN_OR_UNHASHABLE


def test_container_selection():
    """Test container type selection based on method type."""

    class Test:
        def __init__(self) -> None:
            self.counter = 0

        @lazymethod
        def self_only(self):
            self.counter += 1
            return f"self_only_{self.counter}"

        @lazymethod
        def hashable_args(self, a: str, b: int):
            self.counter += 1
            return f"hashable_{self.counter}"

        @lazymethod
        def unhashable_args(self, a: list):
            self.counter += 1
            return f"unhashable_{self.counter}"

    # Extract lazymethod instances
    self_only_method = Test.__dict__["self_only"]
    hashable_method = Test.__dict__["hashable_args"]
    unhashable_method = Test.__dict__["unhashable_args"]

    # Check container types
    assert self_only_method._container is None
    assert hashable_method._container is dict
    assert unhashable_method._container is list


def test_self_only_caching():
    """Test caching with no parameters (only self is used as cache key)."""

    class Test:
        def __init__(self) -> None:
            self.counter = 0

        @lazymethod
        def calculate(self):
            self.counter += 1
            return f"result_{self.counter}"

    # Test with a single instance
    t1 = Test()
    assert t1.calculate() == "result_1"
    assert t1.calculate() == "result_1"  # Cached result
    assert t1.counter == 1  # Function called only once

    # Verify the private attribute exists and holds the value
    private_name = lazymethod.get_private("calculate")
    assert hasattr(t1, private_name)
    assert getattr(t1, private_name) == "result_1"

    # Test with a different instance
    t2 = Test()
    assert t2.calculate() == "result_1"  # New instance, new calculation
    assert t2.counter == 1

    # Verify initialization status
    assert lazymethod.is_initialized(t1, "calculate")
    assert lazymethod.is_initialized(t2, "calculate")
    t3 = Test()
    assert not lazymethod.is_initialized(t3, "calculate")


def test_hashable_args_caching():
    """Test with annotated hashable parameters that are used as cache keys."""

    class Test:
        def __init__(self) -> None:
            self.counter = 0

        @lazymethod
        def calculate_with_params(self, a: str, b: int, c: bool = True):
            self.counter += 1
            return f"{a}_{b}_{int(c)}_{self.counter}"

    t = Test()

    # Basic parameter caching
    assert t.calculate_with_params("test", 1) == "test_1_1_1"
    assert t.calculate_with_params("test", 1) == "test_1_1_1"  # Cached
    assert (
        t.calculate_with_params("other", 1) == "other_1_1_2"
    )  # Different first param
    assert (
        t.calculate_with_params("test", 2) == "test_2_1_3"
    )  # Different second param
    assert t.counter == 3

    # Test with default and explicit kwargs
    assert (
        t.calculate_with_params("test", 1, False) == "test_1_0_4"
    )  # Different default
    assert (
        t.calculate_with_params("test", 1, c=False) == "test_1_0_4"
    )  # Should be cached
    assert (
        t.calculate_with_params("test", b=1, c=True) == "test_1_1_1"
    )  # Should match first call
    assert t.counter == 4

    # Verify the private attribute exists and holds a dict with proper keys
    private_name = lazymethod.get_private("calculate_with_params")
    assert hasattr(t, private_name)
    cache_dict = getattr(t, private_name)
    assert isinstance(cache_dict, dict)

    # Check specific cache keys
    # The key format is (args, tuple(kwargs.items()))
    key1 = (("a", "test"), ("b", 1), ("c", True))  # a="test", b=1, no kwargs
    key2 = (("a", "test"), ("b", 1), ("c", False))  # a="test", b=1, c=False

    assert cache_dict[frozenset(key1)] == "test_1_1_1"
    assert cache_dict[frozenset(key2)] == "test_1_0_4"


def test_unhashable_args_caching():
    """Test with unhashable or unannotated parameters."""

    class Test:
        def __init__(self) -> None:
            self.counter = 0

        @lazymethod
        def calculate_with_list(self, items: list):
            self.counter += 1
            return f"list_{len(items)}_{self.counter}"

    t = Test()

    # List parameter (unhashable)
    list1 = [1, 2, 3]
    list2 = [1, 2, 3]  # Same content but different object

    assert t.calculate_with_list(list1) == "list_3_1"
    assert t.calculate_with_list(list1) == "list_3_1"  # Same object, cached
    assert (
        t.calculate_with_list(list2) == "list_3_1"
    )  # Different object, but equality exists
    assert t.counter == 1

    # Verify the private attribute exists and holds a list with proper items
    private_name = lazymethod.get_private("calculate_with_list")
    assert hasattr(t, private_name)
    cache_list = getattr(t, private_name)
    assert isinstance(cache_list, list)
    assert len(cache_list) == 1

    # Cache items are tuples of ((args, kwargs_tuple), result)
    assert cache_list[0][0] == (("items", list1),)
    assert cache_list[0][1] == "list_3_1"


def test_mixed_parameter_types():
    """Test methods with a mix of hashable and unhashable parameters."""

    class Test:
        def __init__(self) -> None:
            self.counter = 0

        @lazymethod
        def calculate_mixed(self, name: str, items: list):
            self.counter += 1
            return f"{name}_{len(items)}_{self.counter}"

    t = Test()
    list1 = [1, 2, 3]
    list2 = [1, 2, 3]  # Different object, same content

    assert t.calculate_mixed("test", list1) == "test_3_1"
    assert (
        t.calculate_mixed("test", list1) == "test_3_1"
    )  # Same objects, cached
    assert (
        t.calculate_mixed("test", list2) == "test_3_1"
    )  # Different list object, equality still exists
    assert t.calculate_mixed("other", list1) == "other_3_2"  # Different string
    assert t.counter == 2

    # Since there's an unhashable parameter, container should be a list
    private_name = lazymethod.get_private("calculate_mixed")
    cache_list = getattr(t, private_name)
    assert isinstance(cache_list, list)
    assert len(cache_list) == 2


def test_complex_hashable_types():
    """Test caching with complex hashable type annotations."""

    class Test:
        def __init__(self) -> None:
            self.counter = 0

        @lazymethod
        def calculate_complex(self, a: tuple[str, int], b: frozenset):
            self.counter += 1
            return f"complex_{self.counter}"

    t = Test()

    tup = ("test", 1)
    fs = frozenset([1, 2, 3])

    assert t.calculate_complex(tup, fs) == "complex_1"
    assert t.calculate_complex(tup, fs) == "complex_1"  # Cached
    assert (
        t.calculate_complex(("test", 2), fs) == "complex_2"
    )  # Different tuple
    assert t.counter == 2

    # Since parameters are hashable, container should be a dict
    private_name = lazymethod.get_private("calculate_complex")
    cache = getattr(t, private_name)
    assert isinstance(cache, dict)


def test_nested_container_types():
    """Test with nested container types to verify recursive hashability check."""

    class Test:
        def __init__(self) -> None:
            self.counter = 0

        @lazymethod
        def with_nested_tuple_dict(self, a: tuple[dict[str, int], ...]):
            self.counter += 1
            return f"nested_tuple_dict_{self.counter}"

        @lazymethod
        def with_nested_list_dict(self, a: list[dict[str, int]]):
            self.counter += 1
            return f"nested_list_dict_{self.counter}"

    t = Test()

    # Tuple containing dicts (hashable overall)
    tup_dict = ({"a": 1}, {"b": 2})
    assert t.with_nested_tuple_dict(tup_dict) == "nested_tuple_dict_1"
    assert t.with_nested_tuple_dict(tup_dict) == "nested_tuple_dict_1"  # Cached

    # Although parameters' origins are hashable, args are not, container should be list
    private_name = lazymethod.get_private("with_nested_tuple_dict")
    cache = getattr(t, private_name)
    assert isinstance(cache, list)

    # List containing dicts (unhashable)
    list_dict = [{"a": 1}, {"b": 2}]
    assert t.with_nested_list_dict(list_dict) == "nested_list_dict_2"
    assert (
        t.with_nested_list_dict(list_dict) == "nested_list_dict_2"
    )  # Cached by identity

    # Since parameters are unhashable, container should be a list
    private_name = lazymethod.get_private("with_nested_list_dict")
    cache = getattr(t, private_name)
    assert isinstance(cache, list)


def test_kwargs_handling():
    """Test handling of keyword arguments in caching."""

    class Test:
        def __init__(self) -> None:
            self.counter = 0

        @lazymethod
        def with_kwargs(self, a: str, **kwargs: int):
            self.counter += 1
            return f"kwargs_{self.counter}"

    t = Test()

    assert t.with_kwargs("test") == "kwargs_1"
    assert t.with_kwargs("test") == "kwargs_1"  # Cached
    assert t.with_kwargs("test", x=1) == "kwargs_2"  # Different kwargs
    assert t.with_kwargs("test", x=1) == "kwargs_2"  # Cached
    assert t.with_kwargs("test", x=1, y=2) == "kwargs_3"  # More kwargs
    assert (
        t.with_kwargs("test", y=2, x=1) == "kwargs_3"
    )  # Same kwargs, different order
    assert t.counter == 3


def test_descriptor_behavior():
    """Test the descriptor behavior of lazymethod."""

    class Test:
        def __init__(self) -> None:
            self.counter = 0

        @lazymethod
        def calculate(self):
            self.counter += 1
            return f"result_{self.counter}"

    # Access via class should return the descriptor itself
    descriptor = Test.calculate
    assert isinstance(descriptor, lazymethod)

    # Access via instance should return a callable
    t = Test()
    method = t.calculate
    assert callable(method)

    # Calling the method should work
    assert method() == "result_1"


def test_internal_methods():
    """Test internal methods of lazymethod."""

    class Test:
        def __init__(self) -> None:
            self.counter = 0

        @lazymethod
        def calculate(self, a: str):
            self.counter += 1
            return f"{a}_{self.counter}"

    t = Test()

    # Get the descriptor and method name
    descriptor = Test.__dict__["calculate"]
    private_name = descriptor.private_name

    # Test _get when no value exists
    result = descriptor._get(t, private_name, ("test",), {})
    assert result is None

    # Test _set
    result = descriptor._set(t, "test")
    assert result == "test_1"

    # Test _get after value exists
    result = descriptor._get(t, private_name, ("test",), {})
    assert result == "test_1"


def test_inheritance():
    """Test lazymethod behavior with class inheritance."""

    class Base:
        def __init__(self) -> None:
            self.counter = 0

        @lazymethod
        def calculate(self, a: str):
            self.counter += 1
            return f"base_{a}_{self.counter}"

    class Derived(Base):
        @lazymethod
        def calculate(self, a: str):
            self.counter += 1
            return f"derived_{a}_{self.counter}"

    b = Base()
    d = Derived()

    assert b.calculate("test") == "base_test_1"
    assert d.calculate("test") == "derived_test_1"

    # Each instance should have its own cache
    assert lazymethod.is_initialized(b, "calculate")
    assert lazymethod.is_initialized(d, "calculate")


def test_reset_functionality():
    """Test resetting cached values."""

    class Test:
        def __init__(self) -> None:
            self.counter = 0

        @lazymethod
        def self_only(self):
            self.counter += 1
            return f"self_only_{self.counter}"

        @lazymethod
        def with_args(self, a: str):
            self.counter += 1
            return f"{a}_{self.counter}"

        @lazymethod
        def with_unhashable(self, items: list):
            self.counter += 1
            return f"list_{self.counter}"

    t = Test()

    # Initial calculations
    assert t.self_only() == "self_only_1"
    assert t.with_args("test") == "test_2"
    list1 = [1, 2, 3]
    assert t.with_unhashable(list1) == "list_3"

    # Test manual reset by deleting private attributes
    private_name1 = lazymethod.get_private("self_only")
    delattr(t, private_name1)
    assert not lazymethod.is_initialized(t, "self_only")
    assert t.self_only() == "self_only_4"  # Recalculated

    # Reset specific parameter
    private_name2 = lazymethod.get_private("with_args")
    cache_dict = getattr(t, private_name2)
    key = (("a", "test"),)
    del cache_dict[frozenset(key)]
    assert t.with_args("test") == "test_5"  # Recalculated

    # Reset unhashable parameter
    private_name3 = lazymethod.get_private("with_unhashable")
    cache_list = getattr(t, private_name3)
    cache_list.clear()
    assert t.with_unhashable(list1) == "list_6"  # Recalculated


def test_is_hashable_function():
    """Test the _is_hashable function's core logic."""

    class CustomClass:
        pass

    class HashableClass:
        @override
        def __hash__(self):
            return 42

    # Create a lazymethod instance to access _is_hashable
    class TestClass:
        @lazymethod
        def dummy(self):
            pass

    descriptor = TestClass.__dict__["dummy"]

    # Test various types
    assert descriptor.is_hashable(str) is True
    assert descriptor.is_hashable(int) is True
    assert descriptor.is_hashable(tuple) is True
    assert descriptor.is_hashable(list) is False
    assert descriptor.is_hashable(dict[str, int]) is False
    assert descriptor.is_hashable(tuple[int, str]) is True
    assert descriptor.is_hashable(list[int]) is False
    assert descriptor.is_hashable(HashableClass) is True
    assert descriptor.is_hashable(CustomClass) is True  # Classes are hashable

    # Test recursive types
    assert descriptor.is_hashable(tuple[dict[str, int], ...]) is False
    assert descriptor.is_hashable(tuple[tuple[int, str], ...]) is True


def test_generic_types():
    """Test with generic type annotations."""
    T = TypeVar("T")

    class GenericTest(Generic[T]):
        def __init__(self) -> None:
            self.counter = 0

        @lazymethod
        def calculate(self, a: T):
            self.counter += 1
            return f"generic_{self.counter}"

    t_int = GenericTest[int]()
    t_str = GenericTest[str]()

    assert t_int.calculate(1) == "generic_1"
    assert t_int.calculate(1) == "generic_1"  # Cached
    assert t_int.calculate(2) == "generic_2"  # Different value

    assert t_str.calculate("a") == "generic_1"
    assert t_str.calculate("a") == "generic_1"  # Cached
    assert t_str.calculate("b") == "generic_2"  # Different value


def test_descriptor_name_setting():
    """Test that __set_name__ properly sets public and private names."""

    class Test:
        def __init__(self) -> None:
            pass

        @lazymethod
        def original_name(self):
            return "value"

    # Access the descriptor directly
    descriptor = Test.__dict__["original_name"]
    assert descriptor.public_name == "original_name"
    assert descriptor.private_name == "_lazymethod_original_name_"

    # Test format
    assert lazymethod.format_ == "_lazymethod_{method_name}_"
    assert lazymethod.get_private("test_method") == "_lazymethod_test_method_"


def test_overloaded_method():
    """Test lazymethod with type-overloaded methods."""

    class Test:
        def __init__(self) -> None:
            self.counter = 0

        @lazymethod
        def calculate(self, param: str | int):
            self.counter += 1
            if isinstance(param, str):
                return f"str_{param}_{self.counter}"
            else:
                return f"int_{param}_{self.counter}"

    t = Test()

    assert t.calculate("test") == "str_test_1"
    assert t.calculate("test") == "str_test_1"  # Cached
    assert t.calculate(123) == "int_123_2"
    assert t.calculate(123) == "int_123_2"  # Cached
    assert t.counter == 2


def test_edge_cases():
    """Test edge cases and potential issues."""

    class Test:
        def __init__(self) -> None:
            self.counter = 0

        @lazymethod
        def empty_tuple(self, a: tuple = ()):
            self.counter += 1
            return f"empty_{self.counter}"

        @lazymethod
        def none_value(self, a: str | None = None):
            self.counter += 1
            return f"none_{self.counter}"

    t = Test()

    # Empty tuples and None values should work as expected
    assert t.empty_tuple() == "empty_1"
    assert t.empty_tuple() == "empty_1"  # Cached
    assert t.empty_tuple(()) == "empty_1"  # Same as default

    assert t.none_value() == "none_2"
    assert t.none_value() == "none_2"  # Cached
    assert t.none_value(None) == "none_2"  # Same as default


def test_exception_does_not_corrupt_cache():
    class Test:
        def __init__(self) -> None:
            self.counter = 0

        @lazymethod
        def self_only(self):
            # Container is None for SELF_ONLY methods.
            self.counter += 1
            if self.counter <= 1:
                raise ValueError("Exception in self_only")
            return self.counter

        @lazymethod
        def hashable(self, a: int, b: str) -> str:
            # Container is dict because args are hashable.
            self.counter += 1
            if self.counter == 2:
                raise ValueError("Exception in hashable")
            return f"{a}_{b}_{self.counter}"

        @lazymethod
        def mixed(self, a: int, b: list[str], c, d=True) -> str:
            # Container is list because of unhashable argument in b.
            self.counter += 1
            if self.counter == 2:
                raise ValueError("Exception in mixed")
            return f"{a}_{b}_{c}_{d}"

    obj = Test()

    # --- Test SELF_ONLY method ---
    # First call should raise, and since container is None the
    # private attribute shouldn't be created.
    private_self = lazymethod.get_private("self_only")
    with pytest.raises(ValueError):
        _ = obj.self_only()

    assert not hasattr(obj, private_self), (
        "Cache attribute exists even after exception for self_only"
    )

    # Subsequent call succeeds and caches the result.
    result_self = obj.self_only()  # Now counter becomes 2 and no exception
    assert result_self == 2
    assert hasattr(obj, private_self), (
        "Cache attribute not created after successful self_only call"
    )
    # Further calls return the same cached value.
    assert obj.self_only() == 2, (
        "Cached self_only value did not match expected value"
    )

    # --- Test HASHABLE method ---
    # For hashable, container is a dict.
    private_hash = lazymethod.get_private("hashable")
    # First call with (1, "a") should raise.
    obj.counter = 1  # reset counter to force error
    with pytest.raises(ValueError):
        _ = obj.hashable(1, "a")

    # No caching should have occurred for that argument combo.
    assert not hasattr(obj, private_hash), (
        "Cache attribute exists for hashable after exception"
    )

    # Call again; now the call succeeds.
    # After self_only, counter == 2. The first hashable call increments counter from 2 to 3 and raises.
    # A new call will increment counter from 3 to 4.
    result_hash = obj.hashable(1, "a")
    # Expect the method to return a string incorporating the current counter.
    # With counter at 4, we expect "1_a_4".
    assert result_hash == "1_a_3", (
        f"Unexpected result from hashable: {result_hash}"
    )
    # Now the caching container (a dict) should be present
    cache_dict = getattr(obj, private_hash)
    # The key is built via _signature_to_kwargs; for a two-parameter method,
    # the mapping will be {"a": 1, "b": "a"} and the key is frozenset of its items.
    key_hash = frozenset([("a", 1), ("b", "a")])
    assert cache_dict.get(key_hash) == "1_a_3", (
        "Cached value not found in hashable container"
    )

    # --- Test MIXED method ---
    # For mixed, container is a list (because of the unhashable list parameter).
    private_mixed = lazymethod.get_private("mixed")
    # First call with arguments (10, ["x"], "y") should raise.
    obj.counter = 1  # reset counter to trigger error

    with pytest.raises(ValueError):
        _ = obj.mixed(10, ["x"], "y")

    assert not hasattr(obj, private_mixed), (
        "Cache attribute exists for mixed after exception"
    )

    # Call again; the call should succeed.
    result_mixed = obj.mixed(10, ["x"], "y")
    # After hashable, counter should be 4 and mixed call increments it to 5.
    assert result_mixed == "10_['x']_y_True", (
        f"Unexpected result from mixed: {result_mixed}"
    )

    # Now the container (a list) should hold one entry.
    cache_list = getattr(obj, private_mixed)
    assert isinstance(cache_list, list)
    assert len(cache_list) == 1
    # For mixed, the key is built from the normalized signature.
    # Expected normalized mapping is {"a": 10, "b": ["x"], "c": "y", "d": True}.
    # The key in a list container is stored as a tuple of items (order determined by sorting of keys).
    expected_key = (("a", 10), ("b", ["x"]), ("c", "y"), ("d", True))
    cached_key, cached_value = cache_list[0]
    assert cached_key == expected_key, (
        f"Unexpected key in mixed cache: {cached_key}"
    )
    assert cached_value == "10_['x']_y_True", (
        "Cached value in mixed container does not match"
    )

    # --- Verify that further calls with the same arguments return the cached results ---
    obj.counter = 0
    assert obj.self_only() == 2, "Subsequent self_only call used cached value"
    assert obj.hashable(1, "a") == "1_a_3", (
        "Subsequent hashable call used cached value"
    )
    assert obj.mixed(10, ["x"], "y") == "10_['x']_y_True", (
        "Subsequent mixed call used cached value"
    )
    assert obj.counter == 0, "Counter changed on a cached call"
