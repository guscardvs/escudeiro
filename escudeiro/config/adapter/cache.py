from collections.abc import Mapping
from typing import Any, TypeVar

from escudeiro.config.interface import MISSING, ConfigLike
from escudeiro.data import data
from escudeiro.lazyfields import lazyfield

from .factory import DEFAULT_CONFIG, AdapterConfigFactory

T = TypeVar("T")


def _freeze(value: Any) -> Any:
    """Hashable stand-in for an argument, keyed by type and value."""
    if isinstance(value, Mapping):
        return frozenset((key, _freeze(item)) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return type(value), tuple(map(_freeze, value))
    if isinstance(value, (set, frozenset)):
        return type(value), frozenset(map(_freeze, value))
    try:
        _ = hash(value)
    except TypeError:
        # shortcut: unhashable opaque values are keyed by identity
        return id(value)
    return type(value), value


@data
class CachedFactory:
    config: ConfigLike = DEFAULT_CONFIG

    @lazyfield
    def _cache(self) -> dict[Any, Any]:
        return {}

    @lazyfield
    def _primary(self) -> dict[type, Any]:
        return {}

    @lazyfield
    def _internal(self) -> AdapterConfigFactory:
        return AdapterConfigFactory(self.config)

    def load(
        self,
        model_cls: type[T],
        __prefix__: str = "",
        __sep__: str = "__",
        __primary__: bool = False,
        *,
        presets: dict[str, Any] | None = None,
        **defaults: Any,
    ) -> T:
        # the primary is only a stand-in for a plain, argument-less load
        if (
            not (__prefix__ or presets or defaults)
            and (memo := self._primary.get(model_cls, MISSING)) is not MISSING
        ):
            return memo
        key = (
            model_cls,
            __prefix__,
            __sep__,
            _freeze(presets or {}),
            _freeze(defaults),
        )
        if (memo := self._cache.get(key, MISSING)) is not MISSING:
            return memo
        memo = self._internal.load(
            model_cls,
            __prefix__,
            __sep__,
            presets=presets,
            **defaults,
        )
        self._cache[key] = memo
        if __primary__:
            self._primary[model_cls] = memo
        return memo
