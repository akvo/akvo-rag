import pytest
import json

from unittest.mock import Mock
from app.services.job_service import JobService

@pytest.mark.unit
class TestJobService:
    """Test suite for JobService business logic."""

    @pytest.fixture
    def mock_db(self):
        return Mock()

    @pytest.fixture
    def sample_job_data(self):
        return {
            "job": "chat",
            "prompt": "What is the capital of France?",
            "chats": [
                {"role": "user", "content": "Hello!"},
                {"role": "assistant", "content": "Hi there! How can I assist you today?"}
            ],
            "callback_url": "https://example.com/callback",
            "callback_params": {"param1": "value1"},
            "trace_id": "trace_12345"
        }

    def test_create_job(self, mock_db, sample_job_data):
        """Test job creation."""
        job = JobService.create_job(
            db=mock_db,
            job_type="chat",
            data=sample_job_data,
            app_id="app_12345"
        )

        # Verify job object has correct attributes
        assert job.job_type == "chat"
        assert job.app_id == "app_12345"
        assert job.status == "pending"
        assert job.input_data == json.dumps(sample_job_data)
        assert job.callback_url == "https://example.com/callback"
        assert job.callback_params == '{"param1": "value1"}'
        assert job.trace_id == "trace_12345"

    def test_get_job(self, mock_db):
        """Test retrieving a job by ID."""
        # Setup mock return value
        mock_job = Mock()
        mock_db.query().filter().first.return_value = mock_job

        job = JobService.get_job(mock_db, "job_12345")

        # Verify the returned job is the mock job
        assert job == mock_job

    def test_update_to_running(self, mock_db):
        """Test updating job status to running."""
        # Setup mock return value
        mock_job = Mock()
        mock_db.query().filter().first.return_value = mock_job

        job = JobService.update_status_to_running(mock_db, "job_12345")

        # Verify job status was updated
        assert job.status == "running"

    def test_update_to_completed(self, mock_db):
        """Test updating job status to completed."""
        # Setup mock return value
        mock_job = Mock()
        mock_db.query().filter().first.return_value = mock_job

        job = JobService.update_status_to_completed(
            mock_db, "job_12345", output="The capital of France is Paris.")

        # Verify job status was updated
        assert job.status == "completed"
        assert job.output == "The capital of France is Paris."

    def test_update_to_failed(self, mock_db):
        """Test updating job status to failed."""
        # Setup mock return value
        mock_job = Mock()
        mock_db.query().filter().first.return_value = mock_job

        job = JobService.update_status_to_failed(
            mock_db, "job_12345", output="Error processing the job.")

        # Verify job status was updated
        assert job.status == "failed"
        assert job.output == "Error processing the job."

    def test_update_job_status(self, mock_db):
        """Test the internal method to update job status."""
        # Setup mock return value
        mock_job = Mock()
        mock_db.query().filter().first.return_value = mock_job

        job = JobService._update_job_status(
            mock_db, "job_12345", "completed", output="Done.")

        # Verify job status was updated
        assert job.status == "completed"
        assert job.output == "Done."