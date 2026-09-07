from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
import pytest

from app.api.api_v1.auth import get_current_user as get_current_user_auth
from app.core.security import get_current_user, get_current_app
from app.models.user import User
from app.models.app import App
from mcp_clients.kb_mcp_endpoint_service import KnowledgeBaseMCPEndpointService


@pytest.fixture
def override_user_auth(client: TestClient):
    """Override user authentication to provide a mock superuser."""
    from app.main import app

    fake_user = User(
        id=1,
        email="host_tenant@example.com",
        is_active=True,
        is_superuser=True,
    )
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_current_user_auth] = lambda: fake_user
    yield fake_user
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]
    if get_current_user_auth in app.dependency_overrides:
        del app.dependency_overrides[get_current_user_auth]


@pytest.fixture
def override_app_auth(client: TestClient):
    """Override app authentication to provide a mock tenant app."""
    from app.main import app

    fake_app = App(
        id=1,
        app_name="AgriConnect",
        domain="agriconnect.org",
        api_key_hash="hashed_key",
        api_secret_hash="hashed_secret",
        default_chat_prompt="You are AgriConnect assistant.",
    )
    app.dependency_overrides[get_current_app] = lambda: fake_app
    yield fake_app
    if get_current_app in app.dependency_overrides:
        del app.dependency_overrides[get_current_app]


