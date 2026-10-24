import os
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


def test_write_never_replaces_a_file_with_a_dir(tmp_path: Path):
    file_path = tmp_path / "root" / "conflict"
    file_path.parent.mkdir(parents=True)
    _ = file_path.write_text("was a file")

    tree = FileTree(base_dir=tmp_path / "root")
    _ = tree.virtual.create_dir("conflict")
    with pytest.raises(InvalidPath, match="conflict"):
        tree.write()

    assert file_path.read_text() == "was a file"


def test_write_never_replaces_a_dir_with_a_file(tmp_path: Path):
    dir_path = tmp_path / "root" / "conflict"
    dir_path.mkdir(parents=True)

    tree = FileTree(base_dir=tmp_path / "root")
    _ = tree.virtual.create_text_file("conflict", content="now a file")
    with pytest.raises(InvalidPath, match="conflict"):
        tree.write()

    assert dir_path.is_dir()


def test_write_keeps_a_precious_file_that_blocks_a_folder(tmp_path: Path):
    base = tmp_path / "root"
    base.mkdir()
    precious = base / "sub"
    _ = precious.write_text("precious")

    tree = FileTree(base_dir=base)
    _ = tree.virtual.create_text_file("f.txt", "sub", content="x")
    with pytest.raises(InvalidPath):
        tree.write()

    assert precious.read_text() == "precious"


def test_write_is_all_or_nothing_on_conflict(tmp_path: Path):
    base = tmp_path / "root"
    (base / "d").mkdir(parents=True)
    _ = (base / "d" / "keep.txt").write_text("keep")

    tree = FileTree(base_dir=base)
    _ = tree.virtual.create_text_file("a.txt", content="a")
    _ = tree.virtual.create_text_file("d", content="file over non-empty dir")
    with pytest.raises(InvalidPath):
        tree.write()

    assert not (base / "a.txt").exists()
    assert (base / "d" / "keep.txt").read_text() == "keep"


def test_write_replaces_file_content_atomically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    base = tmp_path / "root"
    base.mkdir()
    target = base / "f.txt"
    _ = target.write_text("old")
    target.chmod(0o640)

    tree = FileTree(base_dir=base)
    _ = tree.virtual.create_text_file("f.txt", content="new")
    tree.write()
    assert target.read_text() == "new"
    assert target.stat().st_mode & 0o777 == 0o640
    assert [p.name for p in base.iterdir()] == ["f.txt"]

    def failing_replace(src: object, dst: object) -> None:
        raise OSError("boom")

    _ = tree.virtual.create_text_file("f.txt", content="newer")
    monkeypatch.setattr(os, "replace", failing_replace)
    with pytest.raises(OSError, match="boom"):
        tree.write()
    assert target.read_text() == "new"
    assert [p.name for p in base.iterdir()] == ["f.txt"]  # no temp left over


def test_write_refuses_names_that_escape_base_dir(tmp_path: Path):
    tree = FileTree(base_dir=tmp_path / "root")
    for name in ("../escaped.txt", "a/b.txt"):
        with pytest.raises(InvalidPath):
            _ = tree.virtual.create_text_file(name, content="x")
    tree.write()
    assert not (tmp_path / "escaped.txt").exists()


def test_validate_and_write_nested_path_with_missing_base_dir(tmp_path: Path):
    base = tmp_path / "new" / "project"  # neither level exists yet
    tree = FileTree(base_dir=base)
    _ = tree.virtual.create_text_file("inner.txt", "pkg", "sub", content="x")

    tree.validate()  # used to raise a false FailedFileOperation
    tree.write()

    assert (base / "pkg" / "sub" / "inner.txt").read_text() == "x"


def test_validate_reports_unwritable_ancestor(tmp_path: Path):
    if os.geteuid() == 0:
        pytest.skip("root bypasses permission checks")
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o500)
    try:
        tree = FileTree(base_dir=locked / "a" / "b")
        _ = tree.virtual.create_text_file("f.txt", content="x")
        with pytest.raises(FailedFileOperation, match="locked"):
            tree.validate()
    finally:
        locked.chmod(0o700)


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
