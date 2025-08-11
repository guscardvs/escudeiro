# pyright: reportPrivateUsage=false
# pyright: reportFunctionMemberAccess=false
import asyncio
from contextlib import aclosing
import datetime
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# Import the actual classes
from escudeiro.ds import CronInfo, Task, TaskScheduler

# Import the classes to test - adjust path as needed
from escudeiro.misc import make_noop, timezone


# Fixtures for common test objects
@pytest.fixture
def task_scheduler():
    scheduler = TaskScheduler(
        log_info=lambda msg: None,
        log_warning=lambda msg: None,
        log_exception=lambda msg: None,
    )
    return scheduler


@pytest.fixture
def sample_cron_info():
    return CronInfo(cronexpr="*/5 * * * *")


@pytest.fixture
async def scheduler_with_mock_manager():
    # Create a scheduler with a mocked TaskManager
    async with aclosing(TaskScheduler()) as scheduler:
        await scheduler.setup()
        scheduler.manager = MagicMock(wraps=scheduler.manager)
        scheduler.manager.spawn = MagicMock(wraps=scheduler.manager.spawn)
        scheduler.manager.close = MagicMock(wraps=scheduler.manager.close)

        # Create mocked logging functions that track calls
        scheduler.log_info = MagicMock()
        scheduler.log_warning = MagicMock()
        scheduler.log_exception = MagicMock()

        yield scheduler


# Basic Task Tests
class TestTask:
    def test_task_init(self):
        """Test that Task initializes correctly"""
        func = make_noop()
        task = Task(
            id_="test-id",
            func=func,
            cron=None,
            next_run=datetime.datetime.now(tz=datetime.UTC),
            name="test-task",
        )

        assert task.id_ == "test-id"
        assert task.func is func
        assert task.name == "test-task"
        assert task.is_running is False

    async def test_task_run_count(self):
        """Test task execution count tracking"""
        task = Task(
            id_="test-id",
            func=make_noop(),
            cron=None,
            next_run=datetime.datetime.now(tz=datetime.UTC),
        )

        # Initial count should be 0
        assert await task.run_count() == 0

        # After setting (indicating execution), count should increment
        await task.set()
        assert await task.run_count() == 1

        # After resetting, count should remain at 1
        await task.reset()
        assert await task.run_count() == 1

        # Another run should increment to 2
        await task.set()
        assert await task.run_count() == 2

    async def test_task_status(self):
        """Test task status tracking"""
        task = Task(
            id_="test-id",
            func=lambda: None,
            cron=None,
            next_run=datetime.datetime.now(tz=datetime.UTC),
        )

        # Initial status should be not running
        assert await task.status() is False

        # After setting, status should be running
        await task.set()
        assert await task.status() is True

        # After resetting, status should be not running
        await task.reset()
        assert await task.status() is False


# CronInfo Tests
class TestCronInfo:
    def test_cron_info_init(self):
        """Test CronInfo initialization"""
        cron_info = CronInfo(cronexpr="*/5 * * * *")
        assert cron_info.cronexpr == "*/5 * * * *"
        assert (
            cron_info.timezone is not None
        )  # Should default to local timezone

    def test_cron_info_with_timezone(self):
        """Test CronInfo with explicit timezone"""
        tz = datetime.UTC
        cron_info = CronInfo(cronexpr="*/5 * * * *", timezone=tz)
        assert cron_info.timezone == tz


