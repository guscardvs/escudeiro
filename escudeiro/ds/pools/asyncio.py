import asyncio
from collections.abc import Callable, Coroutine
from time import time
from typing import Any

from escudeiro.data import call_init, data
from escudeiro.exc import ErrorGroup

from .resource import Resource

type FactoryType[T] = Callable[[], Coroutine[Any, Any, T]]
type ReleaserType[T] = Callable[[T], Coroutine[Any, Any, None]]


@data(frozen=False)
class AsyncPool[T]:
    resources: asyncio.Queue[Resource[T]]
    factory: FactoryType[T]
    releaser: ReleaserType[T]
    _pool_recycle: float
    _pool_size: int
    _available: int
    _available_semaphore: asyncio.Semaphore

    def __init__(
        self,
        factory: FactoryType[T],
        releaser: ReleaserType[T],
        queue_class: type[asyncio.Queue[T]] = asyncio.LifoQueue,
        pool_size: int = 10,
        pool_recycle: float = 3600,
    ):
        """
        Initialize the AsyncPool.

        :param factory: A coroutine function that creates a new resource.
        :param releaser: A coroutine function that releases a resource.
        :param queue_class: The class to use for the resources queue. Defaults to asyncio.LifoQueue.
        :param pool_size: The maximum size of the resource pool. Defaults to 10.
        :param pool_recycle: The time in seconds after which a resource is considered expired and should be recycled. Defaults to 3600 (1 hour). ``0`` (or less) disables recycling.
        """
        call_init(
            self,
            resources=queue_class(pool_size),
            factory=factory,
            releaser=releaser,
            pool_recycle=pool_recycle,
            pool_size=pool_size,
            available=pool_size,
            available_semaphore=asyncio.Semaphore(pool_size),
        )

    async def _initialize_resource(self) -> Resource[T]:
        """Creates a resource from the factory and returns it wrapped in the Resource object
        :return: The Resource wrapper
        """
        resource = await self.factory()
        return Resource.from_now(resource)

    async def _maybe_recycle(
        self, resource: Resource[T], current_ts: float | None = None
    ) -> T:
        """Returns resource from resource object or
        releases the current resource and returns a new one if
        resource is expired.

        :param resource: The resource wrapper to be "maybe" recycled.
        :param current_ts: timestamp, defaults to `time.time()`

        :return: The resource acquired.
        """
        current_ts = current_ts or time()
        if (
            self._pool_recycle > 0
            and resource.last_usage + self._pool_recycle <= current_ts
        ):
            await self.releaser(resource.get())
            resource = await self._initialize_resource()
        return resource.get()

    async def acquire(self) -> T:
        """
        Acquires a resource from the pool, waiting until a slot is free.

        The slot (ticket) is returned if anything fails before the resource is
        handed out, so failures and cancellation never shrink the pool.

        :return: T
        """
        await self._take_ticket()
        try:
            try:
                resource = self.resources.get_nowait()
            except asyncio.QueueEmpty:
                resource = await self._initialize_resource()
            return await self._maybe_recycle(resource)
        except BaseException:
            self._return_ticket()
            raise

    async def release(self, resource: T) -> None:
        """Puts resource back in queue and frees its slot

        :param resource: The resource to be put.
        :return: None
        """
        entry = Resource.from_resource(resource)
        try:
            self.resources.put_nowait(entry)
        finally:
            self._return_ticket()

    async def prefill(self, count: int | None = None) -> None:
        """
        Prefills the queue by the amount passed.

        :param count: The amount of resources to initialize, up to the
            `pool_size` and the free pool slots. Defaults to the pool_size if
            None.
        """
        count = count or self._pool_size
        count = min(count, self._pool_size, self._available)

        while self.resources.qsize() < count:
            resource = await self._initialize_resource()
            self.resources.put_nowait(resource)

    async def dispose(self) -> None:
        """
        Remove and release all idle items of the queue.

        Idle resources do not hold slots, so the pool keeps its capacity;
        checked-out resources are not affected.

        :return: None
        :raises: ErrorGroup if any error happened while closing
        """
        errors = []
        while not self.resources.empty():
            resource = self.resources.get_nowait()
            try:
                await self.releaser(resource.get())
            except Exception as e:
                errors.append(e)
        if errors:
            raise ErrorGroup("Could not kill all resources", *errors)

    async def _take_ticket(self) -> None:
        """Wait for a free slot and take it (one ticket per checkout)."""
        _ = await self._available_semaphore.acquire()
        self._available -= 1

    def _return_ticket(self) -> None:
        if self._available == self._pool_size:
            return  # spurious return, nothing is checked out
        self._available += 1
        self._available_semaphore.release()
