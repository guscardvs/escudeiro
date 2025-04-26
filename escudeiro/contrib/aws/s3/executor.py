from collections.abc import AsyncGenerator, Coroutine, Generator, Sequence
from typing import (
    Any,
    overload,
)

from escudeiro.contrib.aws.constants import constants
from escudeiro.contrib.aws.http import AsyncAuthHttpClient, AuthHttpClient
from escudeiro.contrib.aws.s3.handlers import DAY, S3Object
from escudeiro.contrib.aws.s3.models import CopyParams, FileInfo, ObjectTuple
from escudeiro.data import data
from escudeiro.lazyfields import lazyfield
from escudeiro.url import URL


@data
class S3ObjectExecutor[HttpInterface: AsyncAuthHttpClient | AuthHttpClient]:
    """A class that provides an interface to interact with Amazon S3 objects.

    Args:
        http_interface: The HTTP client interface to use for making requests to S3.
        bucket_name: The name of the S3 bucket to interact with.
    """

    http_interface: HttpInterface
    bucket_name: str

    @lazyfield
    def core(self):
        return S3Object(self.http_interface.credentials, self.bucket_name)

    def presigned_url(
        self, object_name: str, expires: int = DAY, version: str | None = None
    ) -> URL:
        """Generate a presigned URL for an S3 object.

        Args:
            object_name: Name of the object to generate a presigned URL for.
            expires: Seconds until the signature expires, defaults to one day.
            version: Version ID of the object to generate a presigned URL for.

        Returns:
            A presigned URL for the specified object.
        """
        return self.core.generate_presigned_url(object_name, expires, version)

    @overload
    def download(
        self: "S3ObjectExecutor[AsyncAuthHttpClient]",
        object_name: str,
        version: str | None = None,
    ) -> Coroutine[Any, Any, bytes]: ...

    @overload
    def download(
        self: "S3ObjectExecutor[AuthHttpClient]",
        object_name: str,
        version: str | None = None,
    ) -> bytes: ...

    def download(
        self, object_name: str, version: str | None = None
    ) -> bytes | Coroutine[Any, Any, bytes]:
        """Download an S3 object.

        Args:
            object_name: Name of the object to download.
            version: Version ID of the object to download.

        Returns:
            A byte string containing the contents of the specified object.

        Raises:
            RequestFailed: If the download fails due to a non-2xx response.
        """
        return self.http_interface.do(self.core.download(object_name, version))

    @overload
    def info(
        self: "S3ObjectExecutor[AsyncAuthHttpClient]",
        object_name: str,
    ) -> Coroutine[Any, Any, FileInfo]: ...

    @overload
    def info(
        self: "S3ObjectExecutor[AuthHttpClient]",
        object_name: str,
    ) -> FileInfo: ...

    def info(
        self,
        object_name: str,
    ) -> FileInfo | Coroutine[Any, Any, FileInfo]:
        """Get information about an S3 object.

        Args:
            object_name: Name of the object to get information about.

        Returns:
            A FileInfo object containing information about the specified object.

        Raises:
            RequestFailed: If the request fails due to a non-2xx response.
            NotFound: If the specified object is not found.
        """
        return self.http_interface.do(self.core.info(object_name))

    @overload
    def delete(
        self: "S3ObjectExecutor[AsyncAuthHttpClient]",
        object_name: str,
        version: str | None = None,
    ) -> Coroutine[Any, Any, None]: ...

    @overload
    def delete(
        self: "S3ObjectExecutor[AuthHttpClient]",
        object_name: str,
        version: str | None = None,
    ) -> None: ...

    def delete(
        self,
        object_name: str,
        version: str | None = None,
    ) -> None | Coroutine[Any, Any, None]:
        """Deletes an object from the S3 service.

        Args:
            object_name: The name of the object to be deleted.
            version: The version of the object to be deleted. If not specified,
                the latest version will be deleted.

        Returns:
            None if the request was successful.

        Raises:
            RequestFailed: If the HTTP request fails.
        """
        return self.http_interface.do(
            self.core.delete_many(ObjectTuple(object_name, version))
        )

    @overload
    def delete_many(
        self: "S3ObjectExecutor[AsyncAuthHttpClient]",
        objects: Sequence[ObjectTuple],
    ) -> Coroutine[Any, Any, None]: ...

    @overload
    def delete_many(
        self: "S3ObjectExecutor[AuthHttpClient]",
        objects: Sequence[ObjectTuple],
    ) -> None: ...

    def delete_many(
        self,
        objects: Sequence[ObjectTuple],
    ) -> None | Coroutine[Any, Any, None]:
        """Deletes multiple objects from the S3 service.

        Args:
            objects: A sequence of ObjectTuple instances representing the objects
                to be deleted.

        Returns:
            None if the request was successful.

        Raises:
            RequestFailed: If the HTTP request fails.
        """
        return self.http_interface.do(self.core.delete_many(*objects))

    @overload
    def upload(
        self: "S3ObjectExecutor[AsyncAuthHttpClient]",
        object_name: str,
        content: bytes,
        *,
        content_type: str | None = None,
        request_timeout_seconds: int = 30 * 60,
    ) -> Coroutine[Any, Any, None]: ...

    @overload
    def upload(
        self: "S3ObjectExecutor[AuthHttpClient]",
        object_name: str,
        content: bytes,
        *,
        content_type: str | None = None,
        request_timeout_seconds: int = 30 * 60,
    ) -> None: ...

    def upload(
        self,
        object_name: str,
        content: bytes,
        *,
        content_type: str | None = None,
        request_timeout_seconds: int = 30 * 60,
    ) -> None | Coroutine[Any, Any, None]:
        """Uploads the given content to S3 with the given object name.

        Args:
            object_name: The object name of the content to upload.
            content: The content to upload.
            content_type: The content type of the content to upload.
            request_timeout_seconds: The maximum time (in seconds) to wait for the request
                to complete.

        Returns:
            If the executor is asynchronous, returns an awaitable that resolves to None
            once the upload is complete. Otherwise, returns None.

        Raises:
            RequestFailed: If the upload request failed (i.e. the HTTP status code is not 204).
        """
        return self.http_interface.do(
            self.core.upload(
                object_name,
                content,
                content_type,
                request_timeout_seconds,
            )
        )

    @overload
    def copy(
        self: "S3ObjectExecutor[AsyncAuthHttpClient]",
        source: CopyParams,
        target: CopyParams,
        *,
        prevalidate: bool = True,
    ) -> Coroutine[Any, Any, None]: ...

    @overload
    def copy(
        self: "S3ObjectExecutor[AuthHttpClient]",
        source: CopyParams,
        target: CopyParams,
        *,
        prevalidate: bool = True,
    ) -> None: ...

    def copy(
        self,
        source: CopyParams,
        target: CopyParams,
        *,
        prevalidate: bool = True,
    ) -> None | Coroutine[Any, Any, None]:
        """Copy an object from source to target location within possibly different buckets.

        Args:
            source: Parameters of the source object to be copied.
            target: Parameters of the target object to be created.
            prevalidate: Whether to validate the existence of the source object before copying.
                Default is True.

        Returns:
            None if the request was successful.

        Raises:
            RequestFailed: If the request fails.
            NotFound: If the specified object is not found and prevalidate was True.
        """
        return self.http_interface.exhaust_with_null(
            self.core.copy(source, target, prevalidate)
        )

    @overload
    def copy_from(
        self: "S3ObjectExecutor[AsyncAuthHttpClient]",
        source: CopyParams,
        target_name: str | None = None,
        *,
        prevalidate: bool = True,
    ) -> Coroutine[Any, Any, None]: ...

    @overload
    def copy_from(
        self: "S3ObjectExecutor[AuthHttpClient]",
        source: CopyParams,
        target_name: str | None = None,
        *,
        prevalidate: bool = True,
    ) -> None: ...

    def copy_from(
        self,
        source: CopyParams,
        target_name: str | None = None,
        *,
        prevalidate: bool = True,
    ) -> None | Coroutine[Any, Any, None]:
        """Copy an object from the source location to a target location in the bucket from config.

        Args:
            source: Parameters of the source object to be copied.
            target_name: The name of the target object. If not specified, the name of the
                source object is used.
            prevalidate: Whether to validate the existence of the source object before copying.
                Default is True.

        Returns:
            None if the request was successful.

        Raises:
            RequestFailed: If the request fails.
            NotFound: If the specified object is not found and prevalidate was True.
        """
        return self.http_interface.exhaust_with_null(
            self.core.copy_from(source, target_name, prevalidate)
        )

    @overload
    def copy_to(
        self: "S3ObjectExecutor[AsyncAuthHttpClient]",
        target: CopyParams,
        source_name: str | None = None,
        *,
        prevalidate: bool = True,
    ) -> Coroutine[Any, Any, None]: ...

    @overload
    def copy_to(
        self: "S3ObjectExecutor[AuthHttpClient]",
        target: CopyParams,
        source_name: str | None = None,
        *,
        prevalidate: bool = True,
    ) -> None: ...

    def copy_to(
        self,
        target: CopyParams,
        source_name: str | None = None,
        *,
        prevalidate: bool = True,
    ) -> None | Coroutine[Any, Any, None]:
        """Copy an object from the source location in the config bucket to a target location.

        Args:
            target: Parameters of the target object to be created.
            source_name: The name of the source object. If not specified, the name of the
                target object is used.
            prevalidate: Whether to validate the existence of the source object before copying.
                Default is True.

        Returns:
            None if the request was successful.

        Raises:
            RequestFailed: If the request fails.
            NotFound: If the specified object is not found and prevalidate was True.
        """
        return self.http_interface.exhaust_with_null(
            self.core.copy_to(target, source_name, prevalidate)
        )

    @overload
    def list_objects(
        self: "S3ObjectExecutor[AsyncAuthHttpClient]",
        prefix: str | None = None,
        chunksize: int = constants.max_chunksize,
    ) -> AsyncGenerator[Sequence[FileInfo]]: ...

    @overload
    def list_objects(
        self: "S3ObjectExecutor[AuthHttpClient]",
        prefix: str | None = None,
        chunksize: int = constants.max_chunksize,
    ) -> Generator[Sequence[FileInfo]]: ...

    def list_objects(
        self,
        prefix: str | None = None,
        chunksize: int = constants.max_chunksize,
    ) -> AsyncGenerator[Sequence[FileInfo]] | Generator[Sequence[FileInfo]]:
        """Lists objects in the S3 bucket, returning a generator that yields chunks of objects.

        Args:
            prefix: Optional prefix to filter objects by.
            chunksize: Optional size of each chunk (defaults to 1000).

        Returns:
            A generator that yields lists of FileInfo objects.

        Raises:
            RequestFailed: If the request to the S3 API fails.
            InvalidParam: If chunksize is less than 1 or greater than the maximum allowed.
        """
        return self.http_interface.iter(self.core.scroll(prefix, chunksize))
