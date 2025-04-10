from typing import overload

from escudeiro.context.atomic_ import AsyncAtomicContext, AtomicContext
from escudeiro.context.bound import AsyncBoundContext, BoundContext
from escudeiro.context.context import AsyncContext, Context


@overload
def atomic[T](context: Context[T], bound: bool = True) -> AtomicContext[T]:
    """
    Create an atomic context or a bound context based on the given context.

    Args:
        context (Context[T]): The base context to be wrapped.
        bound (bool, optional): Whether to create a bound context. Defaults to True.

    Returns:
        AtomicContext[T]: The created atomic or bound context.

    Raises:
        ValueError: If the provider received is not compliant with the atomic adapter interface.
    """
    ...


@overload
def atomic[T](
    context: AsyncContext[T], bound: bool = True
) -> AsyncAtomicContext[T]:
    """
    Create an asynchronous atomic context or a bound context based on the given context.

    Args:
        context (AsyncContext[T]): The base asynchronous context to be wrapped.
        bound (bool, optional): Whether to create a bound context. Defaults to True.

    Returns:
        AsyncAtomicContext[T]: The created asynchronous atomic or bound context.

    Raises:
        ValueError: If the provider received is not compliant with the atomic adapter interface.
    """
    ...


def atomic[T](
    context: Context[T] | AsyncContext[T], bound: bool = True
) -> Context[T] | AsyncContext[T]:
    """
    Create an atomic context or a bound context based on the given context.

    Args:
        context (Union[Context[T], AsyncContext[T]]): The base context to be wrapped.
        bound (bool, optional): Whether to create a bound context. Defaults to True.

    Returns:
        Union[Context[T], AsyncContext[T]]: The created atomic or bound context.

    Raises:
        ValueError: If the provider received is not compliant with the atomic adapter interface.
    """
    required_methods = {"begin", "commit", "rollback", "in_atomic"}
    adapter_methods = set(dir(context.adapter))

    if not required_methods.issubset(adapter_methods):
        raise ValueError(
            f"The adapter does not have required methods {required_methods}"
        )

    if bound:
        return (
            BoundContext(context.adapter, context)  # pyright: ignore[reportArgumentType]
            if isinstance(context, Context)
            else AsyncBoundContext(context.adapter, context)  # pyright:ignore[reportArgumentType]
        )

    return (
        AtomicContext(context.adapter)  # pyright: ignore[reportArgumentType]
        if isinstance(context, Context)
        else AsyncAtomicContext(context.adapter)  # pyright: ignore[reportArgumentType]
    )
