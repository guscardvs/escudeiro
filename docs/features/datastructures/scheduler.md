# Task Scheduler

The `TaskScheduler` module provides an asynchronous, cron-capable task scheduling system for Python. It supports both recurring (cron) and one-time tasks, with thread-safe execution, task management, and flexible logging. This is ideal for background jobs, periodic maintenance, or any workflow requiring scheduled execution.

---

## Why?

Scheduling background tasks is a common requirement, but implementing a robust, thread-safe, and flexible scheduler is non-trivial. The `TaskScheduler` module abstracts away the complexity of:

- Managing task state and concurrency
- Supporting both synchronous and asynchronous functions
- Handling cron expressions and time zones
- Providing hooks for logging and task removal

Example of scheduling a simple task:

```python
from escudeiro.ds.scheduler import TaskScheduler, CronInfo
import asyncio

async def my_job():
    print("Running my job!")

scheduler = TaskScheduler()
cron = CronInfo(cronexpr="*/5 * * * *")  # Every 5 minutes
scheduler.schedule_task(my_job, cron_expr=cron, run_at=None)

asyncio.run(scheduler.start())
```

---

## Features

- **Asynchronous scheduling loop** with support for both sync and async tasks
- **Cron-based and one-time scheduling**
- **Per-task locking** for safe concurrent execution
- **Automatic rescheduling and removal**
- **Customizable logging and callbacks**
- **Task querying and management API**

---

## Usage

### Scheduling a Recurring Task

```python
from escudeiro.ds.scheduler import TaskScheduler, CronInfo

def my_task():
    print("Hello from scheduled task!")

scheduler = TaskScheduler()
cron = CronInfo(cronexpr="0 * * * *")  # Every hour
scheduler.schedule_task(my_task, cron_expr=cron, run_at=None)
```

### Scheduling a One-Time Task

```python
from escudeiro.ds.scheduler import TaskScheduler
from datetime import datetime, timedelta

def one_time():
    print("This runs once!")

scheduler = TaskScheduler()
run_at = datetime.now() + timedelta(minutes=10)
scheduler.schedule_task(one_time, cron_expr=None, run_at=run_at)
```

### Starting and Stopping the Scheduler

```python
import asyncio

async def main():
    scheduler = TaskScheduler()
    # ... schedule tasks ...
    await scheduler.start()  # Runs until stopped

# To stop:
# await scheduler.stop()
```

### Removing Tasks

```python
async def on_remove(task_id):
    print(f"Task {task_id} removed.")

await scheduler.remove_task(task_id, callback=on_remove)
```

---

## API Reference

### Classes

#### `Task`

Represents a scheduled task.

- **Attributes:**
  - `id_`: Unique task ID
  - `func`: Callable (sync or async)
  - `cron`: Cron expression (or None)
  - `next_run`: Next scheduled run time
  - `name`: Optional task name
  - `is_running`: Execution state
  - `remove_callback`: Async callback on removal

#### `CronInfo`

Container for cron scheduling info.

- **Attributes:**
  - `cronexpr`: Cron expression string
  - `timezone`: Timezone (defaults to local)

#### `TaskScheduler`

Main scheduler class.

- **Attributes:**
  - `default_sleep_interval`: Sleep time when idle
  - `log_info`, `log_warning`, `log_exception`: Logging callbacks

- **Methods:**
  - `schedule_task(func, cron_expr, run_at, ...)`: Schedule a new task
  - `is_scheduled(task_id)`: Check if task exists
  - `get_task(task_id)`: Retrieve a task
  - `task_ids()`: List all task IDs
  - `remove_task(task_id, callback)`: Remove a task by ID
  - `remove_by_name(name, callback)`: Remove task(s) by name
  - `start()`: Start the scheduler loop
  - `stop()`: Stop the scheduler
  - `aclose()`: Async cleanup (alias for `stop()`)

---

## Notes

- Both synchronous and asynchronous functions are supported as tasks.
- Use `CronInfo` for recurring tasks, or `run_at` for one-time tasks (not both).
- The scheduler is designed for use in asyncio-based applications.
- Logging and removal callbacks are fully customizable.

---

## See Also

- [asyncio](https://docs.python.org/3/library/asyncio.html)
- [cron expressions](https://en.wikipedia.org/wiki/Cron)
- [Python datetime](https://docs.python.org/3/library/datetime.html)