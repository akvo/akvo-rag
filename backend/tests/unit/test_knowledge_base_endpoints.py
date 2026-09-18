import io
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User
from app.db.session import get_db
from app.core.security import get_current_user
from app.api.api_v1.knowledge_base import get_redis_client, get_minio_service


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def mock_user():
    return User(id=1, email="admin@example.com", username="admin", is_active=True, is_superuser=True)


@pytest.fixture
def mock_redis():
    r = AsyncMock()
    r.aclose = AsyncMock()
    return r


@pytest.fixture
def mock_minio():
    return MagicMock()


@pytest.fixture
def client(mock_db, mock_user, mock_redis, mock_minio):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_redis_client] = lambda: mock_redis
    app.dependency_overrides[get_minio_service] = lambda: mock_minio
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_knowledge_bases_list(client: TestClient):
    fake_kbs = [{"id": 1, "name": "KB 1", "description": "Desc 1"}]
    with patch(
        "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService.list_kbs",
        new_callable=AsyncMock,
        return_value=fake_kbs,
    ):
        response = client.get("/api/v1/knowledge-bases")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "KB 1"
        assert data[0]["is_superuser"] is True


@pytest.mark.asyncio
async def test_get_knowledge_bases_dict_response(client: TestClient):
    fake_kbs = {"knowledge_bases": [{"id": 2, "name": "KB 2"}]}
    with patch(
        "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService.list_kbs",
        new_callable=AsyncMock,
        return_value=fake_kbs,
    ):
        response = client.get("/api/v1/knowledge-bases")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "KB 2"


@pytest.mark.asyncio
async def test_get_knowledge_base_detail(client: TestClient):
    fake_kb = {"id": 1, "name": "Single KB", "description": "Single Desc"}
    with patch(
        "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService.get_kb",
        new_callable=AsyncMock,
        return_value=fake_kb,
    ):
        response = client.get("/api/v1/knowledge-bases/1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["is_superuser"] is True


@pytest.mark.asyncio
async def test_create_knowledge_base(client: TestClient):
    created_kb = {"id": 3, "name": "New KB", "description": "New Desc"}
    with patch(
        "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService.create_kb",
        new_callable=AsyncMock,
        return_value=created_kb,
    ):
        response = client.post(
            "/api/v1/knowledge-bases",
            json={"name": "New KB", "description": "New Desc"},
        )
        assert response.status_code == 200
        assert response.json()["id"] == 3


@pytest.mark.asyncio
async def test_update_knowledge_base(client: TestClient):
    updated_kb = {"id": 1, "name": "Updated KB"}
    with patch(
        "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService.update_kb",
        new_callable=AsyncMock,
        return_value=updated_kb,
    ):
        response = client.put(
            "/api/v1/knowledge-bases/1",
            json={"name": "Updated KB"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated KB"


@pytest.mark.asyncio
async def test_delete_knowledge_base(client: TestClient):
    with patch(
        "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService.delete_kb",
        new_callable=AsyncMock,
        return_value={"status": "deleted", "kb_id": 1},
    ):
        response = client.delete("/api/v1/knowledge-bases/1")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"


@pytest.mark.asyncio
async def test_upload_kb_documents_no_files(client: TestClient):
    response = client.post("/api/v1/knowledge-bases/1/documents/upload")
    assert response.status_code == 400
    assert "No files provided" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_kb_documents_single_file(client: TestClient):
    with patch(
        "app.api.api_v1.knowledge_base.process_and_enqueue_upload",
        new_callable=AsyncMock,
        return_value={"status": "queued", "job_id": "job-1"},
    ):
        file_data = io.BytesIO(b"file content")
        response = client.post(
            "/api/v1/knowledge-bases/1/documents/upload",
            files={"file": ("test.txt", file_data, "text/plain")},
        )
        assert response.status_code == 202
        assert response.json()["job_id"] == "job-1"


@pytest.mark.asyncio
async def test_preview_kb_documents(client: TestClient):
    fake_preview = {"chunks": [{"content": "preview chunk"}], "total_chunks": 1}
    with patch(
        "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService.preview_documents",
        new_callable=AsyncMock,
        return_value=fake_preview,
    ):
        response = client.post(
            "/api/v1/knowledge-bases/1/documents/preview",
            json={"document_ids": [10]},
        )
        assert response.status_code == 200
        assert "chunks" in response.json()


@pytest.mark.asyncio
async def test_get_processing_tasks(client: TestClient):
    fake_tasks = {"task_1": {"status": "completed"}}
    with patch(
        "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService.get_processing_tasks",
        new_callable=AsyncMock,
        return_value=fake_tasks,
    ):
        response = client.get("/api/v1/knowledge-bases/1/documents/tasks?task_ids=task_1,task_2")
        assert response.status_code == 200
        assert "task_1" in response.json()


@pytest.mark.asyncio
async def test_get_and_delete_document(client: TestClient):
    with patch(
        "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService.get_document",
        new_callable=AsyncMock,
        return_value={"id": 5, "file_name": "doc.pdf"},
    ), patch(
        "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService.delete_document",
        new_callable=AsyncMock,
        return_value={"status": "deleted", "doc_id": 5},
    ):
        get_res = client.get("/api/v1/knowledge-bases/1/documents/5")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == 5

        del_res = client.delete("/api/v1/knowledge-bases/1/documents/5")
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "deleted"


@pytest.mark.asyncio
async def test_process_kb_documents_and_cleanup(client: TestClient):
    with patch(
        "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService.process_documents",
        new_callable=AsyncMock,
        return_value={"status": "processing", "count": 1},
    ), patch(
        "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService.cleanup_temp_files",
        new_callable=AsyncMock,
        return_value={"status": "cleaned", "deleted": 0},
    ):
        proc_res = client.post(
            "/api/v1/knowledge-bases/1/documents/process",
            json=[{"filename": "doc.pdf", "status": "uploaded"}],
        )
        assert proc_res.status_code == 200
        assert proc_res.json()["count"] == 1

        clean_res = client.post("/api/v1/knowledge-bases/cleanup")
        assert clean_res.status_code == 200
        assert clean_res.json()["status"] == "cleaned"


@pytest.mark.asyncio
async def test_test_retrieval_endpoint(client: TestClient):
    with patch(
        "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService.test_retrieval",
        new_callable=AsyncMock,
        return_value={"chunks": [{"chunk_id": "c1", "text": "result"}]},
    ):
        response = client.post(
            "/api/v1/knowledge-bases/test-retrieval",
            json={"query": "test query", "kb_id": 1, "top_k": 3},
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert len(response.json()["results"]) == 1
