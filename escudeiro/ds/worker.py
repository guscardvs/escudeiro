import asyncio
import weakref
from collections.abc import Awaitable, Callable, Hashable
from typing import Any, ClassVar, Self, cast

from escudeiro.data import data
from escudeiro.lazyfields import lazyfield


@data(slots=False)
class WorkerQueue[T: Hashable, R]:
    """An asynchronous worker queue with caching capabilities.

    This queue processes items of type T and returns results of type R.
    It maintains a cache to avoid reprocessing the same items and manages
    concurrent processing using asyncio.

    Type Parameters:
        T: The input type (must be hashable)
        R: The result type
    """

    _global_registry: ClassVar[
        weakref.WeakValueDictionary[int, "WorkerQueue"]
    ] = weakref.WeakValueDictionary()
    """Class-level registry tracking live WorkerQueue instances (weakly)"""

    worker: Callable[[T], Awaitable[R]]
    """Async function that processes items"""
    cache_get: Callable[[T], Awaitable[R | None]]
    """Async function to retrieve cached results"""
    cache_set: Callable[[T, R], Awaitable[None]]
    """Async function to store results in cache"""
    maxsize: int = 3
    """Maximum number of items the queue can hold"""
    finish_timeout: float = 3.0
    """Timeout for finishing pending tasks during shutdown"""

    @lazyfield
    def _worker_queue(self) -> asyncio.Queue:
        """Internal queue for holding items awaiting processing"""
        return asyncio.Queue(self.maxsize)

    @lazyfield
    def _worker_task(self) -> asyncio.Task | None:
        """Background task that processes items from the queue"""
        return None

    @lazyfield
    def _ongoing(self) -> dict[T, asyncio.Future]:
        """Dictionary tracking currently processing items and their futures"""
        return {}

    @lazyfield
    def _errors(self) -> list[Exception]:
        """Non-fatal failures (e.g. cache_set) reported when shutting down"""
        return []

    @lazyfield
    def _id(self) -> int:
        """Unique identifier for this worker queue instance"""
        return id(self)

    @lazyfield
    def _maxtasks(self) -> int:
        """Maximum number of concurrent tasks (matches maxsize by default)"""
        return self.maxsize

    @lazyfield
    def _event(self) -> asyncio.Event:
        """Event used to signal shutdown to worker tasks"""
        return asyncio.Event()

    def __post_init__(self):
        """Initialize all lazy fields after instance creation"""
        # Accessing lazyfields to trigger their initialization
        self._worker_queue
        self._worker_task
        self._ongoing
        self._errors
        self._id
        self._maxtasks
        self._event

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        """Create a new instance and register it in the global registry"""
        instance = object.__new__(cls)
        cls._global_registry[id(instance)] = instance
        return instance

    async def require(self, item: T) -> R:
        """Request processing of an item, using cache if available.

        Args:
            item: The item to be processed

        Returns:
            The result of processing the item

        Note:
            - Checks cache first
            - If already being processed, waits for existing result
            - Otherwise, queues the item for processing
            - Automatically starts worker if not running
            - Requesters share one future but wait on it shielded: a timeout or
              cancellation of one requester does not affect the others
            - A failed item is forgotten, so requiring it again retries
        """
        result = await self.cache_get(item)
        if result is not None:
            return result
        future = self._ongoing.get(item)
        if future is None:
            future = asyncio.get_running_loop().create_future()
            self._ongoing[item] = future
            try:
                # Before the put: a full queue is only drained by a worker.
                self._ensure_running()
                await self._worker_queue.put(item)
                # The worker may have finished while put was waiting.
                self._ensure_running()
            except BaseException:
                # Cancelled/failed put: don't leave a future nobody resolves.
                self._settle(item, exc=asyncio.CancelledError())
                raise

        return await asyncio.shield(future)

    def _ensure_running(self) -> None:
        if not self.running:
            WorkerQueue._worker_task.__set__(self, self._open())

    def _settle(
        self,
        item: T,
        result: R | None = None,
        exc: BaseException | None = None,
    ) -> None:
        """Forget ``item`` and resolve its shared future, if still pending."""
        future = self._ongoing.pop(item, None)
        if future is None or future.done():
            return
        if isinstance(exc, asyncio.CancelledError):
            _ = future.cancel()
        elif exc is not None:
            future.set_exception(exc)
        else:
            future.set_result(result)

    def _open(self) -> asyncio.Task:
        """Start the worker task.

        Returns:
            The created asyncio Task

        Note:
            - Registers instance in global registry if not present
            - Resets the shutdown event
            - Creates and returns a new worker task
        """
        if self._id not in (registry := type(self)._global_registry):
            registry[self._id] = self
        if self._event.is_set():
            self._event.clear()
        return asyncio.create_task(self._worker())

    async def _worker(self) -> None:
        """Main worker coroutine: runs the consumers until shutdown.

        Note:
            - Runs up to _maxtasks consumers concurrently
            - On shutdown idle consumers are cancelled, busy ones finish their
              current item, then everything still pending is finished inline
            - Raises collected exceptions at shutdown if any occurred
            - Whatever happens, no pending future is left unresolved
        """
        consumers: list[asyncio.Task[None]] = []
        busy: set[asyncio.Task[None]] = set()
        timeouts: list[asyncio.TimeoutError] = []
        try:
            if not self._event.is_set():
                consumers = [
                    asyncio.create_task(self._consume(busy))
                    for _ in range(self._maxtasks)
                ]
                _ = await self._event.wait()
                for consumer in consumers:
                    if consumer not in busy:
                        _ = consumer.cancel()
            # Busy consumers see the event and stop after their item.
            _ = await asyncio.gather(*consumers, return_exceptions=True)
            timeouts = await self._finish_pending()
        finally:
            for consumer in consumers:
                _ = consumer.cancel()
            for key in list(self._ongoing):
                self._settle(key, exc=asyncio.CancelledError())

        excs: list[Exception] = [*self._errors, *timeouts]
        self._errors.clear()
        if excs:
            raise ExceptionGroup(
                "WorkerQueue stopped due to the following exceptions", excs
            )

    async def _consume(self, busy: set[asyncio.Task[None]]) -> None:
        """Take items off the queue one at a time until shutdown."""
        me = cast(asyncio.Task[None], asyncio.current_task())
        while not self._event.is_set():
            item = await self._worker_queue.get()
            busy.add(me)
            try:
                await self._process(item)
            finally:
                busy.discard(me)
                self._worker_queue.task_done()

    async def _process(self, item: T) -> None:
        """Run the worker function for one item and resolve its future.

        Note:
            - The item is forgotten in every outcome (success, error,
              cancellation), so requiring it again retries
            - The result is cached before waiters are released
        """
        try:
            result = await self.worker(item)
        except Exception as e:
            self._settle(item, exc=e)
            return
        except BaseException as e:
            self._settle(item, exc=e)
            raise
        await self._store(item, result)

    async def _store(self, item: T, result: R) -> None:
        try:
            await self.cache_set(item, result)
        except Exception as e:
            self._errors.append(e)
        finally:
            self._settle(item, result)

    async def _finish_pending(self) -> list[asyncio.TimeoutError]:
        """Process everything still queued or waiting (shutdown path).

        Returns:
            The timeouts hit; each also resolves the affected future.
        """
        timeouts: list[asyncio.TimeoutError] = []
        semaphore = asyncio.Semaphore(self._maxtasks)

        async def _finish(item: T) -> None:
            async with semaphore:
                try:
                    result = await asyncio.wait_for(
                        self.worker(item), self.finish_timeout
                    )
                except TimeoutError as err:
                    timeouts.append(err)
                    self._settle(item, exc=err)
                except Exception as err:
                    self._settle(item, exc=err)
                else:
                    await self._store(item, result)

        while True:
            # Queued items are all in _ongoing too; they are finished here.
            while not self._worker_queue.empty():
                _ = self._worker_queue.get_nowait()
                self._worker_queue.task_done()
            pending = [k for k, f in self._ongoing.items() if not f.done()]
            if not pending:
                return timeouts
            _ = await asyncio.gather(*(_finish(key) for key in pending))

    @classmethod
    async def aclose_all(cls):
        """Close all active WorkerQueue instances.

        Every instance is closed even if some fail; failures are raised
        together afterwards.
        """
        errors: list[Exception] = []
        for instance in list(cls._global_registry.values()):
            try:
                await instance.aclose()
            except Exception as e:
                errors.append(e)
        cls._global_registry.clear()
        if errors:
            raise ExceptionGroup("Could not close all WorkerQueues", errors)

    async def aclose(self):
        """Gracefully shutdown this worker queue.

        Note:
            - Signals shutdown to worker task
            - Waits for in-flight items, then finishes the pending ones
            - Removes instance from registry
            - Raises any exception from the worker task
            - The queue can be used again afterwards
        """
        task = self._worker_task
        if task is None:
            _ = WorkerQueue._global_registry.pop(self._id, None)
            return

        if not self._event.is_set():
            self._event.set()

        try:
            await task
        finally:
            if self._worker_task is task:
                WorkerQueue._worker_task.__set__(self, None)
            _ = WorkerQueue._global_registry.pop(self._id, None)

    @property
    def running(self) -> bool:
        """Check if the worker task is active.

        Returns:
            True if the worker is running, False otherwise
        """
        if self._worker_task is None:
            return False
        return not (self._worker_task.done() or self._worker_task.cancelled())

    async def __aenter__(self) -> Self:
        """Enter async context manager, starting worker if not running."""
        self._ensure_running()
        return self

    async def __aexit__(self, *_) -> None:
        """Exit async context manager, shutting down worker."""
        await self.aclose()
