from datetime import datetime
from typing import NamedTuple, NotRequired, TypedDict, override

from escudeiro.data import data
from escudeiro.misc import ValueEnum, to_pascal

UploadParams = TypedDict(
    "UploadParams",
    {
        "Key": str,
        "Content-Type": str,
        "Content-Disposition": NotRequired[str],
        "Policy": str,
        "X-Amz-Algorithm": str,
        "X-Amz-Credential": str,
        "X-Amz-Date": str,
        "X-Amz-Signature": str,
    },
)


class StorageClass(ValueEnum):
    STANDARD = "STANDARD"
    REDUCED_REDUNDANCY = "REDUCED_REDUNDANCY"
    GLACIER = "GLACIER"
    STANDARD_IA = "STANDARD_IA"
    ONEZONE_IA = "ONEZONE_IA"
    INTELLIGENT_TIERING = "INTELLIGENT_TIERING"
    DEEP_ARCHIVE = "DEEP_ARCHIVE"
    OUTPOSTS = "OUTPOSTS"
    GLACIER_IR = "GLACIER_IR"
    UNKNOWN = "UNKNOWN"

    @classmethod
    @override
    def _missing_(cls, value: object) -> "StorageClass":
        found = super()._missing_(value)
        if found is not None:
            return found
        return cls.UNKNOWN


@data(alias_generator=to_pascal)
class FileInfo:
    key: str
    last_modified: datetime
    size: int
    e_tag: str
    storage_class: StorageClass


class ObjectTuple(NamedTuple):
    object_name: str
    version: str | None = None


class CopyParams(NamedTuple):
    object_name: str
    bucket: str


@data(frozen=False)
class TokenHolder:
    continuation_token: str | None = None
    should_break: bool = False
