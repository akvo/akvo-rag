import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.upload_job_service import execute_upload_job


@pytest.mark.asyncio
async def test_execute_upload_job_success_no_callback():
    mock_db = MagicMock()
    fake_job_id = "job-123"
    fake_kb_id = 1
    fake_files = [{"filename": "test.txt", "content": "hello"}]
    fake_upload_results = [{"filename": "test.txt", "status": "uploaded"}]

    with patch(
        "app.services.upload_job_service.JobService.update_status_to_running"
    ) as mock_running, patch(
        "app.services.upload_job_service.KnowledgeBaseMCPEndpointService.upload_and_process_documents",
        new_callable=AsyncMock,
        return_value=fake_upload_results,
    ) as mock_mcp, patch(
        "app.services.upload_job_service.JobService.update_status_to_completed"
    ) as mock_completed:
        await execute_upload_job(
            db=mock_db,
            job_id=fake_job_id,
            kb_id=fake_kb_id,
            files=fake_files,
            callback_url=None,
        )

        mock_running.assert_called_once_with(mock_db, fake_job_id)
        mock_mcp.assert_called_once_with(kb_id=fake_kb_id, files=fake_files)
        mock_completed.assert_called_once_with(
            mock_db,
            fake_job_id,
            output={
                "kb_id": fake_kb_id,
                "documents": fake_upload_results,
                "file_count": 1,
            },
        )
        mock_db.close.assert_called_once()


@pytest.mark.asyncio
async def test_execute_upload_job_success_with_callback():
    mock_db = MagicMock()
    fake_job_id = "job-456"
    fake_kb_id = 2
    fake_files = []
    fake_job_obj = MagicMock()

    with patch(
        "app.services.upload_job_service.JobService.update_status_to_running"
    ), patch(
        "app.services.upload_job_service.KnowledgeBaseMCPEndpointService.upload_and_process_documents",
        new_callable=AsyncMock,
        return_value=[],
    ), patch(
        "app.services.upload_job_service.JobService.update_status_to_completed"
    ), patch(
        "app.services.upload_job_service.JobService.get_job",
        return_value=fake_job_obj,
    ) as mock_get_job, patch(
        "app.utils.callback_util.send_callback_async",
        new_callable=AsyncMock,
    ) as mock_callback:
        await execute_upload_job(
            db=mock_db,
            job_id=fake_job_id,
            kb_id=fake_kb_id,
            files=fake_files,
            callback_url="https://example.com/callback",
        )

        mock_get_job.assert_called_once_with(mock_db, fake_job_id)
        mock_callback.assert_called_once_with(
            callback_url="https://example.com/callback",
            job=fake_job_obj,
            output={
                "kb_id": fake_kb_id,
                "documents": [],
                "file_count": 0,
            },
        )
        mock_db.close.assert_called_once()


@pytest.mark.asyncio
async def test_execute_upload_job_failure_with_callback():
    mock_db = MagicMock()
    fake_job_id = "job-789"
    fake_kb_id = 3
    fake_job_obj = MagicMock()

    with patch(
        "app.services.upload_job_service.JobService.update_status_to_running"
    ), patch(
        "app.services.upload_job_service.KnowledgeBaseMCPEndpointService.upload_and_process_documents",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Processing failed"),
    ), patch(
        "app.services.upload_job_service.JobService.update_status_to_failed"
    ) as mock_failed, patch(
        "app.services.upload_job_service.JobService.get_job",
        return_value=fake_job_obj,
    ), patch(
        "app.utils.callback_util.send_callback_async",
        new_callable=AsyncMock,
    ) as mock_callback:
        await execute_upload_job(
            db=mock_db,
            job_id=fake_job_id,
            kb_id=fake_kb_id,
            files=None,
            callback_url="https://example.com/callback-err",
        )

        mock_failed.assert_called_once_with(
            mock_db, fake_job_id, output="Processing failed"
        )
        mock_callback.assert_called_once_with(
            callback_url="https://example.com/callback-err",
            job=fake_job_obj,
            error="Processing failed",
        )
        mock_db.close.assert_called_once()
