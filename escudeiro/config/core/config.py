import os
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any, TextIO, overload

from escudeiro.config.interface import MISSING, default_cast
from escudeiro.data import data
from escudeiro.exc import InvalidCast, MissingName
from escudeiro.lazyfields import lazyfield
from escudeiro.misc import (
    closing_quote_position,
    sentence,
    strip_comment,
)

from .mapping import DEFAULT_MAPPING


def clean_dotenv_value(value: str) -> str:
    """clean_dotenv_value removes leading and trailing whitespace and removes
    wrapping quotes from the value."""
    # Remove leading and trailing whitespace
    value = value.strip()

    # Check if value has quotes at the beginning and end
    has_quotes = (
        len(value) >= 2 and value[0] == value[-1] and value[0] in ['"', "'"]
    )

    # Remove quotes if they exist (only once)
    if has_quotes:
        value = value[1:-1]

    return value


@data
class Config:
    env_file: str | Path | None = None
    mapping: Mapping[str, str] = DEFAULT_MAPPING

    @lazyfield
    def file_values(self) -> dict[str, str]:
        return {}

    def __post_init__(self):
        if self.env_file and os.path.isfile(self.env_file):
            with open(self.env_file) as stream:
                self.file_values.update(self._read_file(stream))

    def _read_file(self, stream: TextIO) -> Iterable[tuple[str, str]]:
        for line in stream:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            name, value = line.split("=", maxsplit=1)
            quoted_until = closing_quote_position(value)
            value = strip_comment(value, quoted_until)
            yield name.strip(), clean_dotenv_value(value)

    def _cast(self, name: str, val: Any, cast: Callable) -> Any:
        try:
            val = cast(val)
        except MissingName:
            # avoid shadowing missing name errors from cast
            # to allow functions such as null_is_missing to work
            raise
        except Exception as e:
            raise InvalidCast(
                sentence(f"{name} received an invalid value {val}")
            ) from e
        else:
            return val

    def _get_val(
        self, name: str, default: Any | type[MISSING] = MISSING
    ) -> Any | type[MISSING]:
        value = self.mapping.get(name, MISSING)
        if value is MISSING:
            value = self.file_values.get(name, default)
        return value

    def get(
        self,
        name: str,
        cast: Callable = default_cast,
        default: Any | type[MISSING] = MISSING,
    ) -> Any:
        """
        Get the value of the specified environment variable, optionally casting it.

        Args:
            name (str): The name of the environment variable.
            cast (Callable, optional): The casting function. Defaults to _default_cast.
            default (Union[Any, type[MISSING]], optional):
                The default value to return if the variable is not found. Defaults to MISSING.

        Returns:
            Any: The value of the environment variable, casted if necessary.

        Raises:
            MissingName: If the environment variable is not found and no default value is provided.
            InvalidCast: If casting the value is unsuccessful.
        """
        val = self._get_val(name, default)
        if val is MISSING:
            raise MissingName(
                sentence(f"{name} not found and no default was given")
            )
        return self._cast(name, val, cast)

    @overload
    def __call__[T](
        self,
        name: str,
        cast: Callable[[Any], T] | type[T] = default_cast,
        default: type[MISSING] = MISSING,
    ) -> T: ...

    @overload
    def __call__[T](
        self,
        name: str,
        cast: Callable[[Any], T] | type[T] = default_cast,
        default: T = ...,
    ) -> T: ...

    def __call__[T](
        self,
        name: str,
        cast: Callable[[Any], T] | type[T] = default_cast,
        default: T | type[MISSING] = MISSING,
    ) -> T:
        """
        Get the value of the specified environment variable, optionally casting it using the callable syntax.

        Args:
            name (str): The name of the environment variable.
            cast (Union[Callable[[Any], T], type[T]], optional):
                The casting function or type. Defaults to _default_cast.
            default (Union[T, type[MISSING]], optional):
                The default value to return if the variable is not found. Defaults to MISSING.

        Returns:
            T: The value of the environment variable, casted if necessary.

        Raises:
            MissingName: If the environment variable is not found and no default value is provided.
            InvalidCast: If casting the value is unsuccessful.
        """
        return self.get(name, cast, default)
