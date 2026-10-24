"""Regression tests for the Rust FsNode/FsTree (src/filetree.rs)."""

import pytest

from escudeiro.escudeiro_pyrs import filetree

BAD_NAMES = ["../escaped.txt", "a/b", "", ".", "..", "a\0b", "a\\b"]


def test_cycles_are_rejected():
    parent = filetree.FsNode("parent")
    child = filetree.FsNode("child")
    parent.add_child(child)

    with pytest.raises(ValueError):
        parent.add_child(parent)
    with pytest.raises(ValueError):
        child.add_child(parent)

    # lookups used to loop forever on a cyclic tree
    assert not parent.contains_shallow("missing")
    assert not child.contains_shallow("parent")


def test_duplicate_children_are_rejected():
    parent = filetree.FsNode("parent")
    parent.add_child(filetree.FsNode("a"))
    with pytest.raises(ValueError) as info:
        parent.add_child(filetree.FsNode("a", b""))
    assert info.value.args[1] == filetree.ErrorCodes.DuplicateFile
    assert len(parent.children) == 1


@pytest.mark.parametrize("name", BAD_NAMES)
def test_invalid_child_names_are_rejected(name: str):
    parent = filetree.FsNode("parent")
    with pytest.raises(ValueError) as info:
        parent.add_child(filetree.FsNode(name))
    assert info.value.args[1] == filetree.ErrorCodes.InvalidPath
    assert parent.children == []


@pytest.mark.parametrize("name", BAD_NAMES)
def test_tree_creation_rejects_escaping_names(name: str):
    tree = filetree.FsTree("root")
    with pytest.raises(ValueError):
        tree.create_file(name, b"x")
    with pytest.raises(ValueError):
        tree.create_dir(name)
    with pytest.raises(ValueError):
        tree.create_file("ok.txt", b"x", name)
    assert tree.root.children == []


def test_normal_unicode_and_dotted_names_are_fine():
    tree = filetree.FsTree("root")
    for name in ["a.txt", ".hidden", "..data", "a..b", "こんにちは.txt"]:
        tree.create_file(name, b"x")
    assert len(tree.root.children) == 5


def test_root_node_may_have_any_path_name():
    # FileTree(Path("..")) / Path(".") produce these root names
    assert filetree.FsNode("..").name == ".."
    assert filetree.FsTree("").root.name == ""


def test_write_content_on_directory_is_an_error():
    empty_dir = filetree.FsNode("dir")
    with pytest.raises(ValueError) as info:
        empty_dir.write_content(b"data")
    assert info.value.args[1] == filetree.ErrorCodes.InvalidPath
    with pytest.raises(ValueError):
        empty_dir.append_content(b"data")
    assert not empty_dir.is_file()
    assert empty_dir.content is None


def test_write_content_on_file():
    node = filetree.FsNode("f", b"a")
    node.write_content(b"b")
    node.append_content(b"c")
    assert node.content == b"bc"
    empty_file = filetree.FsNode("e", b"")
    empty_file.append_content(b"x")
    assert empty_file.is_file() and empty_file.content == b"x"


def test_nodes_compare_by_identity():
    parent = filetree.FsNode("parent")
    parent.add_child(filetree.FsNode("a"))
    first, second = parent.get_shallow("a"), parent.get_shallow("a")
    assert first is not second
    assert first == second
    assert hash(first) == hash(second)
    assert first != filetree.FsNode("a")
    assert first != "a"
    assert len({first, second}) == 1
