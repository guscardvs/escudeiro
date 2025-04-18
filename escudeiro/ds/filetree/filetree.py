from __future__ import annotations

import os
from pathlib import Path
from types import TracebackType
from typing import Self

from escudeiro.data import data
from escudeiro.ds.filetree.virtual import VirtualFileTree
from escudeiro.escudeiro_pyrs import filetree
from escudeiro.exc import FailedFileOperation, InvalidPath
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
            if curnode.is_file():
                # file
                self._write_file(curpath, curnode)
            else:
                # folder
                self._write_folder(curpath)
                for node in curnode.children:
                    stack.append((curpath / node.name, node))

    def _write_file(self, path: Path, node: filetree.FsNode):
        if node.content is None:
            raise ValueError(f"Expected file node, got folder at {path}")
        if path.exists() and path.is_dir():
            path.rmdir()
        elif path.exists() and path.is_file():
            path.unlink(missing_ok=True)
        else:
            path.touch()
        with open(path, "wb") as stream:
            _ = stream.write(node.content)

    def _write_folder(self, path: Path):
        if path.exists():
            if path.is_file():
                path.unlink(missing_ok=True)
        else:
            path.mkdir(parents=True)

    def merge(self, tree: FileTree | VirtualFileTree, *path: str) -> None:
        if isinstance(tree, FileTree):
            self.virtual.merge(tree.virtual, *path)
        else:
            self.virtual.merge(tree, *path)

    def validate(self) -> None:
        """
        Validate that the virtual file tree can be safely written to the base_dir in the actual filesystem.
        This includes checking for:
            - Path conflicts (file where folder is expected, etc.)
            - Missing intermediate directories
            - Permissions (read/write) — if needed
        Raises:
            FailedFileOperation: If any part of the tree would fail to be written due to a conflict.
        """
        stack = [(self.base_dir, self.virtual.root)]

        while stack:
            curpath, curnode = stack.pop()

            # Check for invalid file/folder conflicts
            if curpath.exists():
                if not curnode.is_file() and not curpath.is_dir():
                    raise InvalidPath(
                        f"Expected folder at {curpath}, but found file or other"
                    )
                elif curnode.is_file() and not curpath.is_file():
                    raise InvalidPath(
                        f"Expected file at {curpath}, but found directory or other"
                    )

            # Traverse children if directory
            if not curnode.is_file():
                for child in curnode.children:
                    stack.append((curpath / child.name, child))

            # Optional: verify write permission
            if curpath.exists():
                if not os.access(curpath, os.W_OK):
                    raise FailedFileOperation(
                        f"No write permission for {curpath}"
                    )
            else:
                # Check parent directory for writability
                parent = curpath.parent
                if not parent.exists() or not os.access(parent, os.W_OK):
                    raise FailedFileOperation(
                        f"Cannot write to {parent} (nonexistent or unwritable)"
                    )
