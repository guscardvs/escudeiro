# pyright: reportInvalidTypeForm=false

import enum
from collections.abc import Collection, Mapping
from datetime import datetime, tzinfo
from pathlib import Path
from typing import Any, ClassVar, Literal, Self

class url:
    """A collection of URL parsing and manipulation utilities."""

    class Query:
        """Represents and manipulates URL query parameters."""

        def __init__(self, querystr: str) -> None:
            """Initialize with a query string (e.g., 'key1=val1&key2=val2')."""

        def add(self, key: str, value: str) -> None:
            """Add a new key-value pair to the query."""

        def get(self) -> Mapping[str, Collection[str]]:
            """Return all parameters as a mapping of keys to value collections."""

        def encode(self) -> str:
            """Return the URL-encoded query string."""

        def add_map(self, map: Mapping[str, str]) -> None:
            """Add multiple parameters from a mapping of key-value pairs."""

        def set_map(self, map: Mapping[str, str]) -> None:
            """Replace all parameters with those from the given mapping."""

        def remove(self, key: str) -> None:
            """Remove the specified parameter by key."""

        def copy(self) -> Self:
            """Create a deep copy of this Query instance."""

        def omit_empty_equal(self) -> str:
            """Return encoded string omitting equals signs for empty values."""

        def sort(self) -> None:
            """Sort parameters alphabetically by key."""

        def first(self) -> Mapping[str, str]:
            """Return first value for each parameter as a mapping."""

        def compare(self, other: Self) -> bool:
            """Compare if two Query instances have identical parameters."""

        @property
        def params(self) -> Mapping[str, Collection[str]]:
            """Access the underlying parameters mapping directly."""

    class Path:
        """Represents and manipulates URL path components."""

        def __init__(self, pathstr: str) -> None:
            """Initialize with a path string (e.g., '/path/to/resource')."""

        def add(self, pathstr: str) -> None:
            """Append a path segment or segments to the current path."""

        def add_path(self, pathobj: Path) -> None:
            """Append a pathlib.Path object's segments to the current path."""

        def clear(self) -> None:
            """Clear all path segments."""

        def is_dir(self) -> bool:
            """Return True if the path ends with a trailing slash."""

        def encode(self) -> str:
            """Return the properly encoded path string."""

        def normalize(self) -> None:
            """Normalize the path by resolving '.' and '..' segments."""

        def copy(self) -> Self:
            """Create a deep copy of this Path instance."""

        def get(self) -> Collection[str]:
            """Return all path segments as a collection."""

        def compare(self, other: Self) -> bool:
            """Compare if two Path instances have identical segments."""

        @property
        def segments(self) -> Collection[str]:
            """Access the path segments directly."""

    class Fragment:
        """Represents and manipulates URL fragments (after '#')."""

        def __init__(self, fragmentstr: str) -> None:
            """Initialize with a fragment string."""

        def encode(self) -> str:
            """Return the properly encoded fragment string."""

        def set(self, fragmentstr: str) -> None:
            """Replace the current fragment with a new value."""

        def copy(self) -> Self:
            """Create a deep copy of this Fragment instance."""

        def compare(self, other: Self) -> bool:
            """Compare if two Fragment instances are identical."""

    class Netloc:
        """Represents and manipulates network location (host:port with auth)."""

        username: str | None
        password: str | None
        host: str
        port: int | None

        def __init__(self, netloc: str) -> None:
            """Parse a network location string (e.g., 'user:pass@host:port')."""

        def encode(self) -> str:
            """Return the properly encoded network location string."""

        def parse(self, netloc: str) -> None:
            """Parse and replace the current network location values."""

        def set(
            self,
            host: str | None = None,
            port: int | None = None,
            username: str | None = None,
            password: str | None = None,
        ) -> None:
            """Set individual network location components."""

        def merge(self, other: Self) -> Self:
            """Return a new Netloc with values merged from another instance."""

        def merge_left(self, other: Self) -> Self:
            """Return a new Netloc with left-biased merged values."""

        def merge_inplace(self, other: Self) -> None:
            """Merge values from another instance into this one."""

        @staticmethod
        def from_args(
            host: str,
            port: int | None = None,
            username: str | None = None,
            password: str | None = None,
        ) -> url.Netloc:
            """Create a Netloc instance from individual components."""

        def copy(self) -> Self:
            """Create a deep copy of this Netloc instance."""

        def compare(self, other: Self) -> bool:
            """Compare if two Netloc instances are identical."""

    class URL:
        """Comprehensive URL parsing and manipulation class."""

        scheme: str
        netloc: url.Netloc
        path: url.Path
        query: url.Query
        fragment: url.Fragment

        def __init__(self, url: str) -> None:
            """Parse a complete URL string into its components."""

        def encode(self, append_empty_equal: bool = True) -> str:
            """Return the properly encoded URL string."""

        def add(
            self,
            path: str | None = None,
            query: Mapping[str, str] | None = None,
            fragment: str | None = None,
            netloc: str | None = None,
            netloc_obj: url.Netloc | None = None,
            scheme: str | None = None,
        ) -> None:
            """Add components to the existing URL."""

        def set(
            self,
            path: str | None = None,
            query: Mapping[str, str] | None = None,
            fragment: str | None = None,
            netloc: str | None = None,
            netloc_obj: url.Netloc | None = None,
            scheme: str | None = None,
        ) -> None:
            """Replace URL components with new values."""

        @staticmethod
        def from_netloc(
            netloc: url.Netloc | None = None,
            username: str | None = None,
            password: str | None = None,
            host: str | None = None,
            port: int | None = None,
        ) -> url.URL:
            """Create a URL from network location components."""

        @staticmethod
        def from_args(
            path: str | None = None,
            query: Mapping[str, str] | None = None,
            fragment: str | None = None,
            netloc: str | None = None,
            netloc_obj: url.Netloc | None = None,
            scheme: str | None = None,
        ) -> url.URL:
            """Create a URL from individual components."""

        def copy(self) -> Self:
            """Create a deep copy of this URL instance."""

        def compare(self, other: Self) -> bool:
            """Compare if two URL instances are identical."""

