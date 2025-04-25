from escudeiro.exc import SquireError


class DatabaseDriverError(SquireError):
    """Base error for all errors in the contrib.sqlalchemy module."""


class MissingDriverError(DatabaseDriverError):
    """Raised when required driver(s) could not be imported during validation."""


class InvalidDriverError(ValueError, DatabaseDriverError):
    """Raised when using Driver.CUSTOM without providing an explicit DriverPair or Dialect."""


class DriverNotImplementedError(NotImplementedError, DatabaseDriverError):
    """Raised when a Driver enum has no default DriverPair or Dialect mapping."""
