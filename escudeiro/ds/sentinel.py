from typing import Any, TypeVar, override

_registry: dict[str, Any] = {}
T = TypeVar("T")


class _BaseSentinel:
    """Internal base for sentinel instances."""

    @override
    def __repr__(self) -> str:
        name = object.__getattribute__(self, "_name")
        value = object.__getattribute__(self, "_value")
        if value is self:
            return name
        return f"{name}({value!r})"

    @override
    def __reduce__(self) -> tuple[type["_BaseSentinel"], tuple[str, str, Any]]:
        return (
            self.__class__,
            (
                object.__getattribute__(self, "_name"),
                object.__getattribute__(self, "_module_name"),
                object.__getattribute__(self, "_value"),
            ),
        )


class Sentinel:
    """Unique sentinel values.

    This class is designed to be used as a decorator to create unique sentinel
    objects. When a class is decorated with `@Sentinel`, it can either create
    a single unique sentinel instance (if the decorated class is empty) or
    a collection of unique sentinel instances (if the decorated class defines members).
    """

    def __new__(cls, decorated_cls: type[T]) -> T | Any:
        name = decorated_cls.__name__
        module_name = decorated_cls.__module__

        members = {
            k: v
            for k, v in decorated_cls.__dict__.items()
            if not k.startswith("__") and not callable(v)
        }

        if not members:
            # Case 1: Single sentinel (e.g., @Sentinel class MISSING: pass)
            registry_key = f"{module_name}-{name}"
            sentinel_instance = _registry.get(registry_key, None)
            if sentinel_instance is not None:
                return sentinel_instance

            sentinel_instance = _BaseSentinel.__new__(_BaseSentinel)
            object.__setattr__(sentinel_instance, "_name", name)
            object.__setattr__(sentinel_instance, "_module_name", module_name)
            object.__setattr__(sentinel_instance, "_value", sentinel_instance)
            _registry.setdefault(registry_key, sentinel_instance)
            return sentinel_instance

        # Case 2: Enum-like sentinel (e.g., @Sentinel class STATUS: PENDING = 1)
        new_type = type(name, (object,), {})
        object.__setattr__(new_type, "__module__", module_name)

        for member_name, member_value in members.items():
            member_sentinel_name = f"{name}.{member_name}"
            member_sentinel_module = module_name

            registry_key = f"{member_sentinel_module}-{member_sentinel_name}"
            member_sentinel_instance = _registry.get(registry_key, None)

            if member_sentinel_instance is None:
                member_sentinel_instance = _BaseSentinel.__new__(_BaseSentinel)
                object.__setattr__(
                    member_sentinel_instance, "_name", member_sentinel_name
                )
                object.__setattr__(
                    member_sentinel_instance,
                    "_module_name",
                    member_sentinel_module,
                )
                object.__setattr__(
                    member_sentinel_instance, "_value", member_value
                )
                _registry.setdefault(registry_key, member_sentinel_instance)

            setattr(new_type, member_name, member_sentinel_instance)

        return new_type
