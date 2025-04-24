from collections.abc import Mapping
from http import HTTPStatus

from escudeiro.data import data
from escudeiro.url import URL


@data
class ResponseProxy:
    url: URL
    headers: Mapping[str, str]
    status_code: HTTPStatus
    content: bytes

    @property
    def ok(self):
        return self.status_code < HTTPStatus.BAD_REQUEST
