import pathlib
from enum import auto
from typing import NamedTuple

from escudeiro.autodiscovery import smart_import
from escudeiro.contrib.sqlalchemy.exc import MissingDriverError
from escudeiro.misc import SnakeEnum


class Driver(SnakeEnum):
    POSTGRESQL = auto()
    MYSQL = auto()
    MARIADB = auto()
    MSSQL = auto()
    SQLITE = auto()
    COCKROACHDB = auto()
    CUSTOM = auto()


class Paradigm(SnakeEnum):
    ASYNCIO = auto()
    SYNC = auto()
    ALL = auto()


class DriverPair(NamedTuple):
    sync: str
    asyncio: str
    extras: tuple[str, ...] = ()


driver_mapping = {
    Driver.POSTGRESQL: DriverPair("psycopg2", "asyncpg"),
    Driver.MYSQL: DriverPair("pymysql", "aiomysql"),
    Driver.MARIADB: DriverPair("pymysql", "aiomysql"),
    Driver.MSSQL: DriverPair("pyodbc", "aioodbc"),
    Driver.SQLITE: DriverPair("pysqlite", "aiosqlite"),
    Driver.COCKROACHDB: DriverPair(
        "psycopg2", "asyncpg", ("sqlalchemy-cockroachdb",)
    ),
}


def _is_valid_driver(drivername: str) -> bool:
    try:
        _ = smart_import(drivername, pathlib.Path.as_posix)
        return True
    except ImportError:
        return False


def validate_pair(pair: DriverPair, validate: Paradigm) -> None:
    """Validates a (sync, async) driver pair.

    Args:
        pair (DriverPair): The driver names to validate.
        validate (Paradigm): Validation mode.

    Raises:
        ImportError: If any specified driver is missing.
    """
    is_missing: list[str] = []

    match validate:
        case Paradigm.ALL:
            for drivername in (pair.sync, pair.asyncio):
                if not _is_valid_driver(drivername):
                    is_missing.append(drivername)
        case Paradigm.SYNC:
            if not _is_valid_driver(pair.sync):
                is_missing.append(pair.sync)
        case Paradigm.ASYNCIO:
            if not _is_valid_driver(pair.asyncio):
                is_missing.append(pair.asyncio)

    for x in pair.extras:
        if not _is_valid_driver(x):
            is_missing.append(x)

    if is_missing:
        raise MissingDriverError(
            "One or more of the required drivers are missing.", is_missing
        )


def validate_driver(driver: Driver, validate: Paradigm) -> None:
    """Validates drivers for a given Driver enum.

    Args:
        driver (Driver): Enum member to validate.
        validate (Literal['sync', 'asyncio', 'all']): Validation mode.

    Raises:
        ImportError: If any driver is missing.
    """
    if driver is Driver.CUSTOM:
        return
    pair = driver_mapping[driver]
    validate_pair(pair, validate)
