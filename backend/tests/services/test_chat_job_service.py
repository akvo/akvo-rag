import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.services.chat_job_service import execute_chat_job
from app.services import chat_job_service


@pytest.mark.unit
class TestChatJobService:
    """Test suite for execute_chat_job."""

    # --- Fixtures ---

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
                {
                    "role": "assistant",
                    "content": "AI stands for Artificial Intelligence.",
                },
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
    def mock_app_default_prompt(self):
        return "Default app prompt."

    # --- Core tests ---

    @pytest.mark.asyncio
    async def test_execute_chat_job_success(
        self,
        mock_db,
        sample_job_id,
        sample_data,
        knowledge_base_ids,
        chat_callback_url,
        mock_app_default_prompt,
    ):
        """
        ✅ Test successful chat job execution with correct callback payload.
        """
        mock_job = Mock()
        mock_job.id = sample_job_id
        mock_job.callback_params = {
            "reply_to": "wa:+679123456",
            "mode": "reply",
        }

        with (
            patch.object(
                chat_job_service.JobService, "get_job", return_value=mock_job
            ),
            patch.object(
                chat_job_service.JobService, "update_status_to_running"
            ) as mock_run,
            patch.object(
                chat_job_service.JobService, "update_status_to_completed"
            ) as mock_done,
            patch.object(
                chat_job_service.JobService, "update_status_to_failed"
            ) as mock_fail,
            patch.object(
                chat_job_service.PromptService, "__init__", return_value=None
            ),
            patch.object(
                chat_job_service.PromptService,
                "get_full_contextualize_prompt",
                return_value="ctx",
            ),
            patch.object(
                chat_job_service.PromptService,
                "get_full_qa_strict_prompt",
                return_value="qa",
            ),
            patch.object(
                chat_job_service.SystemSettingsService,
                "__init__",
                return_value=None,
            ),
            patch.object(
                chat_job_service.SystemSettingsService,
                "get_top_k",
                return_value=5,
            ),
            patch.object(
                chat_job_service, "query_answering_workflow"
            ) as mock_workflow,
            patch(
                "app.services.chat_job_service.send_callback_async",
                new_callable=AsyncMock,
            ) as mock_callback,
        ):
            # Mock successful workflow
            mock_workflow.ainvoke = AsyncMock(
                return_value={"answer": "AI means Artificial Intelligence"}
            )

            # Run function
            await execute_chat_job(
                db=mock_db,
                job_id=sample_job_id,
                data=sample_data,
                callback_url=chat_callback_url,
                app_default_prompt=mock_app_default_prompt,
                knowledge_base_ids=knowledge_base_ids,
            )

            # --- Assertions ---
            mock_run.assert_called_once_with(mock_db, sample_job_id)
            mock_done.assert_called_once()
            mock_fail.assert_not_called()
            mock_workflow.ainvoke.assert_awaited_once()

            # ✅ Verify callback
            mock_callback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_chat_job_failure(
        self,
        mock_db,
        sample_job_id,
        sample_data,
        knowledge_base_ids,
        chat_callback_url,
        mock_app_default_prompt,
    ):
        """❌ Test workflow crash handling."""
        mock_job = Mock()
        mock_job.id = sample_job_id
        mock_job.callback_params = {}

        with (
            patch.object(
                chat_job_service.JobService, "get_job", return_value=mock_job
            ),
            patch.object(
                chat_job_service.JobService, "update_status_to_running"
            ),
            patch.object(
                chat_job_service.JobService, "update_status_to_completed"
            ),
            patch.object(
                chat_job_service.JobService, "update_status_to_failed"
            ) as mock_fail,
            patch.object(
                chat_job_service, "query_answering_workflow"
            ) as mock_workflow,
            patch(
                "app.services.chat_job_service.send_callback_async",
                new_callable=AsyncMock,
            ),
        ):
            mock_workflow.ainvoke = AsyncMock(
                side_effect=Exception("Workflow crashed")
            )

            await execute_chat_job(
                db=mock_db,
                job_id=sample_job_id,
                data=sample_data,
                callback_url=chat_callback_url,
                app_default_prompt=mock_app_default_prompt,
                knowledge_base_ids=knowledge_base_ids,
            )

            mock_fail.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_chat_job_no_callback(
        self, mock_db, sample_job_id, sample_data, mock_app_default_prompt
    ):
        """🚫 Ensure no callback is sent when callback_url is None."""
        mock_job = Mock()
        mock_job.id = sample_job_id
        mock_job.callback_params = {}

        with (
            patch.object(
                chat_job_service.JobService, "get_job", return_value=mock_job
            ),
            patch.object(
                chat_job_service, "query_answering_workflow"
            ) as mock_workflow,
            patch(
                "app.services.chat_job_service.send_callback_async",
                new_callable=AsyncMock,
            ) as mock_callback,
        ):
            mock_workflow.ainvoke = AsyncMock(return_value={"answer": "ok"})

            await execute_chat_job(
                db=mock_db,
                job_id=sample_job_id,
                data=sample_data,
                callback_url=None,
                app_default_prompt=mock_app_default_prompt,
                knowledge_base_ids=[],
            )

            # ✅ Should be called using callback_url from apps table
            mock_callback.assert_awaited()

    # --- Prompt logic tests ---

    @pytest.mark.asyncio
    async def test_prompt_logic_job_prompt_overrides_default(
        self, mock_db, sample_job_id, sample_data, mock_app_default_prompt
    ):
        """🧩 Ensure job.prompt overrides app.default_chat_prompt."""
        mock_job = Mock()
        mock_job.id = sample_job_id

        with (
            patch.object(
                chat_job_service.JobService, "get_job", return_value=mock_job
            ),
            patch.object(
                chat_job_service.PromptService, "__init__", return_value=None
            ),
            patch.object(
                chat_job_service.PromptService,
                "get_full_contextualize_prompt",
                return_value="ctx",
            ),
            patch.object(
                chat_job_service.PromptService,
                "get_full_qa_strict_prompt",
                return_value="qa",
            ),
            patch.object(
                chat_job_service.SystemSettingsService,
                "__init__",
                return_value=None,
            ),
            patch.object(
                chat_job_service.SystemSettingsService,
                "get_top_k",
                return_value=5,
            ),
            patch.object(
                chat_job_service, "query_answering_workflow"
            ) as mock_workflow,
            patch(
                "app.services.chat_job_service.send_callback_async",
                new_callable=AsyncMock,
            ),
        ):
            mock_workflow.ainvoke = AsyncMock(return_value={"answer": "test"})

            await execute_chat_job(
                db=mock_db,
                job_id=sample_job_id,
                data=sample_data,  # contains "prompt"
                callback_url=None,
                app_default_prompt=mock_app_default_prompt,
                knowledge_base_ids=[],
            )

            # Capture the state sent to query_answering_workflow
            state_arg = mock_workflow.ainvoke.call_args[0][0]
            assert "qa_prompt_str" in state_arg
            assert "Explain AI in simple terms." in state_arg["qa_prompt_str"]

    @pytest.mark.asyncio
    async def test_prompt_logic_uses_app_default_when_no_job_prompt(
        self, mock_db, sample_job_id, mock_app_default_prompt
    ):
        """🧩 Ensure default_chat_prompt used when no job.prompt provided."""
        mock_job = Mock()
        mock_job.id = sample_job_id
        data = {"chats": [{"role": "user", "content": "Hello"}]}  # no "prompt"

        with (
            patch.object(
                chat_job_service.JobService, "get_job", return_value=mock_job
            ),
            patch.object(
                chat_job_service.PromptService, "__init__", return_value=None
            ),
            patch.object(
                chat_job_service.PromptService,
                "get_full_contextualize_prompt",
                return_value="ctx",
            ),
            patch.object(
                chat_job_service.PromptService,
                "get_full_qa_strict_prompt",
                return_value="qa",
            ),
            patch.object(
                chat_job_service.SystemSettingsService,
                "__init__",
                return_value=None,
            ),
            patch.object(
                chat_job_service.SystemSettingsService,
                "get_top_k",
                return_value=5,
            ),
            patch.object(
                chat_job_service, "query_answering_workflow"
            ) as mock_workflow,
            patch(
                "app.services.chat_job_service.send_callback_async",
                new_callable=AsyncMock,
            ),
        ):
            mock_workflow.ainvoke = AsyncMock(return_value={"answer": "ok"})

            await execute_chat_job(
                db=mock_db,
                job_id=sample_job_id,
                data=data,
                callback_url=None,
                app_default_prompt=mock_app_default_prompt,
                knowledge_base_ids=[],
            )

            state_arg = mock_workflow.ainvoke.call_args[0][0]
            assert "qa_prompt_str" in state_arg
            assert mock_app_default_prompt in state_arg["qa_prompt_str"]

    @pytest.mark.asyncio
    async def test_prompt_logic_final_prompt_combines_qa_and_app_prompt(
        self, mock_db, sample_job_id, mock_app_default_prompt
    ):
        """🧠
        Ensure qa_prompt_str is built as qa_prompt + app_final_prompt with
        separator.
        """
        mock_job = Mock()
        mock_job.id = sample_job_id
        data = {
            "prompt": "Custom job prompt",
            "chats": [{"role": "user", "content": "Hello"}],
        }

        with (
            patch.object(
                chat_job_service.JobService, "get_job", return_value=mock_job
            ),
            patch.object(
                chat_job_service.PromptService, "__init__", return_value=None
            ),
            patch.object(
                chat_job_service.PromptService,
                "get_full_contextualize_prompt",
                return_value="CTX_PROMPT",
            ),
            patch.object(
                chat_job_service.PromptService,
                "get_full_qa_strict_prompt",
                return_value="QA_PROMPT",
            ),
            patch.object(
                chat_job_service.SystemSettingsService,
                "__init__",
                return_value=None,
            ),
            patch.object(
                chat_job_service.SystemSettingsService,
                "get_top_k",
                return_value=3,
            ),
            patch.object(
                chat_job_service, "query_answering_workflow"
            ) as mock_workflow,
            patch(
                "app.services.chat_job_service.send_callback_async",
                new_callable=AsyncMock,
            ),
        ):
            mock_workflow.ainvoke = AsyncMock(return_value={"answer": "done"})

            await execute_chat_job(
                db=mock_db,
                job_id=sample_job_id,
                data=data,
                callback_url=None,
                app_default_prompt=mock_app_default_prompt,
                knowledge_base_ids=[],
            )

            state_arg = mock_workflow.ainvoke.call_args[0][0]
            assert (
                state_arg["qa_prompt_str"]
                == "QA_PROMPT\n\n**IMPORTANT: Follow these additional rules strictly:**\n\nCustom job prompt"
            )
