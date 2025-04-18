from typing import Any, ClassVar, override

from pydantic import BaseModel, ConfigDict

from escudeiro.lazyfields import lazy
from escudeiro.misc import to_camel


class Model(BaseModel):
    """
    Model is a BaseModel overload with opinions on mutability and alias generation.

    Configurations:
        - frozen: Model instances are frozen by default.
        - from_attributes: Enables from_attributes mode for this model.
        - alias_generator: Uses utils.to_camel for alias generation.
        - populate_by_name: Allows population of fields by field name.
        - ignore_types: Keeps attributes of type lazy untouched during population.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True,
        populate_by_name=True,
        ignored_types=(lazy,),
        from_attributes=True,
        alias_generator=to_camel,
    )

    @override
    def __setattr__(self, name: str, value: Any, /) -> None:
        """
        Overloads the __setattr__ method to allow lazy fields to work correctly.

        Args:
            name (str): The name of the attribute.
            value (Any): The value to set for the attribute.
        """
        if isinstance(getattr(type(self), name, None), lazy):
            object.__setattr__(self, name, value)
        else:
            return super().__setattr__(name, value)

    @override
    def __delattr__(self, name: str, /) -> None:
        if isinstance(getattr(type(self), name, None), lazy):
            object.__delattr__(self, name)
        else:
            return super().__delattr__(name)


class MutableModel(Model):
    """
    A mutable version of the Model class that allows unfreezing of instances.

    Configurations:
        - frozen: Model instances are not frozen, allowing mutability.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=False)
