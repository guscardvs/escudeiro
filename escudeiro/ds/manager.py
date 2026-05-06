from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Coroutine
from typing import Any, Self
from uuid import uuid4

from escudeiro.data import data
from escudeiro.lazyfields import is_initialized, lazyfield
from escudeiro.misc import moving_window


@data
class Spawned[T]:
    """Handle returned by :meth:`TaskManager.spawn` (awaitable, exposes ``task_id``)."""

    task_id: str
    future: asyncio.Future[T]

    def __await__(self):
        return self.future.__await__()


@data
class TaskManager:
    """An asynchronous task manager that controls concurrent execution of coroutines.

    Features:
    - Limits maximum concurrent tasks (max_tasks)
    - Provides graceful shutdown with timeout
    - Tracks running tasks with unique IDs
    - Supports context manager interface
    - Handles task exceptions gracefully

    Args:
        close_timeout_seconds: Maximum time to wait for tasks to complete during shutdown
        max_tasks: Maximum number of concurrent tasks allowed
    """

    close_timeout_seconds: int = 10
    max_tasks: int = 35

    def __post_init__(self):
        if self.close_timeout_seconds <= 0:
            raise ValueError(
                "close_timeout_seconds value must be greater than zero.",
                self.close_timeout_seconds,
            )

    @lazyfield
    def _pending_coro(self) -> asyncio.Queue[tuple[str, Coroutine[Any, Any, Any]]]:
        """Queue of (task_id, runner coroutine) waiting for a slot."""
        return asyncio.Queue()

    @lazyfield
    def slots(self) -> asyncio.Semaphore:
        """Queue managing available execution slots (max_tasks limit)."""
        return asyncio.Semaphore(self.max_tasks)

    @lazyfield
    def _event(self) -> asyncio.Event:
        """Event used to signal shutdown to the worker task."""
        return asyncio.Event()

    @lazyfield
    def _running_tasks(self) -> dict[str, asyncio.Task]:
        """Dictionary tracking currently running tasks by their IDs."""
        return {}

    @lazyfield
    def _spawn_futures(self) -> dict[str, asyncio.Future[Any]]:
        """task_id -> result future for spawned work (removed when the future completes)."""
        return {}

    @lazyfield
    def _queued_task_ids(self) -> set[str]:
        """task_ids accepted by spawn but not yet assigned a running asyncio.Task."""
        return set()

    @lazyfield
    def _worker_task(self) -> asyncio.Task | None:
        """Background task that processes the coroutine queue."""
        return None

    def spawn[T](self, coro: Coroutine[Any, Any, T]) -> Spawned[T]:
        """Enqueue a coroutine for execution.

        Returns an awaitable handle whose :attr:`~Spawned.future` completes when
        ``coro`` finishes. :attr:`~Spawned.task_id` matches entries in
        :attr:`_running_tasks` while the work runs; use :meth:`future_for` and
        related helpers to inspect state on the manager.

        Args:
            coro: The coroutine to be executed

        Raises:
            RuntimeError: If the manager is not started or there is no running event loop.
        """
        if (
            not is_initialized(self, "_worker_task")
            or self._worker_task is None
        ):
            raise RuntimeError(
                "TaskManager must be started before spawning tasks."
            )
        task_id = uuid4().hex
        future = asyncio.get_running_loop().create_future()
        self._spawn_futures[task_id] = future
        self._queued_task_ids.add(task_id)

        async def _run() -> None:
            self._queued_task_ids.discard(task_id)
            try:
                try:
                    result = await coro
                    if not future.done():
                        future.set_result(result)
                except asyncio.CancelledError:
                    if not future.done():
                        _ = future.cancel()
                    raise
                except Exception as e:
                    if not future.done():
                        future.set_exception(e)
            finally:
                _ = self._spawn_futures.pop(task_id, None)

        self._pending_coro.put_nowait((task_id, _run()))
        return Spawned(task_id, future)

    def future_for(self, task_id: str) -> asyncio.Future[Any] | None:
        """Return the result future for ``task_id``, or ``None`` if unknown or finished."""
        return self._spawn_futures.get(task_id)

    def is_task_running(self, task_id: str) -> bool:
        """Whether ``task_id`` currently has an executing asyncio task."""
        return task_id in self._running_tasks

    def is_task_queued(self, task_id: str) -> bool:
        """Whether ``task_id`` is still waiting for a worker slot."""
        return task_id in self._queued_task_ids

    async def wait_current_snapshot(
        self, timeout: float | None = None
    ) -> None:
        """Wait for tasks that were already running when this method was entered.

        Only :attr:`_spawn_futures` at the instant of the call is considered.
        Spawns still queued for a slot are not included. Any :meth:`spawn` after
        the snapshot is taken has no effect on this wait.

        Args:
            timeout: If set, maximum time to wait; propagates :exc:`asyncio.TimeoutError`.

        Raises:
            asyncio.TimeoutError: If ``timeout`` is not ``None`` and snapshot tasks
                do not all finish within that many seconds.
        """
        snapshot = list(self._spawn_futures.values())
        if not snapshot:
            return
        if timeout is None:
            _ = await asyncio.gather(*snapshot)
        else:
            _ = await asyncio.wait_for(asyncio.gather(*snapshot), timeout)

    async def start(self) -> Self:
        """Start the task manager by launching the worker task

        Returns:
            The started TaskManager instance
        """

        # Start the worker task that processes the queue
        worker_task = asyncio.create_task(self._worker())
        TaskManager._worker_task.__set__(self, worker_task)
        return self

    async def _worker(self):
        """Main worker loop that processes coroutines from the queue.

        Handles:
        - Normal queue processing
        - Shutdown signal (_event)
        - Task creation and tracking
        """
        try:
            while not self._event.is_set():
                # Wait for either a new coroutine or shutdown signal
                coro_task = asyncio.create_task(self._pending_coro.get())
                event_task = asyncio.create_task(self._event.wait())

                done, _ = await asyncio.wait(
                    [coro_task, event_task], return_when=asyncio.FIRST_COMPLETED
                )

                # Handle shutdown signal
                if event_task in done and coro_task not in done:
                    with contextlib.suppress(asyncio.CancelledError):
                        _ = coro_task.cancel()
                    break

                # Get the next (task_id, runner coroutine) to execute
                task_id, coro = coro_task.result()
                with contextlib.suppress(asyncio.CancelledError):
                    _ = event_task.cancel()

                # Wait for an available slot
                _ = await self.slots.acquire()

                # Create and track the new task
                self._running_tasks[task_id] = self._create_task(coro, task_id)

        except Exception as e:
            logging.exception(
                f"Worker crashed due to {e}. Restarting is required."
            )

    async def drain(self) -> None:
        """Wait for completion of all tasks with proper timeout handling.

        Processes:
        1. Currently running tasks (in batches)
        2. Pending coroutines in the queue
        """
        if self._pending_coro.empty() and not self._running_tasks:
            return

        # Process running tasks in batches of max_tasks
        running_tasks = list(self._running_tasks.values())
        self._running_tasks.clear()
        for task_batch in moving_window(running_tasks, self.max_tasks):
            try:
                _ = await asyncio.wait_for(
                    asyncio.gather(*task_batch), self.close_timeout_seconds
                )
            except TimeoutError:
                logging.exception(
                    "Could not finish running tasks due to timeout."
                )

        # Process any remaining pending (task_id, runner) pairs
        pending_runners: list[Coroutine[Any, Any, Any]] = []
        while not self._pending_coro.empty():
            _tid, runner = self._pending_coro.get_nowait()
            pending_runners.append(runner)

        if not pending_runners:
            return

        try:
            _ = await asyncio.wait_for(
                asyncio.gather(*pending_runners),
                self.close_timeout_seconds,
            )
        except TimeoutError:
            logging.error("Could not finish all pending tasks due to timeout.")

    def _create_task(self, coro: Coroutine, task_id: str) -> asyncio.Task:
        """Wrapper for task creation that handles cleanup and error logging.

        Args:
            coro: The coroutine to execute
            task_id: Unique identifier for the task

        Returns:
            The created asyncio Task
        """

        async def _task():
            try:
                await coro
            except Exception:
                logging.exception(f"Failed running coroutine: {coro!r}")
            finally:
                # Return the execution slot and clean up
                self.slots.release()
                if task_id in self._running_tasks:
                    _ = self._running_tasks.pop(task_id, None)

        return asyncio.create_task(_task())

    async def close(self) -> None:
        """Gracefully shutdown the task manager by:
        1. Setting the shutdown event
        2. Waiting for worker task to complete
        3. Draining remaining tasks
        """
        if (
            not is_initialized(self, "_worker_task")
            or self._worker_task is None
        ):
            return

        # Signal shutdown
        self._event.set()
        try:
            await asyncio.wait_for(
                self._worker_task, self.close_timeout_seconds
            )
        except Exception:
            logging.exception("Could not finish worker due to timeout.")

        # Clean up remaining tasks
        await self.drain()
        TaskManager._worker_task.__delete__(self)

    async def aclose(self):
        """Gracefully shutdown task manager, to support contextlib.aclosing"""
        return await self.close()

    def __await__(self):
        """Allow awaiting the manager directly to start it."""
        return self.start().__await__()

    async def __aenter__(self) -> Self:
        """Context manager entry point."""
        _ = await self.start()
        return self

    async def __aexit__(self, *_) -> None:
        """Context manager exit point - ensures proper shutdown."""
        await self.close()
