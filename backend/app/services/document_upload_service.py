import io
import json
import logging
import mimetypes
import os
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import HTTPException, UploadFile, status
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.core.config import settings
from app.services.minio_service import MinIOService, get_minio_service

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent S3 key path traversal and bad characters.
    """
    base = os.path.basename(filename).strip()
    sanitized = re.sub(r"[^a-zA-Z0-9_.-]", "_", base)
    sanitized = re.sub(r"^\.+", "", sanitized)
    return sanitized or "document"


async def validate_and_prepare_file(
    file: Union[UploadFile, StarletteUploadFile],
) -> Tuple[str, str, int]:
    """Validate extension, size ceiling, and magic bytes for upload."""
    raw_filename = getattr(file, "filename", None) or "uploaded_document"
    sanitized = sanitize_filename(raw_filename)
    _, ext = os.path.splitext(sanitized)
    ext = ext.lower()

    if ext not in ALLOWED_EXTENSIONS:
        formats = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file format: {ext}. Allowed formats: {formats}"
            ),
        )

    # Read up to 8KB header chunk for magic bytes inspection
    header_chunk = await file.read(8192)
    if not header_chunk or len(header_chunk) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded file '{sanitized}' is empty",
        )

    # Magic Bytes Validation
    if ext == ".pdf":
        if not header_chunk.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid file content: header does not match {ext} "
                    "specification"
                ),
            )
    elif ext == ".docx":
        if not (
            header_chunk.startswith(b"PK\x03\x04")
            or header_chunk.startswith(b"PK\x05\x06")
            or header_chunk.startswith(b"PK\x07\x08")
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid file content: header does not match {ext} "
                    "specification"
                ),
            )
    elif ext in [".txt", ".md"]:
        try:
            header_chunk.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid file content: header does not match {ext} "
                    "UTF-8 text specification"
                ),
            )

    # Calculate file size
    if getattr(file, "size", None) is not None:
        file_size = file.size
    elif (
        hasattr(file, "file")
        and hasattr(file.file, "seek")
        and hasattr(file.file, "tell")
    ):
        file.file.seek(0, io.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)
    else:
        file_size = len(header_chunk)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=(
                f"File '{sanitized}' exceeds limit of 25MB "
                f"(size: {file_size} bytes)"
            ),
        )

    # Rewind pointer for MinIO streaming
    await file.seek(0)
    content_type = (
        getattr(file, "content_type", None)
        or mimetypes.guess_type(sanitized)[0]
        or "application/octet-stream"
    )
    return sanitized, content_type, file_size


async def process_and_enqueue_upload(
    kb_id: int,
    files: List[Any],
    minio_service: Optional[MinIOService] = None,
    redis_client: Optional[Any] = None,
    single_mode: bool = False,
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Validate files, stream them to MinIO under tenant prefix 'kb_{kb_id}/',
    and enqueue ingestion tasks to the Redis 'document_ingestion' queue.
    """
    minio_svc = minio_service or get_minio_service()

    close_redis_on_finish = False
    if redis_client is None:
        import redis.asyncio as aioredis

        redis_client = aioredis.from_url(
            settings.REDIS_URL, decode_responses=True
        )
        close_redis_on_finish = True

    try:
        # Step 1: Validate all files upfront
        validated_files = []
        for f in files:
            sanitized_name, content_type, file_size = (
                await validate_and_prepare_file(f)
            )
            validated_files.append(
                (f, sanitized_name, content_type, file_size)
            )

        # Step 2: Stream upload to MinIO and push to Redis document_ingestion
        results = []
        for f, sanitized_name, content_type, file_size in validated_files:
            doc_uuid = str(uuid.uuid4())
            object_name = f"kb_{kb_id}/{doc_uuid}_{sanitized_name}"

            # Seek to start
            if hasattr(f, "seek"):
                await f.seek(0)

            file_stream = getattr(f, "file", None)
            if file_stream is None:
                content = await f.read()
                file_stream = io.BytesIO(content)

            try:
                upload_meta = minio_svc.upload_file(
                    file_data=file_stream,
                    object_name=object_name,
                    content_type=content_type,
                    bucket_name="documents",
                )
            except Exception as e:
                logger.error(
                    "MinIO upload failed for '%s': %s", sanitized_name, e
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Document storage failed",
                )

            # Enqueue Task to Redis
            queue_payload = json.dumps(
                {
                    "document_id": doc_uuid,
                    "kb_id": kb_id,
                    "minio_bucket": "documents",
                    "minio_key": object_name,
                    "filename": sanitized_name,
                    "file_size": upload_meta.get("size", file_size),
                    "content_type": content_type,
                }
            )
            try:
                await redis_client.rpush("document_ingestion", queue_payload)
                logger.info(
                    "Enqueued document '%s' (%s) to 'document_ingestion'",
                    doc_uuid,
                    sanitized_name,
                )
            except Exception as e:
                logger.error(
                    "Failed to enqueue ingestion task to Redis: %s", e
                )
                minio_svc.delete_file(object_name, bucket_name="documents")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to enqueue document processing task",
                )

            results.append(
                {
                    "id": doc_uuid,
                    "document_id": doc_uuid,
                    "upload_id": doc_uuid,
                    "filename": sanitized_name,
                    "file_name": sanitized_name,
                    "original_filename": (
                        getattr(f, "filename", sanitized_name)
                        or sanitized_name
                    ),
                    "status": "PROCESSING",
                    "message": f"File '{sanitized_name}' uploaded successfully",  # noqa
                    "skip_processing": False,
                    "temp_path": object_name,
                    "kb_id": kb_id,
                }
            )

        return results[0] if (single_mode and len(results) == 1) else results

    finally:
        if close_redis_on_finish and redis_client:
            await redis_client.aclose()
