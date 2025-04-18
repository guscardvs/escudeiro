# pyright: reportUnannotatedClassAttribute=false, reportUninitializedInstanceVariable=false

import asyncio
import threading
from typing import Any, final

import pytest

from escudeiro.data import data, slot
from escudeiro.lazyfields import asynclazyfield, lazyfield, mark_class
from escudeiro.misc.functions import as_async
from escudeiro.misc.lazy import lazymethod


@final
class Descriptor:
    def __init__(self):
        self.sentinel = object()

    def __get__(self, instance: Any | None, owner: type):
        if instance is None:
            return self
        if hasattr(instance, "_private_"):
            return instance._private_
        object.__setattr__(instance, "_private_", self.sentinel)
        return self.sentinel


def test_slot_allows_for_extra_attributes_on_slotted_classes():
    descriptor = Descriptor()

    @final
    @data
    class Test:
        name: str

        desc = slot.make("_private_", value=descriptor)

    instance = Test("Hello")

    assert instance.desc is descriptor.sentinel
    assert hasattr(instance, "_private_")
    assert hasattr(Test, "__slots__")


def test_extra_attributes_fail_if_not_supported_by_slot():
    @data(frozen=False)
    class Test:
        name: str

        def __post_init__(self):
            self.email = "error"

    with pytest.raises(
        AttributeError, match="'Test' object has no attribute 'email'"
    ):
        _ = Test("invalid")
    assert hasattr(Test, "__slots__")


def test_extra_attributes_work_if_slot_wraps_the_method():
    @data(frozen=False)
    class Test:
        name: str

        @slot("email", "age")
        def __post_init__(self):
            self.email = "test@example.com"
            self.age = 15

    assert Test("test").email == "test@example.com"
    assert Test("another").age == 15
    assert hasattr(Test, "__slots__")


def test_squire_lazyfields_integrate_correctly_with_data():
    @mark_class(threading.Lock)
    @data
    class Test:
        name: str

        @lazyfield
        def email(self) -> str:
            return "test@example.com"

    assert hasattr(Test("Test"), "_lazyfield_sync_ctx_")
    assert Test("test").email == "test@example.com"
    assert hasattr(Test, "__slots__")


async def test_squire_asynclazyfields_integrate_correctly_with_data():
    @mark_class(actx_factory=asyncio.Lock)
    @data
    class Test:
        name: str

        @asynclazyfield
        @as_async
        def email(self) -> str:
            return "test@example.com"

    assert hasattr(Test("Test"), "_lazyfield_async_ctx_")
    assert await Test("test").email() == "test@example.com"
    assert hasattr(Test, "__slots__")


async def test_squire_integrates_with_both_simultaneously():
    @mark_class(threading.RLock, asyncio.Lock)
    @data
    class Test:
        name: str

        @asynclazyfield
        @as_async
        def email(self) -> str:
            return "test@example.com"

        @lazyfield
        def age(self) -> int:
            return 2

    assert hasattr(Test("Test"), "_lazyfield_async_ctx_")
    assert await Test("test").email() == "test@example.com"
    assert hasattr(Test, "__slots__")

    assert hasattr(Test("Test"), "_lazyfield_sync_ctx_")
    assert Test("test").age == 2
    assert hasattr(Test, "__slots__")


def test_squire_integrates_safely_with_lazymethod():
    @data
    class Test:
        name: str

        @lazymethod
        def email(self) -> str:
            return "test@example.com"

    instance = Test("Test")
    assert instance.email() == "test@example.com"
    assert instance.email() == "test@example.com"
    assert hasattr(Test, "__slots__")
