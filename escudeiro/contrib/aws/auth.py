import hashlib
import hmac
from base64 import b64encode
from binascii import hexlify
from collections.abc import Mapping
from datetime import UTC, date, datetime
from functools import reduce

from escudeiro.contrib.aws.constants import constants
from escudeiro.contrib.aws.credentials import Credentials
from escudeiro.contrib.aws.typedef import Methods, Services
from escudeiro.data import data
from escudeiro.url import URL


@data
class AwsAuthV4:
    credentials: Credentials
    service: Services
    use_default_headers: bool = True

    def headers(
        self,
        method: Methods,
        url: URL,
        *,
        headers: Mapping[str, str] | None = None,
        data: bytes | None = None,
        content_type: str | None = None,
        timestamp: datetime | None = None,
    ) -> Mapping[str, str]:
        timestamp = timestamp or datetime.now(UTC)
        data = data or b""
        content_type = content_type or constants.content_type
        payload_hash = self.hash_payload(data)
        headers = self._base_headers(
            url, headers or {}, data, content_type, timestamp
        )
        signed_headers, signature = self.make_signature(
            method, url, payload_hash, timestamp, headers
        )
        credential = self.make_credential(timestamp)
        authorization_header = (
            f"{constants.aws_algorithm} Credential={credential}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )
        return {
            **headers,
            "authorization": authorization_header,
            "x-amz-content-sha256": payload_hash,
        }

    def hash_payload(self, payload: bytes | None = None) -> str:
        return hashlib.sha256(payload or b"").hexdigest()

    def _base_headers(
        self,
        url: URL,
        headers: Mapping[str, str],
        data: bytes,
        content_type: str,
        timestamp: datetime,
    ) -> Mapping[str, str]:
        base_headers = {
            "host": url.netloc.encode(),
            "x-amz-date": amz_dateformat(timestamp),
        }
        if self.use_default_headers:
            base_headers |= {
                "content-md5": b64encode(hashlib.md5(data).digest()).decode(),
                "content-type": content_type,
            }
        result = {**base_headers, **headers}
        return {key: result[key] for key in sorted(result)}

    def make_signature(
        self,
        method: Methods,
        url: URL,
        payload_hash: str,
        timestamp: datetime,
        headers: Mapping[str, str] | None = None,
    ) -> tuple[str, str]:
        timestamp = timestamp
        headers = headers or {}
        signed_headers, canonical_request = self._get_canonical_request(
            method, url, headers, payload_hash
        )
        signed_string = self._create_sign_string(
            timestamp, hashlib.sha256(canonical_request.encode()).hexdigest()
        )
        return signed_headers, self.aws4_sign_string(signed_string, timestamp)

    def _get_canonical_request(
        self,
        method: Methods,
        url: URL,
        headers: Mapping[str, str],
        payload_hash: str,
    ) -> tuple[str, str]:
        header_keys = sorted(headers)
        signed_headers = ";".join(header_keys)
        return signed_headers, "\n".join(
            (
                method,
                url.path.encode(),
                url.query.encode(),
                "\n".join(
                    ":".join((str.lower(key), str.strip(headers[key])))
                    for key in header_keys
                )
                + "\n",
                signed_headers,
                payload_hash,
            )
        )

    def _create_sign_string(
        self, timestamp: datetime, hashed_canonical: str
    ) -> str:
        return "\n".join(
            (
                constants.aws_algorithm,
                amz_dateformat(timestamp),
                self._credential_scope(timestamp),
                hashed_canonical,
            )
        )

    def _credential_scope(self, timestamp: date):
        return "/".join(
            (
                _make_aws_date(timestamp),
                self.credentials.region,
                self.service,
                constants.aws_request,
            )
        )

    def aws4_sign_string(self, string_to_sign: str, timestamp: datetime) -> str:
        key_parts = (
            _make_aws_date(timestamp),
            self.credentials.region,
            self.service,
            constants.aws_request,
            string_to_sign,
        )
        signature_bytes: bytes = reduce(
            _aws4_reduce_signature,
            key_parts,
            b"AWS4" + self.credentials.secret_access_key.encode(),
        )
        return hexlify(signature_bytes).decode()

    def make_credential(self, now: date):
        return "/".join(
            (self.credentials.access_key_id, self._credential_scope(now))
        )


def _aws4_reduce_signature(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def amz_dateformat(dt: datetime):
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _make_aws_date(timestamp: date):
    # make sure to use date, because datetime is a date child
    return "".join(date.isoformat(timestamp).split("-"))
