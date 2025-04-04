import re
from collections.abc import Callable, Sequence
from typing import Any, ForwardRef, NoReturn, TypeVar, get_args, get_origin

from .typedef import UNINITIALIZED, DisassembledType, TypeNode


def disassemble_type(annotation: Any) -> DisassembledType:
    type_ = (
        annotation
        if not isinstance(annotation, str)
        else ForwardRef(annotation)
    )

    node = make_node(type_)
    _, type_vars = extract_typevar(node)
    return DisassembledType(
        type_,
        get_origin(type_),
        get_args(type_),
        type_vars,
        node,
    )


def make_node(annotation: type | ForwardRef) -> TypeNode:
    root_node = TypeNode(get_origin(annotation) or annotation)
    stack: list[tuple[TypeNode, Any]] = [(root_node, annotation)]

    while stack:
        current_node, current_annotation = stack.pop()
        if get_origin(current_annotation) is None:
            continue

        type_args = get_args(current_annotation)
        for arg in type_args:
            if _arg := get_origin(arg):
                orig = _arg
            elif isinstance(arg, str):
                orig = ForwardRef(arg)
            else:
                orig = arg
            arg_node = TypeNode(orig)
            current_node.args.append(arg_node)
            stack.append((arg_node, arg))

    return root_node


def extract_typevar(
    node: TypeNode,
) -> tuple[TypeNode, Sequence[TypeNode]]:
    """Receives a type and returns a tuple with the original type and what typevars are part of it and at what depth"""
    if isinstance(node.type_, ForwardRef):
        return node, ()

    stack = [node]
    type_vars: list[TypeNode] = []
    while stack:
        current = stack.pop()
        if isinstance(current.type_, TypeVar):
            type_vars.append(current)
        if current.args:
            for child in current.args:
                stack.append(child)

    return node, type_vars


def get_forwardrefs(
    node: TypeNode,
) -> tuple[TypeNode, Sequence[TypeNode]]:
    stack = [node]
    type_vars = []
    depth = 0
    while stack:
        current = stack.pop()
        if isinstance(current.type_, ForwardRef):
            type_vars.append(current)
        if current.args:
            depth += 1
            for child in current.args:
                stack.append(child)

    return node, type_vars


def rebuild_type(origin: type, args: Sequence[Any]) -> type:
    if not hasattr(origin, "__getitem__"):
        raise TypeError("Unable to support rebuild, type has no __getitem__")
    try:
        return origin.__getitem__(*args)
    except TypeError:
        return origin[args]  # pyright: ignore[reportIndexIssue]


def rebuild_type_from_depth(node: TypeNode) -> type:
    stack = [(node, None)]
    rebuilt_types = {}

    while stack:
        current_node, rebuilt_type = stack.pop()

        if isinstance(current_node.type_, ForwardRef) or not current_node.args:
            # If the current node is a ForwardRef, use it as the rebuilt type.
            # If the current node has no child nodes, it's a basic type.
            rebuilt_types[current_node] = current_node.type_
        elif all(child in rebuilt_types for child in current_node.args):
            # If all child nodes have been rebuilt, reconstruct the type.
            arg_types = [rebuilt_types[child] for child in current_node.args]
            rebuilt_types[current_node] = rebuild_type(
                current_node.type_, tuple(arg_types)
            )
        else:
            # Push the current node back onto the stack and push its children.
            stack.append((current_node, rebuilt_type))
            for child in current_node.args:
                if child not in rebuilt_types:
                    stack.append((child, None))

    return rebuilt_types[node]


def frozen_setattr(self: object, name: str, value: Any):
    if getattr(self, name, UNINITIALIZED) is UNINITIALIZED:
        return object.__setattr__(self, name, value)
    raise AttributeError(
        f"Class {type(self)} is frozen, and attribute {name} cannot be set"
    )


def frozen_delattr(self: object, name: str) -> NoReturn:
    raise AttributeError(
        f"Class {type(self)} is frozen, and attribute {name} cannot be deleted"
    )


def frozen[T](cls: type[T]) -> type[T]:
    cls.__setattr__ = frozen_setattr
    cls.__delattr__ = frozen_delattr
    return cls


def indent(string: str, *, skip_line: bool = False) -> str:
    returnstr = f"    {string}"
    if skip_line:
        returnstr = "\n" + returnstr
    return returnstr


_sentinel = object()


def stamp_func(item: Callable | classmethod | staticmethod):
    to_stamp = item
    if isinstance(item, classmethod | staticmethod):
        to_stamp = item.__func__
    object.__setattr__(to_stamp, "__squire_func__", True)


def implements(cls: type, name: str):
    attr = getattr(cls, name, _sentinel)
    if attr is _sentinel:
        return False

    if hasattr(attr, "__squire_func__"):
        return False

    if func := getattr(attr, "__func__", None):
        if hasattr(func, "__squire_func__"):
            return False
    return all(
        getattr(base_cls, name, None) is not attr for base_cls in cls.mro()[1:]
    )


_dunder_regex = re.compile("__[a-zA-Z][a-zA-Z0-9]*__")


def is_dunder(string: str) -> bool:
    return _dunder_regex.match(string) is not None


def remove_left_underscores(string: str) -> str:
    if is_dunder(string):
        return string
    return string.lstrip("_")
