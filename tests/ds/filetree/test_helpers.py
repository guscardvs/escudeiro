from collections.abc import Sequence
from typing import Any

import pytest

from escudeiro.ds.filetree.helpers import resolve_error
from escudeiro.escudeiro_pyrs import filetree
from escudeiro.exc import (
    DuplicateFile,
    InvalidParamType,
    InvalidPath,
    SyncError,
)
from escudeiro.misc import next_or


@pytest.mark.parametrize(
    "args, expected_type, expected_msg",
    [
        # One-arg fallback to InvalidPath
        (("some path error",), InvalidPath, "some path error"),
        # Known Rust error mappings
        ("invalid type", filetree.ErrorCodes.InvalidParam, InvalidParamType),
        ("lock error", filetree.ErrorCodes.UnableToAcquireLock, SyncError),
        ("bad path", filetree.ErrorCodes.InvalidPath, InvalidPath),
        ("duplicate", filetree.ErrorCodes.DuplicateFile, DuplicateFile),
        # Unknown code fallback (not mapped)
        (("msg", object()), ValueError, "msg"),
        # Invalid arg count (ignored)
        (("a", "b", "c"), ValueError, None),
    ],
)
def test_resolve_error(
    args: Sequence[Any], expected_type: Any, expected_msg: Any
):
    if isinstance(expected_type, type) and issubclass(expected_type, Exception):
        # one-arg case
        instance = (
            ValueError(*args)
            if isinstance(args, tuple)
            else ValueError(args[0], args[1])
        )
        resolved = resolve_error(instance)

        assert isinstance(resolved, expected_type)
        if expected_msg:
            msg = next_or(resolved.args)
            assert str(msg) == expected_msg
        assert (
            resolved.__cause__ is instance if resolved is not instance else True
        )
    else:
        # fallback to original ValueError
        instance = ValueError(*args)
        resolved = resolve_error(instance)
        assert resolved is instance