class strings:
    """String manipulation utilities."""

    @staticmethod
    def replace_all(value: str, replacements: Mapping[str, str]) -> str:
        """Replace all occurrences of keys with their values in the string."""

    @staticmethod
    def replace_by(
        value: str, replacement: str, to_replace: Collection[str]
    ) -> str:
        """Replace all occurrences of any string in to_replace with replacement."""

    @staticmethod
    def to_snake(value: str) -> str:
        """Convert string to snake_case."""

    @staticmethod
    def to_camel(value: str) -> str:
        """Convert string to camelCase."""

    @staticmethod
    def to_pascal(value: str) -> str:
        """Convert string to PascalCase."""

    @staticmethod
    def to_kebab(value: str, remove_trailing_underscores: bool = True) -> str:
        """Convert string to kebab-case."""

    @staticmethod
    def squote(value: str) -> str:
        """Wrap string in single quotes."""

    @staticmethod
    def dquote(value: str) -> str:
        """Wrap string in double quotes."""

    @staticmethod
    def sentence(value: str) -> str:
        """Capitalize first letter and add period if missing."""

    @staticmethod
    def exclamation(value: str) -> str:
        """Capitalize first letter and add exclamation if missing."""

    @staticmethod
    def question(value: str) -> str:
        """Capitalize first letter and add question mark if missing."""

class squire:
    """Serialization and deserialization utilities."""

    @staticmethod
    def make_mapping(obj: Any, by_alias: bool = False) -> Mapping[str, Any]:
        """Convert an object to a mapping of its attributes."""

    @staticmethod
    def deserialize_mapping(
        mapping: Mapping[str, Any], by_alias: bool = True
    ) -> Mapping[str, Any]:
        """Deserialize a mapping with optional alias resolution."""

    @staticmethod
    def deserialize(value: Any, by_alias: bool = True) -> Any:
        """Generic deserialization with optional alias resolution."""

class cronjob:
    """Cron expression utilities."""

    class CronExpr:
        """Represents and evaluates cron expressions."""

        @property
        def timezone(self) -> tzinfo:
            """Get the timezone used for scheduling."""

        @property
        def next_run(self) -> datetime:
            """Get the next scheduled run time."""

        def __init__(self, expression: str, timezone: tzinfo) -> None:
            """Initialize with a cron expression and timezone."""

        def update(self) -> None:
            """Update next_run to the next scheduled occurrence."""
        def update_after(self, after: datetime) -> None:
            """Update next_run to the next scheduled occurrence after 'after'."""

        def matches(self, value: datetime) -> bool:
            """Check if the given datetime matches the cron schedule."""

