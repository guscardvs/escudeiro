from datetime import datetime
from typing import NotRequired, TypedDict

from escudeiro.contrib.aws.model import AwsModel
from escudeiro.misc import ValueEnum

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


class FileInfo(AwsModel):
    key: str
    last_modified: datetime
    size: int
    e_tag: str
    storage_class: StorageClass
