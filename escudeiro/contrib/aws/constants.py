from gyver.attrs import define
from gyver.config import AdapterConfigFactory


@define
class _Constants:
    xmlns: str
    config_factory: AdapterConfigFactory
    content_type: str
    aws_algorithm: str
    aws_request: str
    default_encoding: str
    default_mimetype: str
    max_chunksize: int


constants = _Constants(
    xmlns="http://s3.amazonaws.com/doc/2006-03-01/",
    config_factory=AdapterConfigFactory(),
    content_type="application/x-www-form-urlencoded",
    aws_algorithm="AWS4-HMAC-SHA256",
    aws_request="aws4_request",
    default_encoding="utf-8",
    default_mimetype="application/octet-stream",
    max_chunksize=1000,
)
