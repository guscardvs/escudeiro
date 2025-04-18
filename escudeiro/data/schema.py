from collections.abc import Sequence
from typing import Protocol, final, override

from escudeiro.misc import to_camel

template = (
    '"title": "{title}"',
    '"type": "{type}"',
)


class HasStr(Protocol):
    @override
    def __str__(self) -> str: ...


class HasToString(HasStr, Protocol):
    def to_string(self) -> str: ...


type PropsType = dict[str, HasStr] | HasStr


def str_cast(string: str):
    return f'"{string}"'


@final
class DictSchema:
    __slots__ = ("type_", "extras")

    def __init__(self, type_: str, **extras: PropsType) -> None:
        self.type_ = type_
        self.extras = extras

    @override
    def __str__(self) -> str:
        return self.to_string()

    def to_string(self) -> str:
        return (
            "{"
            + ",".join(
                item
                for item in (f'"type": "{self.type_}"', self.build_extras())
                if item
            )
            + "}"
        )

    def build_extras(self) -> str:
        if not self.extras:
            return ""
        lines = [
            f'"{to_camel(name)}":'
            + (
                " {"
                + ", ".join(
                    f'"{to_camel(key)}": {value!s}'
                    for key, value in props.items()
                )
                + "}"
                if isinstance(props, dict)
                else str(props)
            )
            for name, props in self.extras.items()
        ]
        return ", ".join(lines)


@final
class ListSchema:
    __slots__ = (
        "type_",
        "items",
    )

    def __init__(self, type_: str, *items: HasStr) -> None:
        self.type_ = type_
        self.items = items

    @override
    def __str__(self):
        return self.to_string()

    def to_string(self):
        items = ", ".join(str(item) for item in self.items)
        return f'{{"{self.type_}": [{items}]}}'


@final
class Items:
    __slots__ = ("items",)

    def __init__(self, *items: HasStr) -> None:
        self.items = items

    @override
    def __str__(self):
        return self.to_string()

    def to_string(self):
        items = ", ".join(str(item) for item in self.items)
        return f"[{items}]"


@final
class RefSchema:
    __slots__ = ("title",)

    def __init__(self, title: str) -> None:
        self.title = title

    def to_string(self) -> str:
        return f'{{"$ref": "#/components/schemas/{self.title}"}}'


@final
class Schema:
    __slots__ = ("title", "type_", "required", "extras", "nullable")

    def __init__(
        self,
        title: str,
        type_: str,
        required: Sequence[str] = (),
        nullable: bool = False,
        **extras: PropsType,
    ) -> None:
        self.title = title
        self.type_ = type_
        self.required = required
        self.nullable = nullable
        self.extras = extras

    @override
    def __str__(self):
        return self.to_string()

    def to_string(self) -> str:
        extras = self.build_extras()
        required = self.build_required()
        return (
            "{"
            + ", ".join(
                item
                for item in (
                    f'"title": "{self.title}"',
                    f'"type": "{self.type_}"',
                    required,
                    extras,
                    f'"nullable": {str(self.nullable)}',
                )
                if item
            )
            + "}"
        )

    def build_extras(self) -> str:
        if not self.extras:
            return ""
        lines = []
        for name, props in self.extras.items():
            props_str = self._make_prop_str(props)
            lines.append(f'"{to_camel(name)}": {props_str}')
        return ", ".join(lines)

    def _make_prop_str(self, props: PropsType):
        if not isinstance(props, dict):
            return str(props)
        props_str = ",".join(
            f'"{to_camel(key)}": {value!s}' for key, value in props.items()
        )
        return f"{{{props_str}}}"

    def build_required(self) -> str:
        return (
            f""""required": [{",".join(f'"{val}"' for val in self.required)}]"""
            if self.required
            else ""
        )
