from typing import Any, Self, cast, override

_registry: dict[str, Any] = {}


class Sentinel[T]:
    """Internal base for sentinel instances."""

    _name: str
    _module_name: str
    _value: Any
    _is_initialized: bool = False

    def __new__(
        cls,
        name: str,
        modulename: str,
        value: Any = None,
    ) -> Self:
        registry_key = f"{modulename}:{name}"
        if self := _registry.get(registry_key):
            return self
        self = super().__new__(cls)
        _registry[registry_key] = self
        return self

    def __init__(
        self,
        name: str,
        modulename: str,
        value: Any = None,
    ) -> None:
        if self._is_initialized:
            return

        self._name = name
        self._module_name = modulename
        self._value = value if value is not None else self
        self._is_initialized = True

    @override
    def __repr__(self) -> str:
        return self._name if self._value is self else f"{self._value!r}"

    @override
    def __reduce__(self) -> tuple[type[Self], tuple[str, str, Any]]:
        return (
            self.__class__,
            (
                self._name,
                self._module_name,
                self._value if self._value is not self else None,
            ),
        )

    @override
    def __eq__(self, value: object, /) -> bool:
        if isinstance(value, Sentinel):
            return self is value
        if self._value is self:
            return NotImplemented
        return self._value == value


def sentinel[T](cls: type[T]) -> T:
    """Unique sentinel values.

    This class is designed to be used as a decorator to create unique sentinel
    objects. When a class is decorated with `@sentinel`, it can either create
    a single unique sentinel instance (if the decorated class is empty) or
    a collection of unique sentinel instances (if the decorated class defines members).
    """
    name = cls.__name__
    module_name = cls.__module__

    members = {
        k: v
        for k, v in cls.__dict__.items()
        if not k.startswith("__") and not callable(v)
    }

    # Case 1: Single sentinel (e.g., @sentinel class MISSING: pass)
    if not members:
        sentinel_instance = Sentinel(name, module_name)
        return cast(T, sentinel_instance)

    # Case 2: Enum-like sentinel (e.g., @sentinel class STATUS: PENDING = 1)
    namespace: dict[str, Any] = {"__module__": module_name}

    for member_name, member_value in members.items():
        member_sentinel_name = f"{name}.{member_name}"
        member_sentinel_module = module_name

        sentinel = Sentinel(
            member_sentinel_name, member_sentinel_module, member_value
        )
        namespace[member_name] = sentinel

    new_type = type(name, (), namespace)
    return cast(T, new_type)
