from collections import OrderedDict
from collections.abc import Sequence
from enum import Enum
from typing import Any, override

from escudeiro.misc.iterx import next_or
from escudeiro.misc.lazy import lazymethod
from escudeiro.misc.strings import to_camel, to_kebab, to_pascal, to_snake


class StrEnum(str, Enum):
    """A base class for string-based enums with enhanced functionality for aliases.

    This class provides a custom `_missing_` method to search for enum members based on aliases
    and includes a method for generating various string aliases for enum values (camel, pascal, kebab, etc.)
    """

    @classmethod
    @override
    def _missing_(cls, value: object) -> Any:
        return next_or(item for item in cls if value in item.get_aliases())

    @lazymethod
    def get_aliases(self) -> Sequence[str]:
        return tuple(
            OrderedDict.fromkeys(
                (
                    self.value,
                    self.name,
                    self.name.upper(),
                    self.name.lower(),
                    to_camel(self.name),
                    to_pascal(self.name),
                    to_kebab(self.name),
                )
            )
        )


class ValueEnum(StrEnum):
    """A subclass of `StrEnum` where the string representation is based on the enum's value.

    This class overrides the `__str__` method to return the value of the enum member instead of its name.
    """

    @override
    def __str__(self) -> str:
        return self.value


class NameEnum(StrEnum):
    """A subclass of `StrEnum` where the string representation is based on the enum's name.

    This class overrides the `__str__` method to return the name of the enum member instead of its value.
    """

    @override
    def __str__(self) -> str:
        return self.name


class SnakeEnum(StrEnum):
    """A subclass of `StrEnum` that automatically generates enum values in snake_case.

    This class overrides the `_generate_next_value_` method to automatically generate a
    snake_case value based on the enum name.
    """

    @staticmethod
    @override
    def _generate_next_value_(
        name: str, start: int, count: int, last_values: list[Any]
    ) -> Any:
        return to_snake(name)


class CamelEnum(StrEnum):
    """A subclass of `StrEnum` that automatically generates enum values in camelCase.

    This class overrides the `_generate_next_value_` method to automatically generate a
    camelCase value based on the enum name.
    """

    @staticmethod
    @override
    def _generate_next_value_(
        name: str, start: int, count: int, last_values: list[Any]
    ) -> Any:
        return to_camel(name)


class PascalEnum(StrEnum):
    """A subclass of `StrEnum` that automatically generates enum values in PascalCase.

    This class overrides the `_generate_next_value_` method to automatically generate a
    PascalCase value based on the enum name.
    """

    @staticmethod
    @override
    def _generate_next_value_(
        name: str, start: int, count: int, last_values: list[Any]
    ) -> Any:
        return to_pascal(name)


class KebabEnum(StrEnum):
    """A subclass of `StrEnum` that automatically generates enum values in kebab-case.

    This class overrides the `_generate_next_value_` method to automatically generate a
    kebab-case value based on the enum name.
    """

    @staticmethod
    @override
    def _generate_next_value_(
        name: str, start: int, count: int, last_values: list[Any]
    ) -> Any:
        return to_kebab(name)


# If combining many of those utilities, inherit the NameEnum or ValueEnum first,
# to avoid overriding the automatic name generation with Enum's default one.
