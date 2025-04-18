from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Coroutine
from typing import Self
from uuid import uuid4

from escudeiro.data import data
from escudeiro.lazyfields import is_initialized, lazyfield
from escudeiro.misc import moving_window


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
    def _pending_coro(self) -> asyncio.Queue[Coroutine]:
        """Queue holding coroutines waiting to be executed."""
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
    def _worker_task(self) -> asyncio.Task | None:
        """Background task that processes the coroutine queue."""
        return None

    def spawn(self, coro: Coroutine) -> None:
        """Enqueue a coroutine for execution.

        Args:
            coro: The coroutine to be executed
        """
        if (
            not is_initialized(self, "_worker_task")
            or self._worker_task is None
        ):
            raise RuntimeError(
                "TaskManager must be started before spawning tasks."
            )
        self._pending_coro.put_nowait(coro)

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

                # Get the next coroutine to execute
                coro = coro_task.result()
                with contextlib.suppress(asyncio.CancelledError):
                    _ = event_task.cancel()

                # Wait for an available slot
                _ = await self.slots.acquire()

                # Create and track the new task
                task_id = uuid4().hex
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

        # Process any remaining pending coroutines
        tasks = []
        while not self._pending_coro.empty():
            tasks.append(self._pending_coro.get_nowait())

        if not tasks:
            return

        try:
            _ = await asyncio.wait_for(
                asyncio.gather(*tasks), self.close_timeout_seconds
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
