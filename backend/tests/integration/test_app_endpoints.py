import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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
    }


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
        assert "callback_token" in data
        assert "scopes" in data

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

    def test_app_me_returns_401_with_invalid_token(self):
        """Test /me endpoint returns 401 with invalid token."""
        headers = {"Authorization": "Bearer tok_invalid_token"}
        response = client.get("/v1/apps/me", headers=headers)

        assert response.status_code == 401

    def test_app_me_returns_401_without_token(self):
        """Test /me endpoint returns 401 without Authorization header."""
        response = client.get("/v1/apps/me")

        assert response.status_code == 403  # HTTPBearer returns 403 when no credentials

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

        # Verify old token still works (per requirements)
        old_headers = {"Authorization": f"Bearer {old_token}"}
        me_response = client.get("/v1/apps/me", headers=old_headers)
        assert me_response.status_code == 200

    def test_rotate_callback_token_only(self, registered_app):
        """Test rotating only the callback token."""
        headers = {"Authorization": f"Bearer {registered_app['access_token']}"}
        payload = {"rotate_access_token": False, "rotate_callback_token": True}

        response = client.post("/v1/apps/rotate", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()

        # Verify callback token was rotated
        assert data["callback_token"] is not None
        assert len(data["callback_token"]) >= 32

        # Verify access token was not rotated
        assert data["access_token"] is None

    def test_rotate_both_tokens(self, registered_app):
        """Test rotating both access and callback tokens."""
        old_access_token = registered_app["access_token"]
        old_callback_token = registered_app["callback_token"]
        headers = {"Authorization": f"Bearer {old_access_token}"}
        payload = {"rotate_access_token": True, "rotate_callback_token": True}

        response = client.post("/v1/apps/rotate", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()

        # Verify both tokens were rotated
        assert data["access_token"] is not None
        assert data["callback_token"] is not None
        assert data["access_token"] != old_access_token
        assert data["callback_token"] != old_callback_token
        assert data["message"] == "Both tokens rotated successfully"

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
