import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import UploadFile
import io

from app.services.storage_service import MinioStorageService
from mcp_clients.kb_mcp_endpoint_service import KnowledgeBaseMCPEndpointService


@pytest.mark.unit
def test_backend_minio_storage_service():
    mock_client = MagicMock()
    mock_client.bucket_exists.return_value = False

    service = MinioStorageService(client_override=mock_client)
    res = service.ensure_bucket("documents")
    assert res is True
    mock_client.bucket_exists.assert_called_once_with("documents")
    mock_client.make_bucket.assert_called_once_with("documents")

    # Upload
    mock_client.bucket_exists.return_value = True
    uploaded = service.upload_file_bytes(
        data=b"test data", object_name="kb_1/test.txt"
    )
    assert uploaded == "kb_1/test.txt"
    assert mock_client.put_object.called

    # Download
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"test data"
    mock_client.get_object.return_value = mock_resp
    downloaded = service.download_file_bytes("kb_1/test.txt")
    assert downloaded == b"test data"

    # Delete
    deleted = service.delete_file("kb_1/test.txt")
    assert deleted is True
    mock_client.remove_object.assert_called_once_with(
        "documents", "kb_1/test.txt"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_kb_mcp_endpoint_service_document_flow():
    mock_dispatcher = MagicMock()
    mock_dispatcher.call_tool = AsyncMock()

    service = KnowledgeBaseMCPEndpointService(dispatcher=mock_dispatcher)

    # 1. Test upload_documents
    fake_file = UploadFile(
        filename="test_guide.pdf",
        file=io.BytesIO(b"PDF raw content mock"),
        headers={"content-type": "application/pdf"},
    )

    mock_dispatcher.call_tool.return_value = {
        "status": "uploaded",
        "document_id": 42,
        "task_id": 101,
        "upload_id": 101,
        "file_name": "test_guide.pdf",
    }

    with patch("app.services.storage_service.storage_service") as mock_storage:
        mock_storage.upload_file_bytes.return_value = (
            "kb_1/uuid_test_guide.pdf"
        )

        upload_res = await service.upload_documents(kb_id=1, files=[fake_file])
        assert len(upload_res) == 1
        assert upload_res[0]["document_id"] == 42
        assert upload_res[0]["upload_id"] == 101
        assert upload_res[0]["status"] == "uploaded"
        assert mock_storage.upload_file_bytes.called

    # 2. Test process_documents
    proc_res = await service.process_documents(
        kb_id=1, upload_results=upload_res
    )
    assert proc_res["status"] == "processing"
    assert len(proc_res["tasks"]) == 1
    assert proc_res["tasks"][0]["upload_id"] == 101

    # 3. Test get_processing_tasks
    mock_dispatcher.call_tool.return_value = {
        101: {
            "document_id": 42,
            "status": "completed",
            "error_message": None,
            "upload_id": 101,
            "file_name": "test_guide.pdf",
        }
    }
    tasks_res = await service.get_processing_tasks(kb_id=1, task_ids=[101])
    assert 101 in tasks_res
    assert tasks_res[101]["status"] == "completed"

    # 4. Test delete_document
    del_res = await service.delete_document(kb_id=1, doc_id=42)
    assert del_res == [{"status": "deleted", "doc_id": 42}]

    # 5. Test process_documents fallback when document_id is omitted
    fallback_payload = [
        {
            "upload_id": 202,
            "file_name": "fallback.docx",
            "chunk_size": 800,
            "chunk_overlap": 150,
        }
    ]
    fb_res = await service.process_documents(
        kb_id=1, upload_results=fallback_payload
    )
    assert fb_res["status"] == "processing"
    assert fb_res["tasks"][0]["task_id"] == 202
