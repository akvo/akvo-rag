"""
Compatibility layer redirecting legacy storage_service imports to MinIOService.
"""

from app.services.minio_service import (
    MinIOService,
    MinIOService as MinioStorageService,
    get_minio_service,
    minio_service,
    minio_service as storage_service,
)

__all__ = [
    "MinIOService",
    "MinioStorageService",
    "get_minio_service",
    "minio_service",
    "storage_service",
]
