import os
from collections.abc import Callable, Sequence
from functools import total_ordering
from pathlib import Path
from typing import Any, override

from escudeiro.config.concepts import Env
from escudeiro.config.core.utils import valid_path
from escudeiro.config.interface import MISSING, default_cast
from escudeiro.data import call_init, data, field
from escudeiro.exc import InvalidCast
from escudeiro.exc.errors import MissingName
from escudeiro.lazyfields import lazyfield
from escudeiro.misc import sentence
from escudeiro.misc.strings import is_none

from .config import Config
from .mapping import DEFAULT_MAPPING, EnvMapping


@total_ordering
@data(order=False)
class DotFile:
    """
    Represents a configuration dotfile associated with a specific environment.

    Attributes:
        filename (Union[str, Path]): The filename or path of the dotfile.
        env (Env): The environment associated with the dotfile.
        apply_to_lower (bool): Indicates whether the dotfile should be applied to lower-priority environments.
    """

    filename: str | Path
    env: Env
    cascade: bool = field(default=False)

    def __gt__(self, other: "Env | DotFile | Any") -> bool:
        """
        Check if the dotfile's environment is higher or equal to the given environment.

        Args:
            env (Env): The environment to compare against.

        Returns:
            bool: True if the dotfile's environment is higher or equal to the given environment, False otherwise.
        """
        if isinstance(other, Env):
            return self.env > other
        if isinstance(other, DotFile):
            return self.env > other.env
        return NotImplemented

    @override
    def __eq__(self, other: "Env | DotFile | Any", /) -> bool:
        if isinstance(other, Env):
            return self.env == other
        if isinstance(other, DotFile):
            return self.env == other.env
        return object.__eq__(self, other)


def default_rule(_: Env):
    return False


@data
class EnvConfig(Config):
    """
    Extended configuration class that supports environment-specific configurations.
    """

    mapping: EnvMapping = field(default=DEFAULT_MAPPING, repr=False)
    env_var: str = "CONFIG_ENV"
    env_cast: Callable[[str], Env] = Env
    dotfiles: Sequence[DotFile] = ()
    ignore_default_rule: Callable[[Env], bool] = default_rule
    default_env: Env | None = None
    strict: bool = True

    def __init__(
        self,
        *dotfiles: DotFile,
        env_var: str = "CONFIG_ENV",
        mapping: EnvMapping = DEFAULT_MAPPING,
        ignore_default_rule: Callable[[Env], bool] = default_rule,
        env_cast: Callable[[str], Env] = Env,
        default_env: Env | None = None,
        strict: bool = True,
    ) -> None:
        """
        Initialize the EnvConfig instance.

        Args:
            *dotfiles (DotFile): One or more DotFile instances representing configuration dotfiles.
            env_var (str): The name of the environment variable to determine the current environment.
            mapping (EnvMapping): An environment mapping to use for configuration values.
            ignore_default_rule (Callable[[Env], bool]): A callable to determine whether to ignore default values.
            env_cast (Callable[[str], Env]): A callable to cast the environment name to an Env enum value.
        """
        call_init(
            self,
            env_var=env_var,
            mapping=mapping,
            dotfiles=dotfiles,
            ignore_default_rule=ignore_default_rule,
            env_cast=env_cast,
            default_env=default_env,
            strict=strict,
        )

    def __post_init__(self):
        if self.dotfile:
            self._load_file(self.dotfile.filename)

    @lazyfield
    def env(self) -> Env | None:
        """
        Get the current environment from the configuration.

        The default env is used only when the variable is absent (or null
        like); a value that does not name an environment always raises.

        Returns:
            Env | None: The current environment.
        """
        raw = self._get_val(self.env_var)
        if isinstance(raw, str) and not is_none(raw):
            try:
                env: Env | None = self.env_cast(raw)
            except Exception as e:
                # the raw value is left out on purpose, it may be a typo of a secret
                raise InvalidCast(
                    sentence(f"{self.env_var} is not a valid environment")
                ) from e
            if env is not None:  # pyright: ignore[reportUnnecessaryComparison]
                return env
        if self.default_env is not None:
            return self.default_env
        if self.dotfile_override is not None:
            return Env.ALWAYS
        if self.strict:
            raise MissingName(
                sentence(
                    f"{self.env_var} not found and no default env was given"
                )
            )
        return None

    @lazyfield
    def dotfile_override(self) -> Path | None:
        """The file named by CONFIG_DOTFILE, if the variable is set."""
        raw = self._get_val("CONFIG_DOTFILE")
        if not isinstance(raw, str) or not raw:
            return None
        try:
            return valid_path(raw)
        except InvalidCast as e:
            raise InvalidCast(
                sentence("CONFIG_DOTFILE does not point to an existing path")
            ) from e

    @lazyfield
    def ignore_default(self) -> bool:
        """
        Determine whether to ignore default values based on the current environment.

        The environment is the real one: a CONFIG_DOTFILE override only
        changes which file is read, never the env the rule is applied to.

        Returns:
            bool: True if default values should be ignored, False otherwise.
        """
        env = self.env
        if not env:
            return False
        return self.ignore_default_rule(env)

    @override
    def get(
        self,
        name: str,
        cast: Callable[..., Any] = default_cast,
        default: Any | type[MISSING] = MISSING,
    ) -> Any:
        """
        Get a configuration value, with the option to cast and provide a default value.

        Args:
            name (str): The name of the configuration value.
            cast (Callable[..., Any]): A callable to cast the value.
            default (Union[Any, type[MISSING]]): The default value if the configuration is not found.

        Returns:
            Any: The configuration value.
        """
        default = MISSING if self.ignore_default else default
        return Config.get(self, name, cast, default)

    @lazyfield
    def dotfile(self) -> DotFile | None:
        """
        Get the applicable dotfile for the current environment.

        An exact match for the env wins; otherwise the closest cascading
        dotfile declared for a higher env applies.

        Returns:
            DotFile: The applicable dotfile, or None if no matching dotfile is found.
        """

        if self.dotfile_override is not None:
            return DotFile(
                filename=self.dotfile_override,
                env=Env.ALWAYS,
                cascade=True,
            )
        if not self.env:
            return None
        existing = [
            dot for dot in self.dotfiles if os.path.isfile(dot.filename)
        ]
        exact = (dot for dot in existing if dot.env is self.env)
        cascading = (dot for dot in existing if dot.cascade and dot >= self.env)
        return next(exact, None) or min(cascading, default=None)
