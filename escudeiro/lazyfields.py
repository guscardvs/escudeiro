import contextlib
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any, Self, cast, final, override

from escudeiro.misc.functions import asyncdo_with, do_with


class lazy:
    def __init__(self, name: str) -> None:
        self.public_name: str = name
        self.private_name: str = self.make_private(name)

    def __set_name__(self, owner: type, name: str) -> None:
        self.public_name = name
        self.private_name = self.make_private(name)

    @staticmethod
    def make_private(public_name: str) -> str:
        return f"_lazyfield_{public_name}"

    def _instance_marked(self, instance: Any) -> bool:
        return hasattr(instance, self.private_name)


class _UNSET:
    pass


@dataclass
class LazyContainer[T]:
    content: T | type[_UNSET]
    lock: contextlib.AbstractContextManager

    def acquire(self) -> T | type[_UNSET]:
        with self.lock:
            return self.content

    def put(self, content: T) -> None:
        with self.lock:
            self.content = content

    def delete(self) -> None:
        with self.lock:
            self.content = _UNSET


@dataclass
class AlazyContainer[T]:
    content: T | type[_UNSET]
    lock: contextlib.AbstractAsyncContextManager

    async def acquire(self) -> T | type[_UNSET]:
        async with self.lock:
            return self.content

    async def put(self, content: T) -> None:
        async with self.lock:
            self.content = content

    async def delete(self) -> None:
        async with self.lock:
            self.content = _UNSET


@final
class lazyfield[SelfT, T](lazy):
    @override
    def __init__(
        self,
        func: Callable[[SelfT], T],
        lock_factory: Callable[
            [], contextlib.AbstractContextManager
        ] = contextlib.nullcontext,
    ) -> None:
        super().__init__(func.__name__)
        self.func = func
        self.lock_factory = lock_factory
        self._internal_lock = lock_factory()

    def __get__(self, instance: SelfT | None, owner: SelfT) -> Self | T:
        if instance is None:
            return self

        return self._do_get(instance)

    def _do_get(self, instance: SelfT) -> T:
        if self._instance_marked(instance):
            return self._get_nosync(instance)
        with self._internal_lock:
            val = self._setval(instance, _UNSET)
            return cast(
                T, val.acquire()
            )  # here container is surely initialized

    def _get_nosync(self, instance: SelfT) -> T:
        container = cast(
            LazyContainer[T],
            # using object.__getattribute__ to bypass
            # custom implementations that change default behavior
            object.__getattribute__(instance, self.private_name),
        )
        content = container.acquire()
        if content is _UNSET:
            content = self.func(instance)
            container.put(content)
        return cast(T, content)

    def _setval(self, instance: SelfT, content: T | type[_UNSET]):
        content = content if content is not _UNSET else self.func(instance)

        # using object.__setattr__ to bypass
        # custom implementations that might block
        # this operation
        container = LazyContainer(content, self.lock_factory())
        object.__setattr__(instance, self.private_name, container)
        return container

    def __set__(self, instance: SelfT, value: T):
        if not self._instance_marked(instance):
            _ = do_with(self._internal_lock, self._setval, instance, value)
            return

        container = object.__getattribute__(instance, self.private_name)
        container.put(value)

    def __delete__(self, instance: SelfT):
        if not self._instance_marked(instance):
            return
        container = object.__getattribute__(instance, self.private_name)
        container.delete()


@final
class asynclazyfield[SelfT, T](lazy):
    @override
    def __init__(
        self,
        func: Callable[[SelfT], Coroutine[Any, Any, T]],
        lock_factory: Callable[
            [], contextlib.AbstractAsyncContextManager
        ] = contextlib.nullcontext,
    ) -> None:
        super().__init__(func.__name__)
        self.func = func
        self.lock_factory = lock_factory
        self._internal_lock = lock_factory()

    def __get__(
        self, instance: SelfT | None, owner: SelfT
    ) -> Self | Callable[[], Coroutine[Any, Any, T]]:
        if instance is None:
            return self

        return self._do_get(instance)

    def _do_get(self, instance: SelfT) -> Callable[[], Coroutine[Any, Any, T]]:
        async def _getter():
            if self._instance_marked(instance):
                return await self._get_nosync(instance)
            async with self._internal_lock:
                val = await self._setval(instance, _UNSET)
                return cast(
                    T, await val.acquire()
                )  # here container is surely initialized

        return _getter

    async def _get_nosync(self, instance: SelfT) -> T:
        container = cast(
            AlazyContainer[T],
            # using object.__getattribute__ to bypass
            # custom implementations that change default behavior
            object.__getattribute__(instance, self.private_name),
        )
        content = await container.acquire()
        if content is _UNSET:
            content = await self.func(instance)
            await container.put(content)
        return cast(T, content)

    async def _setval(self, instance: SelfT, content: T | type[_UNSET]):
        content = (
            content if content is not _UNSET else await self.func(instance)
        )

        # using object.__setattr__ to bypass
        # custom implementations that might block
        # this operation
        container = AlazyContainer(content, self.lock_factory())
        object.__setattr__(instance, self.private_name, container)
        return container

    async def reset(self, instance: SelfT, withval: T | None = None):
        to_reset = withval if withval is not None else _UNSET
        if not self._instance_marked(instance):
            if to_reset is _UNSET:
                return
            _ = await asyncdo_with(
                self._internal_lock, self._setval, instance, to_reset
            )
            return

        container = cast(
            AlazyContainer[T],
            # using object.__getattribute__ to bypass
            # custom implementations that change default behavior
            object.__getattribute__(instance, self.private_name),
        )
        if to_reset is not _UNSET:
            await container.put(cast(T, to_reset))
        else:
            await container.delete()
