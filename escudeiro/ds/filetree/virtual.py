from __future__ import annotations

import os
from contextlib import contextmanager
from functools import partial
from typing import Any, Self

from escudeiro.data import data
from escudeiro.ds.filetree.helpers import resolve_error
from escudeiro.escudeiro_pyrs import filetree
from escudeiro.exc import FailedFileOperation, InvalidPath
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
        except AssertionError as err:
            if "PYTEST_CURRENT_TEST" in os.environ:
                raise
            else:
                raise FailedFileOperation(
                    "unable to complete virtual context after exception", err
                ) from err
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
        if curnode := parent_node.get_shallow(vt.name):
            if curnode.is_file():
                raise InvalidPath(
                    f"Trying to create folder {curnode.name} where there is a file."
                )
            else:
                for child in vt.root.children:
                    if curnode.get_shallow(child.name):
                        raise InvalidPath(
                            f"Conflict: {child.name} already exists in {curnode.name}"
                        )
                    curnode.add_child(child)
        else:
            parent_node.add_child(vt.root)

    def create_file(
        self,
        filename: str,
        *path: str,
        content: bytes = b"",
        append: bool = False,
    ) -> filetree.FsNode:
        file_maker = partial(
            self._internal.create_file,
            filename,
            content,
            *path,
        )
        try:
            parent = self._internal.get_node(*path)
        except ValueError as err:
            raise resolve_error(err)
        else:
            node = parent.get_shallow(filename)
            if not node:
                return file_maker()
            elif node.content is None:
                raise InvalidPath(
                    f"Trying to create file {node.name} where there is a folder."
                )
            else:
                writer = node.append_content if append else node.write_content
                writer(content)
                return node

    def create_text_file(
        self,
        filename: str,
        *path: str,
        content: str = "",
        encoding: str = "utf-8",
        append: bool = False,
    ) -> filetree.FsNode:
        return self.create_file(
            filename,
            *path,
            content=content.encode(encoding),
            append=append,
        )

    def create_py_file(
        self,
        filename: str,
        *path: str,
        private: bool = False,
        dunder: bool = False,
        content: str = "",
        append: bool = False,
    ) -> filetree.FsNode:
        return self.create_text_file(
            filetree.python_filename(
                filename,
                dunder=dunder,
                private=private,
            ),
            *path,
            content=content,
            append=append,
        )

    def create_init_file(
        self,
        *path: str,
        content: str = "",
        append: bool = False,
    ) -> filetree.FsNode:
        return self.create_text_file(
            filetree.init_file(),
            *path,
            content=content,
            append=append,
        )

    def create_dir(self, dirname: str, *path: str) -> filetree.FsNode:
        try:
            return self._internal.create_dir(dirname, *path)
        except ValueError as err:
            raise resolve_error(err)

    def get_path(self, pathname: str, *path: str) -> filetree.FsNode:
        try:
            parent = self._internal.get_node(*path)
        except ValueError as e:
            raise resolve_error(e)
        else:
            file = parent.get_shallow(pathname)
            if file is None:
                raise InvalidPath("path not found")
            else:
                return file

    def __parse_dict__(self, by_alias: bool) -> dict[str, Any]:
        output = {}
        stack = [(self.root, output)]

        while stack:
            node, mapping = stack.pop()

            if node.is_file():
                mapping[node.name] = node.content
            else:
                new_mapping = {}
                mapping[node.name] = new_mapping
                for child in node.children:
                    stack.append((child, new_mapping))

        return output
