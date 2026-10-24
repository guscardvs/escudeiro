import sys
from collections.abc import Callable
from types import ModuleType
from typing import Any, Generic, TypeVar

import pytest

from escudeiro.data import (
    asdict,
    data,
    fromdict,
    get_fields,
    resolve_typevars,
    update_refs,
)
from escudeiro.data.helpers import update_ref
from escudeiro.data.utils.functions import get_class_annotations

LoadModule = Callable[[str], ModuleType]

NODE_SOURCE = """
    from typing import Optional

    from escudeiro.data import data, field

    @data
    class Node:
        value: int
        next: Optional["Node"] = None
        children: list["Node"] = field(default_factory=list)
"""

NODE_DATA: dict[str, Any] = {
    "value": 1,
    "next": {"value": 2, "next": {"value": 3}},
    "children": [{"value": 4}],
}


def test_forward_refs_are_raw_until_resolved(load_module: LoadModule):
    node = load_module(NODE_SOURCE).Node

    assert fromdict(node, NODE_DATA).next == {"value": 2, "next": {"value": 3}}


def test_update_ref_resolves_self_referencing_fields(load_module: LoadModule):
    node = load_module(NODE_SOURCE).Node

    update_ref(node)
    result = fromdict(node, NODE_DATA)

    assert isinstance(result.next, node)
    assert isinstance(result.next.next, node)
    assert result.next.next.value == 3
    assert result.children == [node(4)]
    assert "ForwardRef" not in repr(get_fields(node)["next"].declared_type)
    assert asdict(result) == {
        "value": 1,
        "next": {
            "value": 2,
            "next": {"value": 3, "next": None, "children": []},
            "children": [],
        },
        "children": [{"value": 4, "next": None, "children": []}],
    }


def test_update_refs_with_explicit_klasses(load_module: LoadModule):
    node = load_module(NODE_SOURCE).Node

    update_refs(klasses=[node])

    assert isinstance(fromdict(node, NODE_DATA).next, node)


def test_update_refs_discovers_the_calling_module(load_module: LoadModule):
    module = load_module(
        NODE_SOURCE
        + """
    from escudeiro.data import update_refs

    update_refs()
    """
    )

    assert isinstance(fromdict(module.Node, NODE_DATA).next, module.Node)


def test_update_refs_by_module_name(load_module: LoadModule):
    module = load_module(NODE_SOURCE)

    update_refs(module=module.__name__)

    assert isinstance(fromdict(module.Node, NODE_DATA).next, module.Node)


def test_update_ref_is_a_noop_without_forward_refs():
    @data
    class Plain:
        x: int

    update_ref(Plain)

    assert fromdict(Plain, {"x": 1}) == Plain(1)


def test_update_ref_reports_unresolvable_names(load_module: LoadModule):
    module = load_module(
        """
        from escudeiro.data import data

        @data
        class Broken:
            ref: "DoesNotExist"
        """
    )

    with pytest.raises(NameError):
        update_ref(module.Broken)


def test_get_class_annotations_reads_own_annotations():
    class Base:
        a: int

    class Child(Base):
        b: str

    assert get_class_annotations(Base) == {"a": int}
    assert get_class_annotations(Child) == {"b": str}


@pytest.mark.skipif(
    sys.version_info < (3, 14),
    reason="annotations are only evaluated lazily from Python 3.14",
)
def test_deferred_annotations_allow_self_reference(load_module: LoadModule):
    # on 3.14 `Optional[Node]` is not evaluated while the class body runs
    module = load_module(
        """
        from typing import Optional

        from escudeiro.data import data

        @data
        class Node:
            value: int
            next: Optional[Node] = None
        """
    )
    node = module.Node

    assert node(1, node(2)).next == node(2)
    update_ref(node)
    result = fromdict(node, {"value": 1, "next": {"value": 2}})
    assert result == node(1, node(2))


@pytest.mark.skipif(
    sys.version_info < (3, 14),
    reason="get_class_annotations only returns ForwardRefs on 3.14",
)
def test_get_class_annotations_forwardref_format_on_314():
    class Node:
        next: "Node | Missing"  # pyright: ignore[reportUndefinedVariable]  # noqa: F821

    assert "next" in get_class_annotations(Node)


@pytest.mark.skipif(
    sys.version_info >= (3, 14),
    reason="unquoted self references only fail before 3.14",
)
def test_unquoted_self_reference_still_needs_quotes_before_314():
    with pytest.raises(NameError):
        exec(
            "from typing import Optional\n"
            "from escudeiro.data import data\n"
            "@data\n"
            "class Node:\n"
            "    next: Optional[Node] = None\n",
            {},
        )


def test_resolve_typevars_replaces_the_type_variables():
    t = TypeVar("t")

    @data
    class Box(Generic[t]):
        item: t

    resolved = resolve_typevars((t, int))(Box)

    assert fromdict(resolved, {"item": "3"}).item == 3
    assert get_fields(resolved)["item"].declared_type is int
