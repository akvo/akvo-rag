import io
import pytest
import json

from unittest.mock import Mock, patch
from app.models.app import App, AppStatus, AppKnowledgeBase
from app.models.job import Job


@pytest.fixture
def sample_app_multi_kb(db):
    """Insert a mock active App with multiple KBs (one default)."""
    app_entry = App(
        app_id="app_002",
        client_id="ac_002",
        access_token="tok_multi_kb",
        app_name="multi_kb_app",
        domain="multi.domain.com",
        chat_callback_url="https://example.com/chat_callback",
        upload_callback_url="https://example.com/upload_callback",
        callback_token="cb_tok_456",
        status=AppStatus.active,
        scopes=["jobs.write"],
    )

    kb1 = AppKnowledgeBase(knowledge_base_id=101, is_default=True)
    kb2 = AppKnowledgeBase(knowledge_base_id=102, is_default=False)
    kb3 = AppKnowledgeBase(knowledge_base_id=103, is_default=False)
    app_entry.knowledge_bases.extend([kb1, kb2, kb3])

    db.add(app_entry)
    db.commit()
    db.refresh(app_entry)
    db.close()
    return app_entry


@pytest.fixture
def sample_app_no_default_kb(db):
    """Insert a mock app that has KBs but no default one."""
    app_entry = App(
        app_id="app_003",
        client_id="ac_003",
        access_token="tok_no_default",
        app_name="no_default_app",
        domain="no.default.com",
        chat_callback_url="https://example.com/chat_callback",
        upload_callback_url="https://example.com/upload_callback",
        callback_token="cb_tok_789",
        status=AppStatus.active,
        scopes=["jobs.write"],
    )

    kb1 = AppKnowledgeBase(knowledge_base_id=201, is_default=False)
    kb2 = AppKnowledgeBase(knowledge_base_id=202, is_default=False)
    app_entry.knowledge_bases.extend([kb1, kb2])

    db.add(app_entry)
    db.commit()
    db.refresh(app_entry)
    db.close()
    return app_entry


@pytest.fixture
def sample_chat_job_payload():
    """Payload for a basic chat job (no KBs specified)."""
    payload = {
        "job": "chat",
        "prompt": "Explain AI simply.",
        "chats": [{"role": "user", "content": "What is AI?"}],
        "trace_id": "trace_default_kb",
    }
    return {"payload": json.dumps(payload)}


@pytest.fixture
def sample_upload_job_payload():
    """Payload for a basic upload job (no KB specified)."""
    payload = {
        "job": "upload",
        "metadata": {
            "title": "General SOP",
        },
        "callback_params": {"ui_upload_id": "up_default"},
    }
    return {"payload": json.dumps(payload)}


@pytest.fixture
def chat_payload_with_kb():
    """Payload specifying multiple KBs."""
    payload = {
        "job": "chat",
        "prompt": "Test multi KB chat.",
        "chats": [{"role": "user", "content": "Explain quantum physics."}],
        "trace_id": "trace_multi_kb",
        "knowledge_base_ids": [101, 103],
    }
    return {"payload": json.dumps(payload)}


@pytest.fixture
def chat_payload_invalid_kb():
    """Payload with KBs not linked to the app."""
    payload = {
        "job": "chat",
        "prompt": "Invalid KB chat.",
        "chats": [{"role": "user", "content": "Explain invalid KB."}],
        "trace_id": "trace_invalid_kb",
        "knowledge_base_ids": [999, 888],
    }
    return {"payload": json.dumps(payload)}


@pytest.fixture
def upload_payload_with_kb():
    """Payload for uploading into a specific KB."""
    payload = {
        "job": "upload",
        "metadata": {"title": "SOP Test"},
        "callback_params": {"ui_upload_id": "up_999"},
        "knowledge_base_id": 103,
    }
    return {"payload": json.dumps(payload)}


@pytest.fixture
def upload_payload_invalid_kb():
    """Payload with invalid upload KB."""
    payload = {
        "job": "upload",
        "metadata": {"title": "Invalid KB"},
        "callback_params": {"ui_upload_id": "up_000"},
        "knowledge_base_id": 999,
    }
    return {"payload": json.dumps(payload)}


