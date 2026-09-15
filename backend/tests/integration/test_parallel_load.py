import asyncio
import io
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.services.document_upload_service import (
    MAX_FILE_SIZE,
    process_and_enqueue_upload,
    validate_and_prepare_file,
)


@pytest.mark.asyncio
async def test_validate_and_prepare_file_25mb_limit():
    """Verify that file within 25MB passes and file > 25MB raises HTTP 413."""
    assert MAX_FILE_SIZE == 25 * 1024 * 1024

    # 1. Valid PDF file (1MB)
    valid_content = b"%PDF-1.4 header content" + (b"0" * 1024 * 1024)
    valid_file = StarletteUploadFile(
        file=io.BytesIO(valid_content),
        size=len(valid_content),
        filename="valid.pdf",
    )
    name, content_type, size = await validate_and_prepare_file(valid_file)
    assert name == "valid.pdf"
    assert size == len(valid_content)

    # 2. Oversized file (26MB)
    oversized_content = b"%PDF-1.4 header content" + (b"0" * 26 * 1024 * 1024)
    oversized_file = StarletteUploadFile(
        file=io.BytesIO(oversized_content),
        size=len(oversized_content),
        filename="oversized.pdf",
    )
    with pytest.raises(HTTPException) as exc_info:
        await validate_and_prepare_file(oversized_file)
    assert exc_info.value.status_code == 413
    assert "25MB" in exc_info.value.detail


@pytest.mark.asyncio
async def test_parallel_upload_and_chat_simulation():
    """
    Simulate parallel concurrent execution of document upload enqueueing
    and chat processing tasks to ensure event loops and queues execute
    without contention.
    """
    mock_minio = MagicMock()
    mock_minio.upload_file.return_value = {"size": 1024}

    mock_redis = AsyncMock()
    mock_redis.rpush.return_value = 1

    def make_upload_file(i: int) -> StarletteUploadFile:
        return StarletteUploadFile(
            file=io.BytesIO(b"%PDF-1.4 small test"),
            size=17,
            filename=f"test_{i}.pdf",
        )

    async def simulate_upload(i: int):
        return await process_and_enqueue_upload(
            kb_id=1,
            files=[make_upload_file(i)],
            minio_service=mock_minio,
            redis_client=mock_redis,
            single_mode=True,
        )

    async def simulate_chat():
        await asyncio.sleep(0.01)
        return {"status": "ok", "message": "chat query responded"}

    # Execute 5 uploads and 5 chats concurrently
    upload_tasks = [simulate_upload(i) for i in range(5)]
    chat_tasks = [simulate_chat() for _ in range(5)]
    results = await asyncio.gather(*(upload_tasks + chat_tasks))

    assert len(results) == 10
    assert mock_minio.upload_file.call_count == 5
    assert mock_redis.rpush.call_count == 5
