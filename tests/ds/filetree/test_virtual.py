# pyright: reportOptionalMemberAccess=false
import pytest

from escudeiro.data.converters.utils import asdict
from escudeiro.ds import VirtualFileTree
from escudeiro.exc import FailedFileOperation, InvalidPath


def test_create_dir():
    file_tree = VirtualFileTree.from_basename("root")
    with file_tree.virtual_context("folder") as inner_tree:
        folder = inner_tree.create_dir("subfolder")
        assert folder.name == "subfolder"
        assert folder.children == []


def test_create_dir_existing_folder():
    file_tree = VirtualFileTree.from_basename("root")
    with file_tree.virtual_context("folder") as inner_tree:
        folder1 = inner_tree.create_dir("subfolder")
        folder2 = inner_tree.create_dir("subfolder")
        # get_shallow returns a copy; we check name equality to confirm logical identity
        assert folder1.name == folder2.name


def test_create_dir_existing_file():
    file_tree = VirtualFileTree.from_basename("root")
    with file_tree.virtual_context("folder") as inner_tree:
        _ = inner_tree.create_file("file")
        with pytest.raises(InvalidPath):
            _ = inner_tree.create_dir("file")


def test_create_file():
    file_tree = VirtualFileTree.from_basename("root")
    with file_tree.virtual_context("folder") as inner_tree:
        file = inner_tree.create_file("file")
        assert file.name == "file"
        assert file.content == b""


def test_create_file_existing_folder():
    file_tree = VirtualFileTree.from_basename("root")
    with file_tree.virtual_context("folder") as inner_tree:
        _ = inner_tree.create_dir("subfolder")
        with pytest.raises(InvalidPath):
            _ = inner_tree.create_file("subfolder")


def test_create_file_existing_file():
    file_tree = VirtualFileTree.from_basename("root")
    with file_tree.virtual_context("folder") as inner_tree:
        file1 = inner_tree.create_file("file")
        file2 = inner_tree.create_file("file")
        assert file1.name == file2.name


def test_get_file():
    file_tree = VirtualFileTree.from_basename("root")
    with file_tree.virtual_context("folder") as inner_tree:
        _ = inner_tree.create_file("file")
        file = inner_tree.get_path("file")
        assert file.name == "file"


def test_get_file_nonexistent_folder():
    file_tree = VirtualFileTree.from_basename("root")
    with pytest.raises(InvalidPath):
        _ = file_tree.get_path("file", "invalid")


def test_get_file_nonexistent_file():
    file_tree = VirtualFileTree.from_basename("root")
    with file_tree.virtual_context("folder") as inner_tree:
        with pytest.raises(InvalidPath):
            _ = inner_tree.get_path("file")


def test_get_dir():
    file_tree = VirtualFileTree.from_basename("root")
    with file_tree.virtual_context("folder") as inner_tree:
        _ = inner_tree.create_dir("folder")
        folder = inner_tree.get_path("folder")
        assert folder is not None
        assert folder.name == "folder"


def test_get_dir_nonexistent_folder():
    file_tree = VirtualFileTree.from_basename("root")
    with pytest.raises(InvalidPath):
        _ = file_tree.get_path("folder")


def test_create_py_file():
    file_tree = VirtualFileTree.from_basename("root")
    with file_tree.virtual_context("folder"):
        file = file_tree.create_py_file("script")
        assert file.name == "script.py"


def test_init_file():
    file_tree = VirtualFileTree.from_basename("root")
    with file_tree.virtual_context("folder"):
        file = file_tree.create_init_file()
        assert file.name == "__init__.py"


def test_from_virtual():
    file_tree = VirtualFileTree.from_basename("root")
    with file_tree.virtual_context("folder") as inner_tree:
        _ = inner_tree.create_dir("subfolder")
        _ = inner_tree.create_file("file")

        new_tree = VirtualFileTree.from_basename("new_root")
        new_tree.merge(inner_tree, "folder")
        new_inner_root = new_tree.root.get_shallow("folder")
        assert new_inner_root
        assert new_inner_root.name == "folder"

        old_inner_root = new_inner_root.get_shallow("folder")
        assert old_inner_root
        assert old_inner_root.get_shallow("subfolder")
        assert not old_inner_root.get_shallow("subfolder").is_file()
        assert old_inner_root.get_shallow("file")
        assert old_inner_root.get_shallow("file").is_file()


def test_from_virtual_existing_file():
    file_tree = VirtualFileTree.from_basename("root")
    with file_tree.virtual_context("folder") as inner_tree:
        _ = inner_tree.create_file("file")

    new_tree = VirtualFileTree.from_basename("file")
    with pytest.raises(InvalidPath):
        file_tree.merge(new_tree, "folder")


def test_from_virtual_foldername_conflict():
    file_tree = VirtualFileTree.from_basename("root")
    with file_tree.virtual_context("folder") as inner_tree:
        _ = inner_tree.create_file("subfolder")

    new_tree = VirtualFileTree.from_basename("subfolder")
    with pytest.raises(InvalidPath):
        file_tree.merge(new_tree, "folder")


def test_virtual_context():
    file_tree = VirtualFileTree.from_basename("root")
    with file_tree.virtual_context("folder") as inner_tree:
        folder = inner_tree.create_dir("subfolder")
        file = inner_tree.create_file("file")
        text_file = inner_tree.create_text_file("text_file")
        text_file.append_content(b"Hello")
        assert folder.name == "subfolder"
        assert file.name == "file"
        assert inner_tree.root.get_shallow("subfolder")
        assert inner_tree.root.get_shallow("file")
    assert asdict(file_tree) == {
        "root": {
            "folder": {
                "subfolder": {},
                "file": file.content,
                "text_file": text_file.content,
            }
        },
    }


def test_virtual_context_exception():  # sourcery skip: raise-specific-error
    file_tree = VirtualFileTree.from_basename("root")
    with pytest.raises(FailedFileOperation):
        with file_tree.virtual_context("folder"):
            raise Exception("Something went wrong")

    assert file_tree.root.children == []
