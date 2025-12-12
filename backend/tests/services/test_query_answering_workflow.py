import json
import base64
import pytest
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace
from langchain_core.documents import Document

from app.services.query_answering_workflow import (
    decode_mcp_context,
    contextualize_node,
    scoping_node,
    run_mcp_tool_node,
    post_processing_node,
    response_generation_node,
    classify_intent_node,
    GraphState,
)


@pytest.mark.unit
class TestQueryAnsweringWorkflow:
    """Unit tests for query_answering_workflow nodes."""

    # ---------------- classify_intent_node ----------------

    @pytest.mark.asyncio
    async def test_classify_intent_node_fast_result(self, monkeypatch):
        """classify_intent_node should use LLM to classify small talk."""

        async def fake_ainvoke(msgs):
            return SimpleNamespace(content='{"intent": "small_talk"}')

        fake_llm = MagicMock()
        fake_llm.ainvoke = fake_ainvoke
        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: fake_llm,
        )

        state = {"query": "Hi there!"}
        new_state = await classify_intent_node(state)
        assert new_state["intent"] == "small_talk"

    @pytest.mark.asyncio
    async def test_classify_intent_node_llm_fallback(self, monkeypatch):
        """classify_intent_node should use LLM when uncertain."""

        async def fake_ainvoke(msgs):
            return SimpleNamespace(content='{"intent": "weather_query"}')

        fake_llm = MagicMock()
        fake_llm.ainvoke = fake_ainvoke
        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: fake_llm,
        )

        state = {"query": "random text with no intent"}
        new_state = await classify_intent_node(state)
        assert new_state["intent"] == "weather_query"

    @pytest.mark.asyncio
    async def test_classify_intent_node_llm_error(self, monkeypatch):
        """
        classify_intent_node should fall back to general_query on LLM failure.
        """
        fake_llm = MagicMock()
        fake_llm.ainvoke = AsyncMock(side_effect=Exception("llm down"))
        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: fake_llm,
        )

        state = {"query": "something uncertain"}
        new_state = await classify_intent_node(state)
        assert new_state["intent"] == "general_query"

    # ---------------- decode_mcp_context ----------------

    def test_decode_mcp_context_valid(self):
        """decode_mcp_context() decodes base64 into Document objects."""
        context = {
            "context": [{"page_content": "hello", "metadata": {"x": 1}}]
        }
        encoded = base64.b64encode(json.dumps(context).encode()).decode()

        docs = decode_mcp_context(encoded)
        assert isinstance(docs[0], Document)
        assert docs[0].page_content == "hello"
        assert docs[0].metadata == {"x": 1}

    def test_decode_mcp_context_empty(self):
        """decode_mcp_context() returns empty list when context missing."""
        context = {}
        encoded = base64.b64encode(json.dumps(context).encode()).decode()
        docs = decode_mcp_context(encoded)
        assert docs == []

    # ---------------- contextualize_node ----------------

    @pytest.mark.asyncio
    async def test_contextualize_node_success(self, monkeypatch):
        """contextualize_node() updates state with contextual_query."""

        async def fake_ainvoke(inputs):
            return SimpleNamespace(content=" refined query ")

        fake_chain = MagicMock()
        fake_chain.ainvoke = fake_ainvoke

        monkeypatch.setattr(
            "app.services.query_answering_workflow.ChatPromptTemplate.from_messages",  # noqa
            lambda msgs: MagicMock(__or__=lambda self, other: fake_chain),
        )
        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: MagicMock(),
        )

        state: GraphState = {
            "query": "original query",
            "chat_history": [],
            "contextualize_prompt_str": "contextualize!",
            "qa_prompt_str": "",
            "contextual_query": "",
            "scope": {},
            "mcp_result": None,
            "context": [],
            "answer": "",
        }

        new_state = await contextualize_node(state)
        assert new_state["contextual_query"] == "refined query"

    # ---------------- scoping_node ----------------

    @pytest.mark.asyncio
    async def test_scoping_node_success(self, monkeypatch):
        """scoping_node() sets scope using ScopingAgent mock."""
        fake_agent = MagicMock()
        fake_agent.scope_query = AsyncMock(
            return_value={
                "server_name": "s1",
                "tool_name": "t1",
                "input": {"knowledge_base_ids": [1], "query": "q"},
            }
        )
        monkeypatch.setattr(
            "app.services.query_answering_workflow.ScopingAgent",
            lambda: fake_agent,
        )

        state: GraphState = {"contextual_query": "q", "scope": {}}
        new_state = await scoping_node(state)
        assert new_state["scope"]["server_name"] == "s1"

    # ---------------- run_mcp_tool_node ----------------

    @pytest.mark.asyncio
    async def test_run_mcp_tool_node_success(self, monkeypatch):
        """
        run_mcp_tool_node() calls MCPClientManager.run_tool and stores result.
        """
        fake_manager = MagicMock()
        fake_manager.run_tool = AsyncMock(return_value={"res": 123})
        monkeypatch.setattr(
            "app.services.query_answering_workflow.MCPClientManager",
            lambda: fake_manager,
        )

        state: GraphState = {
            "scope": {"server_name": "s1", "tool_name": "t1", "input": {}},
        }

        new_state = await run_mcp_tool_node(state)
        assert new_state["mcp_result"] == {"res": 123}

    # ---------------- post_processing_node ----------------

    @pytest.mark.asyncio
    async def test_post_processing_node_success(self):
        """post_processing_node() decodes valid MCP base64 context."""
        context = {"context": [{"page_content": "doc", "metadata": {}}]}
        b64 = base64.b64encode(json.dumps(context).encode()).decode()

        state: GraphState = {
            "mcp_result": MagicMock(
                content=[MagicMock(text=json.dumps({"context": b64}))]
            )
        }

        new_state = await post_processing_node(state)
        assert isinstance(new_state["context"][0], Document)
        assert new_state["context"][0].page_content == "doc"

    @pytest.mark.asyncio
    async def test_post_processing_node_can_handle_dict(self):
        """post_processing_node() can handle dict results."""
        state: GraphState = {
            "mcp_result": {"weather": "sunny"},
        }

        new_state = await post_processing_node(state)
        assert isinstance(new_state["context"][0], Document)
        assert "sunny" in new_state["context"][0].page_content

    @pytest.mark.asyncio
    async def test_post_processing_node_can_handle_raw_text(self):
        """post_processing_node() can handle raw text fallback."""
        state: GraphState = {"mcp_result": "Just some text response"}

        new_state = await post_processing_node(state)
        assert "Just some text" in new_state["context"][0].page_content

    # ---------------- response_generation_node ----------------

    @pytest.mark.asyncio
    async def test_response_generation_node_success(self, monkeypatch):
        """response_generation_node() streams chunks and builds answer."""

        async def fake_astream(_):
            yield "Hello"
            yield " world"

        fake_chain = MagicMock()
        fake_chain.astream = fake_astream

        monkeypatch.setattr(
            "app.services.query_answering_workflow.create_stuff_documents_chain",  # noqa
            lambda **_: fake_chain,
        )

        state: GraphState = {
            "qa_prompt_str": "qa!",
            "contextual_query": "my query",
            "chat_history": [],
            "context": [],
        }

        chunks = []
        async for chunk in response_generation_node(state):
            chunks.append(chunk)

        # All chunks yielded as text
        assert any("Hello" in c or "world" in c for c in chunks)
        # The final yield contains the completed answer
        final = [c for c in chunks if isinstance(c, dict)][-1]
        assert final["answer"] == "Hello world"
