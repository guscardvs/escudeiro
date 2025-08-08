import os
from collections.abc import Callable, Sequence
from functools import total_ordering
from pathlib import Path
from typing import Any, override

from escudeiro.config.concepts import Env
from escudeiro.config.core.utils import (
    none_is_missing,
    null_cast,
    valid_path,
)
from escudeiro.config.interface import MISSING, default_cast
from escudeiro.data import call_init, data, field
from escudeiro.exc import SquireError
from escudeiro.exc.errors import MissingName
from escudeiro.lazyfields import lazyfield
from escudeiro.misc.functions import Caster

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

    mapping: EnvMapping = DEFAULT_MAPPING
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
            with open(self.dotfile.filename) as buffer:
                self.file_values.update(self._read_file(buffer))

    @lazyfield
    def env(self) -> Env | None:
        """
        Get the current environment from the configuration.

        Returns:
            Env | None: The current environment.
        """

        caster = none_is_missing(Caster(self.env_cast).or_(null_cast))
        if not self.strict:
            caster = Caster(caster).safe_cast((MissingName,))
        try:
            result = Config.get(
                self,
                self.env_var,
                caster,
                self.default_env,
            )
        except SquireError:
            if not self.default_env:
                raise
            result = None
        return result or self.default_env

    @lazyfield
    def ignore_default(self) -> bool:
        """
        Determine whether to ignore default values based on the current environment.

        Returns:
            bool: True if default values should be ignored, False otherwise.
        """
        env = self.env or self.default_env
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

        Returns:
            DotFile: The applicable dotfile, or None if no matching dotfile is found.
        """

        if dotfile_path := Config.get(
            self,
            "CONFIG_DOTFILE",
            Caster(valid_path).optional,
            None,
        ):
            if dotfile_path.exists():
                EnvConfig.env.__set__(self, Env.ALWAYS)
                return DotFile(
                    filename=dotfile_path,
                    env=Env.ALWAYS,
                    cascade=True,
                )
        if not self.env:
            return None
        for dot in sorted(self.dotfiles, reverse=True):
            if not dot >= self.env:
                break
            if dot.env is not self.env and not (
                dot.cascade and dot >= self.env
            ):
                continue
            if not os.path.isfile(dot.filename):
                continue
            return dot
