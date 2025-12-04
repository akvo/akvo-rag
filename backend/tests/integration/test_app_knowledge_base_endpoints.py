import pytest
import itertools
from unittest.mock import AsyncMock, patch
from app.models.app import App, AppStatus, AppKnowledgeBase


@pytest.fixture
def sample_app_data():
    """Sample data for app registration."""
    return {
        "app_name": "agriconnect2",
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
def mock_mcp_crud_kb():
    """Mock MCP service calls for KB CRUD operations."""
    with patch(
        "mcp_clients.kb_mcp_endpoint_service.KnowledgeBaseMCPEndpointService.create_kb",  # noqa
        new_callable=AsyncMock,
    ) as mock_create_kb, patch(
        "mcp_clients.kb_mcp_endpoint_service.KnowledgeBaseMCPEndpointService.get_kb",  # noqa
        new_callable=AsyncMock,
    ) as mock_get_kb, patch(
        "mcp_clients.kb_mcp_endpoint_service.KnowledgeBaseMCPEndpointService.update_kb",  # noqa
        new_callable=AsyncMock,
    ) as mock_update_kb, patch(
        "mcp_clients.kb_mcp_endpoint_service.KnowledgeBaseMCPEndpointService.delete_kb",  # noqa
        new_callable=AsyncMock,
    ) as mock_delete_kb:

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
        mock_update_kb.return_value = {
            "id": 42,
            "name": "Mock KB Updated",
            "description": "Updated via mock MCP",
        }
        mock_delete_kb.return_value = {"message": "Deleted"}

        yield mock_create_kb, mock_get_kb, mock_update_kb, mock_delete_kb


@pytest.fixture
def mock_mcp_list_kbs():
    """Mock list_kbs call for the list knowledge bases endpoint."""
    with patch(
        "mcp_clients.kb_mcp_endpoint_service.KnowledgeBaseMCPEndpointService.list_kbs",  # noqa
        new_callable=AsyncMock,
    ) as mock_list_kbs:
        mock_list_kbs.return_value = {
            "total": 2,
            "page": 1,
            "size": 2,
            "data": [
                {
                    "id": 1,
                    "name": "KB One",
                    "description": "First KB",
                    "created_at": "2025-01-01T00:00:00",
                    "updated_at": "2025-01-01T00:00:00",
                    "documents": [],
                },
                {
                    "id": 2,
                    "name": "KB Two",
                    "description": "Second KB",
                    "created_at": "2025-01-02T00:00:00",
                    "updated_at": "2025-01-02T00:00:00",
                    "documents": [],
                },
            ],
        }
        yield mock_list_kbs


@pytest.fixture
def mock_mcp_list_documents():
    """Mock MCP list documents (paginated document listing)."""
    with patch(
        "mcp_clients.kb_mcp_endpoint_service.KnowledgeBaseMCPEndpointService.list_documents_by_kb_id",  # noqa
        new_callable=AsyncMock,
    ) as mock_list_docs:
        mock_list_docs.return_value = {
            "total": 18,
            "page": 2,
            "size": 1,
            "data": [
                {
                    "id": 14,
                    "knowledge_base_id": 1,
                    "file_name": "example.pdf",
                    "file_path": "kb_1/example.pdf",
                    "file_hash": "abc123",
                    "file_size": 123456,
                    "content_type": "application/pdf",
                    "created_at": "2025-10-13T07:38:24.232874",
                    "updated_at": "2025-10-13T07:38:24.232878",
                    "processing_tasks": [],
                }
            ],
        }
        yield mock_list_docs


@pytest.mark.usefixtures("mock_mcp_crud_kb")
class TestAppKnowledgeBaseEndpoints:
    """Test suite for multi-KB per app endpoints."""

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

    def test_update_kb_to_default_success(
        self, client, auth_header, registered_app
    ):
        """Should update an existing KB and mark as default."""
        kb_id = registered_app["knowledge_bases"][0]["knowledge_base_id"]

        payload = {
            "name": "Updated KB Name",
            "description": "Updated KB description",
            "is_default": True,
        }

        response = client.patch(
            f"/api/apps/knowledge-bases/{kb_id}",
            json=payload,
            headers=auth_header,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["knowledge_base_id"] == kb_id
        assert data["is_default"] is True
        assert "Updated" in data["name"]

    def test_update_nonexistent_kb_returns_404(self, client, auth_header):
        """Should return 404 when updating non-existing KB."""
        payload = {"is_default": True}
        response = client.patch(
            "/api/apps/knowledge-bases/99999",
            json=payload,
            headers=auth_header,
        )
        assert response.status_code == 404
        assert "not found" in response.text.lower()

    def test_update_kb_for_inactive_app_forbidden(
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
        payload = {"is_default": True}

        response = client.patch(
            f"/api/apps/knowledge-bases/{kb_id}", json=payload, headers=headers
        )

        assert response.status_code == 403
        assert "active" in response.text.lower()

    def test_create_new_default_unsets_previous(
        self, client, auth_header, db, registered_app
    ):
        """
        Creating a new KB with is_default=True should unset existing default.
        """
        existing_app = (
            db.query(App)
            .filter(App.app_id == registered_app["app_id"])
            .first()
        )

        payload = {
            "name": "New Default KB",
            "description": "Should become default",
            "is_default": True,
        }

        response = client.post(
            "/api/apps/knowledge-bases", json=payload, headers=auth_header
        )
        assert response.status_code == 201

        defaults = (
            db.query(AppKnowledgeBase)
            .filter(
                AppKnowledgeBase.app_id == existing_app.id,
                AppKnowledgeBase.is_default == 1,
            )
            .all()
        )
        assert (
            len(defaults) == 1
        ), f"Expected 1 default KB, found {len(defaults)}"


class TestDeleteKnowledgeBaseEndpoint:
    """Test suite for deleting knowledge bases from an app."""

    @pytest.fixture(autouse=True)
    def mock_mcp_delete_kb(self):
        """Mock delete_kb call to MCP service."""
        with patch(
            "mcp_clients.kb_mcp_endpoint_service.KnowledgeBaseMCPEndpointService.delete_kb",  # noqa
            new_callable=AsyncMock,
        ) as mock_delete_kb:
            mock_delete_kb.return_value = {"status": "deleted"}
            yield mock_delete_kb

    @pytest.fixture(autouse=True)
    def mock_unique_mcp_create_kb(self):
        """Ensure each create_kb call returns a unique ID."""
        counter = itertools.count(100)
        with patch(
            "mcp_clients.kb_mcp_endpoint_service.KnowledgeBaseMCPEndpointService.create_kb",  # noqa
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
        app = (
            db.query(App)
            .filter(App.app_id == registered_app["app_id"])
            .first()
        )
        assert len(app.knowledge_bases) == 1

        kb_id = app.knowledge_bases[0].knowledge_base_id
        response = client.delete(
            f"/api/apps/knowledge-bases/{kb_id}", headers=auth_header
        )

        assert response.status_code == 403
        assert "last knowledge base" in response.json()["detail"]

    def test_delete_default_kb_forbidden(
        self, client, auth_header, registered_app
    ):
        """Should forbid deleting the default KB."""
        payload = {
            "name": "Extra KB",
            "description": "Secondary KB for deletion test",
            "is_default": False,
        }
        create_res = client.post(
            "/api/apps/knowledge-bases", json=payload, headers=auth_header
        )
        assert create_res.status_code == 201

        default_kb_id = registered_app["knowledge_bases"][0][
            "knowledge_base_id"
        ]
        response = client.delete(
            f"/api/apps/knowledge-bases/{default_kb_id}", headers=auth_header
        )

        assert response.status_code == 403
        assert "default knowledge base" in response.json()["detail"]

    def test_delete_non_default_kb_success(
        self, client, auth_header, db, registered_app
    ):
        """Should successfully delete a non-default KB."""
        payload = {
            "name": "Extra KB",
            "description": "For deletion test",
            "is_default": False,
        }
        create_res = client.post(
            "/api/apps/knowledge-bases", json=payload, headers=auth_header
        )
        assert create_res.status_code == 201
        kb_to_delete = create_res.json()["knowledge_base_id"]

        delete_res = client.delete(
            f"/api/apps/knowledge-bases/{kb_to_delete}", headers=auth_header
        )
        assert delete_res.status_code == 204

        app = (
            db.query(App)
            .filter(App.app_id == registered_app["app_id"])
            .first()
        )
        kb_ids = [kb.knowledge_base_id for kb in app.knowledge_bases]
        assert kb_to_delete not in kb_ids

    def test_delete_nonexistent_kb_not_found(self, client, auth_header):
        """
        Should return 404 when trying to delete KB not linked to this app.
        """
        response = client.delete(
            "/api/apps/knowledge-bases/999999", headers=auth_header
        )
        assert response.status_code == 404
        assert "not found" in response.text.lower()


@pytest.mark.usefixtures("mock_mcp_crud_kb")
@pytest.mark.usefixtures("mock_mcp_list_kbs")
class TestListKnowledgeBasesEndpoint:
    """Test suite for listing knowledge bases."""

    def test_list_kb_success(
        self, client, auth_header, mock_mcp_list_kbs, registered_app
    ):
        """Should return paginated KB list successfully."""
        response = client.get(
            "/api/apps/knowledge-bases?skip=0&limit=10",
            headers=auth_header,
        )

        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 2
        assert data["page"] == 1
        assert data["size"] == 2
        assert isinstance(data["data"], list)
        assert len(data["data"]) == 2

        # Verify MCP call was correct
        kb_ids = [registered_app["knowledge_bases"][0]["knowledge_base_id"]]
        mock_mcp_list_kbs.assert_awaited_once_with(
            skip=0,
            limit=10,
            with_documents=False,
            include_total=True,
            search=None,
            kb_ids=kb_ids,
        )

    def test_list_kb_with_search(
        self, client, auth_header, mock_mcp_list_kbs, registered_app
    ):
        """Should pass search parameter to MCP."""
        response = client.get(
            "/api/apps/knowledge-bases?search=library",
            headers=auth_header,
        )

        assert response.status_code == 200

        kb_ids = [registered_app["knowledge_bases"][0]["knowledge_base_id"]]
        mock_mcp_list_kbs.assert_awaited_once_with(
            skip=0,
            limit=100,
            with_documents=False,
            include_total=True,
            search="library",
            kb_ids=kb_ids,
        )

    def test_list_kb_with_kb_ids(self, client, auth_header, mock_mcp_list_kbs):
        """Should pass search parameter to MCP."""
        mock_mcp_list_kbs.return_value = {
            "total": 0,
            "page": 1,
            "size": 0,
            "data": [],
        }

        response = client.get(
            "/api/apps/knowledge-bases?kb_ids=9999",
            headers=auth_header,
        )
        assert response.status_code == 200

        mock_mcp_list_kbs.assert_awaited_once_with(
            skip=0,
            limit=100,
            with_documents=False,
            include_total=True,
            search=None,
            kb_ids=[9999],
        )

    def test_list_kb_with_multiple_kb_ids(
        self, client, auth_header, mock_mcp_list_kbs
    ):
        """Should handle multiple kb_ids."""
        mock_mcp_list_kbs.return_value = {
            "total": 0,
            "page": 1,
            "size": 0,
            "data": [],
        }
        response = client.get(
            "/api/apps/knowledge-bases?kb_ids=1&kb_ids=2&kb_ids=3",
            headers=auth_header,
        )
        assert response.status_code == 200
        mock_mcp_list_kbs.assert_awaited_once_with(
            skip=0,
            limit=100,
            with_documents=False,
            include_total=True,
            search=None,
            kb_ids=[1, 2, 3],
        )

    def test_list_kb_with_search_and_kb_ids(
        self, client, auth_header, mock_mcp_list_kbs
    ):
        """Should pass both search and kb_ids parameters."""
        mock_mcp_list_kbs.return_value = {
            "total": 0,
            "page": 1,
            "size": 0,
            "data": [],
        }
        response = client.get(
            "/api/apps/knowledge-bases?search=test&kb_ids=9999",
            headers=auth_header,
        )
        assert response.status_code == 200
        mock_mcp_list_kbs.assert_awaited_once_with(
            skip=0,
            limit=100,
            with_documents=False,
            include_total=True,
            search="test",
            kb_ids=[9999],
        )

    def test_list_kb_empty_result(
        self, client, auth_header, mock_mcp_list_kbs
    ):
        """Should handle empty paginated result cleanly."""
        mock_mcp_list_kbs.return_value = {
            "total": 0,
            "page": 1,
            "size": 0,
            "data": [],
        }

        response = client.get(
            "/api/apps/knowledge-bases",
            headers=auth_header,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["data"] == []

    def test_list_kb_inactive_app_forbidden(
        self, client, db, registered_app, mock_mcp_list_kbs
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

        response = client.get(
            "/api/apps/knowledge-bases",
            headers=headers,
        )

        assert response.status_code == 403
        assert "active" in response.text.lower()

        # MCP should NOT be called
        mock_mcp_list_kbs.assert_not_awaited()

    def test_list_kb_missing_auth(self, client):
        """Should return 401 if no Authorization header."""
        response = client.get("/api/apps/knowledge-bases")
        assert response.status_code == 401

    def test_list_kb_mcp_error_raises_500(
        self, client, auth_header, mock_mcp_list_kbs
    ):
        """If MCP throws an exception, endpoint should return 500."""
        mock_mcp_list_kbs.side_effect = Exception("MCP failure")

        response = client.get(
            "/api/apps/knowledge-bases",
            headers=auth_header,
        )

        assert response.status_code == 500
        assert "Failed to fetch KB list" in response.text


@pytest.mark.usefixtures("mock_mcp_crud_kb")
@pytest.mark.usefixtures("mock_mcp_list_documents")
class TestListDocumentsWithKbId:
    """Tests for /documents when kb_id is provided."""

    def test_list_documents_with_kb_id_success(
        self, client, auth_header, registered_app, mock_mcp_list_documents
    ):
        """Should proxy to MCP list_documents when kb_id is provided."""

        kb_id = registered_app["knowledge_bases"][0]["knowledge_base_id"]
        response = client.get(
            f"/api/apps/documents?kb_id={kb_id}&skip=0&limit=100&search=CDIP",  # noqa
            headers=auth_header,
        )

        assert response.status_code == 200
        data = response.json()

        # Validate paginated structure
        assert data["total"] == 18
        assert data["page"] == 2
        assert data["size"] == 1
        assert isinstance(data["data"], list)
        assert len(data["data"]) == 1

        # Validate MCP call
        mock_mcp_list_documents.assert_awaited_once_with(
            kb_id=kb_id,
            skip=0,
            limit=100,
            search="CDIP",
        )

    def test_list_documents_with_kb_id_and_custom_pagination(
        self, client, auth_header, mock_mcp_list_documents, registered_app
    ):
        """Should forward custom skip/limit/search/flags to MCP."""
        kb_id = registered_app["knowledge_bases"][0]["knowledge_base_id"]

        response = client.get(
            "/api/apps/documents"
            f"?kb_id={kb_id}&skip=20&limit=5&search=test",
            headers=auth_header,
        )

        assert response.status_code == 200

        mock_mcp_list_documents.assert_awaited_once_with(
            kb_id=kb_id,
            skip=20,
            limit=5,
            search="test",
        )

    def test_list_documents_requires_auth(self, client):
        """Should return 401 when Authorization header is missing."""
        response = client.get("/api/apps/documents?kb_id=1")
        assert response.status_code == 401

    def test_list_documents_inactive_app_forbidden(
        self, client, db, registered_app, mock_mcp_list_documents
    ):
        """Should block inactive app from listing documents."""
        app = (
            db.query(App)
            .filter(App.app_id == registered_app["app_id"])
            .first()
        )
        app.status = AppStatus.revoked
        db.commit()

        response = client.get(
            "/api/apps/documents?kb_id=1",
            headers={
                "Authorization": f"Bearer {registered_app['access_token']}"
            },
        )

        assert response.status_code == 403
        assert "active" in response.text.lower()

        # MCP should NOT be called
        mock_mcp_list_documents.assert_not_awaited()


@pytest.mark.usefixtures("mock_mcp_crud_kb")
class TestGetKnowledgeBaseDetails:
    """Test suite for GET /knowledge-bases/{kb_id}"""

    def test_get_kb_details_success(
        self, client, auth_header, registered_app, mock_mcp_crud_kb
    ):
        """Should successfully return KB details merged from MCP + link."""
        (_, mock_get_kb, _, _) = mock_mcp_crud_kb

        # MCP response override (add timestamps for coverage)
        mock_get_kb.return_value = {
            "id": 1,
            "name": "KB One",
            "description": "Merged KB test",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
        }

        kb_id = registered_app["knowledge_bases"][0]["knowledge_base_id"]

        res = client.get(
            f"/api/apps/knowledge-bases/{kb_id}",
            headers=auth_header,
        )
        assert res.status_code == 200

        data = res.json()
        assert data["id"] == kb_id
        assert data["name"] == "KB One"
        assert data["description"] == "Merged KB test"
        assert data["is_default"] is True
        assert data["documents"] == []
        assert "created_at" in data
        assert "updated_at" in data

        mock_get_kb.assert_awaited_once_with(kb_id, with_documents=False)

    def test_get_kb_details_not_linked_returns_404(self, client, auth_header):
        """Should return 404 when KB is not linked to the app."""

        res = client.get(
            "/api/apps/knowledge-bases/9999",
            headers=auth_header,
        )
        assert res.status_code == 404
        assert "not found" in res.text.lower()

    def test_get_kb_details_inactive_app_forbidden(
        self, client, db, registered_app
    ):
        """Should block inactive app from accessing KB details."""
        # Deactivate app
        app = (
            db.query(App)
            .filter(App.app_id == registered_app["app_id"])
            .first()
        )
        app.status = AppStatus.revoked
        db.commit()

        kb_id = registered_app["knowledge_bases"][0]["knowledge_base_id"]

        res = client.get(
            f"/api/apps/knowledge-bases/{kb_id}",
            headers={
                "Authorization": f"Bearer {registered_app['access_token']}"
            },
        )
        assert res.status_code == 403
        assert "active" in res.text.lower()

    def test_get_kb_details_missing_auth_returns_401(self, client):
        """Should return 401 when no auth is provided."""
        res = client.get("/api/apps/knowledge-bases/1")
        assert res.status_code == 401

    def test_get_kb_details_mcp_error_returns_500(
        self, client, auth_header, registered_app, mock_mcp_crud_kb
    ):
        """If MCP raises an error, return a 500 response."""
        (_, mock_get_kb, _, _) = mock_mcp_crud_kb

        mock_get_kb.side_effect = Exception("MCP exploded")

        kb_id = registered_app["knowledge_bases"][0]["knowledge_base_id"]

        res = client.get(
            f"/api/apps/knowledge-bases/{kb_id}",
            headers=auth_header,
        )
        assert res.status_code == 500
        assert "Failed to fetch KB details" in res.text


@pytest.mark.usefixtures("mock_mcp_crud_kb")
@pytest.mark.usefixtures("mock_mcp_list_documents")
class TestDeleteDocumentEndpoint:
    """Tests for DELETE /api/apps/documents"""

    @pytest.fixture
    def mock_mcp_delete_document(self):
        """Mock MCP delete_document call."""
        with patch(
            "mcp_clients.kb_mcp_endpoint_service."
            "KnowledgeBaseMCPEndpointService.delete_document",
            new_callable=AsyncMock,
        ) as mock_delete:
            mock_delete.return_value = {"status": "deleted"}
            yield mock_delete

    def test_delete_document_success(
        self, client, auth_header, registered_app, mock_mcp_delete_document
    ):
        """
        Should successfully delete a document when KB is linked to the app.
        """

        kb_id = registered_app["knowledge_bases"][0]["knowledge_base_id"]

        response = client.delete(
            f"/api/apps/documents?kb_id={kb_id}&doc_id=123",
            headers=auth_header,
        )

        assert response.status_code == 200
        assert response.json() == {"status": "deleted"}

        mock_mcp_delete_document.assert_awaited_once_with(
            kb_id=kb_id, doc_id=123
        )

    def test_delete_document_kb_not_linked_returns_404(
        self, client, auth_header, mock_mcp_delete_document
    ):
        """Should return 404 if KB is NOT linked to this app."""

        response = client.delete(
            "/api/apps/documents?kb_id=9999&doc_id=1",
            headers=auth_header,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

        mock_mcp_delete_document.assert_not_awaited()

    def test_delete_document_inactive_app_forbidden(
        self, client, db, registered_app, mock_mcp_delete_document
    ):
        """Should block an inactive app from deleting document."""

        # deactivate app
        app = (
            db.query(App)
            .filter(App.app_id == registered_app["app_id"])
            .first()
        )
        app.status = AppStatus.revoked
        db.commit()

        kb_id = registered_app["knowledge_bases"][0]["knowledge_base_id"]

        response = client.delete(
            f"/api/apps/documents?kb_id={kb_id}&doc_id=55",
            headers={
                "Authorization": f"Bearer {registered_app['access_token']}"
            },
        )

        assert response.status_code == 403
        assert "active" in response.text.lower()

        mock_mcp_delete_document.assert_not_awaited()

    def test_delete_document_missing_auth_returns_401(self, client):
        """Should return 401 when no Authorization header is provided."""

        response = client.delete("/api/apps/documents?kb_id=1&doc_id=1")
        assert response.status_code == 401

    def test_delete_document_mcp_error_returns_500(
        self, client, auth_header, registered_app, mock_mcp_delete_document
    ):
        """Return 500 if MCP throws an exception."""

        mock_mcp_delete_document.side_effect = Exception("MCP error")

        kb_id = registered_app["knowledge_bases"][0]["knowledge_base_id"]

        response = client.delete(
            f"/api/apps/documents?kb_id={kb_id}&doc_id=123",
            headers=auth_header,
        )

        assert response.status_code == 500
        assert "Failed to delete document" in response.text
