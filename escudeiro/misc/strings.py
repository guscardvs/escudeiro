"""Utilities for working with strings.

This module provides functions for common string conversions, wrapping and parsing.
"""

from __future__ import annotations

import shlex
from collections.abc import Callable, Collection, Mapping
from typing import TYPE_CHECKING, Any, cast

from escudeiro.escudeiro_pyrs import strings


def to_snake(value: str) -> str:
    """Converts a string to snake_case."""
    return strings.to_snake(value)


def to_camel(value: str) -> str:
    """Converts a string to camelCase."""
    return strings.to_camel(value)


def to_pascal(value: str) -> str:
    """Converts a string to PascalCase."""
    return strings.to_pascal(value)


def to_kebab(value: str, remove_trailing_underscores: bool = True) -> str:
    """Converts a string to kebab-case."""
    return strings.to_kebab(value, remove_trailing_underscores)


def sentence(value: str) -> str:
    """Formats a string as a sentence, ensuring proper capitalization and punctuation."""
    return strings.sentence(value)


def exclamation(value: str) -> str:
    """Formats a string as an exclamation."""
    return strings.exclamation(value)


def question(value: str) -> str:
    """Formats a string as a question."""
    return strings.question(value)


def dquote(value: str) -> str:
    """Wraps a string in double quotes."""
    return strings.dquote(value)


def squote(value: str) -> str:
    """Wraps a string in single quotes."""
    return strings.squote(value)


def replace_all(value: str, replacements: Mapping[str, str]) -> str:
    """Replaces multiple substrings in a string based on a mapping of replacements."""
    return strings.replace_all(value, replacements)


def replace_by(
    value: str, replacement: str, to_replace: Collection[str]
) -> str:
    """Replaces all occurrences of a set of substrings with a given replacement string."""
    return strings.replace_by(value, replacement, to_replace)


def make_lex_separator[OuterCastT: list | tuple | set | frozenset](
    outer_cast: type[OuterCastT], cast: type = str
) -> Callable[[str], OuterCastT]:
    """
    Creates a function that splits a string using shell-like syntax and casts the result.

    Args:
        outer_cast: The type to cast the output collection to (e.g., list, tuple, set, frozenset).
        cast: The type to cast each individual element to (default is str).

    Returns:
        A callable that takes a string and returns a collection of the specified type with cast elements.
    """

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
    """
    Wraps a string with the specified character.

    Args:
        value: The string to wrap.
        wrapper_char: The character to wrap the string with.

    Returns:
        A new string wrapped with the specified character.
    """
    return f"{wrapper_char}{value}{wrapper_char}"


def convert[AnyDict: dict[str, Any]](
    value: AnyDict, formatter: Callable[[str], str]
) -> AnyDict:
    """
    Applies a formatter function to the keys of a dictionary.

    Args:
        value: The dictionary whose keys will be formatted.
        formatter: A function that takes a string key and returns a formatted string.

    Returns:
        A new dictionary with formatted keys.
    """
    return cast(
        AnyDict,
        {formatter(key): anyval for key, anyval in value.items()},
    )


def convert_all[AnyDict: dict[str, Any]](
    value: AnyDict, formatter: Callable[[str], str]
) -> AnyDict:
    """
    Recursively applies a formatter function to all keys in a nested dictionary.

    Args:
        value: The nested dictionary whose keys will be formatted.
        formatter: A function that takes a string key and returns a formatted string.

    Returns:
        A new dictionary with all keys formatted recursively.
    """
    output = {}
    stack: list[tuple[dict[str, Any], dict[str, Any]]] = [(value, output)]

    while stack:
        current, target = stack.pop()

        for key, anyval in current.items():
            formatted_key = formatter(key)
            if isinstance(anyval, dict):
                if TYPE_CHECKING:
                    anyval = cast(AnyDict, anyval)
                target[formatted_key] = {}
                stack.append((anyval, target[formatted_key]))
            else:
                target[formatted_key] = anyval

    return cast(AnyDict, output)


def closing_quote_position(value: str) -> int | None:
    """If the text is wrapped by quotes at least partially
    return the position of the closing quote else return None."""
    quotes = ("'", '"')
    if not value or value[0] not in quotes:
        # string does not start with a quote
        return None
    quote_char = value[0]
    closing_quote = next(
        (
            position
            for position, token in enumerate(value[1:], 1)
            if token == quote_char and value[position - 1] != "\\"
        ),
        None,
    )
    return closing_quote


def strip_comment(value: str, closing_quote: int | None = None) -> str:
    """
    Remove comments from the string. A comment starts with a '#'
    character preceded by a space or a tab.

    Args:
        value (str): The input string which might contain a comment.
        closing_quote (int | None): Position of the closing quote, if any.
    Returns:
        str: The string without the comment.
    """

    if "#" not in value:
        return value
    closing_quote = closing_quote or 0
    if closing_quote == len(value) - 1:
        # String is fully quoted
        return value
    comment_starts = next(
        (
            position
            for position, token in enumerate(
                value[closing_quote:], closing_quote
            )
            if token == "#"
            and (position == 0 or value[position - 1] in (" ", "\t"))
            and (
                position == len(value) - 1 or value[position + 1] in (" ", "\t")
            )
        ),
        None,
    )
    if comment_starts is None:
        return value
    return value[:comment_starts].rstrip()


def as_boolean(string: str) -> bool | None:
    """
    Converts a string to its boolean equivalent.

    Args:
        string (str): The string to check if it represents a boolean value.

    Returns:
        bool | None: Returns True for "true", "1", "yes"; False for "false", "0", "no"; None for empty string.
        If the string does not match any of these, it returns None.
    """
    boolean_map = {
        "true": True,
        "1": True,
        "yes": True,
        "false": False,
        "0": False,
        "no": False,
        "": False,
    }
    return boolean_map.get(string.lower())


def is_none(string: str) -> bool:
    """
    Checks if a string is None or empty.

    Args:
        string (str): The string to check.

    Returns:
        bool: True if the string is None or empty, False otherwise.
    """
    null_set = frozenset({"null", "none", "nil", ""})
    return string.lower() in null_set
