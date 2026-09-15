import io
import logging
from typing import Optional
from minio import Minio

from app.core.config import Settings, settings as default_settings

logger = logging.getLogger(__name__)


class MinioStorageService:
    """
    Backend MinIO Object Storage service.
    Handles bucket verification, file uploads, downloads,
    and lifecycle operations.
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
            logger.error("Failed to ensure MinIO bucket '%s': %s", target, e)
            raise

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
        target = bucket_name or self.default_bucket
        self.ensure_bucket(target)
        data_stream = io.BytesIO(data)
        self.client.put_object(
            bucket_name=target,
            object_name=object_name,
            data=data_stream,
            length=len(data),
            content_type=content_type,
        )
        logger.info(
            "Uploaded %d bytes to MinIO object '%s' in bucket '%s'",
            len(data),
            object_name,
            target,
        )
        return object_name

    def download_file_bytes(
        self,
        object_name: str,
        bucket_name: Optional[str] = None,
    ) -> bytes:
        """
        Download raw bytes from MinIO object storage.
        """
        target = bucket_name or self.default_bucket
        response = None
        try:
            response = self.client.get_object(target, object_name)
            data = response.read()
            return data
        except Exception as e:
            logger.error(
                "Failed to download object '%s' from bucket '%s': %s",
                object_name,
                target,
                e,
            )
            raise
        finally:
            if response:
                response.close()
                response.release_conn()

    def delete_file(
        self,
        object_name: str,
        bucket_name: Optional[str] = None,
    ) -> bool:
        """
        Delete an object from MinIO.
        """
        target = bucket_name or self.default_bucket
        try:
            self.client.remove_object(target, object_name)
            logger.info(
                "Deleted object '%s' from bucket '%s'", object_name, target
            )
            return True
        except Exception as e:
            logger.warning(
                "Failed to delete object '%s' from bucket '%s': %s",
                object_name,
                target,
                e,
            )
            return False


storage_service = MinioStorageService()
