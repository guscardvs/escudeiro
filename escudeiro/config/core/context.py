from contextvars import ContextVar

from escudeiro.config.concepts import Env
from escudeiro.config.core.envconfig import EnvConfig
from escudeiro.exc.errors import AlreadySet
from escudeiro.misc import assert_notnone

_default_config = EnvConfig(strict=False)
config = ContextVar[EnvConfig]("config", default=_default_config)


def get_config() -> EnvConfig:
    """Get the current configuration."""
    return config.get()


def set_config(new_config: EnvConfig) -> None:
    """Set a new configuration."""
    if config.get() is not _default_config:
        raise AlreadySet("Configuration has already been set.")
    _ = config.set(new_config)


def get_env() -> Env:
    """Get the current environment."""
    return assert_notnone(get_config().env)
