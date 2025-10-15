import io
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import AsyncMock, patch

from app.main import app
from app.db.session import get_db
from app.models.base import Base
from app.models.app import App, AppStatus

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test and drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_app_data():
    """Sample data for app registration."""
    return {
        "app_name": "agriconnect",
        "domain": "agriconnect.akvo.org/api",
        "default_chat_prompt": "",
        "chat_callback": "https://agriconnect.akvo.org/api/ai/callback",
        "upload_callback": "https://agriconnect.akvo.org/api/kb/callback",
        "callback_token": "test_callback_token_123",
    }


@pytest.fixture(autouse=True)
def mock_mcp_create_kb():
    """
    Automatically mock KnowledgeBaseMCPEndpointService.create_kb
    for any test that calls the /register endpoint.
    """
    with patch(
        "mcp_clients.kb_mcp_endpoint_service.KnowledgeBaseMCPEndpointService.create_kb",
        new_callable=AsyncMock,
    ) as mock_create_kb:
        # Default fake KB response
        mock_create_kb.return_value = {
            "id": 42,
            "name": "Fake KB",
            "description": "KB for testing"
        }
        yield mock_create_kb


@pytest.fixture(autouse=True)
def mock_upload_and_process_documents():
    """
    Automatically mock KnowledgeBaseMCPEndpointService.upload_and_process_documents
    for any test that calls the /upload endpoint.
    """
    with patch(
        "mcp_clients.kb_mcp_endpoint_service.KnowledgeBaseMCPEndpointService.upload_and_process_documents",
        new_callable=AsyncMock,
    ) as mock_upload_and_process_documents:
        # Default fake KB response
        mock_upload_and_process_documents.return_value = {
            "status": "processing",
            "kb_id": 42,
            "file_count": 2,
        }
        yield mock_upload_and_process_documents


@pytest.fixture(autouse=True)
def mock_get_documents_upload():
    """
    Automatically mock KnowledgeBaseMCPEndpointService.get_documents_upload
    for any test that calls the /documents endpoint.
    """
    with patch(
        "mcp_clients.kb_mcp_endpoint_service.KnowledgeBaseMCPEndpointService.get_documents_upload",
        new_callable=AsyncMock,
    ) as mock_get_documents_upload:
        # ✅ Dummy fake KB response
        mock_get_documents_upload.return_value = [
            {
                "id": 1,
                "file_name": "File1.pdf",
                "status": "completed",
                "knowledge_base_id": 42,
                "content_type": "application/pdf",
                "created_at": "2025-10-15T01:34:42.728153",
            },
            {
                "id": 2,
                "file_name": "File2.pdf",
                "status": "processing",
                "knowledge_base_id": 42,
                "content_type": "application/pdf",
                "created_at": "2025-10-15T01:34:42.689894",
            },
        ]
        yield mock_get_documents_upload


class TestAppRegistration:
    """Test suite for POST /v1/apps/register endpoint."""

    def test_register_app_success(self, sample_app_data):
        """Test successful app registration returns credentials."""
        response = client.post("/v1/apps/register", json=sample_app_data)

        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert "app_id" in data
        assert "client_id" in data
        assert "access_token" in data
        assert "scopes" in data
        assert "knowledge_base_id" in data
        assert data["knowledge_base_id"] == 42

        # Verify ID prefixes
        assert data["app_id"].startswith("app_")
        assert data["client_id"].startswith("ac_")
        assert data["access_token"].startswith("tok_")

        # Verify default scopes
        assert "jobs.write" in data["scopes"]
        assert "kb.read" in data["scopes"]
        assert "kb.write" in data["scopes"]
        assert "apps.read" in data["scopes"]

    def test_register_app_validates_https_chat_callback(self, sample_app_data):
        """Test that non-HTTPS chat_callback URL is rejected."""
        sample_app_data["chat_callback"] = "http://agriconnect.akvo.org/api/ai/callback"
        response = client.post("/v1/apps/register", json=sample_app_data)

        assert response.status_code == 422  # Validation error
        assert "https" in response.text.lower()

    def test_register_app_validates_https_upload_callback(self, sample_app_data):
        """Test that non-HTTPS upload_callback URL is rejected."""
        sample_app_data["upload_callback"] = "http://agriconnect.akvo.org/api/kb/callback"
        response = client.post("/v1/apps/register", json=sample_app_data)

        assert response.status_code == 422  # Validation error
        assert "https" in response.text.lower()


