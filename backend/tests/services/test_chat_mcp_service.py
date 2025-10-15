import pytest
from unittest.mock import MagicMock
from types import SimpleNamespace

from app.services import chat_mcp_service


@pytest.mark.unit
class TestChatMCPServiceStubbed:
    """Pure unit tests for stream_mcp_response (all externals stubbed)."""

    def setup_method(self, method):
        """Stub common dependencies before each test."""
        self.fake_db = MagicMock()
        self.fake_db.add.return_value = None
        self.fake_db.commit.return_value = None
        self.fake_db.close.return_value = None
        self.fake_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = (
            []
        )

    def _stub_common_services(self, monkeypatch, tokens=None, context=True):
        # PromptService
        fake_prompt_service = MagicMock()
        fake_prompt_service.get_full_contextualize_prompt.return_value = "ctx"
        fake_prompt_service.get_full_qa_strict_prompt.return_value = "qa"
        monkeypatch.setattr(
            chat_mcp_service, "PromptService", lambda db: fake_prompt_service
        )

        # SettingsService
        fake_settings_service = MagicMock()
        fake_settings_service.get_top_k.return_value = 5
        monkeypatch.setattr(
            chat_mcp_service,
            "SystemSettingsService",
            lambda db: fake_settings_service,
        )

        # MCP workflow nodes
        async def fake_contextualize_node(state):
            state["contextual_query"] = "fake_query"
            return state

        async def fake_scoping_node(state):
            state["scope"]["top_k"] = 1
            return state

        async def fake_run_mcp_tool_node(state):
            if context:
                state["context"] = [
                    SimpleNamespace(page_content="doc1", metadata={"id": 1})
                ]
            else:
                state["context"] = []
            return state

        async def fake_post_processing_node(state):
            return state

        monkeypatch.setattr(
            chat_mcp_service, "contextualize_node", fake_contextualize_node
        )
        monkeypatch.setattr(
            chat_mcp_service, "scoping_node", fake_scoping_node
        )
        monkeypatch.setattr(
            chat_mcp_service, "run_mcp_tool_node", fake_run_mcp_tool_node
        )
        monkeypatch.setattr(
            chat_mcp_service, "post_processing_node", fake_post_processing_node
        )

        # Fake QA chain
        async def fake_astream(inputs):
            if tokens:
                for t in tokens:
                    yield t

        fake_chain = SimpleNamespace(astream=fake_astream)
        monkeypatch.setattr(
            chat_mcp_service,
            "create_stuff_documents_chain",
            lambda **kwargs: fake_chain,
        )

        # LLMFactory
        monkeypatch.setattr(
            chat_mcp_service.LLMFactory, "create", lambda: MagicMock()
        )

    @pytest.mark.asyncio
    async def test_stream_success_with_context(self, monkeypatch):
        self._stub_common_services(
            monkeypatch, tokens=["Hello", " world"], context=True
        )

        chunks = []
        async for chunk in chat_mcp_service.stream_mcp_response(
            query="Hi",
            messages={"messages": []},
            knowledge_base_ids=[1],
            chat_id=123,
            db=self.fake_db,
        ):
            chunks.append(chunk)

        assert any(c.startswith('0:"') for c in chunks)  # context prefix
        assert any("Hello" in c for c in chunks)
        assert any("world" in c for c in chunks)
        assert any(c.startswith("d:") for c in chunks)

    @pytest.mark.asyncio
    async def test_stream_success_no_context(self, monkeypatch):
        self._stub_common_services(monkeypatch, tokens=["Hey"], context=False)

        chunks = []
        async for chunk in chat_mcp_service.stream_mcp_response(
            query="Hello",
            messages={"messages": []},
            knowledge_base_ids=[1],
            chat_id=456,
            db=self.fake_db,
        ):
            chunks.append(chunk)

        assert any('0:"Hey"' in c for c in chunks)

    @pytest.mark.asyncio
    async def test_stream_no_chunks(self, monkeypatch):
        self._stub_common_services(monkeypatch, tokens=[], context=True)

        chunks = []
        async for chunk in chat_mcp_service.stream_mcp_response(
            query="Hi",
            messages={"messages": []},
            knowledge_base_ids=[1],
            chat_id=789,
            db=self.fake_db,
        ):
            chunks.append(chunk)

        # Should still end with final d: metadata
        assert (
            chunks[-1]
            == 'd:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n'
        )

    @pytest.mark.asyncio
    async def test_stream_db_commit_error(self, monkeypatch):
        self.fake_db.commit.side_effect = Exception("DB commit failed")
        self._stub_common_services(monkeypatch, tokens=["Hello"], context=True)

        chunks = []
        async for chunk in chat_mcp_service.stream_mcp_response(
            query="Hi",
            messages={"messages": []},
            knowledge_base_ids=[1],
            chat_id=999,
            db=self.fake_db,
        ):
            chunks.append(chunk)

        # Should yield an error line
        assert any(c.startswith("3:") for c in chunks)
        assert "DB commit failed" in chunks[-1]

    @pytest.mark.asyncio
    async def test_stream_messages_truncate(self, monkeypatch):
        messages = {
            "messages": [
                {"role": "user", "content": f"msg{i}"} for i in range(20)
            ]
        }
        self._stub_common_services(monkeypatch, tokens=["chunk"], context=True)

        async def fake_astream(inputs):
            # Ensure truncation to max_history_length
            assert len(inputs["chat_history"]) <= 10
            yield "chunk"

        fake_chain = SimpleNamespace(astream=fake_astream)
        monkeypatch.setattr(
            chat_mcp_service,
            "create_stuff_documents_chain",
            lambda **kwargs: fake_chain,
        )

        chunks = []
        async for chunk in chat_mcp_service.stream_mcp_response(
            query="Test",
            messages=messages,
            knowledge_base_ids=[1],
            chat_id=42,
            db=self.fake_db,
            max_history_length=10,
        ):
            chunks.append(chunk)

        assert any("chunk" in c for c in chunks)
        assert any(c.startswith("d:") for c in chunks)
