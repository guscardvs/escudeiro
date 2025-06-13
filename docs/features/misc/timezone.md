# Timezone Utilities

The `timezone` module provides simple, safe utilities for working with timezones in Python, including a `TimeZone` helper class and convenience functions for retrieving the current date and time with timezone awareness.

---

## Why?

Working with timezones in Python can be error-prone, especially when mixing naive and aware datetime objects. The `timezone` module offers a minimal, explicit API for timezone-aware operations, ensuring that all returned values are properly localized and that timezone changes are controlled.

Consider the following:

```python
import datetime

now = datetime.datetime.now(datetime.UTC)
today = now.date()
```

This works, but managing timezones and ensuring consistency can be tricky. The `timezone` module provides a `TimeZone` class that encapsulates timezone logic and prevents accidental misuse.

---

## Features

- **Timezone-aware `now()` and `today()`** helpers
- **Explicit timezone management** via the `TimeZone` class
- **Prevents accidental timezone changes** after first use
- **Simple, type-safe API**

---

## Usage

### Getting the Current Time and Date

```python
from escudeiro.misc.timezone import now, today

print(now())         # Current UTC datetime
print(today())       # Current UTC date
```

You can specify a custom timezone:

```python
import datetime
from escudeiro.misc.timezone import now

print(now(datetime.timezone(datetime.timedelta(hours=-3))))  # e.g., UTC-3
```

### Using the `TimeZone` Class

```python
import datetime
from escudeiro.misc.timezone import TimeZone

tz = TimeZone(datetime.timezone.utc)
print(tz.now())    # Current UTC datetime
print(tz.today())  # Current UTC date

# Set a custom timezone before first use
tz = TimeZone(datetime.timezone.utc)
tz.set_tz(datetime.timezone(datetime.timedelta(hours=2)))
print(tz.now())    # Current UTC+2 datetime

# Attempting to change timezone after first use raises an error
tz = TimeZone(datetime.timezone.utc)
_ = tz.now()
tz.set_tz(datetime.timezone(datetime.timedelta(hours=2)))  # Raises ValueError
```

---

## API Reference

### `TimeZone` class

```python
class TimeZone:
    def __init__(self, tz: datetime.tzinfo) -> None
    def now(self) -> datetime.datetime
    def today(self) -> datetime.date
    def set_tz(self, tz: datetime.tzinfo) -> None
```

- **Description:** Encapsulates a timezone and provides methods for retrieving the current time and date.
- **Methods:**
  - `now()`: Returns the current datetime in the configured timezone.
  - `today()`: Returns the current date in the configured timezone.
  - `set_tz(tz)`: Sets the timezone. Can only be called before the first retrieval.

### Functions

#### `now`

```python
def now(tz: datetime.tzinfo = datetime.UTC) -> datetime.datetime
```
- **Description:** Returns the current datetime in the specified timezone (default: UTC).

#### `today`

```python
def today(tz: datetime.tzinfo = datetime.UTC) -> datetime.date
```
- **Description:** Returns the current date in the specified timezone (default: UTC).

---

## Notes

- The default timezone is UTC.
- Once a `TimeZone` instance is used to retrieve the time, its timezone cannot be changed.
- Use the module-level `now()` and `today()` for quick access, or `TimeZone` for explicit control.

---

## See Also

- [datetime — Basic date and time types](https://docs.python.org/3/library/datetime.html)
- [PEP 495 — Local Time Disambiguation](https://peps.python.org/pep-0495/)
- [Python time zone handling](https://docs.python.org/3/library/datetime.html#aware-and-naive-objects)