from escudeiro.contrib.sqlalchemy.exc import (
    DriverNotImplementedError,
    InvalidDriverError,
)
from escudeiro.data import data
from escudeiro.misc import lazymethod

from .drivers import Driver, DriverPair, Paradigm, driver_mapping, validate_pair


@data
class Dialect:
    default_port: int
    driver: Driver
    only_host: bool
    paradigm: Paradigm
    pair: DriverPair | None = None

    @lazymethod
    def get_pair(self) -> DriverPair:
        """
        Returns the effective driver pair for this dialect.

        User-provided `pair` takes precedence over built-in driver mappings.
        Raises errors if no usable configuration is found.
        """
        if self.driver is Driver.CUSTOM and self.pair is None:
            raise InvalidDriverError(
                "Driver.CUSTOM requires an explicit 'pair' configuration."
                + " Provide a DriverPair instance when using a custom driver."
            )
        pair = self.pair or driver_mapping.get(self.driver)

        if pair is None:
            raise DriverNotImplementedError(
                f"No default DriverPair is configured for driver: {self.driver}."
                + " Please provide a 'pair' explicitly."
            )

        validate_pair(pair, self.paradigm)
        return pair

    def get_schemes(self) -> tuple[str, str]:
        """
        Returns the SQLAlchemy dialect+driver schemes for sync and async paradigms.

        Returns a pair `(sync_scheme, async_scheme)`, where the unused side will be
        an empty string if the configured paradigm is not applicable.

        Examples:
        - Paradigm.SYNC ➜ (driver+psycopg2, "")
        - Paradigm.ASYNCIO ➜ ("", driver+asyncpg)
        - Paradigm.ALL ➜ ("driver+psycopg2", "driver+asyncpg")
        """

        scheme_template = f"{self.driver}+{{driver}}"
        pair = self.get_pair()

        match self.paradigm:
            case Paradigm.SYNC:
                return scheme_template.format(driver=pair.sync), ""
            case Paradigm.ASYNCIO:
                return "", scheme_template.format(driver=pair.asyncio)
            case Paradigm.ALL:
                return (
                    scheme_template.format(driver=pair.sync),
                    scheme_template.format(driver=pair.asyncio),
                )


DEFAULT_DIALECTS: dict[Driver, Dialect] = {
    Driver.MYSQL: Dialect(
        default_port=3306,
        driver=Driver.MYSQL,
        only_host=False,
        paradigm=Paradigm.ALL,
    ),
    Driver.POSTGRESQL: Dialect(
        default_port=5432,
        driver=Driver.POSTGRESQL,
        only_host=False,
        paradigm=Paradigm.ALL,
    ),
    Driver.MARIADB: Dialect(
        default_port=3306,
        driver=Driver.MARIADB,
        only_host=False,
        paradigm=Paradigm.ALL,
    ),
    Driver.MSSQL: Dialect(
        default_port=1433,
        driver=Driver.MSSQL,
        only_host=False,
        paradigm=Paradigm.ALL,
    ),
    Driver.SQLITE: Dialect(
        default_port=0,
        driver=Driver.SQLITE,
        only_host=True,
        paradigm=Paradigm.ALL,
    ),
    Driver.COCKROACHDB: Dialect(
        default_port=26257,
        driver=Driver.COCKROACHDB,
        only_host=False,
        paradigm=Paradigm.ALL,
    ),
}
