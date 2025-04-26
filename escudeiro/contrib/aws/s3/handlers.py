import base64
import io
import mimetypes
import re
from collections.abc import Generator, Sequence
from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Any, cast
from xml.etree import ElementTree as ET

from escudeiro.contrib.aws.auth import AwsAuthV4, amz_dateformat
from escudeiro.contrib.aws.constants import constants
from escudeiro.contrib.aws.credentials import Credentials
from escudeiro.contrib.aws.exc import (
    InvalidParam,
    NotFound,
    RequestFailed,
    UnexpectedResponse,
)
from escudeiro.contrib.aws.http.opts import Opts, response_failed_handler
from escudeiro.contrib.aws.http.response import ResponseProxy
from escudeiro.contrib.aws.s3.models import (
    CopyParams,
    FileInfo,
    ObjectTuple,
    StorageClass,
    TokenHolder,
    UploadParams,
)
from escudeiro.contrib.aws.typedef import (
    GET,
    HEAD,
    POST,
    PUT,
    Services,
)
from escudeiro.data import data
from escudeiro.data.converters.utils import fromdict
from escudeiro.lazyfields import lazyfield
from escudeiro.misc import jsonx, lazymethod
from escudeiro.misc.iterx import next_or
from escudeiro.url.path import Path
from escudeiro.url.url import URL

HOST_TEMPLATE = "{scheme}://{bucket}.s3.{region}.{host}"
DAY = 86400
WEEK = 7 * DAY
xmlns_re = re.compile(f' xmlns="{re.escape(constants.xmlns)}"'.encode())


