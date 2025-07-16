from __future__ import annotations

import os
from functools import partial
from pathlib import Path
from typing import Literal

from escudeiro.misc.functions import isinstance_or_cast

type StrOrPath = str | Path


@partial(isinstance_or_cast, Path)
def autopath(value: StrOrPath) -> Path:
    """
    Converts a string or Path to a Path object.
    If the input is already a Path, it returns it unchanged.
    """
    return Path(value)


def get_extension(value: StrOrPath) -> str:
    """
    Returns the file extension of a given path or string.
    If the input is a string without a path, it returns an empty string.
    """
    value = autopath(value)
    _, ext = os.path.splitext(value)
    return ext.lstrip(".") if ext else ""


def is_extension(value: StrOrPath, *exts: str) -> bool:
    """
    Checks if the file extension of a given path or string matches any of the provided extensions.

    Args:
        value (StrOrPath): The input path or string to check.
        *exts (str): The file extensions to check against.

    Returns:
        bool: True if the file extension matches any of the provided extensions, False otherwise.
    """
    return any(
        get_extension(value).lower() == ext.lower().rstrip(".") for ext in exts
    )


def is_valid_path(value: StrOrPath) -> bool:
    """
    Checks if the given path exists.

    Args:
        value (StrOrPath): The input path or string to check.

    Returns:
        bool: True if the path exists, False otherwise.
    """
    return autopath(value).exists()


def valid_or_new(
    value: StrOrPath, mode: Literal["dir", "file", "guess"] = "guess"
) -> Path:
    """
    Validates if the given path exists or creates a new one based on the mode.

    Args:
        value (StrOrPath): The input path or string to check.
        mode (Literal["dir", "file", "guess"]): The mode to determine how to handle the path.

    Returns:
        Path: The validated or newly created Path object.
    """
    value = autopath(value)

    match mode:
        case "dir":
            if not value.exists():
                value.mkdir(parents=True, exist_ok=True)
            else:
                if not value.is_dir():
                    raise NotADirectoryError(f"{value!s} is not a directory")
        case "file":
            if not value.exists():
                value.touch(exist_ok=True)
            else:
                if not value.is_file():
                    raise IsADirectoryError(f"{value!s} is not a file")
        case "guess":
            if not value.exists():
                if value.suffix:
                    value.touch(exist_ok=True)
                else:
                    value.mkdir(parents=True, exist_ok=True)
        case _:  # pyright: ignore[reportUnnecessaryComparison]
            raise ValueError(f"Invalid mode: {mode}")  # pyright: ignore[reportUnreachable]
    return value


def is_valid_link(value: StrOrPath) -> bool:
    """
    Checks if the given path is a symbolic link.

    Args:
        value (StrOrPath): The input path or string to check.

    Returns:
        bool: True if the path is a symbolic link, False otherwise.
    """
    return autopath(value).is_symlink() and autopath(value).exists()
