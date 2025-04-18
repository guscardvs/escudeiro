from pathlib import Path

import pytest

from escudeiro.ds import FileTree
from escudeiro.exc import FailedFileOperation, InvalidPath


def test_write_file(tmp_path: Path):
    file_tree = FileTree(base_dir=tmp_path / "root")
    vt = file_tree.virtual
    _ = vt.create_text_file("file.txt", content="Hello, World!")

    file_tree.write()

    assert (tmp_path / "root").is_dir()
    assert (tmp_path / "root").exists()
    assert (tmp_path / "root/file.txt").is_file()
    with open(tmp_path / "root/file.txt") as f:
        assert f.read() == "Hello, World!"


def test_write_folder(tmp_path: Path):
    file_tree = FileTree(base_dir=tmp_path)
    vt = file_tree.virtual
    _ = vt.root
    _ = vt.create_text_file("file.txt", content="Hello, World!")
    _ = vt.create_dir("subfolder")
    _ = vt.create_text_file(
        "subfile.txt", "subfolder", content="This is a subfile."
    )

    file_tree.write()

    assert (tmp_path / "file.txt").is_file()
    with open(tmp_path / "file.txt") as f:
        assert f.read() == "Hello, World!"

    assert (tmp_path / "subfolder" / "subfile.txt").is_file()
    with open(tmp_path / "subfolder" / "subfile.txt") as f:
        assert f.read() == "This is a subfile."


def test_filetree_context_manager(tmp_path: Path):
    file_path = tmp_path / "root" / "ctxfile.txt"
    with FileTree(base_dir=tmp_path / "root") as tree:
        _ = tree.virtual.create_text_file("ctxfile.txt", content="Contextual")

    assert file_path.exists()
    assert file_path.read_text() == "Contextual"


def test_filetree_context_manager_raises(tmp_path: Path):
    file_path = tmp_path / "root" / "f.txt"
    with pytest.raises(FailedFileOperation):
        with FileTree(base_dir=tmp_path / "root") as tree:
            _ = tree.virtual.create_text_file(
                "f.txt", content="Should not persist"
            )
            raise RuntimeError("boom")

    assert not file_path.exists()


def test_filetree_merge(tmp_path: Path):
    ft1 = FileTree(base_dir=tmp_path / "root1")
    _ = ft1.virtual.create_text_file("common.txt", content="Tree 1")
    ft2 = FileTree(base_dir=tmp_path / "root2")
    _ = ft2.virtual.create_text_file("other.txt", content="Tree 2")

    ft1.merge(ft2)

    ft1.write()

    assert (tmp_path / "root1/common.txt").exists()
    assert (tmp_path / "root1/root2/other.txt").exists()


def test_filetree_overwrites_file_with_dir(tmp_path: Path):
    file_path = tmp_path / "root" / "conflict"
    file_path.parent.mkdir(parents=True)
    _ = file_path.write_text("was a file")

    tree = FileTree(base_dir=tmp_path / "root")
    _ = tree.virtual.create_dir("conflict")
    tree.write()

    assert not file_path.is_file()


def test_filetree_overwrites_dir_with_file(tmp_path: Path):
    dir_path = tmp_path / "root" / "conflict"
    dir_path.mkdir(parents=True)

    tree = FileTree(base_dir=tmp_path / "root")
    _ = tree.virtual.create_text_file("conflict", content="now a file")
    tree.write()

    assert dir_path.is_file()


def test_filetree_deep_nesting(tmp_path: Path):
    tree = FileTree(base_dir=tmp_path / "deep")
    vt = tree.virtual
    _ = vt.root
    for i in range(100):  # depends on realistic limits
        _ = vt.create_dir(f"lvl{i}", *(f"lvl{j}" for j in range(i)))
    tree.write()
    assert (tmp_path / "deep" / "lvl0" / "lvl1" / "lvl2").exists()


def test_filetree_unicode_paths(tmp_path: Path):
    tree = FileTree(base_dir=tmp_path / "üñíçødé")
    vt = tree.virtual
    _ = vt.create_text_file("こんにちは.txt", content="こんにちは")
    tree.write()
    assert (tmp_path / "üñíçødé" / "こんにちは.txt").exists()


def test_validate_success(tmp_path: Path):
    base = tmp_path / "project"
    base.mkdir()
    _ = (base / "file.txt").write_text("hello")
    (base / "dir").mkdir()
    _ = (base / "dir" / "inner.txt").write_text("world")

    ft = FileTree(base_dir=base)
    vt = ft.virtual
    _ = vt.create_text_file("file.txt", content="hello")
    _ = vt.create_dir("dir")
    _ = vt.create_text_file("inner.txt", "dir", content="world")

    # Should not raise
    ft.validate()


def test_validate_file_vs_dir_mismatch(tmp_path: Path):
    base = tmp_path / "root"
    base.mkdir()
    (base / "something").mkdir()

    ft = FileTree(base_dir=base)
    vt = ft.virtual
    _ = vt.create_text_file("something", content="not a folder")

    with pytest.raises(InvalidPath, match="something"):
        ft.validate()
