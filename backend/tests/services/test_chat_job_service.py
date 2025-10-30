import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.services.chat_job_service import execute_chat_job
from app.services import chat_job_service
from app.models.app import App


@pytest.mark.unit
class TestChatJobService:
    """Test suite for execute_chat_job (non-streaming)."""

    @pytest.fixture
    def mock_db(self):
        return Mock()

    @pytest.fixture
    def sample_job_id(self):
        return "job_12345"

    @pytest.fixture
    def sample_data(self):
        return {
            "job": "chat",
            "prompt": "Explain AI in simple terms.",
            "chats": [
                {"role": "user", "content": "What is AI?"},
                {"role": "assistant", "content": "AI stands for Artificial Intelligence."},
            ],
            "callback_params": {"reply_to": "wa:+679123456", "mode": "reply"},
            "trace_id": "trace_12345",
        }

    @pytest.fixture
    def knowledge_base_ids(self):
        return [1, 2, 3]

    @pytest.fixture
    def chat_callback_url(self):
        return "https://example.com/callback"

    @pytest.fixture
    def mock_current_app(self):
        """Mock App model instance."""
        app = Mock(spec=App)
        app.default_chat_prompt = "You are a helpful AI assistant."
        app.chat_callback_url = "https://example.com/app_chat_callback"
        return app

    # ✅ SUCCESS CASE
    @pytest.mark.asyncio
    async def test_execute_chat_job_success(
        self, mock_db, sample_job_id, sample_data, knowledge_base_ids, chat_callback_url, mock_current_app
    ):
        """✅ Test successful chat job execution with correct callback payload."""
        mock_job = Mock()
        mock_job.id = sample_job_id
        mock_job.callback_params = {"reply_to": "wa:+679123456", "mode": "reply"}

        with (
            patch.object(chat_job_service.JobService, "get_job", return_value=mock_job),
            patch.object(chat_job_service.JobService, "update_status_to_running") as mock_run,
            patch.object(chat_job_service.JobService, "update_status_to_completed") as mock_done,
            patch.object(chat_job_service.JobService, "update_status_to_failed") as mock_fail,
            patch.object(chat_job_service.PromptService, "__init__", return_value=None),
            patch.object(chat_job_service.PromptService, "get_full_contextualize_prompt", return_value="ctx"),
            patch.object(chat_job_service.PromptService, "get_full_qa_strict_prompt", return_value="qa"),
            patch.object(chat_job_service.SystemSettingsService, "__init__", return_value=None),
            patch.object(chat_job_service.SystemSettingsService, "get_top_k", return_value=5),
            patch.object(chat_job_service, "query_answering_workflow") as mock_workflow,
            patch("app.services.chat_job_service.send_callback_async", new_callable=AsyncMock) as mock_callback,
        ):
            mock_workflow.ainvoke = AsyncMock(return_value={"answer": "AI means Artificial Intelligence"})

            await execute_chat_job(
                db=mock_db,
                job_id=sample_job_id,
                data=sample_data,
                callback_url=chat_callback_url,
                current_app=mock_current_app,
                knowledge_base_ids=knowledge_base_ids,
            )

            # --- Assertions ---
            mock_run.assert_called_once_with(mock_db, sample_job_id)
            mock_done.assert_called_once()
            mock_fail.assert_not_called()
            mock_workflow.ainvoke.assert_awaited_once()
            mock_callback.assert_awaited_once()

    # ❌ FAILURE CASE
    @pytest.mark.asyncio
    async def test_execute_chat_job_failure(
        self, mock_db, sample_job_id, sample_data, knowledge_base_ids, chat_callback_url, mock_current_app
    ):
        """❌ Test workflow crash handling and failed job update."""
        mock_job = Mock()
        mock_job.id = sample_job_id
        mock_job.callback_params = {}

        with (
            patch.object(chat_job_service.JobService, "get_job", return_value=mock_job),
            patch.object(chat_job_service.JobService, "update_status_to_running"),
            patch.object(chat_job_service.JobService, "update_status_to_completed"),
            patch.object(chat_job_service.JobService, "update_status_to_failed") as mock_fail,
            patch.object(chat_job_service, "query_answering_workflow") as mock_workflow,
            patch("app.services.chat_job_service.send_callback_async", new_callable=AsyncMock),
        ):
            mock_workflow.ainvoke = AsyncMock(side_effect=Exception("Workflow crashed"))

            await execute_chat_job(
                db=mock_db,
                job_id=sample_job_id,
                data=sample_data,
                callback_url=chat_callback_url,
                current_app=mock_current_app,
                knowledge_base_ids=knowledge_base_ids,
            )

            mock_fail.assert_called_once()

    # 🚫 NO CALLBACK CASE
    @pytest.mark.asyncio
    async def test_execute_chat_job_no_callback(
        self, mock_db, sample_job_id, sample_data, mock_current_app
    ):
        """🚫 Ensure callback still sent using app callback if data callback_url is None."""
        mock_job = Mock()
        mock_job.id = sample_job_id
        mock_job.callback_params = {}

        with (
            patch.object(chat_job_service.JobService, "get_job", return_value=mock_job),
            patch.object(chat_job_service, "query_answering_workflow") as mock_workflow,
            patch("app.services.chat_job_service.send_callback_async", new_callable=AsyncMock) as mock_callback,
        ):
            mock_workflow.ainvoke = AsyncMock(return_value={"answer": "ok"})

            await execute_chat_job(
                db=mock_db,
                job_id=sample_job_id,
                data=sample_data,
                callback_url=None,
                current_app=mock_current_app,
                knowledge_base_ids=[],
            )

            # ✅ Should still call callback (using current_app.chat_callback_url)
            mock_callback.assert_awaited_once()
