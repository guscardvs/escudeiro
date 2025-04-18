"""Utilities for context managers, with type casting and async compatibility.

This module provides utilities for working with context managers, including
type casting and compatibility with asynchronous context managers.
"""

from contextlib import AbstractAsyncContextManager, AbstractContextManager
from dataclasses import dataclass
from types import TracebackType
from typing import Any, final, override

from typing_extensions import TypeIs


@final
@dataclass
class AsyncContextWrapper[T](AbstractAsyncContextManager):
    """Wraps a synchronous context manager to be used in an asynchronous context.

    This class allows using a synchronous context manager in an asynchronous
    context (e.g., using `async with`), by delegating context management
    operations to the wrapped synchronous context manager.

    Args:
        context: The synchronous context manager to wrap.

    Methods:
        __enter__: Enters the synchronous context.
        __exit__: Exits the synchronous context.
        __aenter__: Asynchronously enters the synchronous context.
        __aexit__: Asynchronously exits the synchronous context.
    """

    context: AbstractContextManager[T]

    def __enter__(self) -> T:
        return self.context.__enter__()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Any:
        return self.context.__exit__(exc_type, exc_value, traceback)

    @override
    async def __aenter__(self) -> T:
        return self.context.__enter__()

    @override
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Any:
        return self.context.__exit__(exc_type, exc_value, traceback)


def is_async_context[T](
    context: AbstractContextManager[T] | AbstractAsyncContextManager[T],
) -> TypeIs[AbstractAsyncContextManager[T]]:
    """Checks whether the given context manager is asynchronous.

    This function takes a lightweight approach by checking for the presence of
    `__aenter__` and `__aexit__` rather than using `isinstance`. This avoids
    unnecessary class hierarchy resolution while still providing a reliable check.

    Args:
        context: The context manager to check.

    Returns:
        `True` if the context manager is asynchronous, otherwise `False`.
    """
    return hasattr(context, "__aenter__") and hasattr(context, "__aexit__")
