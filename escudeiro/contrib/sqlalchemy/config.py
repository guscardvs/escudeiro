from typing import ClassVar, NamedTuple

from escudeiro.contrib.sqlalchemy.exc import (
    DriverNotImplementedError,
    InvalidDriverError,
)
from escudeiro.data import data, field
from escudeiro.misc import lazymethod
from escudeiro.url import URL

from .dialects import DEFAULT_DIALECTS, Dialect
from .drivers import Driver

INT_NOTSET = -1
STR_NOTSET = ""
DEFAULT_POOL_SIZE = 4
HOUR = 3600


@data
class PoolConfig:
    size: int = DEFAULT_POOL_SIZE
    recycle: int = HOUR
    max_overflow: int = 0


class _DialectURI(NamedTuple):
    sync: URL
    asyncio: URL


@data
class DatabaseConfig:
    __prefix__: ClassVar[str] = "db"

    driver: Driver
    host: str
    port: int = INT_NOTSET
    user: str = STR_NOTSET
    password: str = STR_NOTSET
    name: str = STR_NOTSET
    pool: PoolConfig = field(default_factory=PoolConfig)
    dialect: Dialect | None = None

    @lazymethod
    def get_port(self) -> int:
        return (
            self.port
            if self.port != INT_NOTSET
            else self.get_dialect().default_port
        )

    @lazymethod
    def get_dialect(self) -> Dialect:
        if self.driver is Driver.CUSTOM and self.dialect is None:
            raise InvalidDriverError(
                "Driver.CUSTOM requires an explicit 'dialect' configuration. "
                + "No default Dialect is available for custom drivers—"
                + "please provide a Dialect instance explicitly."
            )
        dialect = self.dialect or DEFAULT_DIALECTS.get(self.driver)

        if dialect is None:
            raise DriverNotImplementedError(
                f"No default Dialect is configured for driver '{self.driver}'. "
                + "Please provide a 'dialect' explicitly in your configuration."
            )
        return dialect

    @lazymethod
    def make_uris(self) -> _DialectURI:
        dialect = self.get_dialect()
        sync_scheme, async_scheme = dialect.get_schemes()

        if dialect.only_host:
            base_uri = URL.from_netloc(host=self.host)
            return _DialectURI(
                base_uri.copy().set(scheme=sync_scheme),
                base_uri.copy().set(scheme=async_scheme),
            )

        url = URL.from_netloc(
            host=self.host,
            port=self.get_port(),
            username=self.user,
            password=self.password,
        ).add(path=self.name)

        return _DialectURI(
            url.copy().set(scheme=sync_scheme),
            url.copy().set(scheme=async_scheme),
        )

    @property
    def async_uri(self) -> str:
        return self.make_uris().asyncio.encode()

    @property
    def sync_uri(self) -> str:
        return self.make_uris().sync.encode()
