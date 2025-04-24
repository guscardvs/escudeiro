from http import HTTPStatus
from typing import Any, Protocol

from escudeiro.exc import SquireError
from escudeiro.url import URL


class AwsError(SquireError):
    """Base exception for gyver-aws"""


class InvalidParam(AwsError):
    def __init__(self, name: str, val: Any, message: str) -> None:
        super().__init__(name, val, message)
        self.name = name
        self.val = val
        self.message = message


class ResponseProtocol(Protocol):
    @property
    def url(self) -> URL: ...

    @property
    def status_code(self) -> HTTPStatus: ...


class RequestFailed(AwsError):
    def __init__(self, response: ResponseProtocol) -> None:
        super().__init__(response.status_code, response.url.encode())
        self.response = response


class NotFound(AwsError):
    def __init__(self, object_name: str, service_name: str) -> None:
        super().__init__(object_name, service_name)


class UnexpectedResponse(AwsError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
