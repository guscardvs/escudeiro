import linecache
import sys
from collections.abc import Mapping
from enum import Enum, auto
from typing import Any, Self, final

from .utils.functions import implements, stamp_func

EllipsisType = type(...)


class MethodType(str, Enum):
    INSTANCE = "instance"
    CLASS = "class"
    STATIC = "static"


class ArgumentType(Enum):
    POSITIONAL = auto()
    KEYWORD = auto()


@final
class MethodBuilder:
    def __init__(
        self, method_name: str, globs: dict[str, Any] | None = None
    ) -> None:
        self.method_name = method_name
        self.globs = globs or {}
        self.script_lines: list[str] = []
        self.annotations: dict[str, type | None] = {}
        self.funcargs: list[str] = []
        self.funckwargs: list[str] = []
        self.meth_type = MethodType.INSTANCE

    def add_scriptline(self, line: str) -> Self:
        self.script_lines.append(line)
        return self

    def add_scriptlines(self, *lines: str) -> Self:
        self.script_lines.extend(lines)
        return self

    def add_glob(self, name: str, value: Any) -> Self:
        self.globs[name] = value
        return self

    def merge_globs(self, globs: Mapping[str, Any]) -> Self:
        self.globs |= globs
        return self

    def add_annotation(self, name: str, value: Any) -> Self:
        self.annotations[name] = value
        return self

    def add_arg(self, name: str, type_: ArgumentType) -> Self:
        if type_ is ArgumentType.POSITIONAL:
            self.funcargs.append(name)
        else:
            self.funckwargs.append(name)
        return self

    def set_type(self, meth_type: MethodType) -> Self:
        self.meth_type = meth_type
        return self

    def prepare_method_name(self, cls: type):
        method_name = self.method_name
        if implements(cls, method_name):
            method_name = self.make_squire_name(method_name)
        return method_name

    @staticmethod
    def make_squire_name(method_name: str) -> str:
        return "_".join(("__squire", method_name.lstrip("_")))

    def build(self, cls: type) -> dict[str, Any]:
        method_name = self.prepare_method_name(cls)
        method_annotations, method_script = self.make_methodstr(method_name)
        if cls.__module__ in sys.modules:
            _ = self.merge_globs(sys.modules[cls.__module__].__dict__)
        func = _make_method(
            method_name,
            method_script,
            _generate_unique_filename(cls, method_name),
            self.globs,
        )
        func.__annotations__ = method_annotations
        stamp_func(func)
        return {method_name: func}

    def make_methodstr(self, method_name: str):
        method_header = f"def {method_name}("
        method_footer = "):"
        method_decorator = ""
        funcargs = self.funcargs.copy()

        if self.meth_type is MethodType.STATIC:
            method_decorator = "@staticmethod\n"
        elif self.meth_type is MethodType.CLASS:
            method_decorator = "@classmethod\n"
            funcargs.insert(0, "cls")
        else:
            funcargs.insert(0, "self")
        args = ", ".join(funcargs)
        if self.funckwargs:
            args += f"{', ' if args else ''}*, {', '.join(self.funckwargs)}"
        method_signature = method_header + args + method_footer

        method_body = (
            "\n    ".join(self.script_lines) if self.script_lines else "pass"
        )
        if method_decorator:
            method_signature = method_decorator + method_signature

        method_annotations = {
            name: value
            for name, value in self.annotations.items()
            if not isinstance(value, EllipsisType)  # pyright: ignore[reportUnnecessaryIsInstance]
        }
        method_script = f"{method_signature}\n    {method_body}"
        return method_annotations, method_script


def _make_method(
    name: str,
    script: str,
    filename: str,
    globs: dict[str, Any],
):
    """
    Create the method with the script given and return the method object.
    """
    locs: dict[str, Any] = {}

    count = 1
    base_filename = filename
    while True:
        linecache_tuple = (
            len(script),
            None,
            script.splitlines(True),
            filename,
        )
        old_val = linecache.cache.setdefault(filename, linecache_tuple)
        if old_val == linecache_tuple:
            break
        filename = f"{base_filename[:-1]}-{count}>"
        count += 1

    _compile_and_eval(script, globs, locs, filename)

    return locs[name]


def _compile_and_eval(
    script: str,
    globs: dict[str, Any],
    locs: Mapping[str, Any] | None = None,
    filename: str = "",
) -> None:
    """
    "Exec" the script with the given global (globs) and local (locs) variables.
    """
    bytecode = compile(script, filename, "exec")
    eval(bytecode, globs, locs)


def _generate_unique_filename(cls: type, func_name: str):
    """
    Create a "filename" suitable for a function being generated.
    """
    return (
        f"<squire {func_name} {cls.__module__}."
        f"{getattr(cls, '__qualname__', cls.__name__)}>"
    )
