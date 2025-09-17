import json
import base64
import pytest
from unittest.mock import AsyncMock, MagicMock

from langchain_core.documents import Document
from types import SimpleNamespace

from app.services.query_answering_workflow import (
    decode_mcp_context,
    contextualize_node,
    scoping_node,
    run_mcp_tool_node,
    post_processing_node,
    response_generation_node,
    GraphState,
)


@pytest.mark.unit
class TestQueryAnsweringWorkflow:
    """Unit tests for query_answering_workflow nodes."""

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

    def test_contextualize_node_success(self, monkeypatch):
        """contextualize_node() updates state with contextual_query."""

        # Monkeypatch chain.invoke to bypass real LLM/prompt logic
        monkeypatch.setattr(
            "app.services.query_answering_workflow.ChatPromptTemplate.from_messages",
            lambda msgs: MagicMock(
                __or__=lambda self, other: MagicMock(
                    invoke=lambda inputs: SimpleNamespace(
                        content=" refined query "
                    )
                )
            ),
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

        new_state = contextualize_node(state)
        assert new_state["contextual_query"] == "refined query"

    # ---------------- scoping_node ----------------

    @pytest.mark.asyncio
    async def test_scoping_node_success(self, monkeypatch):
        """scoping_node() sets scope using ScopingAgent mock."""
        fake_agent = MagicMock()
        fake_agent.scope_query.return_value = {
            "server_name": "s1",
            "tool_name": "t1",
            "input": {"kb_id": 1, "query": "q"},
        }
        monkeypatch.setattr(
            "app.services.query_answering_workflow.ScopingAgent",
            lambda: fake_agent,
        )

        state: GraphState = {
            "query": "q",
            "chat_history": [],
            "contextualize_prompt_str": "",
            "qa_prompt_str": "",
            "contextual_query": "q",
            "scope": {"kb_id": 1},
            "mcp_result": None,
            "context": [],
            "answer": "",
        }

        new_state = await scoping_node(state)
        assert new_state["scope"]["server_name"] == "s1"

    @pytest.mark.asyncio
    async def test_scoping_node_missing_kb_id(self):
        """scoping_node() raises ValueError if kb_id missing."""
        state: GraphState = {
            "query": "q",
            "chat_history": [],
            "contextualize_prompt_str": "",
            "qa_prompt_str": "",
            "contextual_query": "q",
            "scope": {},
            "mcp_result": None,
            "context": [],
            "answer": "",
        }
        with pytest.raises(ValueError):
            await scoping_node(state)

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
            "query": "",
            "chat_history": [],
            "contextualize_prompt_str": "",
            "qa_prompt_str": "",
            "contextual_query": "",
            "scope": {"server_name": "s1", "tool_name": "t1", "input": {}},
            "mcp_result": None,
            "context": [],
            "answer": "",
        }

        new_state = await run_mcp_tool_node(state)
        assert new_state["mcp_result"] == {"res": 123}

    # ---------------- post_processing_node ----------------

    def test_post_processing_node_success(self):
        """post_processing_node() decodes valid MCP base64 context."""
        context = {"context": [{"page_content": "doc", "metadata": {}}]}
        b64 = base64.b64encode(json.dumps(context).encode()).decode()

        state: GraphState = {
            "query": "",
            "chat_history": [],
            "contextualize_prompt_str": "",
            "qa_prompt_str": "",
            "contextual_query": "",
            "scope": {},
            "mcp_result": MagicMock(
                content=[MagicMock(text=json.dumps({"context": b64}))]
            ),
            "context": [],
            "answer": "",
        }

        new_state = post_processing_node(state)
        assert isinstance(new_state["context"][0], Document)
        assert new_state["context"][0].page_content == "doc"

    def test_post_processing_node_invalid(self):
        """post_processing_node() falls back to empty context on error."""
        state: GraphState = {
            "query": "",
            "chat_history": [],
            "contextualize_prompt_str": "",
            "qa_prompt_str": "",
            "contextual_query": "",
            "scope": {},
            "mcp_result": MagicMock(content=[MagicMock(text="not-json")]),
            "context": [],
            "answer": "",
        }

        new_state = post_processing_node(state)
        assert new_state["context"] == []

    # ---------------- response_generation_node ----------------

    @pytest.mark.asyncio
    async def test_response_generation_node_success(self, monkeypatch):
        """response_generation_node() streams chunks and builds answer."""

        async def fake_astream(_):
            yield "Hello"
            yield " world"

        fake_chain = MagicMock()
        fake_chain.astream = fake_astream

        fake_llm = MagicMock()
        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: fake_llm,
        )
        monkeypatch.setattr(
            "app.services.query_answering_workflow.create_stuff_documents_chain",
            lambda **_: fake_chain,
        )

        state: GraphState = {
            "query": "",
            "chat_history": [],
            "contextualize_prompt_str": "",
            "qa_prompt_str": "qa!",
            "contextual_query": "my query",
            "scope": {},
            "mcp_result": None,
            "context": [],
            "answer": "",
        }

        chunks = []
        async for chunk in response_generation_node(state):
            chunks.append(chunk)

        # Verify yielded chunks and final state answer
        assert any("Hello" in c or "world" in c for c in chunks)
        assert state["answer"] == "Hello world"
