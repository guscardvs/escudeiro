from typing import TYPE_CHECKING

from escudeiro.escudeiro_pyrs import filetree
from escudeiro.exc.errors import (
    DuplicateFile,
    InvalidParamType,
    InvalidPath,
    SyncError,
)


def resolve_error(instance: ValueError) -> Exception:
    if not instance.args:
        return instance
    if len(instance.args) == 1:
        err = InvalidPath(*instance.args)
        err.__cause__ = instance
        return err
    else:
        msg, errkind, *_ = instance.args
        if TYPE_CHECKING:
            errkind: filetree.ErrorCodes

        match errkind:
            case filetree.ErrorCodes.InvalidParam:
                err = InvalidParamType(msg)
            case filetree.ErrorCodes.UnableToAcquireLock:
                err = SyncError(msg)
            case filetree.ErrorCodes.InvalidPath:
                err = InvalidPath(msg)
            case filetree.ErrorCodes.DuplicateFile:
                err = DuplicateFile(msg)
            case _:
                err = instance

        if err is not instance:
            err.__cause__ = instance
        return err
