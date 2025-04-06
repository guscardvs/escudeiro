from __future__ import annotations

from contextlib import contextmanager
from typing import Self

from escudeiro.data import data
from escudeiro.escudeiro_pyrs import filetree
from escudeiro.exc.errors import FailedFileOperation
from escudeiro.lazyfields import lazyfield


@data(frozen=False)
class VirtualFileTree:
    root: filetree.FsNode

    @lazyfield
    def _internal(self) -> filetree.FsTree:
        return filetree.FsTree.from_node(self.root)

    @property
    def name(self) -> str:
        return self.root.name

    @classmethod
    def from_basename(cls, name: str) -> Self:
        return cls(filetree.FsNode(name))

    @contextmanager
    def virtual_context(self, dirname: str, *path: str):
        try:
            folder = self._get_node(dirname, *path) or filetree.FsNode(dirname)
            vt = VirtualFileTree(folder)
            yield vt
        except Exception as err:
            raise FailedFileOperation(
                "unable to complete virtual context after exception", err
            ) from err
        else:
            self.merge(vt, *path)

    def _get_node(self, name: str, *path: str) -> filetree.FsNode | None:
        try:
            parent = self._internal.get_node(*path)
        except ValueError:
            return None
        else:
            return parent.get_shallow(name)

    def merge(self, vt: VirtualFileTree, *path: str) -> None:
        if path:
            *restpath, parent = path
            parent_node = self._internal.create_dir(parent, *restpath)
        else:
            parent_node = self._internal.root
        parent_node.add_child(vt.root)
