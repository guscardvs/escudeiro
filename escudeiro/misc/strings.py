from __future__ import annotations

import shlex
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

from escudeiro_pyrs import strings

to_snake = strings.to_snake
to_camel = strings.to_camel
to_pascal = strings.to_pascal
to_kebab = strings.to_kebab
sentence = strings.sentence
exclamation = strings.exclamation
question = strings.question
dquote = strings.dquote
squote = strings.squote


def make_lex_separator[OuterCastT: list | tuple | set | frozenset](  # pyright: ignore[reportMissingTypeArgument]
    outer_cast: type[OuterCastT], cast: type = str
) -> Callable[[str], OuterCastT]:
    def wrapper(value: str) -> OuterCastT:
        lex = shlex.shlex(value, posix=True)
        lex.whitespace = ","
        lex.whitespace_split = True
        return outer_cast(cast(item.strip()) for item in lex)

    return wrapper


comma_separator: Callable[[str], tuple[str, ...]] = make_lex_separator(
    tuple, str
)


def wrap(value: str, wrapper_char: str) -> str:
    return f"{wrapper_char}{value}{wrapper_char}"


def convert[AnyDict: dict[str, Any]](
    value: AnyDict, formatter: Callable[[str], str]
) -> AnyDict:
    return cast(
        AnyDict,
        {formatter(key): anyval for key, anyval in value.items()},  # pyright: ignore[reportAny]
    )


def convert_all[AnyDict: dict[str, Any]](
    value: AnyDict, formatter: Callable[[str], str]
) -> AnyDict:
    output = {}
    stack: list[tuple[dict[str, Any], dict[str, Any]]] = [(value, output)]  # pyright: ignore[reportExplicitAny]

    while stack:
        current, target = stack.pop()

        for key, anyval in current.items():  # pyright: ignore[reportAny]
            formatted_key = formatter(key)
            if isinstance(anyval, dict):
                if TYPE_CHECKING:
                    anyval = cast(AnyDict, anyval)
                target[formatted_key] = {}
                stack.append((anyval, target[formatted_key]))
            else:
                target[formatted_key] = anyval

    return cast(AnyDict, output)


__all__ = [
    "to_snake",
    "to_camel",
    "to_pascal",
    "to_kebab",
    "comma_separator",
    "sentence",
    "exclamation",
    "question",
    "make_lex_separator",
    "wrap",
    "convert",
    "convert_all",
    "dquote",
    "squote",
]
