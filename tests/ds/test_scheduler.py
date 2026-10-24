# pyright: reportPrivateUsage=false
# pyright: reportFunctionMemberAccess=false
import asyncio
import datetime
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest

# Import the actual classes
from escudeiro.ds import CronInfo, Task, TaskScheduler
from escudeiro.escudeiro_pyrs import cronjob
from escudeiro.misc import make_noop, timezone

UTC = datetime.UTC
MINUS_3 = datetime.timezone(datetime.timedelta(hours=-3))


@asynccontextmanager
async def scheduler_ctx(**kwargs: Any) -> AsyncIterator[TaskScheduler]:
    """A scheduler with a real, started TaskManager (no mocks)."""
    scheduler = TaskScheduler(**kwargs)
    await scheduler.setup()
    try:
        yield scheduler
    finally:
        await scheduler.stop()


@asynccontextmanager
async def running(
    scheduler: TaskScheduler,
) -> AsyncIterator[asyncio.Task[None]]:
    """Run ``scheduler.start()`` in the background; stop it on exit."""
    run = asyncio.create_task(scheduler.start())
    for _ in range(5):  # let the loop reach its first sleep
        await asyncio.sleep(0)
    try:
        yield run
    finally:
        await scheduler.stop()
        await asyncio.wait_for(run, 1)


async def until(predicate: Callable[[], bool], timeout: float = 1.0) -> None:
    async def _poll():
        while not predicate():
            await asyncio.sleep(0.005)

    await asyncio.wait_for(_poll(), timeout)


def fake_clock(start: datetime.datetime):
    cell = [start]
    return cell, lambda: cell[0]


@pytest.fixture
def sample_cron_info():
    return CronInfo(cronexpr="*/5 * * * *")


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

    async def test_task_claim(self):
        task = Task(
            id_="test-id",
            func=lambda: None,
            cron=None,
            next_run=datetime.datetime.now(tz=datetime.UTC),
        )
        assert task.claim() is True
        assert task.claim() is False  # already owned
        assert await task.run_count() == 1
        await task.reset()
        assert task.claim() is True


