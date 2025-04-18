import contextlib
import warnings
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from functools import wraps
from typing import Any, Self, cast, final, overload, override

from escudeiro.data.slots import slot
from escudeiro.misc import asyncdo_with, do_with, make_noop


class lazy:
    def __init__(self, name: str) -> None:
        self.public_name: str = name
        self.private_name: str = self.make_private(name)

    def __set_name__(self, owner: type, name: str) -> None:
        self.public_name = name
        self.private_name = self.make_private(name)

    @staticmethod
    def make_private(public_name: str) -> str:
        return f"_lazyfield_{public_name}_"

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
class ALazyContainer[T]:
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
class LazyField[SelfT, T](lazy):
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

    @overload
    def __get__(self, instance: SelfT, owner: type[SelfT]) -> T: ...

    @overload
    def __get__(self, instance: None, owner: type[SelfT]) -> Self: ...

    def __get__(self, instance: SelfT | None, owner: type[SelfT]) -> Self | T:
        if instance is None:
            return self

        return self._do_get(instance)

    def _do_get(self, instance: SelfT) -> T:
        is_marked_instance = check_marking(instance, is_async=False)
        lock = (
            self._internal_lock
            if not is_marked_instance
            else get_ctx(instance, is_async=False)
        )

        if (
            lock is self._internal_lock
            and not isinstance(lock, contextlib.nullcontext)
            and not is_marked_instance
        ):
            warnings.warn(
                "Trying to use synchronization without marking class"
                + f" might lock all instances and methods. {lock}",
                UserWarning,
                stacklevel=3,
            )
        with lock:
            if self._instance_marked(instance):
                return self._get_nosync(instance)
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
        is_marked_instance = check_marking(instance, is_async=False)
        lock = (
            self._internal_lock
            if not is_marked_instance
            else get_ctx(instance, is_async=False)
        )

        if (
            lock is self._internal_lock
            and not isinstance(lock, contextlib.nullcontext)
            and not is_marked_instance
        ):
            warnings.warn(
                "Trying to use synchronization without marking class"
                + f" might lock all instances and methods. {lock}",
                UserWarning,
                stacklevel=2,
            )
        if not self._instance_marked(instance):
            _ = do_with(lock, self._setval, instance, value)
            return

        container = object.__getattribute__(instance, self.private_name)
        container.put(value)

    def __delete__(self, instance: SelfT):
        if not self._instance_marked(instance):
            return
        container = object.__getattribute__(instance, self.private_name)
        container.delete()


@final
class AsyncLazyField[SelfT, T](lazy):
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

    @overload
    def __get__(
        self, instance: SelfT, owner: type[SelfT]
    ) -> Callable[[], Coroutine[Any, Any, T]]: ...

    @overload
    def __get__(self, instance: None, owner: type[SelfT]) -> Self: ...

    def __get__(
        self, instance: SelfT | None, owner: type[SelfT]
    ) -> Self | Callable[[], Coroutine[Any, Any, T]]:
        if instance is None:
            return self
        return self._do_get(instance)

    def _do_get(self, instance: SelfT) -> Callable[[], Coroutine[Any, Any, T]]:
        is_marked_instance = check_marking(instance, is_async=True)
        lock = (
            self._internal_lock
            if not is_marked_instance
            else get_ctx(instance, is_async=True)
        )
        if (
            lock is self._internal_lock
            and not isinstance(lock, contextlib.nullcontext)
            and not is_marked_instance
        ):
            warnings.warn(
                "Trying to use synchronization without marking class"
                + f" might lock all instances and methods. {lock}",
                UserWarning,
                stacklevel=3,
            )

        async def _getter():
            async with lock:
                if self._instance_marked(instance):
                    return await self._get_nosync(instance)
                val = await self._setval(instance, _UNSET)
                return cast(
                    T, await val.acquire()
                )  # here container is surely initialized

        return _getter

    async def _get_nosync(self, instance: SelfT) -> T:
        container = cast(
            ALazyContainer[T],
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
        container = ALazyContainer(content, self.lock_factory())
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
            ALazyContainer[T],
            # using object.__getattribute__ to bypass
            # custom implementations that change default behavior
            object.__getattribute__(instance, self.private_name),
        )
        if to_reset is not _UNSET:
            await container.put(cast(T, to_reset))
        else:
            await container.delete()


def mark_class(
    ctx_factory: Callable[[], contextlib.AbstractContextManager] | None = None,
    actx_factory: Callable[[], contextlib.AbstractAsyncContextManager]
    | None = None,
):
    """Mark a class for proper lazyfield isolation, supporting both sync and async fields.

    Args:
        ctx_factory: Factory for synchronous locks (used by @lazyfield)
        actx_factory: Factory for async locks (used by @asynclazyfield)
    """

    def _wrap[T](cls: type[T]) -> type[T]:
        original_init = cls.__init__

        @wraps(original_init)
        def _init_(self: T, *args: Any, **kwargs: Any):
            original_init(self, *args, **kwargs)
            # Store both factories if provided
            if ctx_factory is not None:
                object.__setattr__(self, "_lazyfield_sync_ctx_", ctx_factory())
            if actx_factory is not None:
                object.__setattr__(
                    self, "_lazyfield_async_ctx_", actx_factory()
                )

        type.__setattr__(cls, "__init__", _init_)
        type.__setattr__(cls, "_lazyfield_marked_", True)
        return cls

    return _wrap


