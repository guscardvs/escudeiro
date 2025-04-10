from typing import Any, TypeVar

from escudeiro.config.interface import ConfigLike
from escudeiro.data import data
from escudeiro.lazyfields import lazyfield

from .factory import DEFAULT_CONFIG, AdapterConfigFactory

T = TypeVar("T")


@data
class CachedFactory:
    config: ConfigLike = DEFAULT_CONFIG

    @lazyfield
    def _cache(self) -> dict[tuple[str, type], Any]:
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
        if memo := self._cache.get((__prefix__, model_cls)):
            return memo
        if (memo := self._primary.get(model_cls)) and not __prefix__:
            return memo
        memo = self._internal.load(
            model_cls,
            __prefix__,
            __sep__,
            presets=presets,
            **defaults,
        )
        self._cache[(__prefix__, model_cls)] = memo
        if __primary__:
            self._primary[model_cls] = memo
        return memo
