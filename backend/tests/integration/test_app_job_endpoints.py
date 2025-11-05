import io
import pytest
import json

from unittest.mock import Mock, patch
from app.models.app import App, AppStatus, AppKnowledgeBase
from app.models.job import Job


@pytest.fixture
def sample_app(db):
    """Insert a mock active App into the test DB."""
    app_entry = App(
        app_id="app_001",
        client_id="ac_001",
        access_token="tok_abc123",
        app_name="test_app",
        domain="test.domain.com",
        chat_callback_url="https://example.com/chat_callback",
        upload_callback_url="https://example.com/upload_callback",
        callback_token="cb_tok_123",
        status=AppStatus.active,
        scopes=["jobs.write"],
    )

    app_kb_entry = AppKnowledgeBase(
        knowledge_base_id=42,
        is_default=True,
    )
    app_entry.knowledge_bases.append(app_kb_entry)

    db.add(app_entry)
    db.commit()
    db.refresh(app_entry)
    db.close()
    return app_entry


@pytest.fixture
def sample_chat_job_payload():
    """Payload for creating a chat job."""
    payload = {
        "job": "chat",
        "prompt": "Explain AI simply.",
        "chats": [
            {"role": "user", "content": "What is AI?"},
            {
                "role": "assistant",
                "content": "AI means Artificial Intelligence.",
            },
        ],
        "callback_params": {"reply_to": "wa:+1234"},
        "trace_id": "trace_abc_123",
    }
    return {"payload": json.dumps(payload)}


@pytest.fixture
def sample_upload_job_payload():
    """Payload for creating a upload job"""
    payload = {
        "job": "upload",
        "metadata": {
            "kb_id": 1,
            "title": "Chlorination SOP",
            "tags": ["chlorine", "ops"],
        },
        "callback_params": {"ui_upload_id": "up_456"},
    }
    return {"payload": json.dumps(payload)}


class TestAppJobsEndpoints:
    """Integration tests for /api/apps/jobs endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.api_v1.jobs.execute_chat_job_task")
    def test_create_chat_job_success(
        self, mock_task, client, db, sample_app, sample_chat_job_payload
    ):
        """Should create a chat job and queue it for background execution."""
        mock_task.delay = Mock(return_value=Mock(id="fake-task-id-123"))

        headers = {"Authorization": f"Bearer {sample_app.access_token}"}
        response = client.post(
            "/api/apps/jobs", data=sample_chat_job_payload, headers=headers
        )

        assert response.status_code == 200
        data = response.json()

        # Validate response content
        assert data["job_id"] == data["job_id"]
        assert data["status"] == "pending"

        # Check the job exists in the DB
        job = db.query(Job).filter(Job.id == data["job_id"]).first()
        assert job is not None
        assert job.status == "pending"
        assert job.app_id == sample_app.app_id
        assert job.input_data is not None
        assert job.celery_task_id == "fake-task-id-123"
        db.close()

    def test_create_chat_job_requires_auth(
        self, client, sample_chat_job_payload
    ):
        """Should reject unauthenticated requests."""
        response = client.post("/api/apps/jobs", data=sample_chat_job_payload)
        assert response.status_code == 401

    def test_create_chat_job_invalid_token(
        self, client, sample_chat_job_payload
    ):
        """Should reject invalid tokens."""
        headers = {"Authorization": "Bearer tok_invalid"}
        response = client.post(
            "/api/apps/jobs", data=sample_chat_job_payload, headers=headers
        )
        assert response.status_code == 401

    def test_create_chat_job_for_revoked_app(
        self, client, db, sample_app, sample_chat_job_payload
    ):
        """Should reject requests for revoked app."""
        # Revoke the app manually
        app_obj = db.query(App).filter(App.app_id == sample_app.app_id).first()
        app_obj.status = AppStatus.revoked
        db.commit()
        db.close()

        headers = {"Authorization": f"Bearer {sample_app.access_token}"}
        response = client.post(
            "/api/apps/jobs", data=sample_chat_job_payload, headers=headers
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    @patch("app.api.api_v1.jobs.upload_full_process_task")
    async def test_create_upload_job_success(
        self, mock_task, client, db, sample_app, sample_upload_job_payload
    ):
        """✅ Should create an upload job and queue Celery task."""

        # Mock Celery task async delay
        mock_task.delay = Mock(return_value=Mock(id="upload-task-id-789"))

        # Prepare mock file upload
        file_content = io.BytesIO(b"dummy pdf data")
        files = {"files": ("sample.pdf", file_content, "application/pdf")}

        headers = {"Authorization": f"Bearer {sample_app.access_token}"}
        response = client.post(
            "/api/apps/jobs",
            data=sample_upload_job_payload,
            files=files,
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify DB job created
        job = db.query(Job).filter(Job.id == data["job_id"]).first()
        assert job is not None
        assert job.status == "pending"
        assert job.job_type == "upload"
        assert job.app_id == sample_app.app_id

        default_kb = next(
            (kb for kb in sample_app.knowledge_bases if kb.is_default), None
        )

        # Verify Celery called correctly
        mock_task.delay.assert_called_once()
        call_args = mock_task.delay.call_args.kwargs
        assert call_args["job_id"] == job.id
        assert call_args["callback_url"] == sample_app.upload_callback_url
        assert call_args["knowledge_base_id"] == default_kb.knowledge_base_id
        assert "file_paths" in call_args
        assert isinstance(call_args["file_paths"], list)
        assert all("sample.pdf" in f for f in call_args["file_paths"])

        # Verify response structure
        assert data["job_id"] == job.id
        assert data["status"] == "pending"
        db.close()

    def test_create_upload_job_requires_auth(
        self, client, sample_upload_job_payload
    ):
        """❌ Should reject unauthenticated upload job creation."""
        response = client.post(
            "/api/apps/jobs", data=sample_upload_job_payload
        )
        assert response.status_code == 401


class TestGetJobStatus:
    """Tests for GET /api/apps/jobs/{job_id} endpoint."""

    def test_get_job_status_success(
        self, client, db, sample_app, sample_chat_job_payload
    ):
        """Should return the job status for a valid chat job."""
        # Insert a job in the DB
        job = Job(
            id="job_abc",
            app_id=sample_app.app_id,
            job_type="chat",
            status="running",
            trace_id="trace_001",
            input_data=json.dumps(sample_chat_job_payload),
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        db.close()

        headers = {"Authorization": f"Bearer {sample_app.access_token}"}
        response = client.get(f"/api/apps/jobs/{job.id}", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["job_id"] == "job_abc"
        assert data["status"] == "running"
        assert data["trace_id"] == "trace_001"

    def test_get_job_status_requires_auth(self, client):
        """Should return 401 if no token is provided."""
        response = client.get("/api/apps/jobs/job_abc")
        assert response.status_code == 401

    def test_get_job_status_not_found(self, client, sample_app):
        """Should return 404 for unknown job_id."""
        headers = {"Authorization": f"Bearer {sample_app.access_token}"}
        response = client.get("/api/apps/jobs/job_not_exist", headers=headers)
        assert response.status_code == 404