class TestAppMe:
    """Test suite for GET /v1/apps/me endpoint."""

    @pytest.fixture
    def registered_app(self, sample_app_data):
        """Register an app and return credentials."""
        response = client.post("/v1/apps/register", json=sample_app_data)
        return response.json()

    def test_app_me_success_with_valid_token(self, registered_app):
        """Test /me endpoint returns app info with valid token."""
        headers = {"Authorization": f"Bearer {registered_app['access_token']}"}
        response = client.get("/v1/apps/me", headers=headers)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["app_id"] == registered_app["app_id"]
        assert data["app_name"] == "agriconnect"
        assert data["domain"] == "agriconnect.akvo.org/api"
        assert data["chat_callback_url"] == "https://agriconnect.akvo.org/api/ai/callback"
        assert data["upload_callback_url"] == "https://agriconnect.akvo.org/api/kb/callback"
        assert data["status"] == "active"
        assert data["scopes"] == registered_app["scopes"]
        assert data["knowledge_base_id"] == 42

    def test_app_me_returns_401_with_invalid_token(self):
        """Test /me endpoint returns 401 with invalid token."""
        headers = {"Authorization": "Bearer tok_invalid_token"}
        response = client.get("/v1/apps/me", headers=headers)

        assert response.status_code == 401

    def test_app_me_returns_401_without_token(self):
        """Test /me endpoint returns 401 without Authorization header."""
        response = client.get("/v1/apps/me")

        assert response.status_code == 401

    def test_app_me_returns_403_for_inactive_app(self, registered_app):
        """Test /me endpoint returns 403 for inactive app."""
        # Manually set app to revoked status
        db = TestingSessionLocal()
        app = db.query(App).filter(App.app_id == registered_app["app_id"]).first()
        app.status = AppStatus.revoked
        db.commit()
        db.close()

        headers = {"Authorization": f"Bearer {registered_app['access_token']}"}
        response = client.get("/v1/apps/me", headers=headers)

        assert response.status_code == 403


