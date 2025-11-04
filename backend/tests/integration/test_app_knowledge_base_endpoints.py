import pytest
from unittest.mock import AsyncMock, patch
from app.models.app import App, AppStatus, AppKnowledgeBase


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


@pytest.fixture
def registered_app(client, sample_app_data):
    """Register an app and return credentials."""
    response = client.post("/api/apps/register", json=sample_app_data)
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def auth_header(registered_app):
    """Return Authorization header for the registered app."""
    return {"Authorization": f"Bearer {registered_app['access_token']}"}


@pytest.fixture(autouse=True)
def mock_mcp_create_and_get_kb():
    """Mock both create_kb and get_kb calls to MCP service."""
    with patch(
        "mcp_clients.kb_mcp_endpoint_service.KnowledgeBaseMCPEndpointService.create_kb",
        new_callable=AsyncMock,
    ) as mock_create_kb, patch(
        "mcp_clients.kb_mcp_endpoint_service.KnowledgeBaseMCPEndpointService.get_kb",
        new_callable=AsyncMock,
    ) as mock_get_kb:

        mock_create_kb.return_value = {
            "id": 42,
            "name": "Mock KB",
            "description": "Created via mock MCP",
        }
        mock_get_kb.return_value = {
            "id": 42,
            "name": "Mock KB",
            "description": "Fetched via mock MCP",
        }

        yield mock_create_kb, mock_get_kb


class TestAppKnowledgeBaseEndpoints:
    """Test suite for multi KB per app endpoints."""

    def test_create_knowledge_base_success(self, client, auth_header):
        """Should successfully create a KB for the active app."""
        payload = {
            "name": "Knowledge Base 1",
            "description": "Test KB for app",
            "is_default": True,
        }

        response = client.post(
            "/api/apps/knowledge-bases", json=payload, headers=auth_header
        )

        assert response.status_code == 201
        data = response.json()

        assert "id" in data
        assert "knowledge_base_id" in data
        assert data["name"] == "Knowledge Base 1"
        assert data["is_default"] is True

    def test_create_kb_for_inactive_app_forbidden(
        self, client, db, registered_app
    ):
        """Should return 403 if app is inactive."""
        app = (
            db.query(App)
            .filter(App.app_id == registered_app["app_id"])
            .first()
        )
        app.status = AppStatus.revoked
        db.commit()

        headers = {"Authorization": f"Bearer {registered_app['access_token']}"}
        payload = {"name": "Should Fail", "is_default": True}

        response = client.post(
            "/api/apps/knowledge-bases", json=payload, headers=headers
        )

        assert response.status_code == 403
        assert "active" in response.text.lower()

    def test_set_default_kb_success(self, client, auth_header, registered_app):
        """Should set an existing KB as the default."""
        kb_id = registered_app["knowledge_bases"][0]["knowledge_base_id"]

        response = client.patch(
            f"/api/apps/knowledge-bases/{kb_id}/default", headers=auth_header
        )

        assert response.status_code == 200
        data = response.json()

        assert data["knowledge_base_id"] == kb_id
        assert data["is_default"] is True
        assert data["name"] == "Mock KB"

    def test_set_default_kb_not_found(self, client, auth_header):
        """Should return 404 if KB not found for this app."""
        response = client.patch(
            "/api/apps/knowledge-bases/9999/default", headers=auth_header
        )

        assert response.status_code == 404
        assert "not found" in response.text.lower()

    def test_set_default_kb_for_inactive_app_forbidden(
        self, client, db, registered_app
    ):
        """Should return 403 if app is inactive."""
        app = (
            db.query(App)
            .filter(App.app_id == registered_app["app_id"])
            .first()
        )
        app.status = AppStatus.revoked
        db.commit()

        kb_id = registered_app["knowledge_bases"][0]["knowledge_base_id"]
        headers = {"Authorization": f"Bearer {registered_app['access_token']}"}

        response = client.patch(
            f"/api/apps/knowledge-bases/{kb_id}/default", headers=headers
        )

        assert response.status_code == 403
        assert "active" in response.text.lower()

    def test_create_new_default_unsets_previous(
        self, client, auth_header, db, registered_app
    ):
        """
        Creating a new KB with is_default=True should unset existing default.
        Ensures AppService._unset_existing_default() keeps only one default.
        """
        # Ensure we have a default KB already (from registration)
        existing_default_app = (
            db.query(App)
            .filter(App.app_id == registered_app["app_id"])
            .first()
        )

        # Create a new KB marked as default
        payload = {
            "name": "New Default KB",
            "description": "This one should become default",
            "is_default": True,
        }

        response = client.post(
            "/api/apps/knowledge-bases", json=payload, headers=auth_header
        )
        assert response.status_code == 201
        data = response.json()
        assert data["is_default"] is True

        # ✅ Now verify that only ONE KB is default for this app
        defaults = (
            db.query(AppKnowledgeBase)
            .filter(
                AppKnowledgeBase.app_id == existing_default_app.id,
                AppKnowledgeBase.is_default == 1,
            )
            .all()
        )
        assert (
            len(defaults) == 1
        ), f"Expected 1 default KB, found {len(defaults)}"

        # ✅ Optionally enforce logic-level integrity check
        # (simulate multiple concurrent defaults to test the safeguard)
        count_defaults = (
            db.query(AppKnowledgeBase)
            .filter(
                AppKnowledgeBase.app_id == existing_default_app.id,
                AppKnowledgeBase.is_default == 1,
            )
            .count()
        )
        assert (
            count_defaults == 1
        ), "App must never have more than one default KB"