# TaskScheduler Tests
class TestTaskScheduler:
    def test_scheduler_init(self):
        """Test TaskScheduler initialization"""
        scheduler = TaskScheduler()
        assert scheduler.default_sleep_interval == 1
        assert len(scheduler._tasks) == 0
        assert scheduler._running is False

    def test_make_task_id(self):
        """Test task ID generation"""
        scheduler = TaskScheduler()
        task_id = scheduler.make_task_id()
        # Should be a valid hex UUID string
        assert len(task_id) == 32
        try:
            _ = uuid.UUID(hex=task_id)
        except ValueError:
            pytest.fail("Generated task ID is not a valid UUID")

    async def test_schedule_task_with_cron(
        self,
        scheduler_with_mock_manager: TaskScheduler,
    ):
        """Test scheduling a task with cron expression"""
        scheduler = scheduler_with_mock_manager
        cron_info = CronInfo(cronexpr="*/5 * * * *")

        task_id = scheduler.schedule_task(
            func=lambda: None,
            cron_expr=cron_info,
            run_at=None,
            name="test-cron-task",
        )

        assert task_id in scheduler._tasks
        assert scheduler._tasks[task_id].name == "test-cron-task"
        assert scheduler._tasks[task_id].cron is not None

    async def test_schedule_task_with_run_at(
        self, scheduler_with_mock_manager: TaskScheduler
    ):
        """Test scheduling a one-time task"""
        scheduler = scheduler_with_mock_manager
        run_time = timezone.now() + datetime.timedelta(minutes=10)

        task_id = scheduler.schedule_task(
            func=lambda: None,
            cron_expr=None,
            run_at=run_time,
            name="test-one-time-task",
        )

        assert task_id in scheduler._tasks
        assert scheduler._tasks[task_id].name == "test-one-time-task"
        assert scheduler._tasks[task_id].cron is None
        assert (
            abs(
                (scheduler._tasks[task_id].next_run - run_time).total_seconds()
            )
            < 1
        )  # Almost equal

    async def test_schedule_task_validation(
        self, scheduler_with_mock_manager: TaskScheduler
    ):
        """Test validation in schedule_task"""
        scheduler = scheduler_with_mock_manager

        # Test missing both cron_expr and run_at
        with pytest.raises(
            ValueError, match="cron_expr or run_at must be provided"
        ):
            _ = scheduler.schedule_task(
                func=lambda: None, cron_expr=None, run_at=None
            )

        # Test specifying both cron_expr and run_at
        with pytest.raises(
            ValueError, match="Cannot specify both cron_expr and run_at"
        ):
            _ = scheduler.schedule_task(
                func=lambda: None,
                cron_expr=CronInfo(cronexpr="*/5 * * * *"),
                run_at=timezone.now(),
            )

    async def test_is_scheduled(
        self, scheduler_with_mock_manager: TaskScheduler
    ):
        """Test is_scheduled method"""
        scheduler = scheduler_with_mock_manager
        cron_info = CronInfo(cronexpr="*/5 * * * *")

        task_id = scheduler.schedule_task(
            func=lambda: None, cron_expr=cron_info, run_at=None
        )

        assert scheduler.is_scheduled(task_id) is True
        assert scheduler.is_scheduled("non-existent-id") is False

    async def test_get_task(self, scheduler_with_mock_manager: TaskScheduler):
        """Test get_task method"""
        scheduler = scheduler_with_mock_manager
        cron_info = CronInfo(cronexpr="*/5 * * * *")

        task_id = scheduler.schedule_task(
            func=lambda: None,
            cron_expr=cron_info,
            run_at=None,
            name="test-task",
        )

        task = scheduler.get_task(task_id)
        assert task is not None
        assert task.name == "test-task"

        non_existent_task = scheduler.get_task("non-existent-id")
        assert non_existent_task is None

    async def test_task_ids(self, scheduler_with_mock_manager: TaskScheduler):
        """Test task_ids method"""
        scheduler = scheduler_with_mock_manager
        cron_info = CronInfo(cronexpr="*/5 * * * *")

        # Initially empty
        assert len(scheduler.task_ids()) == 0

        # After adding tasks
        task_id1 = scheduler.schedule_task(
            func=lambda: None, cron_expr=cron_info, run_at=None, name="task1"
        )

        task_id2 = scheduler.schedule_task(
            func=lambda: None, cron_expr=cron_info, run_at=None, name="task2"
        )

        task_ids = scheduler.task_ids()
        assert len(task_ids) == 2
        assert task_id1 in task_ids
        assert task_id2 in task_ids

    async def test_remove_task(
        self, scheduler_with_mock_manager: TaskScheduler
    ):
        """Test remove_task method"""
        scheduler = scheduler_with_mock_manager
        cron_info = CronInfo(cronexpr="*/5 * * * *")
        callback = AsyncMock()

        task_id = scheduler.schedule_task(
            func=lambda: None,
            cron_expr=cron_info,
            run_at=None,
            name="test-task",
        )

        # Test successful removal
        result = await scheduler.remove_task(task_id, callback)
        assert result is True
        assert task_id not in scheduler._tasks
        callback.assert_called_once_with(task_id)

        # Test removal of non-existent task
        result = await scheduler.remove_task("non-existent-id", callback)
        assert result is False
        # Callback should still be called just once from the previous successful removal
        assert callback.call_count == 1

    async def test_remove_by_name(
        self, scheduler_with_mock_manager: TaskScheduler
    ):
        """Test remove_by_name method"""
        scheduler = scheduler_with_mock_manager
        cron_info = CronInfo(cronexpr="*/5 * * * *")
        callback = AsyncMock()

        task_id = scheduler.schedule_task(
            func=lambda: None,
            cron_expr=cron_info,
            run_at=None,
            name="test-task",
        )

        # Test successful removal by name
        removed_id = await scheduler.remove_by_name("test-task", callback)
        assert removed_id == task_id
        assert task_id not in scheduler._tasks
        callback.assert_called_once_with(task_id)

        # Test removal of non-existent task
        removed_id = await scheduler.remove_by_name(
            "non-existent-task", callback
        )
        assert removed_id is None
        # Callback should still be called just once from the previous successful removal
        assert callback.call_count == 1

    async def test_execute_task_sync_function(
        self, scheduler_with_mock_manager: TaskScheduler
    ):
        """Test execution of synchronous task function"""
        scheduler = scheduler_with_mock_manager
        mock_func = MagicMock()

        task = Task(
            id_="test-id",
            func=mock_func,
            cron=None,
            next_run=timezone.now(),
            name="test-sync-task",
        )

        await scheduler._execute_task(task)

        # The function should have been called
        mock_func.assert_called_once()
        # Task should be marked as not running after execution
        assert await task.status() is False

    async def test_execute_task_async_function(
        self, scheduler_with_mock_manager: TaskScheduler
    ):
        """Test execution of asynchronous task function"""
        scheduler = scheduler_with_mock_manager
        mock_func = AsyncMock()

        task = Task(
            id_="test-id",
            func=mock_func,
            cron=None,
            next_run=timezone.now(),
            name="test-async-task",
        )

        await scheduler._execute_task(task)

        # The function should have been called
        mock_func.assert_called_once()
        # Task should be marked as not running after execution
        assert await task.status() is False

    async def test_execute_task_handles_exceptions(
        self, scheduler_with_mock_manager: TaskScheduler
    ):
        """Test that exceptions in task execution are handled"""
        scheduler = scheduler_with_mock_manager

        # Function that raises an exception
        def failing_func():
            raise ValueError("Task failed intentionally")

        task = Task(
            id_="test-id",
            func=failing_func,
            cron=None,
            next_run=timezone.now(),
            name="test-failing-task",
        )

        # This should not raise
        await scheduler._execute_task(task)

        # Exception should be logged
        scheduler.log_exception.assert_called_once()
        assert "failed" in scheduler.log_exception.call_args[0][0]

        # Task should be marked as not running despite exception
        assert await task.status() is False

    async def test_execute_task_removes_one_time_task(
        self, scheduler_with_mock_manager: TaskScheduler
    ):
        """Test that one-time tasks are removed after execution"""
        scheduler = scheduler_with_mock_manager
        mock_func = MagicMock()
        remove_callback = AsyncMock()

        task = Task(
            id_="test-id",
            func=mock_func,
            cron=None,
            next_run=timezone.now(),
            name="test-one-time-task",
            remove_callback=remove_callback,
        )

        scheduler._tasks["test-id"] = task

        await scheduler._execute_task(task)

        # Task should be removed and manager should spawn removal process
        scheduler.manager.spawn.assert_called_once()

    async def test_execute_task_reschedules_cron_task(
        self, scheduler_with_mock_manager: TaskScheduler
    ):
        """Test that cron tasks are rescheduled after execution"""
        scheduler = scheduler_with_mock_manager
        mock_func = MagicMock()

        # Create a task with a mock cron expression
        mock_cron = MagicMock()
        mock_cron.update_after = MagicMock()
        mock_cron.next_run = timezone.now() + datetime.timedelta(minutes=5)

        task = Task(
            id_="test-id",
            func=mock_func,
            cron=mock_cron,
            next_run=timezone.now(),
            name="test-cron-task",
        )

        scheduler._tasks["test-id"] = task
        initial_next_run = task.next_run

        await scheduler._execute_task(task)

        # Function should be called
        mock_func.assert_called_once()

        # Cron expression should be updated
        mock_cron.update_after.assert_called_once()

        # Next run should be different after rescheduling
        assert task.next_run != initial_next_run

    async def test_execute_tasks_concurrent(
        self, scheduler_with_mock_manager: TaskScheduler
    ):
        """Test that multiple tasks can be executed concurrently"""
        scheduler = scheduler_with_mock_manager

        # Create a set of mock functions that we can track
        mock_funcs = [AsyncMock() for _ in range(5)]
        tasks = []

        # Create tasks for each function
        for i, mock_func in enumerate(mock_funcs):
            task = Task(
                id_=f"test-id-{i}",
                func=mock_func,
                cron=None,
                next_run=timezone.now(),
                name=f"test-task-{i}",
            )
            tasks.append(task)
            scheduler._tasks[task.id_] = task

        # Execute all tasks concurrently
        await scheduler._execute_tasks(tasks)

        # All functions should have been called
        for mock_func in mock_funcs:
            mock_func.assert_called_once()

    async def test_execute_tasks_handles_exceptions(
        self, scheduler_with_mock_manager: TaskScheduler
    ):
        """Test that exceptions in concurrent task execution are handled"""
        scheduler = scheduler_with_mock_manager

        # Create mixed set of succeeding and failing functions
        success_func = AsyncMock()

        def failing_func():
            raise ValueError("Task failed intentionally")

        tasks = [
            Task(
                id_="task-1",
                func=success_func,
                cron=None,
                next_run=timezone.now(),
                name="success-task",
            ),
            Task(
                id_="task-2",
                func=failing_func,
                cron=None,
                next_run=timezone.now(),
                name="failing-task",
            ),
        ]

        for task in tasks:
            scheduler._tasks[task.id_] = task

        # This should not raise despite one task failing
        await scheduler._execute_tasks(tasks)

        # The successful function should have been called
        success_func.assert_called_once()

        # The exception should be logged
        scheduler.log_exception.assert_called_once()

    async def test_calculate_and_sleep(
        self,
        scheduler_with_mock_manager: TaskScheduler,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test calculation of sleep time between task checks"""
        scheduler = scheduler_with_mock_manager

        # Mock asyncio.sleep to avoid actual sleeping
        mock_sleep = AsyncMock()
        monkeypatch.setattr(asyncio, "sleep", mock_sleep)

        # Case 1: No tasks - should sleep for default interval
        scheduler._tasks.clear()
        await scheduler._calculate_and_sleep()
        mock_sleep.assert_called_with(scheduler.default_sleep_interval)

        # Case 2: With task(s) - should sleep until next task
        future_time = timezone.now() + datetime.timedelta(seconds=30)
        task = Task(
            id_="test-id",
            func=lambda: None,
            cron=None,
            next_run=future_time,
            name="test-task",
        )
        scheduler._tasks["test-id"] = task

        mock_sleep.reset_mock()
        await scheduler._calculate_and_sleep()

        # Should be called with time until next task (within a small margin)
        call_arg = mock_sleep.call_args[0][0]
        assert 0 <= call_arg <= 30  # Between 0 and 30 seconds

    async def test_scheduler_loop(
        self,
        scheduler_with_mock_manager: TaskScheduler,
    ):
        """Test the main scheduler loop"""
        scheduler = scheduler_with_mock_manager

        # Mock methods to avoid actual execution
        _original_exec_tasks = TaskScheduler._execute_tasks
        _original_calc = TaskScheduler._calculate_and_sleep
        TaskScheduler._execute_tasks = AsyncMock()
        TaskScheduler._calculate_and_sleep = AsyncMock()

        # Set up a task due for execution
        mock_func = MagicMock()
        _task_status = Task.status
        Task.status = AsyncMock(return_value=False)
        task = Task(
            id_="test-id",
            func=mock_func,
            cron=None,
            next_run=timezone.now()
            - datetime.timedelta(seconds=1),  # Past due
            name="test-task",
        )
        scheduler._tasks["test-id"] = task

        # Start the scheduler and let it run one iteration
        scheduler._running = True

        # Run one iteration then stop
        async def side_effect(*args: Any, **kwargs: Any):
            _ = args, kwargs
            scheduler._running = False

        scheduler._calculate_and_sleep.side_effect = side_effect

        await scheduler._scheduler_loop()

        # The execute_tasks method should be called with our task
        scheduler._execute_tasks.assert_called_once()
        assert len(scheduler._execute_tasks.call_args[0][0]) == 1
        assert scheduler._execute_tasks.call_args[0][0][0].id_ == "test-id"

        TaskScheduler._execute_tasks = _original_exec_tasks
        TaskScheduler._calculate_and_sleep = _original_calc
        Task.status = _task_status

    async def test_start_stop(
        self, scheduler_with_mock_manager: TaskScheduler
    ):
        """Test starting and stopping the scheduler"""
        scheduler = scheduler_with_mock_manager

        # Mock the scheduler loop to avoid actual execution
        _scheduler_loop = TaskScheduler._scheduler_loop
        TaskScheduler._scheduler_loop = AsyncMock()

        # Test starting
        await scheduler.start()
        assert scheduler._running is True
        scheduler._scheduler_loop.assert_called_once()

        # Starting again should be no-op
        scheduler._scheduler_loop.reset_mock()
        await scheduler.start()
        scheduler._scheduler_loop.assert_not_called()

        # Test stopping
        await scheduler.stop()
        assert scheduler._running is False
        scheduler.manager.close.assert_called_once()

        TaskScheduler._scheduler_loop = _scheduler_loop

    async def test_aclose(self, scheduler_with_mock_manager: TaskScheduler):
        """Test aclose method (alias for stop)"""
        scheduler = scheduler_with_mock_manager
        _stop = TaskScheduler.stop
        TaskScheduler.stop = AsyncMock()

        await scheduler.aclose()
        scheduler.stop.assert_called_once()

        TaskScheduler.stop = _stop
