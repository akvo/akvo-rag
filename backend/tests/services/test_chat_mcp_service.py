import pytest
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace

from app.services.chat_mcp_service import stream_mcp_response


@pytest.mark.unit
class TestChatMCPService:
    """Unit tests for stream_mcp_response (success and edge cases)."""

    @pytest.mark.asyncio
    async def test_stream_mcp_response_single_message_success(
        self, monkeypatch
    ):
        """Stream response with DB chat history (messages length <= 1)."""
        fake_db = MagicMock()
        fake_message = SimpleNamespace(role="user", content="hi")
        fake_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            fake_message
        ]

        # Mock PromptService
        fake_prompt_service = MagicMock()
        fake_prompt_service.get_full_contextualize_prompt.return_value = (
            "context prompt"
        )
        fake_prompt_service.get_full_qa_strict_prompt.return_value = (
            "qa prompt"
        )
        monkeypatch.setattr(
            "app.services.chat_mcp_service.PromptService",
            lambda db: fake_prompt_service,
        )

        # Mock workflow astream_events
        async def fake_astream(initial_state, stream_mode):
            yield {
                "event": "on_chain_stream",
                "name": "generate",
                "data": {"chunk": "Hello"},
            }

        monkeypatch.setattr(
            "app.services.chat_mcp_service.query_answering_workflow.astream_events",
            fake_astream,
        )

        # Mock workflow ainvoke
        monkeypatch.setattr(
            "app.services.chat_mcp_service.query_answering_workflow.ainvoke",
            AsyncMock(return_value={"answer": "Final answer"}),
        )

        chunks = []
        async for chunk in stream_mcp_response(
            query="Hi",
            messages={"messages": []},
            knowledge_base_ids=[1],
            chat_id=123,
            db=fake_db,
        ):
            chunks.append(chunk)

        # Assertions
        assert any("Hello" in c for c in chunks)
        fake_db.add_all.assert_called()
        fake_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_stream_mcp_response_multiple_messages_success(
        self, monkeypatch
    ):
        """Stream response with messages from frontend (length > 1)."""
        fake_db = MagicMock()
        messages = {
            "messages": [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "ok"},
            ]
        }

        fake_prompt_service = MagicMock()
        fake_prompt_service.get_full_contextualize_prompt.return_value = (
            "context prompt"
        )
        fake_prompt_service.get_full_qa_strict_prompt.return_value = (
            "qa prompt"
        )
        monkeypatch.setattr(
            "app.services.chat_mcp_service.PromptService",
            lambda db: fake_prompt_service,
        )

        async def fake_astream(initial_state, stream_mode):
            yield {
                "event": "on_chain_stream",
                "name": "generate",
                "data": {"chunk": "World"},
            }

        monkeypatch.setattr(
            "app.services.chat_mcp_service.query_answering_workflow.astream_events",
            fake_astream,
        )
        monkeypatch.setattr(
            "app.services.chat_mcp_service.query_answering_workflow.ainvoke",
            AsyncMock(return_value={"answer": "Final answer"}),
        )

        chunks = []
        async for chunk in stream_mcp_response(
            query="Hello",
            messages=messages,
            knowledge_base_ids=[1],
            chat_id=456,
            db=fake_db,
        ):
            chunks.append(chunk)

        assert any("World" in c for c in chunks)
        fake_db.add_all.assert_called()
        fake_db.commit.assert_called()

    # ---------------- Edge / Error Cases ----------------

    @pytest.mark.asyncio
    async def test_stream_mcp_response_no_chunks(self, monkeypatch):
        """Workflow yields no chunks at all."""
        fake_db = MagicMock()

        fake_prompt_service = MagicMock()
        fake_prompt_service.get_full_contextualize_prompt.return_value = "ctx"
        fake_prompt_service.get_full_qa_strict_prompt.return_value = "qa"
        monkeypatch.setattr(
            "app.services.chat_mcp_service.PromptService",
            lambda db: fake_prompt_service,
        )

        async def fake_astream(initial_state, stream_mode):
            if False:  # never yield
                yield

        monkeypatch.setattr(
            "app.services.chat_mcp_service.query_answering_workflow.astream_events",
            fake_astream,
        )
        monkeypatch.setattr(
            "app.services.chat_mcp_service.query_answering_workflow.ainvoke",
            AsyncMock(return_value={"answer": ""}),
        )

        chunks = []
        async for chunk in stream_mcp_response(
            query="Hi",
            messages={"messages": []},
            knowledge_base_ids=[1],
            chat_id=1,
            db=fake_db,
        ):
            chunks.append(chunk)

        assert chunks == []
        fake_db.add_all.assert_called()
        fake_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_stream_mcp_response_db_commit_error(self, monkeypatch):
        """DB commit failure raises exception."""
        fake_db = MagicMock()
        fake_db.commit.side_effect = Exception("DB commit failed")

        fake_prompt_service = MagicMock()
        fake_prompt_service.get_full_contextualize_prompt.return_value = "ctx"
        fake_prompt_service.get_full_qa_strict_prompt.return_value = "qa"
        monkeypatch.setattr(
            "app.services.chat_mcp_service.PromptService",
            lambda db: fake_prompt_service,
        )

        async def fake_astream(initial_state, stream_mode):
            yield {
                "event": "on_chain_stream",
                "name": "generate",
                "data": {"chunk": "Hello"},
            }

        monkeypatch.setattr(
            "app.services.chat_mcp_service.query_answering_workflow.astream_events",
            fake_astream,
        )
        monkeypatch.setattr(
            "app.services.chat_mcp_service.query_answering_workflow.ainvoke",
            AsyncMock(return_value={"answer": "Final"}),
        )

        with pytest.raises(Exception) as e:
            async for _ in stream_mcp_response(
                query="Hi",
                messages={"messages": []},
                knowledge_base_ids=[1],
                chat_id=1,
                db=fake_db,
            ):
                pass
        assert "DB commit failed" in str(e.value)

    @pytest.mark.asyncio
    async def test_stream_mcp_response_messages_truncate(self, monkeypatch):
        """Messages exceeding max_history_length are truncated."""
        fake_db = MagicMock()
        messages = {
            "messages": [
                {"role": "user", "content": f"msg{i}"} for i in range(20)
            ]
        }

        fake_prompt_service = MagicMock()
        fake_prompt_service.get_full_contextualize_prompt.return_value = "ctx"
        fake_prompt_service.get_full_qa_strict_prompt.return_value = "qa"
        monkeypatch.setattr(
            "app.services.chat_mcp_service.PromptService",
            lambda db: fake_prompt_service,
        )

        async def fake_astream(initial_state, stream_mode):
            # verify truncation applied
            assert len(initial_state["chat_history"]) <= 10
            yield {
                "event": "on_chain_stream",
                "name": "generate",
                "data": {"chunk": "chunk"},
            }

        monkeypatch.setattr(
            "app.services.chat_mcp_service.query_answering_workflow.astream_events",
            fake_astream,
        )
        monkeypatch.setattr(
            "app.services.chat_mcp_service.query_answering_workflow.ainvoke",
            AsyncMock(return_value={"answer": "Final"}),
        )

        chunks = []
        async for chunk in stream_mcp_response(
            query="Test",
            messages=messages,
            knowledge_base_ids=[1],
            chat_id=1,
            db=fake_db,
            max_history_length=10,
        ):
            chunks.append(chunk)

        assert any("chunk" in c for c in chunks)
        fake_db.add_all.assert_called()
        fake_db.commit.assert_called()
