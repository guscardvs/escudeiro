from collections.abc import AsyncGenerator, Generator, Mapping, Sequence
from http import HTTPStatus
from typing import (
    Any,
    Literal,
    overload,
    override,
)

import aiohttp

from escudeiro.context import AsyncAdapter
from escudeiro.contrib.aws.auth import AwsAuthV4
from escudeiro.contrib.aws.credentials import Credentials
from escudeiro.contrib.aws.exc import InvalidParam
from escudeiro.contrib.aws.http.opts import Opts
from escudeiro.contrib.aws.http.response import ResponseProxy
from escudeiro.contrib.aws.typedef import GET, HEAD, POST, PUT, Services
from escudeiro.data import data
from escudeiro.lazyfields import lazyfield
from escudeiro.url import URL


@data
class AsyncAuthHttpClient:
    credentials: Credentials
    service: Services
    use_default_headers: bool = True
    verify_ssl: bool = True

    @lazyfield
    def aws_auth(self):
        return AwsAuthV4(
            self.credentials, self.service, self.use_default_headers
        )

    @lazyfield
    def session(self) -> aiohttp.ClientSession:
        session = aiohttp.ClientSession()
        session.verify = self.verify_ssl
        return session

    @property
    def is_closed(self):
        return self.session.closed

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.close()

    async def close(self):
        await self.session.close()

    async def do[T](self, opts: Opts[T]) -> T:
        response: aiohttp.ClientResponse = await self._methods[opts.method](
            self, **opts.kwargs()
        )
        return opts.response_handler(
            ResponseProxy(
                opts.url,
                headers=response.headers,
                status_code=HTTPStatus(response.status),
                content=await response.read(),
            )
        )

    async def iter[T](
        self, opt_generator: Generator[Opts[T], None, None]
    ) -> AsyncGenerator[T]:
        for item in opt_generator:
            yield await self.do(item)

    async def exhaust[T](
        self, opt_generator: Generator[Opts[T]]
    ) -> Sequence[T]:
        return [await self.do(item) for item in opt_generator]

    async def exhaust_with_null(
        self, opt_generator: Generator[Opts, None, None]
    ) -> None:
        _ = await self.exhaust(opt_generator)

    async def head(
        self,
        url: URL,
        headers: Mapping[str, str] | None = None,
        raw: bool = False,
    ):
        headers = headers or {}
        headers = (
            headers
            if raw
            else self.aws_auth.headers(HEAD, url, headers=headers)
        )
        return await self.session.head(url.encode(), headers=headers)

    async def get(
        self,
        url: URL,
        headers: Mapping[str, str] | None = None,
        raw: bool = False,
    ):
        headers = headers or {}
        headers = (
            headers if raw else self.aws_auth.headers(GET, url, headers=headers)
        )
        return await self.session.get(url.encode(), headers=headers)

    @overload
    async def post(
        self,
        url: URL,
        data: bytes = b"",
        headers: Mapping[str, str] | None = None,
        files: Mapping[str, bytes] | None = None,
        raw: bool = False,
    ) -> aiohttp.ClientResponse: ...

    @overload
    async def post(
        self,
        url: URL,
        data: Mapping[str, Any],
        headers: Mapping[str, str] | None = None,
        files: Mapping[str, bytes] | None = None,
        *,
        raw: Literal[True],
    ) -> aiohttp.ClientResponse: ...

    async def post(
        self,
        url: URL,
        data: bytes | Mapping[str, Any] = b"",
        headers: Mapping[str, str] | None = None,
        files: Mapping[str, bytes] | None = None,
        raw: bool = False,
    ):
        headers = headers or {}
        if not raw:
            if not isinstance(data, bytes):
                raise InvalidParam(
                    "data", data, "Requests using data as mapping must be raw"
                )
            headers = self.aws_auth.headers(
                POST, url, headers=headers, data=data
            )
        if files:
            if isinstance(data, bytes):
                raise InvalidParam(
                    "data",
                    data,
                    "Requests using files must have mapping as files",
                )
            data = {**data, **files}
        return await self.session.post(url.encode(), data=data, headers=headers)

    async def put(
        self,
        url: URL,
        data: bytes | Mapping[str, Any] = b"",
        headers: Mapping[str, str] | None = None,
        files: Mapping[str, bytes] | None = None,
        raw: bool = False,
    ):
        headers = headers or {}
        if not raw:
            if not isinstance(data, bytes):
                raise InvalidParam(
                    "data", data, "Requests using data as mapping must be raw"
                )
            headers = self.aws_auth.headers(
                PUT, url, headers=headers, data=data
            )
        if files:
            if isinstance(data, bytes):
                raise InvalidParam(
                    "data",
                    data,
                    "Requests using files must have mapping as files",
                )
            data = {**data, **files}
        return await self.session.put(url.encode(), data=data, headers=headers)

    _methods = {
        GET: get,
        POST: post,
        PUT: put,
        HEAD: head,
    }


@data
class AsyncAuthHttpAdapter(AsyncAdapter[AsyncAuthHttpClient]):
    credentials: Credentials
    service: Services
    use_default_headers: bool = True
    verify_ssl: bool = True

    @override
    async def is_closed(self, client: AsyncAuthHttpClient) -> bool:
        return client.is_closed

    @override
    async def release(self, client: AsyncAuthHttpClient) -> None:
        await client.close()

    @override
    async def new(self):
        return AsyncAuthHttpClient(
            self.credentials,
            self.service,
            self.use_default_headers,
            self.verify_ssl,
        )
