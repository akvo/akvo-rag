import pytest
import json

from unittest.mock import AsyncMock, patch
from app.models.app import App, AppStatus
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
        knowledge_base_id=42,
        scopes=["jobs.write"],
    )
    db.add(app_entry)
    db.commit()
    db.refresh(app_entry)
    db.close()
    return app_entry


@pytest.fixture
def sample_job_payload():
    """Payload for creating a chat job."""
    return {
        "job": "chat",
        "prompt": "Explain AI simply.",
        "chats": [
            {"role": "user", "content": "What is AI?"},
            {"role": "assistant", "content": "AI means Artificial Intelligence."},
        ],
        "callback_url": "https://example.com/callback",
        "callback_params": {"reply_to": "wa:+1234"},
        "trace_id": "trace_abc_123",
    }


class TestJobsEndpointIntegration:
    """Integration tests for /v1/apps/jobs endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.api_v1.jobs.execute_chat_job", new_callable=AsyncMock)
    def test_create_chat_job_success(
        self, mock_execute_chat_job, client, db, sample_app, sample_job_payload
    ):
        """Should create a chat job and queue it for background execution."""

        headers = {"Authorization": f"Bearer {sample_app.access_token}"}
        response = client.post(
            "/v1/apps/jobs", json=sample_job_payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        print(data)

        # Validate response content
        assert data["job_id"] == data["job_id"]
        assert data["status"] == "pending"
        assert data["trace_id"] == "trace_abc_123"

        # Check the job exists in the DB
        job = db.query(Job).filter(Job.id == data["job_id"]).first()
        assert job is not None
        assert job.status == "pending"
        assert job.app_id == sample_app.app_id
        assert job.input_data is not None
        db.close()

    def test_create_chat_job_requires_auth(self, client, sample_job_payload):
        """Should reject unauthenticated requests."""
        response = client.post("/v1/apps/jobs", json=sample_job_payload)
        assert response.status_code == 401

    def test_create_chat_job_invalid_token(self, client, sample_job_payload):
        """Should reject invalid tokens."""
        headers = {"Authorization": "Bearer tok_invalid"}
        response = client.post(
            "/v1/apps/jobs", json=sample_job_payload, headers=headers)
        assert response.status_code == 401

    def test_create_chat_job_for_revoked_app(
        self, client, db, sample_app, sample_job_payload
    ):
        """Should reject requests for revoked app."""
        # Revoke the app manually
        app_obj = db.query(App).filter(App.app_id == sample_app.app_id).first()
        app_obj.status = AppStatus.revoked
        db.commit()
        db.close()

        headers = {"Authorization": f"Bearer {sample_app.access_token}"}
        response = client.post(
            "/v1/apps/jobs", json=sample_job_payload, headers=headers)
        assert response.status_code == 403


class TestGetJobStatus:
    """Tests for GET /v1/apps/jobs/{job_id} endpoint."""

    def test_get_job_status_success(
        self, client, db, sample_app, sample_job_payload
    ):
        """Should return the job status for a valid chat job."""
        # Insert a job in the DB
        job = Job(
            id="job_abc",
            app_id=sample_app.app_id,
            job_type="chat",
            status="running",
            trace_id="trace_001",
            input_data=json.dumps(sample_job_payload)
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        db.close()

        headers = {"Authorization": f"Bearer {sample_app.access_token}"}
        response = client.get(f"/v1/apps/jobs/{job.id}", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["job_id"] == "job_abc"
        assert data["status"] == "running"
        assert data["trace_id"] == "trace_001"

    def test_get_job_status_requires_auth(self, client):
        """Should return 401 if no token is provided."""
        response = client.get("/v1/apps/jobs/job_abc")
        assert response.status_code == 401

    def test_get_job_status_not_found(self, client, sample_app):
        """Should return 404 for unknown job_id."""
        headers = {"Authorization": f"Bearer {sample_app.access_token}"}
        response = client.get("/v1/apps/jobs/job_not_exist", headers=headers)
        assert response.status_code == 404
