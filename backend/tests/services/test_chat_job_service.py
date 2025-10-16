import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.services.chat_job_service import execute_chat_job
from app.services import chat_job_service


@pytest.mark.unit
class TestChatJobService:
    """Test suite for execute_chat_job."""

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
            "callback_url": "https://example.com/callback",
            "callback_params": {"reply_to": "wa:+679123456", "mode": "reply"},
            "trace_id": "trace_12345",
        }

    @pytest.fixture
    def knowledge_base_ids(self):
        return [1, 2, 3]

    @pytest.mark.asyncio
    async def test_execute_chat_job_success(
        self, mock_db, sample_job_id, sample_data, knowledge_base_ids
    ):
        """✅ Test successful chat job execution with correct callback payload."""
        with (
            patch.object(chat_job_service.JobService, "get_job", return_value=True),
            patch.object(chat_job_service.JobService, "update_status_to_running") as mock_run,
            patch.object(chat_job_service.JobService, "update_status_to_completed") as mock_done,
            patch.object(chat_job_service.JobService, "update_status_to_failed") as mock_fail,
            patch.object(chat_job_service.PromptService, "__init__", return_value=None),
            patch.object(chat_job_service.PromptService, "get_full_contextualize_prompt", return_value="ctx"),
            patch.object(chat_job_service.PromptService, "get_full_qa_strict_prompt", return_value="qa"),
            patch.object(chat_job_service.SystemSettingsService, "__init__", return_value=None),
            patch.object(chat_job_service.SystemSettingsService, "get_top_k", return_value=5),
            patch.object(chat_job_service, "query_answering_workflow") as mock_workflow,
            patch("app.services.chat_job_service.httpx.AsyncClient") as mock_httpx_client,
        ):
            # Mock successful workflow
            mock_workflow.ainvoke = AsyncMock(return_value={"answer": "AI means Artificial Intelligence"})

            # Mock HTTP client
            mock_client = AsyncMock()
            mock_httpx_client.return_value.__aenter__.return_value = mock_client

            # Run function
            await execute_chat_job(
                db=mock_db,
                job_id=sample_job_id,
                data=sample_data,
                knowledge_base_ids=knowledge_base_ids,
            )

            # --- Assertions ---
            mock_run.assert_called_once_with(mock_db, sample_job_id)
            mock_done.assert_called_once()
            mock_fail.assert_not_called()
            mock_workflow.ainvoke.assert_awaited_once()

            # Verify callback was called once
            mock_client.post.assert_awaited_once()
            callback_url, callback_kwargs = mock_client.post.call_args

            # Verify correct URL and payload content
            assert callback_url[0] == "https://example.com/callback"
            payload = callback_kwargs["json"]

            assert payload["job_id"] == sample_job_id
            assert payload["trace_id"] == "trace_12345"
            assert payload["status"] == "completed"
            assert payload["output"] == {
                'answer': 'AI means Artificial Intelligence', 'citations': []
            }
            assert payload["error"] is None
            assert payload["callback_params"] == {"reply_to": "wa:+679123456", "mode": "reply"}

            # Optional: ensure timeout param is correct
            assert mock_httpx_client.call_args.kwargs["timeout"] == 10

    @pytest.mark.asyncio
    async def test_execute_chat_job_failure(
        self, mock_db, sample_job_id, sample_data, knowledge_base_ids
    ):
        with (
            patch.object(chat_job_service.JobService, "get_job", return_value=True),
            patch.object(chat_job_service.JobService, "update_status_to_running"),
            patch.object(chat_job_service.JobService, "update_status_to_completed"),
            patch.object(chat_job_service.JobService, "update_status_to_failed") as mock_fail,
            patch.object(chat_job_service, "query_answering_workflow") as mock_workflow,
        ):
            mock_workflow.ainvoke = AsyncMock(
                side_effect=Exception("Workflow crashed"))

            await execute_chat_job(
                db=mock_db,
                job_id=sample_job_id,
                data=sample_data,
                knowledge_base_ids=knowledge_base_ids,
            )

            mock_fail.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_chat_job_no_callback(
        self, mock_db, sample_job_id, sample_data
    ):
        data = dict(sample_data)
        data.pop("callback_url")

        with (
            patch.object(chat_job_service.JobService, "get_job", return_value=True),
            patch.object(chat_job_service, "query_answering_workflow") as mock_workflow,
            patch("app.services.chat_job_service.httpx.AsyncClient") as mock_httpx_client,
        ):
            mock_workflow.ainvoke = AsyncMock(return_value={"answer": "ok"})
            mock_httpx_client.return_value.__aenter__.return_value = AsyncMock()

            await execute_chat_job(mock_db, sample_job_id, data, [])

            mock_httpx_client.return_value.__aenter__.return_value.post.assert_not_awaited()