# ---------------------------------------------------------------------
# Knowledge Base & Documents Host REST Endpoints Parity Tests
# ---------------------------------------------------------------------
@pytest.mark.unit
class TestHostKnowledgeBaseEndpoints:
    """Validates backward compatibility for AgriConnect and CoM."""

    def test_list_knowledge_bases_contract(
        self, client: TestClient, override_user_auth, monkeypatch
    ):
        """Test GET /api/knowledge-base returns list with expected fields."""
        fake_dispatcher = MagicMock()
        fake_dispatcher.call_tool = AsyncMock(
            return_value={
                "knowledge_bases": [
                    {
                        "id": 1,
                        "name": "AgriConnect KB",
                        "description": "Farming documentation",
                        "created_at": "2026-09-01T00:00:00",
                        "documents": [],
                    }
                ]
            }
        )
        fake_service = KnowledgeBaseMCPEndpointService(
            dispatcher=fake_dispatcher
        )
        monkeypatch.setattr(
            "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService",
            lambda: fake_service,
        )

        response = client.get("/api/knowledge-base")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["name"] == "AgriConnect KB"
        assert data[0]["is_superuser"] is True

    def test_get_knowledge_base_details_contract(
        self, client: TestClient, override_user_auth, monkeypatch
    ):
        """Test GET /api/knowledge-base/{id} returns single KB object."""
        fake_dispatcher = MagicMock()
        fake_dispatcher.call_tool = AsyncMock(
            return_value={
                "knowledge_base": {
                    "id": 42,
                    "name": "CoM Handpump SOP",
                    "description": "Water sanitation maintenance",
                    "status": "ACTIVE",
                }
            }
        )
        fake_service = KnowledgeBaseMCPEndpointService(
            dispatcher=fake_dispatcher
        )
        monkeypatch.setattr(
            "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService",
            lambda: fake_service,
        )

        response = client.get("/api/knowledge-base/42")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 42
        assert data["name"] == "CoM Handpump SOP"
        assert data["is_superuser"] is True

    def test_create_knowledge_base_contract(
        self, client: TestClient, override_user_auth, monkeypatch
    ):
        """Test POST /api/knowledge-base creates new KB and returns JSON."""
        fake_dispatcher = MagicMock()
        fake_dispatcher.call_tool = AsyncMock(
            return_value={
                "knowledge_base": {
                    "id": 101,
                    "name": "Irrigation Standard",
                    "description": "Drip irrigation SOPs",
                }
            }
        )
        fake_service = KnowledgeBaseMCPEndpointService(
            dispatcher=fake_dispatcher
        )
        monkeypatch.setattr(
            "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService",
            lambda: fake_service,
        )

        payload = {
            "name": "Irrigation Standard",
            "description": "Drip irrigation SOPs",
            "embedding_model": "text-embedding-3-small",
        }
        response = client.post("/api/knowledge-base", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 101
        assert data["name"] == "Irrigation Standard"

    def test_update_knowledge_base_contract(
        self, client: TestClient, override_user_auth, monkeypatch
    ):
        """Test PUT /api/knowledge-base/{id} updates metadata."""
        fake_dispatcher = MagicMock()
        fake_dispatcher.call_tool = AsyncMock(
            return_value={
                "knowledge_base": {
                    "id": 101,
                    "name": "Updated Irrigation Standard",
                    "description": "Updated SOPs",
                }
            }
        )
        fake_service = KnowledgeBaseMCPEndpointService(
            dispatcher=fake_dispatcher
        )
        monkeypatch.setattr(
            "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService",
            lambda: fake_service,
        )

        payload = {
            "name": "Updated Irrigation Standard",
            "description": "Updated SOPs",
        }
        response = client.put("/api/knowledge-base/101", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Irrigation Standard"

    def test_delete_knowledge_base_contract(
        self, client: TestClient, override_user_auth, monkeypatch
    ):
        """Test DELETE /api/knowledge-base/{id} deletes KB."""
        fake_dispatcher = MagicMock()
        fake_dispatcher.call_tool = AsyncMock(
            return_value={"status": "deleted", "id": 101}
        )
        fake_service = KnowledgeBaseMCPEndpointService(
            dispatcher=fake_dispatcher
        )
        monkeypatch.setattr(
            "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService",
            lambda: fake_service,
        )

        response = client.delete("/api/knowledge-base/101")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "deleted"

    def test_test_retrieval_endpoint_contract(
        self, client: TestClient, override_user_auth, monkeypatch
    ):
        """Test POST /api/knowledge-base/test-retrieval returns chunks."""
        fake_dispatcher = MagicMock()
        fake_dispatcher.call_tool = AsyncMock(
            return_value={
                "chunks": [
                    {
                        "chunk_id": "chk-001",
                        "content": "Chlorination dose is 0.5mg/L.",
                        "score": 0.96,
                    }
                ]
            }
        )
        fake_service = KnowledgeBaseMCPEndpointService(
            dispatcher=fake_dispatcher
        )
        monkeypatch.setattr(
            "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService",
            lambda: fake_service,
        )

        payload = {
            "kb_id": 1,
            "query": "chlorination dose",
            "top_k": 3,
        }
        response = client.post(
            "/api/knowledge-base/test-retrieval", json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert "chunks" in data
        assert len(data["chunks"]) == 1
        assert data["chunks"][0]["chunk_id"] == "chk-001"

    def test_document_upload_contract(
        self, client: TestClient, override_user_auth, monkeypatch
    ):
        """Test POST /api/v1/knowledge-bases/{id}/documents/upload
        multipart upload."""
        fake_minio = MagicMock()
        fake_minio.upload_file.return_value = {
            "bucket": "documents",
            "object_name": "kb_10/doc_sop.pdf",
            "size": 512,
        }
        fake_redis = AsyncMock()
        fake_redis.rpush = AsyncMock(return_value=1)
        fake_redis.aclose = AsyncMock()

        from app.services.minio_service import get_minio_service
        from app.api.api_v1.knowledge_base import get_redis_client
        from app.main import app

        app.dependency_overrides[get_minio_service] = lambda: fake_minio
        app.dependency_overrides[get_redis_client] = lambda: fake_redis

        files = {
            "file": (
                "pest_sop.pdf",
                b"%PDF-1.4 test bytes",
                "application/pdf",
            )
        }
        response = client.post(
            "/api/v1/knowledge-bases/10/documents/upload", files=files
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "PROCESSING"
        assert data["kb_id"] == 10
        assert "pest_sop.pdf" in data["filename"]

        app.dependency_overrides.pop(get_minio_service, None)
        app.dependency_overrides.pop(get_redis_client, None)

    def test_get_processing_tasks_contract(
        self, client: TestClient, override_user_auth, monkeypatch
    ):
        """Test GET /api/v1/knowledge-bases/{id}/documents/tasks
        returns task status."""
        fake_dispatcher = MagicMock()
        fake_dispatcher.call_tool = AsyncMock(
            return_value={
                "tasks": [
                    {
                        "task_id": "task-abc",
                        "status": "INDEXED",
                        "progress": 1.0,
                    }
                ]
            }
        )
        fake_service = KnowledgeBaseMCPEndpointService(
            dispatcher=fake_dispatcher
        )
        monkeypatch.setattr(
            "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService",
            lambda: fake_service,
        )

        response = client.get(
            "/api/v1/knowledge-bases/10/documents/tasks?task_ids=task-abc"
        )
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert data["tasks"][0]["task_id"] == "task-abc"
        assert data["tasks"][0]["status"] == "INDEXED"

    def test_v1_knowledge_bases_parity(
        self, client: TestClient, override_user_auth, monkeypatch
    ):
        """Verify both /api/knowledge-bases and /api/v1/knowledge-bases
        return identical data."""
        fake_dispatcher = MagicMock()
        fake_dispatcher.call_tool = AsyncMock(
            return_value={
                "knowledge_bases": [{"id": 1, "name": "KB 1", "documents": []}]
            }
        )
        fake_service = KnowledgeBaseMCPEndpointService(
            dispatcher=fake_dispatcher
        )
        monkeypatch.setattr(
            "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService",
            lambda: fake_service,
        )

        resp_api = client.get("/api/knowledge-bases")
        resp_v1 = client.get("/api/v1/knowledge-bases")
        assert resp_api.status_code == 200
        assert resp_v1.status_code == 200
        assert resp_api.json() == resp_v1.json()


# ---------------------------------------------------------------------
# Chat & App Tenant Endpoints Parity Tests
# ---------------------------------------------------------------------
@pytest.mark.unit
class TestHostChatAndAppsEndpoints:
    """Validates backwards compatibility for Chat and App contracts."""

    def test_create_chat_session_contract(
        self, client: TestClient, override_user_auth
    ):
        """Test POST /api/chat creates a new chat session."""
        payload = {
            "title": "AgriConnect Q&A Session",
            "knowledge_base_ids": [1],
        }
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "AgriConnect Q&A Session"
        assert "id" in data
        assert "created_at" in data

    def test_get_chats_list_contract(
        self, client: TestClient, override_user_auth
    ):
        """Test GET /api/chat lists all user chats."""
        # Create chat first
        client.post(
            "/api/chat",
            json={"title": "Session 1", "knowledge_base_ids": [1]},
        )
        response = client.get("/api/chat")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["title"] == "Session 1"

    def test_register_app_contract(
        self, client: TestClient, override_user_auth, monkeypatch
    ):
        """Test POST /api/apps/register creates a new host app."""
        fake_dispatcher = MagicMock()
        fake_dispatcher.call_tool = AsyncMock(
            return_value={
                "knowledge_base": {"id": 1, "name": "AgriConnect App"}
            }
        )
        fake_service = KnowledgeBaseMCPEndpointService(
            dispatcher=fake_dispatcher
        )
        monkeypatch.setattr(
            "app.api.api_v1.apps.KnowledgeBaseMCPEndpointService",
            lambda: fake_service,
        )

        payload = {
            "app_name": "AgriConnect App",
            "domain": "agriconnect.org",
            "default_chat_prompt": "You are AgriConnect assistant.",
            "chat_callback": "https://agriconnect.org/api/callback/chat",
            "upload_callback": "https://agriconnect.org/api/callback/upload",
        }
        response = client.post("/api/apps/register", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "app_id" in data
        assert "client_id" in data
        assert "access_token" in data
