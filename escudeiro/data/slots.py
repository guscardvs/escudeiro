from collections.abc import Sequence
from typing import Any, final


@final
class slot:
    __slots__ = ("slots",)

    def __init__(self, *slots: str):
        self.slots = slots

    def __call__[T](self, value: T) -> T:
        object.__setattr__(value, "__squire_slotted__", self.slots)
        return value

    @staticmethod
    def get_slots(value: Any) -> Sequence[str] | None:
        try:
            return object.__getattribute__(value, "__squire_slotted__")
        except AttributeError:
            return None

    @classmethod
    def make[T](cls, *slots: str, value: T) -> T:
        return cls(*slots)(value)
