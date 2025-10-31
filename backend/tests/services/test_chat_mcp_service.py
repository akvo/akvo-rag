import pytest
from unittest.mock import MagicMock
from types import SimpleNamespace

from app.services import chat_mcp_service


@pytest.mark.unit
class TestChatMCPServiceStubbed:
    """Pure unit tests for stream_mcp_response (all externals stubbed)."""

    def setup_method(self, method):
        self.fake_db = MagicMock()
        self.fake_db.add.return_value = None
        self.fake_db.commit.return_value = None
        self.fake_db.close.return_value = None
        self.fake_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = (
            []
        )

    def _stub_common_services(
        self, monkeypatch, tokens=None, context=True, intent="knowledge_query"
    ):
        """Stub all dependencies for stream_mcp_response."""

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
        async def fake_classify_intent_node(state):
            state["intent"] = intent
            return state

        async def fake_small_talk_node(state):
            state["answer"] = "Hey there! Small talk mode."
            return state

        async def fake_contextualize_node(state):
            state["contextual_query"] = f"ctx_{intent}"
            return state

        async def fake_scoping_node(state):
            state["scope"]["top_k"] = 1
            return state

        async def fake_run_mcp_tool_node(state):
            # Different behavior depending on intent
            if intent == "weather_query":
                state["context"] = [
                    SimpleNamespace(page_content="It’s 30°C in Bali.", metadata={"tool": "weather"})
                ]
            elif context:
                state["context"] = [
                    SimpleNamespace(page_content="doc1", metadata={"id": 1})
                ]
            else:
                state["context"] = []
            return state

        async def fake_post_processing_node(state):
            return state

        monkeypatch.setattr(
            chat_mcp_service, "classify_intent_node", fake_classify_intent_node
        )
        monkeypatch.setattr(
            chat_mcp_service, "small_talk_node", fake_small_talk_node
        )
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

    # ============================ TESTS ==================================

    @pytest.mark.asyncio
    async def test_stream_success_with_context(self, monkeypatch):
        """Should stream QA tokens and context correctly."""
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

        assert any(c.startswith('0:"') for c in chunks)
        assert any("Hello" in c for c in chunks)
        assert any("world" in c for c in chunks)
        assert any(c.startswith("d:") for c in chunks)

    @pytest.mark.asyncio
    async def test_stream_success_no_context(self, monkeypatch):
        """Should stream QA tokens even with no retrieved context."""
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

        assert any("Hey" in c for c in chunks)
        assert any(c.startswith("d:") for c in chunks)

    @pytest.mark.asyncio
    async def test_stream_no_chunks(self, monkeypatch):
        """Should gracefully finish even if no LLM tokens are emitted."""
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

        assert chunks[-1].startswith('d:')
        assert '"finishReason":"stop"' in chunks[-1]

    @pytest.mark.asyncio
    async def test_stream_db_commit_error(self, monkeypatch):
        """Should yield an error line if DB commit fails."""
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

        assert any(c.startswith("3:") for c in chunks)
        assert "DB commit failed" in chunks[-1]

    @pytest.mark.asyncio
    async def test_stream_messages_truncate(self, monkeypatch):
        """Should truncate message history to max_history_length."""
        messages = {
            "messages": [
                {"role": "user", "content": f"msg{i}"} for i in range(20)
            ]
        }
        self._stub_common_services(monkeypatch, tokens=["chunk"], context=True)

        async def fake_astream(inputs):
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

    # ============= NEW TESTS =============

    @pytest.mark.asyncio
    async def test_stream_small_talk_intent(self, monkeypatch):
        """Should skip MCP and reply immediately for small talk."""
        self._stub_common_services(monkeypatch, intent="small_talk")

        chunks = []
        async for chunk in chat_mcp_service.stream_mcp_response(
            query="Hi there!",
            messages={"messages": []},
            knowledge_base_ids=[1],
            chat_id=321,
            db=self.fake_db,
        ):
            chunks.append(chunk)

        assert any("Hey there! Small talk mode." in c for c in chunks)
        assert any('d:{"finishReason":"stop"}' in c for c in chunks)

    @pytest.mark.asyncio
    async def test_stream_weather_intent(self, monkeypatch):
        """Should trigger Weather MCP flow and stream weather info tokens."""
        self._stub_common_services(
            monkeypatch, tokens=["Weather", " info"], context=True, intent="weather_query"
        )

        chunks = []
        async for chunk in chat_mcp_service.stream_mcp_response(
            query="What's the weather in Bali?",
            messages={"messages": []},
            knowledge_base_ids=[1],
            chat_id=101,
            db=self.fake_db,
        ):
            chunks.append(chunk)

        # Ensure context came from weather MCP
        assert any("Bali" not in c or "base64" in c for c in chunks)
        assert any("Weather" in c for c in chunks)
        assert any("info" in c for c in chunks)
        assert any(c.startswith("d:") for c in chunks)

    @pytest.mark.asyncio
    async def test_stream_kb_intent(self, monkeypatch):
        """Should trigger KB MCP flow for general knowledge base query."""
        self._stub_common_services(
            monkeypatch, tokens=["KB", " answer"], context=True, intent="kb_query"
        )

        chunks = []
        async for chunk in chat_mcp_service.stream_mcp_response(
            query="What is the capital of France?",
            messages={"messages": []},
            knowledge_base_ids=[1],
            chat_id=202,
            db=self.fake_db,
        ):
            chunks.append(chunk)

        assert any("KB" in c for c in chunks)
        assert any("answer" in c for c in chunks)
        assert any(c.startswith("d:") for c in chunks)

    @pytest.mark.asyncio
    async def test_stream_no_kb_ids_raises(self, monkeypatch):
        """Should raise ValueError when no knowledge base IDs provided."""
        self._stub_common_services(monkeypatch)

        with pytest.raises(ValueError):
            async for _ in chat_mcp_service.stream_mcp_response(
                query="Hi",
                messages={"messages": []},
                knowledge_base_ids=[],
                chat_id=100,
                db=self.fake_db,
            ):
                pass
