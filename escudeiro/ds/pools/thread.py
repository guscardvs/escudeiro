import threading
from collections.abc import Callable
from queue import Empty, LifoQueue, Queue
from time import time

from escudeiro.data import call_init, data
from escudeiro.exc import ErrorGroup

from .resource import Resource

type FactoryType[T] = Callable[[], T]
type ReleaserType[T] = Callable[[T], None]


@data(frozen=False)
class ThreadPool[T]:
    resources: Queue[Resource[T]]
    factory: FactoryType[T]
    releaser: ReleaserType[T]
    _pool_recycle: float
    _pool_size: int
    _available: int
    _available_semaphore: threading.Lock
    _tickets: threading.Semaphore

    def __init__(
        self,
        factory: FactoryType[T],
        releaser: ReleaserType[T],
        queue_class: type[Queue] = LifoQueue,
        pool_size: int = 10,
        pool_recycle: float = 3600,
    ):
        """
        :param pool_recycle: Age in seconds after which a resource is
            released and replaced on acquire. ``0`` (or less) disables recycling.
        """
        call_init(
            self,
            resources=queue_class(pool_size),
            factory=factory,
            releaser=releaser,
            pool_recycle=pool_recycle,
            pool_size=pool_size,
            available=pool_size,
            available_semaphore=threading.Lock(),
            tickets=threading.Semaphore(pool_size),
        )

    def _initialize_resource(self) -> Resource[T]:
        resource = self.factory()
        return Resource.from_now(resource)

    def _maybe_recycle(
        self, resource: Resource[T], current: float | None = None
    ) -> T:
        current = current or time()
        if (
            self._pool_recycle > 0
            and resource.last_usage + self._pool_recycle <= current
        ):
            self.releaser(resource.get())
            resource = self._initialize_resource()
        return resource.get()

    def acquire(self) -> T:
        """Take a resource, blocking until a ticket (pool slot) is free.

        The ticket is returned if anything fails before the resource is handed
        out, so failures never shrink the pool.
        """
        self._take_ticket()
        try:
            try:
                resource = self.resources.get_nowait()
            except Empty:
                resource = self._initialize_resource()
            return self._maybe_recycle(resource)
        except BaseException:
            self._return_ticket()
            raise

    def release(self, resource: T) -> None:
        entry = Resource.from_resource(resource)
        try:
            self.resources.put_nowait(entry)
        finally:
            self._return_ticket()

    def prefill(self, count: int | None = None) -> None:
        """Create idle resources, up to ``count`` and the free pool slots."""
        count = count or self._pool_size
        count = min(count, self._pool_size, self._available)

        while self.resources.qsize() < count:
            resource = self._initialize_resource()
            self.resources.put_nowait(resource)

    def dispose(self) -> None:
        """Release every idle resource; checked-out ones are not affected.

        Idle resources do not hold tickets, so the pool keeps its capacity.
        """
        errors = []
        while True:
            try:
                resource = self.resources.get_nowait()
            except Empty:
                break
            try:
                self.releaser(resource.get())
            except Exception as e:
                errors.append(e)
        if errors:
            raise ErrorGroup("Could not kill all resources", *errors)

    def _take_ticket(self) -> None:
        """Block until a slot is free and take it (one ticket per checkout)."""
        _ = self._tickets.acquire()
        with self._available_semaphore:
            self._available -= 1

    def _return_ticket(self) -> None:
        with self._available_semaphore:
            if self._available == self._pool_size:
                return  # spurious return, nothing is checked out
            self._available += 1
        self._tickets.release()