class filetree:
    """
    Python interface for file tree manipulation implemented in Rust.

    This module provides utilities for creating and manipulating file and directory
    structures in memory. It includes functions for generating Python filenames
    and classes for representing filesystem nodes and trees.
    """

    @staticmethod
    def python_filename(
        filename: str, private: bool = False, dunder: bool = False
    ) -> str:
        """
        Format a string as a Python filename with appropriate prefixes and extension.

        Args:
            filename: Base name of the file without extension
            private: If True, prepends a single underscore to the filename
            dunder: If True, wraps the filename with double underscores

        Returns:
            Formatted Python filename with .py extension

        Raises:
            ValueError: If both private and dunder are True
        """
        ...

    @staticmethod
    def init_file() -> str:
        """
        Generate a standard Python package __init__.py filename.

        Returns:
            The string "__init__.py"
        """
        ...

    class ErrorCodes(enum.Enum):
        """Mapping of possible error codes."""

        InvalidParam: ClassVar[Literal[1]]
        UnableToAcquireLock: ClassVar[Literal[2]]
        InvalidPath: ClassVar[Literal[3]]
        DuplicateFile: ClassVar[Literal[4]]

    class FsNode:
        """
        Represents a node in a file system tree.

        A node can be either a file (with content) or a directory (containing other nodes).
        Thread-safe operations are ensured through internal locking mechanisms.
        """

        def __init__(self, name: str, content: bytes | None = None) -> None:
            """
            Initialize a new filesystem node.

            Args:
                name: Name of the node
                content: If provided, the node is treated as a file with this content;
                        otherwise, it's treated as a directory
            """
            ...

        @property
        def name(self) -> str:
            """
            Get the name of this node.

            Returns:
                The name of the node

            Raises:
                ValueError: If the internal lock cannot be acquired
            """
            ...

        @property
        def content(self) -> bytes | None:
            """
            Get the content of this node if it's a file.

            Returns:
                The content as bytes if node is a file, None if it's a directory

            Raises:
                ValueError: If the internal lock cannot be acquired
            """
            ...

        @property
        def children(self) -> list[filetree.FsNode]:
            """
            Get all child nodes if this node is a directory.

            Returns:
                List of child nodes

            Raises:
                ValueError: If the internal lock cannot be acquired
            """
            ...

        def is_file(self) -> bool:
            """
            Check if this node represents a file.

            Returns:
                True if the node is a file, False if it's a directory

            Raises:
                ValueError: If the internal lock cannot be acquired
            """
            ...

        def contains_shallow(self, name: str) -> bool:
            """
            Check if this directory contains a child with the given name.
            Only checks immediate children, not descendents.

            Args:
                name: Name of the child node to look for

            Returns:
                True if a child with the given name exists, False otherwise

            Raises:
                ValueError: If the internal lock cannot be acquired
            """
            ...

        def get_shallow(self, name: str) -> filetree.FsNode | None:
            """
            Get a child node by name if it exists.
            Only checks immediate children, not descendents.

            Args:
                name: Name of the child node to retrieve

            Returns:
                The child node if found, None otherwise

            Raises:
                ValueError: If the internal lock cannot be acquired
            """
            ...

        def add_child(self, node: filetree.FsNode) -> None:
            """
            Add a child node to this directory.

            Args:
                node: The node to add as a child

            Raises:
                ValueError: If this node is a file, or if the lock cannot be acquired
            """
            ...

        def write_content(self, content: bytes) -> None:
            """
            Write content to this node.

            Args:
                content: the content to be written in bytes

            Raises:
                ValueError: if this node is a directory, or if the lock cannot be acquired.
            """
            ...

        def append_content(self, content: bytes) -> None:
            """
            Append content to this node.

            Args:
                content: the content to be appended in bytes

            Raises:
                ValueError: if this node is a directory, or if the lock cannot be acquired.
            """
            ...

    class FsTree:
        """
        Represents a file system tree structure.

        Provides methods for creating and navigating directories and files within
        the tree structure.
        """

        def __init__(self, basename: str) -> None:
            """
            Initialize a new file system tree with a root directory.

            Args:
                basename: Name of the root directory
            """
            ...

        @staticmethod
        def from_node(root: filetree.FsNode) -> filetree.FsTree:
            """Initialize a new file system tree with a root directory as the node.

            Args:
                root: Root node of the file tree.
            """

        @property
        def root(self) -> filetree.FsNode:
            """
            Get the root node of this tree.

            Returns:
                The root node
            """
            ...

        def create_dir(self, name: str, *path: str) -> filetree.FsNode:
            """
            Create a new directory at the specified path.

            If the path doesn't exist, intermediate directories will be created.
            If the directory already exists, it will be returned.

            Args:
                name: Name of the directory to create
                *path: Path components leading to the parent directory

            Returns:
                The newly created or existing directory node

            Raises:
                ValueError: If a file with the same name exists at the specified location
            """
            ...

        def create_file(
            self, name: str, content: bytes, *path: str
        ) -> filetree.FsNode:
            """
            Create a new file with the specified content at the given path.

            If the path doesn't exist, intermediate directories will be created.

            Args:
                name: Name of the file to create
                content: Content of the file as bytes
                *path: Path components leading to the parent directory

            Returns:
                The newly created file node

            Raises:
                ValueError: If a node with the same name already exists at the specified location
            """
            ...

        def get_node(self, *path: str) -> filetree.FsNode:
            """
            Get a node at the specified path, creating directories as needed.

            Args:
                *path: Path components to navigate

            Returns:
                The node at the specified path

            Raises:
                ValueError: If a path component is a file but not the last component
            """
            ...
