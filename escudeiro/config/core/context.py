from contextvars import ContextVar

from escudeiro.config.concepts import Env
from escudeiro.config.core.envconfig import EnvConfig
from escudeiro.exc.errors import AlreadySet, MissingName

# built on first use, so CONFIG_ENV set after import is still honored
_default_config: EnvConfig | None = None
config = ContextVar[EnvConfig | None]("config", default=None)


def get_config() -> EnvConfig:
    """Get the current configuration."""
    global _default_config
    if (current := config.get()) is not None:
        return current
    if _default_config is None:
        _default_config = EnvConfig(strict=False)
    return _default_config


def set_config(new_config: EnvConfig) -> None:
    """Set a new configuration."""
    if config.get() is not None:
        raise AlreadySet("Configuration has already been set.")
    _ = config.set(new_config)


def get_env() -> Env:
    """Get the current environment."""
    current = get_config()
    if (env := current.env) is None:
        raise MissingName(
            f"{current.env_var} not found and no default was given."
        )
    return env
