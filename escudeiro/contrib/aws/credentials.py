from typing import ClassVar
from escudeiro.data import data


@data
class Credentials:
    __prefix__: ClassVar[str] = "aws"

    access_key_id: str
    secret_access_key: str
    region: str
    endpoint_url: str | None = None
