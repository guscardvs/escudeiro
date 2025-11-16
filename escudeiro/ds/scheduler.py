import asyncio
import inspect
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, tzinfo
from typing import TYPE_CHECKING, Any

from escudeiro.data import data, field
from escudeiro.ds.manager import TaskManager
from escudeiro.escudeiro_pyrs import cronjob
from escudeiro.lazyfields import lazyfield
from escudeiro.misc import make_noop, now


@data(frozen=False)
class Task:
    id_: str
    func: Callable[[], Any]
    cron: cronjob.CronExpr | None
    next_run: datetime
    name: str | None = None
    is_running: bool = False
    remove_callback: Callable[[str], Awaitable[None]] = field(
        default=make_noop(asyncio=True)
    )

    @lazyfield
    def _count(self) -> int:
        """Counter tracking how many times the task has executed."""
        return 0

    @lazyfield
    def lock(self) -> asyncio.Lock:
        """Asyncio lock for thread-safe task state management."""
        return asyncio.Lock()

    async def run_count(self):
        """Get the number of times this task has executed.

        Returns:
            The execution count
        """
        return self._count

    async def set(self):
        """Mark the task as running and increment execution count."""
        async with self.lock:
            self.is_running = True
            self._count += 1

    async def reset(self):
        """Mark the task as not running."""
        async with self.lock:
            self.is_running = False

    async def status(self):
        """Check if the task is currently running.

        Returns:
            True if the task is running, False otherwise
        """
        async with self.lock:
            return self.is_running


@data
class CronInfo:
    """Container for cron expression scheduling information.

    Attributes:
        cronexpr: String representing the cron schedule
        timezone: Timezone for the schedule (defaults to local timezone)
    """

    cronexpr: str
    timezone: tzinfo = field(
        default_factory=lambda: datetime.now().astimezone().tzinfo
    )