# CronInfo Tests
class TestCronInfo:
    def test_cron_info_init(self):
        """Test CronInfo initialization"""
        cron_info = CronInfo(cronexpr="*/5 * * * *")
        assert cron_info.cronexpr == "*/5 * * * *"
        assert cron_info.timezone is UTC  # explicit, DST-free default

    def test_cron_info_with_timezone(self):
        """Test CronInfo with explicit timezone"""
        tz = datetime.UTC
        cron_info = CronInfo(cronexpr="*/5 * * * *", timezone=tz)
        assert cron_info.timezone == tz

    def test_cron_info_accepts_zoneinfo(self):
        ny = ZoneInfo("America/New_York")
        assert CronInfo("0 9 * * *", ny).timezone is ny


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

    def test_schedule_task_with_cron(self):
        """Test scheduling a task with cron expression"""
        scheduler = TaskScheduler()
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

    def test_schedule_task_with_run_at(self):
        """Test scheduling a one-time task"""
        scheduler = TaskScheduler()
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
            abs((scheduler._tasks[task_id].next_run - run_time).total_seconds())
            < 1
        )  # Almost equal

    def test_schedule_task_validation(self):
        """Test validation in schedule_task"""
        scheduler = TaskScheduler()

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

    def test_is_scheduled(self):
        """Test is_scheduled method"""
        scheduler = TaskScheduler()
        cron_info = CronInfo(cronexpr="*/5 * * * *")

        task_id = scheduler.schedule_task(
            func=lambda: None, cron_expr=cron_info, run_at=None
        )

        assert scheduler.is_scheduled(task_id) is True
        assert scheduler.is_scheduled("non-existent-id") is False

    def test_get_task(self):
        """Test get_task method"""
        scheduler = TaskScheduler()
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

    def test_task_ids(self):
        """Test task_ids method"""
        scheduler = TaskScheduler()
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

    async def test_remove_task(self):
        """Test remove_task method"""
        scheduler = TaskScheduler()
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

    async def test_remove_by_name(self):
        """Test remove_by_name method"""
        scheduler = TaskScheduler()
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

    async def test_execute_task_sync_function(self):
        """Test execution of synchronous task function"""
        async with scheduler_ctx() as scheduler:
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

    async def test_execute_task_async_function(self):
        """Test execution of asynchronous task function"""
        async with scheduler_ctx() as scheduler:
            mock_func = AsyncMock()
            task = Task(
                id_="test-id",
                func=mock_func,
                cron=None,
                next_run=timezone.now(),
                name="test-async-task",
            )

            await scheduler._execute_task(task)

            mock_func.assert_called_once()
            assert await task.status() is False

    async def test_execute_task_handles_exceptions(self):
        """Test that exceptions in task execution are handled"""
        logs: list[str] = []
        async with scheduler_ctx(log_exception=logs.append) as scheduler:

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

            assert len(logs) == 1
            assert "failed" in logs[0]
            # Task should be marked as not running despite exception
            assert await task.status() is False

    async def test_execute_task_already_running_is_skipped(self):
        logs: list[str] = []
        async with scheduler_ctx(log_warning=logs.append) as scheduler:
            func = MagicMock()
            task = Task(id_="t", func=func, cron=None, next_run=timezone.now())
            await task.set()
            await scheduler._execute_task(task)
            func.assert_not_called()
            assert "already running" in logs[0]

    async def test_execute_task_removes_one_time_task(self):
        """Test that one-time tasks are removed after execution"""
        async with scheduler_ctx() as scheduler:
            remove_callback = AsyncMock()
            task = Task(
                id_="test-id",
                func=MagicMock(),
                cron=None,
                next_run=timezone.now(),
                name="test-one-time-task",
                remove_callback=remove_callback,
            )
            scheduler._tasks["test-id"] = task

            await scheduler._execute_task(task)
            await until(lambda: not scheduler.is_scheduled("test-id"))

            remove_callback.assert_awaited_once_with("test-id")

    async def test_execute_task_reschedules_cron_task(self):
        """Cron tasks get their next run from a real CronExpr."""
        cell, clock = fake_clock(
            datetime.datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
        )
        async with scheduler_ctx(clock=clock) as scheduler:
            func = MagicMock()
            task_id = scheduler.schedule_task(
                func, CronInfo("*/5 * * * *"), None, name="cron"
            )
            task = scheduler._tasks[task_id]
            assert task.next_run == datetime.datetime(
                2024, 1, 1, 10, 5, tzinfo=UTC
            )

            cell[0] = datetime.datetime(2024, 1, 1, 10, 5, 1, tzinfo=UTC)
            await scheduler._execute_task(task)

            func.assert_called_once()
            assert task.next_run == datetime.datetime(
                2024, 1, 1, 10, 10, tzinfo=UTC
            )
            assert scheduler.is_scheduled(task_id)

    # --- regressions for the review findings ---------------------------

    def test_cron_next_run_is_relative_to_finish_time(self):
        """`* * * * *` finishing at 10:00:00.2 runs at 10:01, not 10:02."""
        _, clock = fake_clock(
            datetime.datetime(2024, 1, 1, 10, 0, 0, 200_000, tzinfo=UTC)
        )
        scheduler = TaskScheduler(clock=clock)
        task_id = scheduler.schedule_task(
            lambda: None, CronInfo("* * * * *"), None
        )
        task = scheduler._tasks[task_id]
        scheduler._reschedule_task(task, clock())
        assert task.next_run == datetime.datetime(2024, 1, 1, 10, 1, tzinfo=UTC)

    def test_cron_reschedule_keeps_cron_timezone(self):
        """09:00-03:00 must stay 09:00-03:00 on later runs (was 09:00 UTC)."""
        _, clock = fake_clock(
            datetime.datetime(2024, 1, 1, 8, 0, tzinfo=MINUS_3)
        )
        scheduler = TaskScheduler(clock=clock)
        task_id = scheduler.schedule_task(
            lambda: None, CronInfo("0 9 * * *", MINUS_3), None
        )
        task = scheduler._tasks[task_id]
        assert task.next_run == datetime.datetime(2024, 1, 1, 9, tzinfo=MINUS_3)

        # the finish time may be given in any zone (the loop uses UTC clocks)
        finished = datetime.datetime(2024, 1, 1, 12, 0, 0, 500_000, tzinfo=UTC)
        scheduler._reschedule_task(task, finished)
        assert task.next_run == datetime.datetime(2024, 1, 2, 9, tzinfo=MINUS_3)
        assert task.next_run.utcoffset() == datetime.timedelta(hours=-3)

    def test_cron_with_zoneinfo_follows_dst(self):
        ny = ZoneInfo("America/New_York")
        scheduler = TaskScheduler()
        task_id = scheduler.schedule_task(
            lambda: None, CronInfo("0 9 * * *", ny), None
        )
        task = scheduler._tasks[task_id]
        # 2024-03-09 10:00 EST; DST starts on the 10th -> 09:00 EDT = 13:00Z
        scheduler._reschedule_task(
            task, datetime.datetime(2024, 3, 9, 15, 0, tzinfo=UTC)
        )
        assert task.next_run == datetime.datetime(2024, 3, 10, 13, tzinfo=UTC)

    async def test_cron_task_keeps_timezone_after_running(self):
        cell, clock = fake_clock(
            datetime.datetime(2024, 1, 1, 8, 0, tzinfo=MINUS_3)
        )
        done = asyncio.Event()

        async def job():
            done.set()

        async with scheduler_ctx(clock=clock) as scheduler:
            task_id = scheduler.schedule_task(
                job, CronInfo("0 9 * * *", MINUS_3), None
            )
            task = scheduler._tasks[task_id]
            first = task.next_run
            assert first == datetime.datetime(2024, 1, 1, 9, tzinfo=MINUS_3)
            cell[0] = datetime.datetime(
                2024, 1, 1, 9, 0, 0, 500_000, tzinfo=MINUS_3
            )
            async with running(scheduler):
                await asyncio.wait_for(done.wait(), 1)
                await until(lambda: task.next_run != first)
            assert task.next_run == datetime.datetime(
                2024, 1, 2, 9, tzinfo=MINUS_3
            )
            assert task.next_run.utcoffset() == datetime.timedelta(hours=-3)

    async def test_new_earlier_task_wakes_the_loop(self):
        ran = asyncio.Event()
        async with scheduler_ctx() as scheduler:
            _ = scheduler.schedule_task(
                lambda: None,
                None,
                timezone.now() + datetime.timedelta(seconds=300),
                name="late",
            )
            async with running(scheduler):
                # the loop is now sleeping towards the +300s task
                _ = scheduler.schedule_task(
                    ran.set,
                    None,
                    timezone.now() + datetime.timedelta(milliseconds=50),
                    name="soon",
                )
                await asyncio.wait_for(ran.wait(), 1)

    async def test_slow_task_does_not_block_others(self):
        release = asyncio.Event()
        quick_ran = asyncio.Event()

        async def slow():
            await release.wait()  # only the quick task can release it

        async def quick():
            quick_ran.set()
            release.set()

        async with scheduler_ctx() as scheduler:
            soon = timezone.now() + datetime.timedelta(milliseconds=20)
            _ = scheduler.schedule_task(slow, None, soon, name="slow")
            _ = scheduler.schedule_task(
                quick, None, soon + datetime.timedelta(milliseconds=100)
            )
            async with running(scheduler):
                await asyncio.wait_for(quick_ran.wait(), 1)

    async def test_stop_wakes_the_loop_promptly(self):
        async with scheduler_ctx() as scheduler:
            _ = scheduler.schedule_task(
                lambda: None,
                None,
                timezone.now() + datetime.timedelta(seconds=300),
            )
            run = asyncio.create_task(scheduler.start())
            for _ in range(5):
                await asyncio.sleep(0)
            await scheduler.stop()
            await asyncio.wait_for(run, 0.5)  # was: blocked in the sleep
            assert scheduler._running is False

    async def test_scheduler_can_be_restarted(self):
        calls: list[int] = []
        removed = asyncio.Event()

        async def on_removed(_: str):
            removed.set()

        async with scheduler_ctx() as scheduler:
            async with running(scheduler):
                pass
            # restart: the old wake event / manager shutdown event are stale
            _ = scheduler.schedule_task(
                lambda: calls.append(1),
                None,
                timezone.now() + datetime.timedelta(milliseconds=30),
                remove_callback=on_removed,
            )
            async with running(scheduler):
                await asyncio.wait_for(removed.wait(), 1)
                for _ in range(20):  # a due task must not be re-run
                    await asyncio.sleep(0.001)
            assert calls == [1]
            assert scheduler.task_ids() == []

    async def test_callable_returning_coroutine_is_awaited(self):
        done = asyncio.Event()

        async def real():
            done.set()

        async with scheduler_ctx() as scheduler:
            task = Task(
                id_="t",
                func=lambda: real(),
                cron=None,
                next_run=timezone.now(),
            )
            await scheduler._execute_task(task)
            assert done.is_set()

    async def test_failed_reschedule_retires_the_task(self):
        class BrokenCron:
            next_run = timezone.now()

            def update_after(self, _: datetime.datetime):
                raise RuntimeError("no next run")

        logs: list[str] = []
        calls: list[int] = []
        async with scheduler_ctx(log_exception=logs.append) as scheduler:
            task = Task(
                id_="broken",
                func=lambda: calls.append(1),
                cron=cast(cronjob.CronExpr, BrokenCron()),
                next_run=timezone.now(),
            )
            scheduler._tasks["broken"] = task
            async with running(scheduler):
                await until(lambda: not scheduler.is_scheduled("broken"))
                for _ in range(20):
                    await asyncio.sleep(0.001)
            assert calls == [1]  # was: re-run in a tight loop
            assert any("Failed to reschedule" in log for log in logs)