def is_marked(val: Any) -> bool:
    return getattr(val, "_lazyfield_marked_", False)


def check_marking(instance: Any, is_async: bool):
    if not is_marked(instance):
        return False

    ctx_attr = "_lazyfield_async_ctx_" if is_async else "_lazyfield_sync_ctx_"
    return hasattr(instance, ctx_attr)


def get_ctx(instance: Any, is_async: bool):
    if is_async:
        return object.__getattribute__(instance, "_lazyfield_async_ctx_")
    return object.__getattribute__(instance, "_lazyfield_sync_ctx_")


@overload
def lazyfield[SelfT, T](
    func: Callable[[SelfT], T], /
) -> LazyField[SelfT, T]: ...


@overload
def lazyfield[SelfT, T](
    func: None = None,
    /,
    lock_factory: Callable[
        [], contextlib.AbstractContextManager
    ] = contextlib.nullcontext,
) -> Callable[[Callable[[SelfT], T]], LazyField[SelfT, T]]: ...


def lazyfield[SelfT, T](
    func: Callable[[SelfT], T] | None = None,
    /,
    lock_factory: Callable[
        [], contextlib.AbstractContextManager
    ] = contextlib.nullcontext,
) -> (
    LazyField[SelfT, T] | Callable[[Callable[[SelfT], T]], LazyField[SelfT, T]]
):
    def _wrap(func: Callable[[SelfT], T]) -> LazyField[SelfT, T]:
        return slot.make(
            "_lazyfield_sync_ctx_", value=LazyField(func, lock_factory)
        )

    return _wrap if func is None else _wrap(func)


@overload
def asynclazyfield[SelfT, T](
    func: Callable[[SelfT], Coroutine[Any, Any, T]], /
) -> AsyncLazyField[SelfT, T]: ...


@overload
def asynclazyfield[SelfT, T](
    func: None = None,
    /,
    lock_factory: Callable[
        [], contextlib.AbstractAsyncContextManager
    ] = contextlib.nullcontext,
) -> Callable[
    [Callable[[SelfT], Coroutine[Any, Any, T]]], AsyncLazyField[SelfT, T]
]: ...


def asynclazyfield[SelfT, T](
    func: Callable[[SelfT], Coroutine[Any, Any, T]] | None = None,
    /,
    lock_factory: Callable[
        [], contextlib.AbstractAsyncContextManager
    ] = contextlib.nullcontext,
) -> (
    AsyncLazyField[SelfT, T]
    | Callable[
        [Callable[[SelfT], Coroutine[Any, Any, T]]], AsyncLazyField[SelfT, T]
    ]
):
    def _wrap(
        func: Callable[[SelfT], Coroutine[Any, Any, T]],
    ) -> AsyncLazyField[SelfT, T]:
        return slot.make(
            "_lazyfield_async_ctx_",
            value=AsyncLazyField(func, lock_factory),
        )

    return _wrap if func is None else _wrap(func)


def getlazyfield(instance: Any, attr: str) -> lazy:
    cls: type | object = instance
    if not isinstance(cls, type):
        cls = type(cls)
    lazyf = getattr(cls, attr)
    if not isinstance(lazyf, lazy):
        raise TypeError(f"Attribute {cls.__name__}.{attr} is not a lazyfield")
    return lazyf


@overload
def _get_container(instance: Any, lazyf: LazyField) -> LazyContainer: ...
@overload
def _get_container(instance: Any, lazyf: AsyncLazyField) -> ALazyContainer: ...


def _get_container(
    instance: Any, lazyf: LazyField | AsyncLazyField
) -> LazyContainer | ALazyContainer:
    return object.__getattribute__(instance, lazyf.private_name)


def is_initialized(instance: Any, attr: str) -> bool:
    lazyf = getlazyfield(instance, attr)
    return hasattr(instance, lazyf.private_name)


_mock_coroutine = make_noop(asyncio=True, returns=None)


@overload
def dellazy(instance: Any, lazyf: LazyField) -> None: ...
@overload
def dellazy(
    instance: Any, lazyf: AsyncLazyField
) -> Coroutine[None, None, None]: ...


def dellazy(
    instance: Any, lazyf: LazyField | AsyncLazyField
) -> None | Coroutine[None, None, None]:
    if not hasattr(instance, lazyf.private_name):
        if isinstance(lazyf, AsyncLazyField):
            return _mock_coroutine()
        else:
            return None

    container = _get_container(instance, lazyf)
    return container.put(_UNSET)
