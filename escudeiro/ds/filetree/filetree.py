from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING, Self

from escudeiro.data import data
from escudeiro.ds.filetree.virtual import VirtualFileTree
from escudeiro.escudeiro_pyrs import filetree
from escudeiro.exc.errors import FailedFileOperation
from escudeiro.lazyfields import lazyfield


@data(frozen=False)
class FileTree:
    base_dir: Path

    @lazyfield
    def root(self):
        return filetree.FsNode(self.base_dir.name)

    @lazyfield
    def virtual(self):
        return VirtualFileTree(self.root)

    def write(self):
        self.write_tree(self.base_dir, self.root)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        *exc_info: *tuple[
            type[BaseException] | None,
            BaseException | None,
            TracebackType | None,
        ],
    ):
        if any(exc_info):
            _, exc, _ = exc_info

            raise FailedFileOperation(
                "unable to write to disk after exception", exc
            ) from exc
        self.write()

    def write_tree(self, path: Path, node: filetree.FsNode) -> None:
        stack = [(path, node)]

        while stack:
            curpath, curnode = stack.pop()
            if curnode.content is not None:
                # file
                self._write_file(curpath, curnode)
            else:
                # folder
                self._write_folder(curpath)
                for node in curnode.children:
                    stack.append((curpath / node.name, node))

    def _write_file(self, path: Path, node: filetree.FsNode):
        if TYPE_CHECKING:
            assert node.content is not None
        if path.exists() and path.is_dir():
            path.rmdir()
        elif path.exists() and path.is_file():
            path.unlink()
        else:
            path.touch()
        with open(path, "wb") as stream:
            _ = stream.write(node.content)

    def _write_folder(self, path: Path):
        if path.exists() and path.is_file():
            path.unlink()
        else:
            path.mkdir(exist_ok=True)

    def merge(self, tree: FileTree | VirtualFileTree, *path: str) -> None:
        if isinstance(tree, FileTree):
            self.virtual.merge(tree.virtual, *path)
        else:
            self.virtual.merge(tree, *path)
