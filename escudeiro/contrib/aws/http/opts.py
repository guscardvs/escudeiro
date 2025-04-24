from collections.abc import Callable, Generator, Mapping
from typing import Any

from escudeiro.contrib.aws.exc import RequestFailed
from escudeiro.contrib.aws.http.response import ResponseProxy
from escudeiro.contrib.aws.typedef import Methods
from escudeiro.data import data
from escudeiro.url import URL


@data
class Opts[T]:
    response_handler: Callable[[ResponseProxy], T]
    method: Methods
    url: URL
    data: bytes | Mapping[str, Any] = b""
    headers: Mapping[str, str] | None = None
    files: Mapping[str, bytes] | None = None
    raw: bool = False

    def kwargs(self):
        mapping: dict[str, Any] = {
            "url": self.url,
            "raw": self.raw,
            "headers": self.headers,
        }
        if self.files is not None:
            mapping["files"] = self.files
        if self.data:
            mapping["data"] = self.data
        return mapping


def response_failed_handler(response: ResponseProxy):
    if not response.ok:
        raise RequestFailed(response)


@data
class OptsGenerator[T]:
    generator: Generator[T]
    returns_none: bool
