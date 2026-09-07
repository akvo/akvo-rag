import io
import logging
from typing import BinaryIO, Dict, Any, Optional
from minio import Minio
from minio.error import S3Error

from app.core.config import Settings, settings as default_settings

logger = logging.getLogger("minio_service")


class MinIOService:
    """
    MinIO S3 Object Storage Service.
    Handles bucket auto-provisioning, memory-safe direct streaming uploads,
    downloads, and lifecycle operations.
    """

    def __init__(
        self,
        settings_override: Optional[Settings] = None,
        client_override: Optional[Minio] = None,
    ):
        self.settings = settings_override or default_settings
        self.default_bucket = getattr(
            self.settings, "MINIO_BUCKET_DOCUMENTS", "documents"
        )
        if client_override:
            self.client = client_override
        else:
            self.client = Minio(
                endpoint=self.settings.MINIO_ENDPOINT,
                access_key=self.settings.MINIO_ACCESS_KEY,
                secret_key=self.settings.MINIO_SECRET_KEY,
                secure=self.settings.MINIO_SECURE,
            )
        self.ensure_bucket(self.default_bucket)

    def ensure_bucket(self, bucket_name: Optional[str] = None) -> bool:
        """
        Verify that the target bucket exists, creating it if missing.
        """
        target = bucket_name or self.default_bucket
        try:
            if not self.client.bucket_exists(target):
                self.client.make_bucket(target)
                logger.info("Created MinIO bucket '%s'", target)
            else:
                logger.debug("MinIO bucket '%s' exists", target)
            return True
        except Exception as e:
            logger.error(
                "Failed to verify/create MinIO bucket '%s': %s", target, e
            )
            return False

    def _ensure_bucket_exists(self, bucket_name: Optional[str] = None) -> bool:
        """Alias for ensure_bucket."""
        return self.ensure_bucket(bucket_name)

    def upload_file(
        self,
        file_data: BinaryIO,
        object_name: str,
        content_type: str = "application/octet-stream",
        bucket_name: Optional[str] = None,
        part_size: int = 10 * 1024 * 1024,
    ) -> Dict[str, Any]:
        """
        Streams a file directly to MinIO without loading entire file into RAM.
        """
        bucket = bucket_name or self.default_bucket
        self.ensure_bucket(bucket)

        # Determine stream length if seekable
        size = -1
        try:
            file_data.seek(0, io.SEEK_END)
            size = file_data.tell()
            file_data.seek(0)
        except Exception:
            size = -1

        result = self.client.put_object(
            bucket_name=bucket,
            object_name=object_name,
            data=file_data,
            length=size,
            content_type=content_type,
            part_size=part_size if size < 0 or size > part_size else part_size,
        )

        logger.info(
            "Uploaded file to MinIO object '%s' in bucket '%s' "
            "(etag: %s, size: %s)",
            object_name,
            bucket,
            result.etag,
            size,
        )
        return {
            "bucket": bucket,
            "object_name": object_name,
            "etag": result.etag,
            "size": size,
        }

    def upload_file_bytes(
        self,
        data: bytes,
        object_name: str,
        content_type: str = "application/octet-stream",
        bucket_name: Optional[str] = None,
    ) -> str:
        """
        Upload raw bytes to MinIO object storage.
        """
        bucket = bucket_name or self.default_bucket
        self.ensure_bucket(bucket)
        data_stream = io.BytesIO(data)
        self.client.put_object(
            bucket_name=bucket,
            object_name=object_name,
            data=data_stream,
            length=len(data),
            content_type=content_type,
        )
        logger.info(
            "Uploaded %d bytes to MinIO object '%s' in bucket '%s'",
            len(data),
            object_name,
            bucket,
        )
        return object_name

    def get_file_stream(
        self,
        object_name: str,
        bucket_name: Optional[str] = None,
    ) -> BinaryIO:
        """
        Retrieve binary stream for an object in MinIO.
        """
        bucket = bucket_name or self.default_bucket
        return self.client.get_object(bucket, object_name)

    def download_file_bytes(
        self,
        object_name: str,
        bucket_name: Optional[str] = None,
    ) -> bytes:
        """
        Download raw bytes from MinIO object storage and cleanly close
        connection.
        """
        bucket = bucket_name or self.default_bucket
        response = None
        try:
            response = self.client.get_object(bucket, object_name)
            data = response.read()
            return data
        except Exception as e:
            logger.error(
                "Failed to download object '%s' from bucket '%s': %s",
                object_name,
                bucket,
                e,
            )
            raise
        finally:
            if response:
                try:
                    response.close()
                    response.release_conn()
                except Exception:
                    pass

    def delete_file(
        self,
        object_name: str,
        bucket_name: Optional[str] = None,
    ) -> bool:
        """
        Delete an object from MinIO.
        """
        bucket = bucket_name or self.default_bucket
        try:
            self.client.remove_object(bucket, object_name)
            logger.info(
                "Deleted object '%s' from bucket '%s'", object_name, bucket
            )
            return True
        except S3Error as e:
            logger.error(
                "Failed to delete object '%s' from bucket '%s': %s",
                object_name,
                bucket,
                e,
            )
            return False
        except Exception as e:
            logger.error(
                "Unexpected error deleting object '%s' from bucket '%s': %s",
                object_name,
                bucket,
                e,
            )
            return False


_minio_service_instance: Optional[MinIOService] = None


def get_minio_service() -> MinIOService:
    """
    FastAPI dependency injection provider for MinIOService singleton.
    """
    global _minio_service_instance
    if _minio_service_instance is None:
        _minio_service_instance = MinIOService()
    return _minio_service_instance


minio_service = get_minio_service()
