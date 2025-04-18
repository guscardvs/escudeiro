import asyncio
from collections.abc import Awaitable, Callable, Coroutine, Hashable
from typing import Any, ClassVar, Self

from escudeiro.data import data
from escudeiro.lazyfields import lazyfield
from escudeiro.misc import filter_isinstance


@data
class WorkerQueue[T: Hashable, R]:
    """An asynchronous worker queue with caching capabilities.

    This queue processes items of type T and returns results of type R.
    It maintains a cache to avoid reprocessing the same items and manages
    concurrent processing using asyncio.

    Type Parameters:
        T: The input type (must be hashable)
        R: The result type
    """

    _global_registry: ClassVar[dict[int, "WorkerQueue"]] = {}
    """Class-level registry tracking all active WorkerQueue instances"""

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
        """
        result = await self.cache_get(item)
        if result is not None:
            return result
        if item in self._ongoing:
            return await self._ongoing[item]

        self._ongoing[item] = asyncio.Future()
        await self._worker_queue.put(item)

        if not self.running:
            await self.aclose()
            WorkerQueue._worker_task.__set__(self, self._open())

        return await self._ongoing[item]

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
        """Main worker coroutine that processes items from the queue.

        Note:
            - Processes items concurrently up to _maxtasks
            - Collects exceptions during processing
            - Handles graceful shutdown when event is set
            - Raises collected exceptions at shutdown if any occurred
        """
        excs = None
        while not self._event.is_set():
            # Process up to _maxtasks concurrently
            excs = list(
                filter_isinstance(
                    Exception,
                    await asyncio.gather(
                        *(
                            self._handle_request()
                            for _ in range(self._maxtasks)
                        ),
                        return_exceptions=True,
                    ),
                )
            )

        # Graceful shutdown - finish pending tasks
        tasks: list[asyncio.Task] = []
        finisher_function, timeouts = self._finisher()
        for key, ongoing in self._ongoing.items():
            if ongoing.done():
                continue
            task = asyncio.create_task(finisher_function(key, ongoing))
            tasks.append(task)

        _ = await asyncio.gather(*tasks)
        if timeouts:
            excs = (excs or []) + timeouts
        if excs:
            raise ExceptionGroup(
                "WorkerQueue stopped due to the following exceptions", excs
            )

    async def _handle_request(self) -> None:
        """Process a single item from the queue.

        Note:
            - Gets item from queue
            - Handles shutdown signal (None item)
            - Processes item using worker function
            - Stores result in cache
            - Manages futures for ongoing items
        """
        item = await self._worker_queue.get()
        if item is None:
            if not self._event.is_set():
                self._event.set()
            self._worker_queue.task_done()
            return

        try:
            result = await self.worker(item)
        except Exception as e:
            self._ongoing[item].set_exception(e)
            self._event.set()
        else:
            future = self._ongoing.pop(item, None)
            if future and not future.done():
                future.set_result(result)
            await self.cache_set(item, result)
            self._worker_queue.task_done()

    @classmethod
    async def aclose_all(cls):
        """Close all active WorkerQueue instances."""
        for instance in cls._global_registry.values():
            await instance.aclose()
        cls._global_registry.clear()

    async def aclose(self):
        """Gracefully shutdown this worker queue.

        Note:
            - Signals shutdown to worker task
            - Fills queue with None to wake up workers
            - Waits for task completion
            - Removes instance from registry
            - Raises any exception from the worker task
        """
        if self._worker_task is None:
            return

        if not self._event.is_set():
            self._event.set()

        # Fill queue to wake up workers
        while self._worker_queue.qsize() != self._maxtasks:
            self._worker_queue.put_nowait(None)

        await self._worker_task
        if (exception := self._worker_task.exception()) is not None:
            raise exception

        _ = WorkerQueue._global_registry.pop(self._id, None)

    def _finisher(
        self,
    ) -> tuple[
        Callable[[T, asyncio.Future], Coroutine[None, None, None]],
        list[asyncio.TimeoutError],
    ]:
        """Create a finisher function for pending tasks during shutdown.

        Returns:
            A tuple containing:
            - The finisher coroutine function
            - A list to collect timeout errors

        Note:
            - Uses semaphore to limit concurrent finishing tasks
            - Tracks timeout errors during shutdown
        """
        semaphore = asyncio.Semaphore(self._maxtasks)
        timeouts: list[asyncio.TimeoutError] = []

        async def _finish(item: T, future: asyncio.Future) -> None:
            """Finish processing an item during shutdown.

            Args:
                item: The item to process
                future: The future to complete
            """
            async with semaphore:
                try:
                    result = await asyncio.wait_for(
                        self.worker(item),
                        self.finish_timeout,
                    )
                except TimeoutError as err:
                    future.set_exception(err)
                    timeouts.append(err)
                else:
                    await self.cache_set(item, result)
                    future.set_result(result)

        return _finish, timeouts

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
        if not self.running:
            WorkerQueue._worker_task.__set__(self, self._open())
        return self

    async def __aexit__(self, *_) -> None:
        """Exit async context manager, shutting down worker."""
        await self.aclose()