@data(frozen=False)
class TaskScheduler:
    """Asynchronous task scheduler with cron-based and one-time execution support.

    Attributes:
        default_sleep_interval: Default sleep time (seconds) when no tasks exist
        log_info: Info logging callback
        log_warning: Warning logging callback
        log_exception: Error logging callback
    """

    default_sleep_interval: int = 1
    log_info: Callable[[str], Any] = make_noop()
    log_warning: Callable[[str], Any] = make_noop()
    log_exception: Callable[[str], Any] = make_noop()

    def __post_init__(self):
        _ = self._tasks, self._running, self.manager

    @lazyfield
    def _tasks(self) -> dict[str, Task]:
        """Dictionary mapping task IDs to Task instances."""
        return {}

    @lazyfield
    def _running(self):
        """Flag indicating if the scheduler is active."""
        return False

    @lazyfield
    def manager(self) -> TaskManager:
        """Task manager for handling background operations."""
        return TaskManager()

    @staticmethod
    def make_task_id() -> str:
        """Generate a unique task identifier.

        Returns:
            Hex string representing a UUID4
        """
        return uuid.uuid4().hex

    def schedule_task(
        self,
        func: Callable[[], Any],
        cron_expr: CronInfo | None,
        run_at: datetime | None,
        name: str | None = None,
        task_id: str | None = None,
        remove_callback: Callable[[str], Awaitable[None]] | None = None,
    ) -> str:
        """Schedule a new task for execution.

        Args:
            func: Callable to execute (sync or async)
            cron_expr: CronInfo for recurring tasks
            run_at: Specific datetime for one-time execution
            name: Optional task name (defaults to function name)
            task_id: Optional custom task ID
            remove_callback: Async callback when task is removed

        Returns:
            str: The task ID

        Raises:
            ValueError: If neither cron_expr nor run_at is provided,
                       or if both are provided
        """
        if not cron_expr and not run_at:
            raise ValueError("cron_expr or run_at must be provided.")

        if cron_expr is not None and run_at is not None:
            raise ValueError("Cannot specify both cron_expr and run_at")

        if run_at is not None:
            run_at = run_at.astimezone()
        task_id = task_id or self.make_task_id()
        cronexpr = cron_expr and cronjob.CronExpr(
            cron_expr.cronexpr, cron_expr.timezone
        )
        if cronexpr is not None:
            cronexpr.update()
            run_at = cronexpr.next_run

        if TYPE_CHECKING:
            assert run_at is not None

        task = Task(
            id_=task_id,
            func=func,
            cron=cronjob.CronExpr(cron_expr.cronexpr, cron_expr.timezone)
            if cron_expr
            else None,
            next_run=run_at,
            name=name or func.__name__,
            remove_callback=remove_callback or make_noop(asyncio=True),
        )

        self._tasks[task_id] = task
        self.log_info(f"Task '{task.name}' scheduled with ID {task_id}")
        return task_id

    def is_scheduled(self, task_id: str) -> bool:
        """Check if a task exists in the scheduler.

        Args:
            task_id: ID of the task to check

        Returns:
            bool: True if task exists, False otherwise
        """
        return task_id in self._tasks

    def get_task(self, task_id: str) -> Task | None:
        """Retrieve a task by its ID.

        Args:
            task_id: ID of the task to retrieve

        Returns:
            Task if found, None otherwise
        """
        return self._tasks.get(task_id)

    def task_ids(self) -> list[str]:
        """Get list of all scheduled task IDs.

        Returns:
            List of task ID strings
        """
        return list(self._tasks.keys())

    async def remove_task(
        self,
        task_id: str,
        callback: Callable[[str], Awaitable[None]],
    ) -> bool:
        """Remove a scheduled task.

        Args:
            task_id: ID of task to remove
            callback: Async callback to invoke after removal

        Returns:
            bool: True if task was removed, False if not found
        """
        if task_id not in self._tasks:
            return False
        task = self._tasks.pop(task_id)
        await callback(task_id)
        self.log_info(f"Taskt with ID {task_id} removed '{task.name}'")
        return True

    async def remove_by_name(
        self, name: str, callback: Callable[[str], Awaitable[None]]
    ) -> str | None:
        """Remove task(s) by name.

        Args:
            name: Name of task(s) to remove
            callback: Async callback to invoke after removal

        Returns:
            str: ID of removed task if found, None otherwise
        """
        for task_id, task in self._tasks.items():
            if task.name == name:
                _ = await self.remove_task(task_id, callback)
                return task_id
        return None

    async def _execute_task(self, task: Task) -> None:
        """Execute a task and handle post-execution logic.

        Args:
            task: Task instance to execute

        Note:
            Handles both synchronous and asynchronous functions,
            manages task state, and handles rescheduling/removal
        """
        if await task.status():
            self.log_warning(f"Task '{task.name}' is already running")
            return

        self.log_info(f"Starting task '{task.name}'")
        await task.set()
        try:
            if inspect.iscoroutinefunction(task.func):
                await task.func()
            else:
                await asyncio.to_thread(task.func)
            self.log_info(f"Task '{task.name}' finished.")

        except Exception as err:
            self.log_exception(f"Task '{task.name}' failed: {err}")

        finally:
            await task.reset()
            self._reschedule_task(task)

    def _reschedule_task(self, task: Task) -> None:
        """Reschedule a recurring task or queue for removal.

        Args:
            task: Task to reschedule

        Note:
            For cron-based tasks, calculates next run time.
            One-time tasks are queued for removal.
        """
        if task.cron:
            try:
                task.cron.update_after(
                    now().replace(second=0, microsecond=0)
                    + timedelta(minutes=1)
                )
                task.next_run = task.cron.next_run
            except Exception as e:
                self.log_exception(
                    f"Failed to reschedule task '{task.name}': {e}"
                )
                # Handle failed rescheduling
        else:
            self.manager.spawn(self.remove_task(task.id_, task.remove_callback))

    async def _scheduler_loop(self) -> None:
        """Main scheduling loop that executes due tasks.

        Continuously checks for and executes due tasks,
        sleeping between checks based on next scheduled run.
        """
        while self._running:
            timestamp = now()

            # Find and execute due tasks
            due_tasks = [
                task
                for task in self._tasks.values()
                if task.next_run <= timestamp
            ]

            # Check status only for tasks we'll actually run
            tasks_to_run = []
            for task in due_tasks:
                if not await task.status():
                    tasks_to_run.append(task)

            if tasks_to_run:
                await self._execute_tasks(tasks_to_run)

            await self._calculate_and_sleep()

    async def _calculate_and_sleep(self):
        """Calculate optimal sleep time before next task check.

        Sleeps until next scheduled task or default interval.
        """
        # Sleep for a short interval before next check
        if self._tasks:
            next_run_time = min(task.next_run for task in self._tasks.values())
            sleep_time = max(0, (next_run_time - now()).total_seconds())
        else:
            sleep_time = self.default_sleep_interval
        await asyncio.sleep(sleep_time)

    async def _execute_tasks(self, tasks: list[Task]) -> None:
        """Execute multiple tasks concurrently.

        Args:
            tasks: List of Task instances to execute

        Note:
            Gathers results and handles any exceptions
        """
        results = await asyncio.gather(
            *(self._execute_task(task) for task in tasks),
            return_exceptions=True,
        )
        for task, result in zip(tasks, results):
            if isinstance(result, Exception):
                self.log_exception(f"Task '{task.name}' failed {result}")

    async def setup(self) -> None:
        """Setup method to initialize the scheduler.

        Can be overridden for custom initialization logic.
        """
        _ = await self.manager.start()
        self.log_info("Task scheduler setup complete.")

    async def start(self) -> None:
        """Start the scheduler event loop."""
        if self._running:
            return

        self._running = True
        await self.setup()
        self.log_info("Task scheduler started.")
        await self._scheduler_loop()

    async def stop(self) -> None:
        """Stop the scheduler event loop."""
        self._running = False
        self.log_info("Task scheduler stopped")
        await self.manager.close()

    async def aclose(self):
        """Async cleanup method to stop scheduler and release resources.

        Alias for stop() for contextlib.aclosing.
        """
        await self.stop()