class TestMultiKBJobEndpoints:
    """Tests for multi-KB support in /api/apps/jobs endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.api_v1.jobs.execute_chat_job_task")
    async def test_chat_job_with_multiple_valid_kbs(
        self, mock_task, client, db, sample_app_multi_kb, chat_payload_with_kb
    ):
        """✅ Should accept specific KBs and pass them to Celery."""
        mock_task.delay = Mock(return_value=Mock(id="multi-kb-task-1"))

        headers = {
            "Authorization": f"Bearer {sample_app_multi_kb.access_token}"
        }
        response = client.post(
            "/api/apps/jobs", data=chat_payload_with_kb, headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        job = db.query(Job).filter(Job.id == data["job_id"]).first()
        assert job is not None

        mock_task.delay.assert_called_once()
        called_kb_ids = mock_task.delay.call_args.kwargs["knowledge_base_ids"]
        assert set(called_kb_ids) == {101, 103}

        assert data["status"] == "pending"
        db.close()

    @pytest.mark.asyncio
    async def test_chat_job_with_invalid_kbs_rejected(
        self, client, db, sample_app_multi_kb, chat_payload_invalid_kb
    ):
        """🚫 Should return 404 if provided KBs aren't linked to the app."""
        headers = {
            "Authorization": f"Bearer {sample_app_multi_kb.access_token}"
        }
        response = client.post(
            "/api/apps/jobs", data=chat_payload_invalid_kb, headers=headers
        )

        assert response.status_code == 404
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    @patch("app.api.api_v1.jobs.execute_chat_job_task")
    async def test_chat_job_fallback_to_default_kb(
        self,
        mock_task,
        client,
        db,
        sample_app_multi_kb,
        sample_chat_job_payload,
    ):
        """✅ Should use default KB if none provided."""
        mock_task.delay = Mock(return_value=Mock(id="default-fallback-task"))
        headers = {
            "Authorization": f"Bearer {sample_app_multi_kb.access_token}"
        }
        response = client.post(
            "/api/apps/jobs", data=sample_chat_job_payload, headers=headers
        )

        assert response.status_code == 200
        mock_task.delay.assert_called_once()
        kb_ids = mock_task.delay.call_args.kwargs["knowledge_base_ids"]
        assert kb_ids == [101]  # only default KB used
        db.close()

    @pytest.mark.asyncio
    @patch("app.api.api_v1.jobs.upload_full_process_task")
    async def test_upload_job_with_custom_kb(
        self,
        mock_task,
        client,
        db,
        sample_app_multi_kb,
        upload_payload_with_kb,
    ):
        """✅ Should upload into specified KB."""
        mock_task.delay = Mock(return_value=Mock(id="upload-kb-task"))
        headers = {
            "Authorization": f"Bearer {sample_app_multi_kb.access_token}"
        }

        file_content = io.BytesIO(b"dummy data")
        files = {"files": ("doc.pdf", file_content, "application/pdf")}

        response = client.post(
            "/api/apps/jobs",
            data=upload_payload_with_kb,
            files=files,
            headers=headers,
        )

        assert response.status_code == 200
        mock_task.delay.assert_called_once()
        kb_id = mock_task.delay.call_args.kwargs["knowledge_base_id"]
        assert kb_id == 103
        db.close()

    @pytest.mark.asyncio
    async def test_upload_job_invalid_kb_rejected(
        self, client, db, sample_app_multi_kb, upload_payload_invalid_kb
    ):
        """🚫 Should reject upload job with KB not linked to app."""
        headers = {
            "Authorization": f"Bearer {sample_app_multi_kb.access_token}"
        }
        response = client.post(
            "/api/apps/jobs", data=upload_payload_invalid_kb, headers=headers
        )

        assert response.status_code == 404
        assert "not associated" in response.json()["detail"].lower()

    # --------------------------------------------------------------------------
    # 🧩 Edge Cases: No Default KB Available
    # --------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_chat_job_no_default_kb_fails(
        self, client, db, sample_app_no_default_kb, sample_chat_job_payload
    ):
        """🚫 Should return 404 if no default KB exists and none provided."""
        headers = {
            "Authorization": f"Bearer {sample_app_no_default_kb.access_token}"
        }
        response = client.post(
            "/api/apps/jobs", data=sample_chat_job_payload, headers=headers
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_job_no_default_kb_fails(
        self, client, db, sample_app_no_default_kb, sample_upload_job_payload
    ):
        """
        🚫 Should return 404 if upload job has no KB and no default one exists.
        """
        headers = {
            "Authorization": f"Bearer {sample_app_no_default_kb.access_token}"
        }
        file_content = io.BytesIO(b"dummy data")
        files = {"files": ("doc.pdf", file_content, "application/pdf")}

        response = client.post(
            "/api/apps/jobs",
            data=sample_upload_job_payload,
            files=files,
            headers=headers,
        )

        assert response.status_code == 404