class TestAppRotate:
    """Test suite for POST /v1/apps/rotate endpoint."""

    @pytest.fixture
    def registered_app(self, sample_app_data):
        """Register an app and return credentials."""
        response = client.post("/v1/apps/register", json=sample_app_data)
        return response.json()

    def test_rotate_access_token_only(self, registered_app):
        """Test rotating only the access token."""
        old_token = registered_app["access_token"]
        headers = {"Authorization": f"Bearer {old_token}"}
        payload = {"rotate_access_token": True, "rotate_callback_token": False}

        response = client.post("/v1/apps/rotate", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()

        # Verify new access token is different
        assert data["access_token"] is not None
        assert data["access_token"] != old_token
        assert data["access_token"].startswith("tok_")

        # Verify callback token was not rotated
        assert data["callback_token"] is None

        # Verify new token works
        new_headers = {"Authorization": f"Bearer {data['access_token']}"}
        me_response = client.get("/v1/apps/me", headers=new_headers)
        assert me_response.status_code == 200

        # Verify old token is invalidated
        old_headers = {"Authorization": f"Bearer {old_token}"}
        old_me_response = client.get("/v1/apps/me", headers=old_headers)
        assert old_me_response.status_code == 401

    def test_rotate_callback_token_only(self, registered_app):
        """Test rotating only the callback token."""
        headers = {"Authorization": f"Bearer {registered_app['access_token']}"}
        payload = {
            "rotate_access_token": False,
            "rotate_callback_token": True,
            "new_callback_token": "new_test_callback_token_456"
        }

        response = client.post("/v1/apps/rotate", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()

        # Verify callback token was rotated (returns None in response)
        assert data["callback_token"] is None

        # Verify access token was not rotated
        assert data["access_token"] is None

        # Verify the callback token was updated in the database
        db = TestingSessionLocal()
        app = db.query(App).filter(App.app_id == registered_app["app_id"]).first()
        assert app.callback_token == "new_test_callback_token_456"
        db.close()

    def test_rotate_both_tokens(self, registered_app):
        """Test rotating both access and callback tokens."""
        old_access_token = registered_app["access_token"]
        headers = {"Authorization": f"Bearer {old_access_token}"}
        payload = {
            "rotate_access_token": True,
            "rotate_callback_token": True,
            "new_callback_token": "new_test_callback_token_789"
        }

        response = client.post("/v1/apps/rotate", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()

        # Verify both tokens were rotated
        assert data["access_token"] is not None
        assert data["access_token"] != old_access_token
        assert data["callback_token"] is None  # callback_token not returned in response
        assert data["message"] == "Both tokens rotated successfully"

        # Verify the callback token was updated in the database
        db = TestingSessionLocal()
        app = db.query(App).filter(App.app_id == registered_app["app_id"]).first()
        assert app.callback_token == "new_test_callback_token_789"
        db.close()

    def test_rotate_no_tokens(self, registered_app):
        """Test rotate endpoint when no tokens are requested to rotate."""
        headers = {"Authorization": f"Bearer {registered_app['access_token']}"}
        payload = {"rotate_access_token": False, "rotate_callback_token": False}

        response = client.post("/v1/apps/rotate", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["access_token"] is None
        assert data["callback_token"] is None
        assert data["message"] == "No tokens were rotated"


class TestAppRevoke:
    """Test suite for POST /v1/apps/revoke endpoint."""

    @pytest.fixture
    def registered_app(self, sample_app_data):
        """Register an app and return credentials."""
        response = client.post("/v1/apps/register", json=sample_app_data)
        return response.json()

    def test_revoke_app_success(self, registered_app):
        """Test successful app revocation."""
        headers = {"Authorization": f"Bearer {registered_app['access_token']}"}
        response = client.post("/v1/apps/revoke", headers=headers)

        assert response.status_code == 204

        # Verify /me endpoint now returns 401
        me_response = client.get("/v1/apps/me", headers=headers)
        assert me_response.status_code == 403  # Inactive app

    def test_revoke_app_idempotent(self, registered_app):
        """Test that revoking an app is idempotent."""
        headers = {"Authorization": f"Bearer {registered_app['access_token']}"}

        # First revocation
        response1 = client.post("/v1/apps/revoke", headers=headers)
        assert response1.status_code == 204

        # Attempting to use revoked token should fail
        me_response = client.get("/v1/apps/me", headers=headers)
        assert me_response.status_code == 403

    def test_revoke_requires_valid_token(self):
        """Test that revoke endpoint requires valid token."""
        headers = {"Authorization": "Bearer tok_invalid"}
        response = client.post("/v1/apps/revoke", headers=headers)

        assert response.status_code == 401


class TestAppUpload:
    """
    Test suite for POST /v1/apps/upload endpoint.
    and GET /v1/apps/documents endpoint.
    """

    @pytest.fixture
    def registered_app(self, sample_app_data):
        """Register an app and return credentials."""
        response = client.post("/v1/apps/register", json=sample_app_data)
        return response.json()

    def test_upload_success(self, registered_app):
        """Test successful document upload and processing."""
        headers = {"Authorization": f"Bearer {registered_app['access_token']}"}

        # Create dummy files to upload
        files = [
            ("files", ("doc1.txt", io.BytesIO(b"Test content 1"), "text/plain")),
            ("files", ("doc2.txt", io.BytesIO(b"Test content 2"), "text/plain")),
        ]

        response = client.post("/v1/apps/upload", headers=headers, files=files)

        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Document received and is being processed."
        assert data["file_count"] == 2

    def test_upload_unauthorized_no_token(self):
        """Test upload without Authorization header returns 401."""
        files = [
            ("files", ("doc.txt", io.BytesIO(b"Test content"), "text/plain")),
        ]

        response = client.post("/v1/apps/upload", files=files)
        assert response.status_code == 401

    def test_upload_unauthorized_invalid_token(self):
        """Test upload with invalid token returns 401."""
        headers = {"Authorization": "Bearer invalid_token"}
        files = [
            ("files", ("doc.txt", io.BytesIO(b"Test content"), "text/plain")),
        ]

        response = client.post("/v1/apps/upload", headers=headers, files=files)
        assert response.status_code == 401

    def test_upload_forbidden_revoked_app(self, registered_app):
        """Test upload returns 403 for revoked app."""
        # Set app status to revoked manually
        db = TestingSessionLocal()
        app = db.query(App).filter(App.app_id == registered_app["app_id"]).first()
        app.status = "revoked"
        db.commit()
        db.close()

        headers = {"Authorization": f"Bearer {registered_app['access_token']}"}
        files = [
            ("files", ("doc.txt", io.BytesIO(b"Test content"), "text/plain")),
        ]

        response = client.post("/v1/apps/upload", headers=headers, files=files)
        assert response.status_code == 403

    def test_get_upload_docs(self, registered_app):
        """Test successful get uploaded documents."""
        headers = {"Authorization": f"Bearer {registered_app['access_token']}"}

        response = client.get("/v1/apps/documents", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["file_name"] == "File1.pdf"
        assert data[1]["file_name"] == "File2.pdf"
        assert data[0]["knowledge_base_id"] == 42
        assert data[1]["knowledge_base_id"] == 42

    def test_get_upload_failed(self, registered_app):
        """Test no auth get uploaded documents."""

        response = client.get("/v1/apps/documents")
        assert response.status_code == 401
