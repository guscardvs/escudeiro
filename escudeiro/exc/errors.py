class SquireError(Exception):
    """Base exception for all errors raised by the Escudeiro library."""


class KeyAlreadyRead(SquireError, KeyError):
    """Raised when an attempt to write a key from a mutable mapping is already read"""


class InvalidCast(SquireError):
    """
    Exception raised when the configuration cast callable raises an error.

    This exception is raised when the casting function provided to the configuration
    is unable to successfully cast a value.
    """


class MissingName(SquireError, KeyError):
    """
    Exception raised when a configuration name is not found in the given environment.

    This exception is raised when attempting to retrieve a configuration value by name,
    but the name is not found in the configuration environment.
    """


class AlreadySet(SquireError):
    """
    Exception raised when attempting to set a value that is already set.

    This exception is raised when trying to set a value for a configuration that
    has already been set previously.
    """


class StrictCast(InvalidCast):
    """
    Exception raised when a strict cast is used for casting a configuration value.

    This exception is raised when a strict cast is used for casting a value, and
    the cast operation encounters an error.
    """


class InvalidEnv(SquireError):
    """
    Exception raised when an environment variable does not pass the rule check.

    This exception is raised when an environment variable does not meet the requirements
    specified by the rule check.
    """


class InvalidParamType(SquireError, TypeError):
    """Raised when a parameter's type is not as expected."""


class ErrorGroup(ExceptionGroup):
    """Used to group SquireError instances"""


class FailedFileOperation(SquireError):
    """Raised when an error occurs during an interaction with a file."""


class InvalidPath(SquireError, ValueError):
    """Raised when an invalid file or directory path is encountered."""


class SyncError(SquireError, ValueError):
    """Raised when a synchronization fails, such as acquiring a lock."""


class DuplicateFile(SquireError, ValueError):
    """Raised when trying to write a file that already exists"""


class RetryError(SquireError):
    """Raised when a retry operation failed."""