@data
class S3Object:
    credentials: Credentials
    bucket_name: str

    def _make_bucket_uri(self, bucket_name: str) -> URL:
        if self.credentials.endpoint_url:
            endpoint_url = URL(self.credentials.endpoint_url)
            return URL(
                HOST_TEMPLATE.format(
                    scheme=endpoint_url.scheme,
                    bucket=bucket_name,
                    region=self.credentials.region,
                    host=endpoint_url.netloc.encode(),
                )
            )
        else:
            return URL(
                HOST_TEMPLATE.format(
                    scheme="https",
                    bucket=bucket_name,
                    region=self.credentials.region,
                    host="amazonaws.com",
                )
            )

    @lazyfield
    def bucket_uri(self) -> URL:
        return self._make_bucket_uri(self.bucket_name)

    @lazymethod
    def get_auth(self) -> AwsAuthV4:
        return AwsAuthV4(self.credentials, Services.S3)

    def get_mimetype(self, object_name: str, content_type: str | None) -> str:
        return (
            content_type
            or next_or(mimetypes.guess_type(object_name.strip("/")))
            or constants.default_mimetype
        )

    def object_url(self, object_name: str) -> URL:
        return self.bucket_uri.copy_add(path=object_name)

    def generate_presigned_url(
        self,
        object_name: str,
        expires: int = DAY,
        version: str | None = None,
    ) -> URL:
        if not (1 <= expires <= WEEK):
            raise InvalidParam(
                "expires",
                expires,
                f"Expires must be greater than 1 and lower than a {WEEK=}",
            )
        timestamp = constants.timezone.now()
        url = self.object_url(object_name).add(
            query={
                "X-Amz-Algorithm": constants.aws_algorithm,
                "X-Amz-Credential": self.get_auth().make_credential(timestamp),
                "X-Amz-Date": amz_dateformat(timestamp),
                "X-Amz-Expires": str(expires),
                "X-Amz-SignedHeaders": "host",
            }
        )
        _, signature = self.get_auth().make_signature(
            GET,
            url,
            "UNSIGNED-PAYLOAD",
            timestamp,
            {"host": url.netloc.encode()},
        )
        url = url.add(query={"X-Amz-Signature": signature})
        if version is not None:
            url = url.add(query={"v": version})
        return url

    def download(self, object_name: str, version: str | None = None):
        presigned_url = self.generate_presigned_url(
            object_name, version=version
        )

        def _handler(response: ResponseProxy):
            response_failed_handler(response)
            return response.content

        return Opts(_handler, GET, url=presigned_url, raw=True)

    def _download_handler(self, response: ResponseProxy) -> bytes:
        response_failed_handler(response)
        return response.content

    def info(self, object_name: str) -> Opts[FileInfo]:
        url = self.object_url(object_name)

        def _info_handler(response: ResponseProxy):
            if not response.ok:
                if response.status_code == HTTPStatus.NOT_FOUND:
                    raise NotFound(object_name, Services.S3)

            # formatting last_modifies from this format:
            # Fri, 27 Jan 2023 10:21:12 GMT
            return FileInfo(
                key=object_name,
                last_modified=datetime.strptime(
                    response.headers["Last-Modified"],
                    "%a, %d %b %Y %H:%M:%S GMT",
                ),
                size=int(
                    str(filter(str.isdigit, response.headers["Content-Length"]))
                ),
                e_tag=response.headers["ETag"].strip("\"'"),
                storage_class=StorageClass(
                    response.headers.get("x-amz-storage-class")
                ),
            )

        return Opts(_info_handler, HEAD, url)

    def delete_many(self, *objects: ObjectTuple) -> Opts[None]:
        url = self.bucket_uri.copy_add(query={"delete": ""}, path="/")
        payload = self._build_delete_payload(objects)
        return Opts(
            response_failed_handler,
            POST,
            url,
            data=payload,
            headers={"Content-Type": "text/xml"},
        )

    def _build_delete_payload(self, objects: Sequence[ObjectTuple]) -> bytes:
        root = ET.Element("Delete", xmlns=constants.xmlns)
        for item in objects:
            object_el = ET.SubElement(root, "Object")
            ET.SubElement(object_el, "Key").text = item.object_name
            if item.version:
                ET.SubElement(object_el, "VersionId").text = item.version
        et = ET.ElementTree(root)
        stream = io.BytesIO()
        et.write(
            stream, encoding=constants.default_encoding, xml_declaration=True
        )
        return stream.getvalue()

    def upload(
        self,
        object_name: str,
        content: bytes,
        content_type: str | None = None,
        request_timeout_seconds: int = 30 * 60,
    ) -> Opts[None]:
        mimetype = self.get_mimetype(object_name, content_type)
        content_size = len(content)
        parts = object_name.strip("/").rsplit("/", maxsplit=1)
        fields = self._upload_object_fields(
            parts[0] if len(parts) > 1 else "",
            parts[-1],
            constants.timezone.now()
            + timedelta(seconds=request_timeout_seconds),
            mimetype,
            content_size,
        )

        def _handler(response: ResponseProxy):
            if response.status_code != HTTPStatus.NO_CONTENT:
                raise RequestFailed(response)

        return Opts(
            _handler,
            POST,
            self.bucket_uri.copy(),
            data=fields,
            files={"file": content},
            raw=True,
        )

    def _upload_object_fields(
        self,
        path: str,
        filename: str,
        expires: datetime,
        mimetype: str,
        content_size: int,
    ) -> UploadParams:
        key = "/".join(item.strip("/") for item in (path, filename) if item)
        policy_conditions = [
            {"bucket": self.bucket_name},
            {"key": key},
            {"content-type": mimetype},
            ["content-length-range", content_size, content_size],
        ]
        content_disposition_fields = {}
        policy_conditions.append(
            content_disposition_fields := {
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
        timestamp = constants.timezone.now()
        policy_conditions.extend(self._upload_additional_conditions(timestamp))

        expiration = expires or timestamp + timedelta(seconds=60)
        policy: dict[str, Any] = {
            "expiration": f"{expiration:%Y-%m-%dT%H:%M:%SZ}",
            "conditions": policy_conditions,
        }
        b64_policy = base64.b64encode(jsonx.dumps(policy).encode()).decode()
        return cast(
            UploadParams,  # pyright: ignore[reportInvalidCast]
            {
                "key": key,
                "content-type": mimetype,
                **content_disposition_fields,
                "policy": b64_policy,
                **self._signed_upload_fields(timestamp, b64_policy),
            },
        )

    def _upload_additional_conditions(self, timestamp: datetime):
        return [
            {"x-amz-credential": self.get_auth().make_credential(timestamp)},
            {"x-amz-algorithm": constants.aws_algorithm},
            {"x-amz-date": amz_dateformat(timestamp)},
        ]

    def _signed_upload_fields(self, timestamp: datetime, policy: str):
        return {
            "x-amz-algorithm": constants.aws_algorithm,
            "x-amz-credential": self.get_auth().make_credential(timestamp),
            "x-amz-date": amz_dateformat(timestamp),
            "x-amz-signature": self.get_auth().aws4_sign_string(
                policy, timestamp
            ),
        }

    def copy(
        self, source: CopyParams, target: CopyParams, prevalidate: bool = True
    ) -> Generator[Opts]:
        target_url = self._make_bucket_uri(target.bucket).add(
            path=target.object_name
        )
        if prevalidate:
            yield S3Object(self.credentials, source.bucket).info(
                source.object_name
            )
        yield Opts(
            response_failed_handler,
            PUT,
            target_url,
            headers={
                "x-amz-copy-source": Path(source.bucket)
                .add(source.object_name)
                .encode()
            },
        )

    def copy_from(
        self,
        source: CopyParams,
        target_name: str | None = None,
        prevalidate: bool = True,
    ) -> Generator[Opts]:
        return self.copy(
            source,
            CopyParams(target_name or source.object_name, self.bucket_name),
            prevalidate,
        )

    def copy_to(
        self,
        target: CopyParams,
        source_name: str | None = None,
        prevalidate: bool = True,
    ) -> Generator[Opts]:
        return self.copy(
            CopyParams(source_name or target.object_name, self.bucket_name),
            target,
            prevalidate,
        )

    def scroll(
        self,
        prefix: str | None = None,
        chunksize: int = constants.max_chunksize,
    ) -> Generator[Opts[Sequence[FileInfo]]]:
        if not (1 <= chunksize <= constants.max_chunksize):
            raise InvalidParam(
                "chunksize",
                chunksize,
                "Chunksize must be greater "
                + f"than 1 and lesser than {constants.max_chunksize}",
            )

        url = self.bucket_uri.copy_add(
            query={"list-type": "2", "max-keys": str(chunksize)}, path="/"
        )
        if prefix is not None:
            url = url.add(query={"prefix": prefix.removeprefix("/")})

        token_holder = TokenHolder()
        fetch_handler = self._get_fetch_handler(token_holder)
        while True:
            current_url = url.copy()
            if token := token_holder.continuation_token:
                current_url = current_url.add(
                    query={"continuation-token": token}
                )
            yield Opts(fetch_handler, GET, url)
            if token_holder.should_break:
                break

    def _get_fetch_handler(self, token_holder: TokenHolder):
        def _fetch_handler(response: ResponseProxy) -> Sequence[FileInfo]:
            response_failed_handler(response)
            xml_content = ET.fromstring(xmlns_re.sub(b"", response.content))
            results = []
            for contents in xml_content.findall("Contents"):
                results.append(
                    fromdict(
                        FileInfo, {items.tag: items.text for items in contents}
                    )
                )
            if self._list_is_exhausted(xml_content):
                token_holder.should_break = True
            else:
                if (t := xml_content.find("NextContinuationToken")) is not None:
                    token_holder.continuation_token = t.text
                else:
                    raise UnexpectedResponse("unexpected response from S3")
            return results

        return _fetch_handler

    def _list_is_exhausted(self, xml_content: ET.Element[str]) -> bool:
        return (
            t := xml_content.find("IsTruncated")
        ) is not None and t.text == "false"
