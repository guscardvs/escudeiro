from typing import Any, cast, override

_registry: dict[str, Any] = {}


class Sentinel:
    """Internal base for sentinel instances."""

    @override
    def __repr__(self) -> str:
        name = object.__getattribute__(self, "_name")
        value = object.__getattribute__(self, "_value")
        return name if value is self else f"{value!r}"

    @override
    def __reduce__(self) -> tuple[type["Sentinel"], tuple[str, str, Any]]:
        return (
            self.__class__,
            (
                object.__getattribute__(self, "_name"),
                object.__getattribute__(self, "_module_name"),
                object.__getattribute__(self, "_value"),
            ),
        )


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
        registry_key = f"{module_name}-{name}"
        sentinel_instance = _registry.get(registry_key, None)
        if sentinel_instance is not None:
            return sentinel_instance

        sentinel_instance = Sentinel.__new__(Sentinel)
        object.__setattr__(sentinel_instance, "_name", name)
        object.__setattr__(sentinel_instance, "_module_name", module_name)
        object.__setattr__(sentinel_instance, "_value", sentinel_instance)
        _registry.setdefault(registry_key, sentinel_instance)
        return cast(T, sentinel_instance)

    # Case 2: Enum-like sentinel (e.g., @sentinel class STATUS: PENDING = 1)
    new_type = type(name, (object,), {"__module__": module_name})

    for member_name, member_value in members.items():
        member_sentinel_name = f"{name}.{member_name}"
        member_sentinel_module = module_name

        registry_key = f"{member_sentinel_module}-{member_sentinel_name}"
        final_value = _registry.setdefault(registry_key, member_value)

        setattr(new_type, member_name, final_value)

    return cast(T, new_type)
