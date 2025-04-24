from pydantic import ConfigDict

from escudeiro.contrib.pydantic import Model
from escudeiro.misc import strings


class AwsModel(Model):
    model_config = ConfigDict(alias_generator=strings.to_pascal)
