import pytest
import itertools
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


@pytest.fixture
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


@pytest.mark.usefixtures("mock_mcp_create_and_get_kb")
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


class TestDeleteKnowledgeBaseEndpoint:
    """Test suite for deleting knowledge bases from an app."""

    @pytest.fixture(autouse=True)
    def mock_mcp_delete_kb(self):
        """Mock delete_kb call to MCP service."""
        with patch(
            "mcp_clients.kb_mcp_endpoint_service.KnowledgeBaseMCPEndpointService.delete_kb",
            new_callable=AsyncMock,
        ) as mock_delete_kb:
            mock_delete_kb.return_value = {"status": "deleted"}
            yield mock_delete_kb

    @pytest.fixture(autouse=True)
    def mock_unique_mcp_create_kb(self):
        """Ensure each create_kb call returns a unique ID."""
        counter = itertools.count(100)
        with patch(
            "mcp_clients.kb_mcp_endpoint_service.KnowledgeBaseMCPEndpointService.create_kb",
            new_callable=AsyncMock,
        ) as mock_create_kb:
            mock_create_kb.side_effect = lambda *a, **kw: {
                "id": next(counter),
                "name": "Mock KB",
                "description": "Created via mock MCP",
            }
            yield mock_create_kb

    def test_delete_last_kb_forbidden(
        self, client, auth_header, db, registered_app
    ):
        """Should forbid deleting the last remaining KB."""
        # Simulate app with only one KB in DB
        app = (
            db.query(App)
            .filter(App.app_id == registered_app["app_id"])
            .first()
        )

        # Manually ensure only one KB remains
        assert len(app.knowledge_bases) == 1

        kb_id = app.knowledge_bases[0].knowledge_base_id
        response = client.delete(
            f"/api/apps/knowledge-bases/{kb_id}", headers=auth_header
        )

        assert response.status_code == 403
        assert (
            response.json()["detail"]
            == "Cannot delete the last knowledge base for this app."
        )

    def test_delete_default_kb_forbidden(
        self, client, auth_header, registered_app
    ):
        """Should forbid deleting the default KB."""
        # Create a second non-default KB (unique ID now guaranteed)
        payload = {
            "name": "Extra KB",
            "description": "Secondary KB for deletion test",
            "is_default": False,
        }
        create_res = client.post(
            "/api/apps/knowledge-bases", json=payload, headers=auth_header
        )
        assert create_res.status_code == 201

        # delete default kb
        default_kb_id = registered_app["knowledge_bases"][0][
            "knowledge_base_id"
        ]

        response = client.delete(
            f"/api/apps/knowledge-bases/{default_kb_id}", headers=auth_header
        )

        assert response.status_code == 403
        assert (
            response.json()["detail"]
            == "Cannot delete the default knowledge base. Set another KB as default first."
        )

    def test_delete_non_default_kb_success(
        self, client, auth_header, db, registered_app
    ):
        """Should successfully delete a non-default KB."""

        # Step 1️⃣: Create a second non-default KB (unique ID now guaranteed)
        payload = {
            "name": "Extra KB",
            "description": "Secondary KB for deletion test",
            "is_default": False,
        }
        create_res = client.post(
            "/api/apps/knowledge-bases", json=payload, headers=auth_header
        )
        assert create_res.status_code == 201
        kb_to_delete = create_res.json()["knowledge_base_id"]

        # Step 2️⃣: Delete the new KB
        delete_res = client.delete(
            f"/api/apps/knowledge-bases/{kb_to_delete}", headers=auth_header
        )
        assert delete_res.status_code == 204

        # Step 3️⃣: Verify KB link removed in DB
        app = (
            db.query(App)
            .filter(App.app_id == registered_app["app_id"])
            .first()
        )
        kb_ids = [kb.knowledge_base_id for kb in app.knowledge_bases]
        assert kb_to_delete not in kb_ids

    def test_delete_nonexistent_kb_not_found(self, client, auth_header):
        """
        Should return 404 when trying to delete a KB not linked to this app.
        """
        response = client.delete(
            "/api/apps/knowledge-bases/999999", headers=auth_header
        )
        assert response.status_code == 404
