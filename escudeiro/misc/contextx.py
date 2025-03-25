from contextlib import AbstractAsyncContextManager, AbstractContextManager
from types import TracebackType
from typing import Any, final, override

from typing_extensions import TypeIs


@final
class AsyncContextWrapper[T](AbstractAsyncContextManager):
    def __init__(self, context: AbstractContextManager[T]):
        self.context = context

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
    return hasattr(context, "__aenter__") and hasattr(context, "__aexit__")
