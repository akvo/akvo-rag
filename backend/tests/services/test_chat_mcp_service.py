import pytest
from unittest.mock import MagicMock
from types import SimpleNamespace

from app.services.chat_mcp_service import stream_mcp_response


@pytest.mark.unit
class TestChatMCPService:
    """Unit tests for stream_mcp_response (success and edge cases)."""

    @pytest.mark.asyncio
    async def test_stream_mcp_response_single_message_success(
        self, monkeypatch
    ):
        fake_db = MagicMock()
        fake_message = SimpleNamespace(role="user", content="hi")
        fake_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            fake_message
        ]

        fake_prompt_service = MagicMock()
        fake_prompt_service.get_full_contextualize_prompt.return_value = "ctx"
        fake_prompt_service.get_full_qa_strict_prompt.return_value = "qa"
        monkeypatch.setattr(
            "app.services.chat_mcp_service.PromptService",
            lambda db: fake_prompt_service,
        )

        async def fake_astream(inputs):
            for token in ["Hello", " world"]:
                yield token

        monkeypatch.setattr(
            "app.services.chat_mcp_service.create_stuff_documents_chain",
            lambda **kwargs: SimpleNamespace(astream=fake_astream),
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

        # Should include token chunks
        assert any("Hello" in c for c in chunks)
        assert any("world" in c for c in chunks)
        # Should include final d: metadata
        assert any(c.startswith("d:") for c in chunks)

    @pytest.mark.asyncio
    async def test_stream_mcp_response_multiple_messages_success(
        self, monkeypatch
    ):
        fake_db = MagicMock()
        messages = {
            "messages": [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "ok"},
            ]
        }

        fake_prompt_service = MagicMock()
        fake_prompt_service.get_full_contextualize_prompt.return_value = "ctx"
        fake_prompt_service.get_full_qa_strict_prompt.return_value = "qa"
        monkeypatch.setattr(
            "app.services.chat_mcp_service.PromptService",
            lambda db: fake_prompt_service,
        )

        async def fake_astream(inputs):
            for token in ["World", "!"]:
                yield token

        monkeypatch.setattr(
            "app.services.chat_mcp_service.create_stuff_documents_chain",
            lambda **kwargs: SimpleNamespace(astream=fake_astream),
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
        assert any("!" in c for c in chunks)
        assert any(c.startswith("d:") for c in chunks)

    @pytest.mark.asyncio
    async def test_stream_mcp_response_no_chunks(self, monkeypatch):
        fake_db = MagicMock()

        fake_prompt_service = MagicMock()
        fake_prompt_service.get_full_contextualize_prompt.return_value = "ctx"
        fake_prompt_service.get_full_qa_strict_prompt.return_value = "qa"
        monkeypatch.setattr(
            "app.services.chat_mcp_service.PromptService",
            lambda db: fake_prompt_service,
        )

        async def fake_astream(inputs):
            if False:
                yield

        monkeypatch.setattr(
            "app.services.chat_mcp_service.create_stuff_documents_chain",
            lambda **kwargs: SimpleNamespace(astream=fake_astream),
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

        # Even if no chunks, should yield final d: line
        assert chunks == [
            'd:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n'
        ]

    @pytest.mark.asyncio
    async def test_stream_mcp_response_db_commit_error(self, monkeypatch):
        fake_db = MagicMock()
        fake_db.commit.side_effect = Exception("DB commit failed")

        fake_prompt_service = MagicMock()
        fake_prompt_service.get_full_contextualize_prompt.return_value = "ctx"
        fake_prompt_service.get_full_qa_strict_prompt.return_value = "qa"
        monkeypatch.setattr(
            "app.services.chat_mcp_service.PromptService",
            lambda db: fake_prompt_service,
        )

        async def fake_astream(inputs):
            for token in ["Hello"]:
                yield token

        monkeypatch.setattr(
            "app.services.chat_mcp_service.create_stuff_documents_chain",
            lambda **kwargs: SimpleNamespace(astream=fake_astream),
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

        async def fake_astream(inputs):
            assert len(inputs["chat_history"]) <= 10
            for token in ["chunk"]:
                yield token

        monkeypatch.setattr(
            "app.services.chat_mcp_service.create_stuff_documents_chain",
            lambda **kwargs: SimpleNamespace(astream=fake_astream),
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
        assert any(c.startswith("d:") for c in chunks)
