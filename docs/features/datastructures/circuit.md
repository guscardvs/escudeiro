# Circuit Breaker

The `CircuitBreaker` class provides a robust implementation of the circuit breaker pattern for asynchronous Python code. It helps prevent repeated failures by temporarily blocking execution after an error, allowing systems to recover gracefully from transient faults.

---

## Why?

Suppose you have an async function that calls an unreliable external service. If the service fails, you don't want to keep retrying immediately and overwhelm it or your own system. Instead, you want to "freeze" further attempts for a while after a failure:

```python
async def fetch_data():
    # May raise exceptions
    ...
```

Without a circuit breaker, repeated failures can cause cascading issues. With `CircuitBreaker`, you can automatically pause execution after a failure:

```python
from escudeiro.ds.circuit import CircuitBreaker

breaker = CircuitBreaker()

async def safe_fetch():
    return await breaker.execute(fetch_data)
```

---

## Features

- **Async circuit breaker** for coroutine-based code
- **Automatic freezing** after failures, with configurable delay
- **Customizable error handling** via callback
- **Decorator support** for easy integration
- **Thread-safe** via internal asyncio lock

---

## Usage

### Basic Usage

```python
from escudeiro.ds.circuit import CircuitBreaker

breaker = CircuitBreaker()

async def unreliable():
    # Some async operation that may fail
    ...

result = await breaker.execute(unreliable)
```

### Using as a Decorator

```python
from escudeiro.ds.circuit import CircuitBreaker, with_circuit_breaker

breaker = CircuitBreaker()

@with_circuit_breaker(breaker)
async def my_async_func():
    # ...
    pass

await my_async_func()
```

### Customizing Freeze Duration and Error Handling

```python
import asyncio

def on_error(exc):
    print(f"Error occurred: {exc}")

breaker = CircuitBreaker(
    freeze_function=lambda: asyncio.sleep(10),  # Freeze for 10 seconds
    on_error=on_error,
)
```

---

## API Reference

### `CircuitBreaker`

```python
class CircuitBreaker:
    freeze_function: Callable[[], Coroutine]
    on_error: Callable[[Exception], None]
    is_frozen: bool

    async def execute(
        self,
        func: Callable[..., Coroutine],
        *args,
        **kwargs
    ) -> Any
```

- **freeze_function**: Coroutine called to determine freeze duration (default: `asyncio.sleep(5)`).
- **on_error**: Callback invoked with the exception when an error occurs.
- **is_frozen**: Property indicating if the breaker is currently frozen.
- **execute**: Runs the given async function with circuit breaker logic.

### `with_circuit_breaker`

```python
def with_circuit_breaker(
    circuit_breaker: CircuitBreaker
) -> Callable[[Callable[..., Coroutine]], Callable[..., Coroutine]]
```

- **Description:** Decorator to wrap async functions with circuit breaker logic.

---

## Notes

- When the circuit is "frozen", all calls wait until the freeze period ends.
- The breaker is per-instance; use a separate `CircuitBreaker` for each independent resource.
- The default freeze duration is 5 seconds; customize via `freeze_function`.

---

## See Also

- [Circuit breaker pattern (Wikipedia)](https://en.wikipedia.org/wiki/Circuit_breaker_design_pattern)
- [asyncio](https://docs.python.org/3/library/asyncio.html)
- [Python decorators](https://docs.python.org/3/glossary.html#term-decorator)