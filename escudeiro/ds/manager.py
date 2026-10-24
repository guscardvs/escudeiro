from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from functools import partial
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
        # shield: cancelling/timing out one awaiter must not cancel the shared
        # future (and with it every other awaiter).
        return asyncio.shield(self.future).__await__()


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
        """Queue of (task_id, coroutine) waiting for a slot."""
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
        self._pending_coro.put_nowait((task_id, coro))
        return Spawned(task_id, future)

    async def _run_job(self, task_id: str, coro: Coroutine[Any, Any, Any]):
        """Run ``coro`` and resolve the future of ``task_id`` with its outcome."""
        self._queued_task_ids.discard(task_id)
        future = self._spawn_futures.get(task_id)
        try:
            try:
                result = await coro
                if future is not None and not future.done():
                    future.set_result(result)
            except asyncio.CancelledError:
                if future is not None and not future.done():
                    _ = future.cancel()
                raise
            except Exception as e:
                if future is not None and not future.done():
                    future.set_exception(e)
        finally:
            _ = self._spawn_futures.pop(task_id, None)

    def _discard_job(self, task_id: str, coro: Coroutine[Any, Any, Any]):
        """Drop a job that will never run: close the coroutine, cancel its future."""
        coro.close()
        self._queued_task_ids.discard(task_id)
        future = self._spawn_futures.pop(task_id, None)
        if future is not None and not future.done():
            _ = future.cancel()

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
        """Wait for every spawn that was accepted before this method was entered.

        Only :attr:`_spawn_futures` at the instant of the call is considered:
        that is running work *and* spawns still queued for a slot (a spawn
        immediately followed by this call must wait for it). Any :meth:`spawn`
        after the snapshot is taken has no effect on this wait. The tasks' own
        results and exceptions are not raised here, and a timeout never
        cancels them.

        Args:
            timeout: If set, maximum time to wait; raises :exc:`asyncio.TimeoutError`.

        Raises:
            asyncio.TimeoutError: If ``timeout`` is not ``None`` and snapshot tasks
                do not all finish within that many seconds.
        """
        snapshot = list(self._spawn_futures.values())
        if not snapshot:
            return
        # asyncio.wait never cancels the futures it is given (unlike wait_for
        # over gather), so a timeout leaves the users' futures untouched.
        _, pending = await asyncio.wait(snapshot, timeout=timeout)
        if pending:
            raise TimeoutError

    async def start(self) -> Self:
        """Start the task manager by launching the worker task.

        Starting an already running manager is a no-op; a closed manager can be
        started again (it gets a fresh shutdown event).

        Returns:
            The started TaskManager instance
        """
        if (
            is_initialized(self, "_worker_task")
            and self._worker_task is not None
            and not self._worker_task.done()
        ):
            return self

        # A fresh event per run: close() leaves the previous one set.
        TaskManager._event.__set__(self, asyncio.Event())
        worker_task = asyncio.create_task(self._worker())
        TaskManager._worker_task.__set__(self, worker_task)
        return self

    async def _next_job(self) -> tuple[str, Coroutine[Any, Any, Any]] | None:
        """Wait for the next queued job; ``None`` when shutdown was signalled."""
        get_task = asyncio.create_task(self._pending_coro.get())
        event_task = asyncio.create_task(self._event.wait())
        try:
            _ = await asyncio.wait(
                [get_task, event_task], return_when=asyncio.FIRST_COMPLETED
            )
        except asyncio.CancelledError:
            # The item may already have been dequeued: don't lose it.
            if get_task.done() and not get_task.cancelled():
                self._discard_job(*get_task.result())
            raise
        finally:
            _ = event_task.cancel()
            _ = get_task.cancel()
        if get_task.done() and not get_task.cancelled():
            return get_task.result()
        return None

    async def _worker(self):
        """Main worker loop that processes coroutines from the queue.

        Handles:
        - Normal queue processing
        - Shutdown signal (_event)
        - Task creation and tracking
        - Jobs dequeued but still waiting for a slot when the worker is
          cancelled (they are discarded: coroutine closed, future cancelled)
        """
        current: tuple[str, Coroutine[Any, Any, Any]] | None = None
        try:
            while not self._event.is_set():
                current = await self._next_job()
                if current is None:
                    break

                # Wait for an available slot
                _ = await self.slots.acquire()

                # Create and track the new task
                task_id, coro = current
                self._running_tasks[task_id] = self._create_task(
                    self._run_job(task_id, coro), task_id
                )
                current = None
        except Exception as e:
            logging.exception(
                f"Worker crashed due to {e}. Restarting is required."
            )
        finally:
            if current is not None:
                self._discard_job(*current)

    async def drain(self) -> None:
        """Wait for completion of all tasks with proper timeout handling.

        Processes:
        1. Currently running tasks (in batches)
        2. Pending coroutines in the queue

        Jobs that do not finish within ``close_timeout_seconds`` are cancelled,
        so every :class:`Spawned` future is resolved when this returns.
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

        # Process any remaining pending (task_id, coroutine) pairs
        pending: list[tuple[str, Coroutine[Any, Any, Any]]] = []
        while not self._pending_coro.empty():
            pending.append(self._pending_coro.get_nowait())

        if not pending:
            return

        tasks = [
            asyncio.create_task(self._run_job(task_id, coro))
            for task_id, coro in pending
        ]
        _, unfinished = await asyncio.wait(
            tasks, timeout=self.close_timeout_seconds
        )
        if unfinished:
            logging.error("Could not finish all pending tasks due to timeout.")
            for task in unfinished:
                _ = task.cancel()
            _ = await asyncio.gather(*unfinished, return_exceptions=True)
        # A task cancelled before its first step never ran its body.
        for task_id, coro in pending:
            if task_id in self._spawn_futures:
                self._discard_job(task_id, coro)

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
                await self._run_job(task_id, coro)
            except Exception:
                logging.exception(f"Failed running coroutine: {coro!r}")

        task = asyncio.create_task(_task())
        # A done callback also runs for a task cancelled before its first step.
        task.add_done_callback(partial(self._job_done, task_id, coro))
        return task

    def _job_done(
        self,
        task_id: str,
        coro: Coroutine[Any, Any, Any],
        _task: asyncio.Task[None],
    ) -> None:
        # Return the execution slot and clean up
        self.slots.release()
        _ = self._running_tasks.pop(task_id, None)
        if task_id in self._spawn_futures:  # the job never got to run
            self._discard_job(task_id, coro)

    async def close(self) -> None:
        """Gracefully shutdown the task manager by:
        1. Setting the shutdown event
        2. Waiting for worker task to complete
        3. Draining remaining tasks

        Afterwards every spawned job is resolved: finished, or cancelled (its
        future cancelled and its coroutine closed if it never ran).
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
