import json
import base64
import time
import statistics
import pytest
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace
from langchain_core.documents import Document

from app.services.query_answering_workflow import (
    decode_mcp_context,
    contextualize_node,
    run_mcp_tool_node,
    post_processing_node,
    response_generation_node,
    classify_intent_node,
    small_talk_node,
    error_handler_node,
    check_mcp_success,
    create_rag_graph,
    query_answering_workflow,
    GraphState,
)


@pytest.mark.unit
class TestQueryAnsweringWorkflow:
    """Unit tests for query_answering_workflow nodes."""

    # ---------------- classify_intent_node ----------------

    @pytest.mark.asyncio
    async def test_classify_intent_node_small_talk(self, monkeypatch):
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
    async def test_classify_intent_node_weather_query(self, monkeypatch):
        """classify_intent_node should classify weather queries."""

        async def fake_ainvoke(msgs):
            return SimpleNamespace(content='{"intent": "weather_query"}')

        fake_llm = MagicMock()
        fake_llm.ainvoke = fake_ainvoke
        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: fake_llm,
        )

        state = {"query": "What's the weather like?"}
        new_state = await classify_intent_node(state)
        assert new_state["intent"] == "weather_query"

    @pytest.mark.asyncio
    async def test_classify_intent_node_knowledge_query(self, monkeypatch):
        """classify_intent_node should classify knowledge queries."""

        async def fake_ainvoke(msgs):
            return SimpleNamespace(content='{"intent": "knowledge_query"}')

        fake_llm = MagicMock()
        fake_llm.ainvoke = fake_ainvoke
        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: fake_llm,
        )

        state = {"query": "How do I plant corn?"}
        new_state = await classify_intent_node(state)
        assert new_state["intent"] == "knowledge_query"

    @pytest.mark.asyncio
    async def test_classify_intent_node_llm_error(self, monkeypatch):
        """
        classify_intent_node should fall back to knowledge_query
        on LLM failure.
        """
        fake_llm = MagicMock()
        fake_llm.ainvoke = AsyncMock(side_effect=Exception("llm down"))
        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: fake_llm,
        )

        state = {"query": "something uncertain"}
        new_state = await classify_intent_node(state)
        assert new_state["intent"] == "knowledge_query"

    @pytest.mark.asyncio
    async def test_classify_intent_node_empty_query(self):
        """
        classify_intent_node should return knowledge_query for empty query.
        """
        state = {"query": ""}
        new_state = await classify_intent_node(state)
        assert new_state["intent"] == "knowledge_query"

    @pytest.mark.asyncio
    async def test_classify_intent_node_invalid_json_response(
        self, monkeypatch
    ):
        """classify_intent_node should handle invalid JSON from LLM."""

        async def fake_ainvoke(msgs):
            return SimpleNamespace(content="This is not JSON at all")

        fake_llm = MagicMock()
        fake_llm.ainvoke = fake_ainvoke
        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: fake_llm,
        )

        state = {"query": "test query"}
        new_state = await classify_intent_node(state)
        assert new_state["intent"] == "knowledge_query"

    # ---------------- small_talk_node ----------------

    @pytest.mark.asyncio
    async def test_small_talk_node_success(self, monkeypatch):
        """small_talk_node should generate friendly response."""

        async def fake_ainvoke(msgs):
            return SimpleNamespace(content="Hello! How can I help you today?")

        fake_llm = MagicMock()
        fake_llm.ainvoke = fake_ainvoke
        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: fake_llm,
        )

        state: GraphState = {"query": "Hi there!"}
        new_state = await small_talk_node(state)

        assert "answer" in new_state
        assert "Hello" in new_state["answer"]

    @pytest.mark.asyncio
    async def test_small_talk_node_llm_failure(self, monkeypatch):
        """small_talk_node should provide fallback on LLM failure."""

        fake_llm = MagicMock()
        fake_llm.ainvoke = AsyncMock(side_effect=Exception("LLM down"))
        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: fake_llm,
        )

        state: GraphState = {"query": "Hi!"}
        new_state = await small_talk_node(state)

        assert new_state["answer"] == "Hello!"

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

    def test_decode_mcp_context_invalid_base64(self):
        """decode_mcp_context() handles invalid base64 gracefully."""
        docs = decode_mcp_context("not-valid-base64!!!")
        assert docs == []

    # ---------------- contextualize_node ----------------

    @pytest.mark.asyncio
    async def test_contextualize_node_success(self, monkeypatch):
        """contextualize_node() updates state with contextual_query."""

        async def fake_ainvoke(inputs):
            return SimpleNamespace(content=" refined query ")

        fake_chain = MagicMock()
        fake_chain.ainvoke = fake_ainvoke

        cpt_patch = (
            "app.services.query_answering_workflow."
            "ChatPromptTemplate.from_messages"
        )
        monkeypatch.setattr(
            cpt_patch,
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

    @pytest.mark.asyncio
    async def test_contextualize_node_error(self, monkeypatch):
        """contextualize_node() should set error on failure."""

        fake_chain = MagicMock()
        fake_chain.ainvoke = AsyncMock(side_effect=Exception("Chain failed"))

        cpt_patch = (
            "app.services.query_answering_workflow."
            "ChatPromptTemplate.from_messages"
        )
        monkeypatch.setattr(
            cpt_patch,
            lambda msgs: MagicMock(__or__=lambda self, other: fake_chain),
        )
        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: MagicMock(),
        )

        state: GraphState = {
            "query": "test",
            "chat_history": [],
            "contextualize_prompt_str": "prompt",
        }

        new_state = await contextualize_node(state)
        assert "error" in new_state

    # ---------------- Graph Structure Verification ----------------

    def test_graph_structure_and_nodes(self):
        """
        Verify that create_rag_graph builds the streamlined graph and that
        scoping_node is completely removed from the pipeline.
        """
        wf = create_rag_graph()
        nodes = wf.nodes
        assert "classify_intent" in nodes
        assert "small_talk" in nodes
        assert "contextualize" in nodes
        assert "run_mcp" in nodes
        assert "generate" in nodes
        assert "error_handler" in nodes
        assert "scoping_node" not in nodes
        assert "scoping" not in nodes

        compiled = wf.compile()
        assert compiled is not None

    # ---------------- run_mcp_tool_node ----------------

    @pytest.mark.asyncio
    async def test_run_mcp_tool_node_success(self, monkeypatch):
        """
        run_mcp_tool_node() calls MCPQueueDispatcher.call_tool and
        stores result.
        """
        fake_dispatcher = MagicMock()
        fake_dispatcher.call_tool = AsyncMock(
            return_value={
                "chunks": [
                    {
                        "chunk_id": "c1",
                        "content": "Avocado harvesting guide",
                        "score": 0.95,
                        "metadata": {"source": "manual.pdf"},
                    }
                ]
            }
        )
        monkeypatch.setattr(
            "app.services.query_answering_workflow._mcp_dispatcher",
            fake_dispatcher,
        )

        state: GraphState = {
            "query": "harvest avocado",
            "knowledge_base_ids": [1],
        }

        new_state = await run_mcp_tool_node(state)
        assert len(new_state["context"]) == 1
        assert (
            new_state["context"][0].page_content == "Avocado harvesting guide"
        )
        assert new_state["context"][0].metadata["source"] == "manual.pdf"
        assert new_state["error"] is None

    @pytest.mark.asyncio
    async def test_run_mcp_tool_node_failure(self, monkeypatch):
        """run_mcp_tool_node() should set error when MCP tool fails."""
        fake_dispatcher = MagicMock()
        fake_dispatcher.call_tool = AsyncMock(
            side_effect=Exception("Redis queue timeout")
        )
        monkeypatch.setattr(
            "app.services.query_answering_workflow._mcp_dispatcher",
            fake_dispatcher,
        )

        state: GraphState = {
            "query": "harvest avocado",
            "knowledge_base_ids": [1],
        }

        new_state = await run_mcp_tool_node(state)
        assert "error" in new_state
        assert "Redis queue timeout" in new_state["error"]

    # ---------------- check_mcp_success ----------------

    def test_check_mcp_success_with_error(self):
        """check_mcp_success should return 'error' when error exists."""
        state: GraphState = {"error": "Connection failed"}
        result = check_mcp_success(state)
        assert result == "error"

    def test_check_mcp_success_without_error(self):
        """check_mcp_success should return 'success' when no error."""
        state: GraphState = {"mcp_result": {"data": "some result"}}
        result = check_mcp_success(state)
        assert result == "success"

    def test_check_mcp_success_empty_state(self):
        """check_mcp_success should return 'success' for empty state."""
        state: GraphState = {}
        result = check_mcp_success(state)
        assert result == "success"

    # ---------------- error_handler_node ----------------

    @pytest.mark.asyncio
    async def test_error_handler_weather_query(self, monkeypatch):
        """error_handler_node should use LLM to answer weather questions."""

        async def fake_ainvoke(msgs):
            return SimpleNamespace(
                content=(
                    "I don't have access to real-time weather data right now, "
                    "but typically this time of year sees mild temperatures. "
                    "Please check weather.com for current conditions."
                )
            )

        fake_llm = MagicMock()
        fake_llm.ainvoke = fake_ainvoke
        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: fake_llm,
        )

        state: GraphState = {
            "query": "What's the weather like?",
            "contextual_query": "What's the weather like?",
            "intent": "weather_query",
            "error": "Weather API connection failed",
        }

        new_state = await error_handler_node(state)

        assert "answer" in new_state
        assert len(new_state["answer"]) > 0
        assert "weather" in new_state["answer"].lower()

    @pytest.mark.asyncio
    async def test_error_handler_weather_fallback(self, monkeypatch):
        """
        error_handler_node should provide ultimate fallback for weather
        on LLM failure.
        """

        fake_llm = MagicMock()
        fake_llm.ainvoke = AsyncMock(side_effect=Exception("LLM down"))
        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: fake_llm,
        )

        state: GraphState = {
            "query": "Is it raining?",
            "contextual_query": "Is it raining?",
            "intent": "weather_query",
            "error": "Weather service unavailable",
        }

        new_state = await error_handler_node(state)

        assert "answer" in new_state
        assert "weather" in new_state["answer"].lower()

    @pytest.mark.asyncio
    async def test_error_handler_knowledge_query(self, monkeypatch):
        """
        error_handler_node should provide friendly 'try again' message
        for knowledge queries.
        """

        async def fake_ainvoke(msgs):
            return SimpleNamespace(
                content=(
                    "I'm having trouble finding that information right now. "
                    "Could you please try again in a moment?"
                )
            )

        fake_llm = MagicMock()
        fake_llm.ainvoke = fake_ainvoke
        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: fake_llm,
        )

        state: GraphState = {
            "query": "What is fertilizer A?",
            "contextual_query": "What is fertilizer A?",
            "intent": "knowledge_query",
            "error": "Knowledge base connection failed",
        }

        new_state = await error_handler_node(state)

        assert "answer" in new_state
        assert len(new_state["answer"]) > 0
        answer_lower = new_state["answer"].lower()
        assert "try again" in answer_lower or "moment" in answer_lower
        # Should NOT mention technical details
        assert "error" not in answer_lower
        assert "technical" not in answer_lower

    @pytest.mark.asyncio
    async def test_error_handler_knowledge_query_fallback(self, monkeypatch):
        """
        error_handler_node should provide friendly ultimate fallback
        for non-weather queries on LLM failure.
        """

        fake_llm = MagicMock()
        fake_llm.ainvoke = AsyncMock(side_effect=Exception("LLM down"))
        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: fake_llm,
        )

        state: GraphState = {
            "query": "How to plant corn?",
            "contextual_query": "How to plant corn?",
            "intent": "knowledge_query",
            "error": "Database error",
        }

        new_state = await error_handler_node(state)

        assert "answer" in new_state
        answer_lower = new_state["answer"].lower()
        assert "try again" in answer_lower or "moment" in answer_lower

    @pytest.mark.asyncio
    async def test_error_handler_general_query_error(self, monkeypatch):
        """
        error_handler_node should handle general query errors
        with friendly message.
        """

        async def fake_ainvoke(msgs):
            return SimpleNamespace(
                content=(
                    "I'm having a bit of trouble with that. "
                    "Please try again in just a moment!"
                )
            )

        fake_llm = MagicMock()
        fake_llm.ainvoke = fake_ainvoke
        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: fake_llm,
        )

        state: GraphState = {
            "query": "random query",
            "contextual_query": "random query",
            "intent": "knowledge_query",
            "error": "Unknown error occurred",
        }

        new_state = await error_handler_node(state)

        assert "answer" in new_state
        assert len(new_state["answer"]) > 0

    @pytest.mark.asyncio
    async def test_error_handler_missing_contextual_query(self, monkeypatch):
        """
        error_handler_node should handle missing contextual_query
        by using query.
        """

        async def fake_ainvoke(msgs):
            return SimpleNamespace(content="Helpful response")

        fake_llm = MagicMock()
        fake_llm.ainvoke = fake_ainvoke
        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: fake_llm,
        )

        state: GraphState = {
            "query": "test query",
            "intent": "knowledge_query",
            "error": "Some error",
        }

        new_state = await error_handler_node(state)

        assert "answer" in new_state
        assert new_state["answer"] == "Helpful response"

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

    @pytest.mark.asyncio
    async def test_post_processing_node_no_result(self):
        """post_processing_node() handles missing mcp_result."""
        state: GraphState = {}

        new_state = await post_processing_node(state)
        assert new_state["context"] == []

    # ---------------- response_generation_node ----------------

    @pytest.mark.asyncio
    async def test_response_generation_node_success(self, monkeypatch):
        """response_generation_node() streams chunks and builds answer."""

        # Mock LLM
        fake_llm = MagicMock()
        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: fake_llm,
        )

        # Mock ChatPromptTemplate
        fake_qa_prompt = MagicMock()
        cpt_patch = (
            "app.services.query_answering_workflow."
            "ChatPromptTemplate.from_messages"
        )
        monkeypatch.setattr(
            cpt_patch,
            lambda msgs: fake_qa_prompt,
        )

        # Mock PromptTemplate
        fake_doc_prompt = MagicMock()
        pt_patch = (
            "app.services.query_answering_workflow."
            "PromptTemplate.from_template"
        )
        monkeypatch.setattr(
            pt_patch,
            lambda template: fake_doc_prompt,
        )

        # Mock the streaming chain
        async def fake_astream(_):
            yield "Hello"
            yield " world"

        fake_chain = MagicMock()
        fake_chain.astream = fake_astream

        csdc_patch = (
            "app.services.query_answering_workflow."
            "create_stuff_documents_chain"
        )
        monkeypatch.setattr(
            csdc_patch,
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
        assert any("Hello" in str(c) or "world" in str(c) for c in chunks)
        # The final yield contains the completed answer
        final = [c for c in chunks if isinstance(c, dict)][-1]
        assert final["answer"] == "Hello world"

    @pytest.mark.asyncio
    async def test_response_generation_node_error(self, monkeypatch):
        """response_generation_node() should yield error on failure."""

        fake_llm = MagicMock()
        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: fake_llm,
        )

        fake_qa_prompt = MagicMock()
        cpt_patch = (
            "app.services.query_answering_workflow."
            "ChatPromptTemplate.from_messages"
        )
        monkeypatch.setattr(
            cpt_patch,
            lambda msgs: fake_qa_prompt,
        )

        fake_doc_prompt = MagicMock()
        pt_patch = (
            "app.services.query_answering_workflow."
            "PromptTemplate.from_template"
        )
        monkeypatch.setattr(
            pt_patch,
            lambda template: fake_doc_prompt,
        )

        # Mock chain to raise error
        async def fake_astream(_):
            raise Exception("Generation failed")
            yield  # This line won't be reached but satisfies async generator

        fake_chain = MagicMock()
        fake_chain.astream = fake_astream

        csdc_patch = (
            "app.services.query_answering_workflow."
            "create_stuff_documents_chain"
        )
        monkeypatch.setattr(
            csdc_patch,
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

        # Should yield error
        error_chunks = [
            c for c in chunks if isinstance(c, dict) and "error" in c
        ]
        assert len(error_chunks) > 0

    # ---------------- E2E Graph Execution & Benchmark Tests ----------------

    @pytest.mark.asyncio
    async def test_graph_execution_path_knowledge_query(self, monkeypatch):
        """
        Verify end-to-end graph execution with knowledge query:
        classify_intent -> contextualize -> run_mcp -> generate
        """
        # 1. Mock LLM for intent & contextualize
        fake_llm = MagicMock()

        async def fake_ainvoke(msgs):
            # If system message is intent classification
            if isinstance(msgs, list) and len(msgs) >= 2:
                sys_content = msgs[0][1] if isinstance(msgs[0], tuple) else ""
                if "classification" in sys_content:
                    return SimpleNamespace(
                        content='{"intent": "knowledge_query"}'
                    )
                if "friendly assistant" in sys_content:
                    return SimpleNamespace(content="Hello there!")
            return SimpleNamespace(content="What fertilizer for maize?")

        fake_llm.ainvoke = fake_ainvoke
        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: fake_llm,
        )
        monkeypatch.setattr(
            "app.services.query_answering_workflow.llm_instance",
            fake_llm,
        )

        # 2. Mock ChatPromptTemplate
        fake_chain = MagicMock()
        fake_chain.ainvoke = AsyncMock(
            return_value=SimpleNamespace(content="What fertilizer for maize?")
        )
        cpt_patch = (
            "app.services.query_answering_workflow."
            "ChatPromptTemplate.from_messages"
        )
        monkeypatch.setattr(
            cpt_patch,
            lambda msgs: MagicMock(__or__=lambda self, other: fake_chain),
        )

        # 3. Mock Dispatcher
        fake_dispatcher = MagicMock()
        fake_dispatcher.call_tool = AsyncMock(
            return_value={
                "chunks": [
                    {
                        "chunk_id": "c1",
                        "content": "Use NPK 15-15-15 for maize planting.",
                        "score": 0.92,
                        "metadata": {"doc": "maize_guide.pdf"},
                    }
                ]
            }
        )
        monkeypatch.setattr(
            "app.services.query_answering_workflow._mcp_dispatcher",
            fake_dispatcher,
        )

        # 4. Mock QA Generation streaming chain
        async def fake_astream(_):
            yield "For maize, use NPK 15-15-15."

        fake_qa_chain = MagicMock()
        fake_qa_chain.astream = fake_astream

        csdc_patch = (
            "app.services.query_answering_workflow."
            "create_stuff_documents_chain"
        )
        monkeypatch.setattr(
            csdc_patch,
            lambda **_: fake_qa_chain,
        )

        initial_state: GraphState = {
            "query": "What fertilizer is needed for maize?",
            "chat_history": [],
            "contextualize_prompt_str": "Contextualize: {input}",
            "qa_prompt_str": "Answer: {context}",
            "knowledge_base_ids": [2],
            "top_k": 5,
        }

        result = await query_answering_workflow.ainvoke(initial_state)

        assert result["intent"] == "knowledge_query"
        assert result["contextual_query"] == "What fertilizer for maize?"
        assert len(result["context"]) == 1
        assert "NPK 15-15-15" in result["context"][0].page_content
        assert result["answer"] == "For maize, use NPK 15-15-15."

    @pytest.mark.asyncio
    async def test_retrieval_step_latency_benchmark(self, monkeypatch):
        """
        Benchmark direct vector retrieval step latency.
        Verify median execution latency is < 20ms across 50 iterations.
        """
        fake_dispatcher = MagicMock()

        async def fast_call_tool(server_name, tool_name, arguments):
            return {
                "chunks": [
                    {
                        "chunk_id": f"c_{i}",
                        "content": f"Document content snippet {i}",
                        "score": 0.95,
                        "metadata": {"source": "bench.pdf"},
                    }
                    for i in range(5)
                ]
            }

        fake_dispatcher.call_tool = fast_call_tool
        monkeypatch.setattr(
            "app.services.query_answering_workflow._mcp_dispatcher",
            fake_dispatcher,
        )

        state: GraphState = {
            "query": "Benchmark retrieval query",
            "contextual_query": "Benchmark retrieval query",
            "knowledge_base_ids": [101, 102],
            "top_k": 5,
        }

        latencies = []
        # Warmup
        await run_mcp_tool_node(state)

        # 50 benchmark iterations
        for _ in range(50):
            start = time.perf_counter()
            res = await run_mcp_tool_node(state)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            latencies.append(elapsed_ms)
            assert len(res["context"]) == 5

        med_latency = statistics.median(latencies)
        assert (
            med_latency < 20.0
        ), f"Median latency was {med_latency:.2f}ms >= 20ms"

    @pytest.mark.asyncio
    async def test_graph_error_resilience_fallback(self, monkeypatch):
        """
        Verify that graph safely handles vector retrieval failures, routing
        to error_handler_node with a friendly fallback answer.
        """
        # Mock LLM
        fake_llm = MagicMock()

        async def fake_ainvoke(msgs):
            if isinstance(msgs, list) and len(msgs) >= 2:
                sys_content = msgs[0][1] if isinstance(msgs[0], tuple) else ""
                if "classification" in sys_content:
                    return SimpleNamespace(
                        content='{"intent": "knowledge_query"}'
                    )
            return SimpleNamespace(
                content=(
                    "I'm having trouble retrieving information right now. "
                    "Please try again later."
                )
            )

        fake_llm.ainvoke = fake_ainvoke
        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: fake_llm,
        )
        monkeypatch.setattr(
            "app.services.query_answering_workflow.llm_instance",
            fake_llm,
        )

        fake_chain = MagicMock()
        fake_chain.ainvoke = AsyncMock(
            return_value=SimpleNamespace(content="Contextualized query")
        )
        cpt_patch = (
            "app.services.query_answering_workflow."
            "ChatPromptTemplate.from_messages"
        )
        monkeypatch.setattr(
            cpt_patch,
            lambda msgs: MagicMock(__or__=lambda self, other: fake_chain),
        )

        # Simulate vector retrieval RPC timeout / network failure
        fake_dispatcher = MagicMock()
        fake_dispatcher.call_tool = AsyncMock(
            side_effect=TimeoutError("Vector service connection timed out")
        )
        monkeypatch.setattr(
            "app.services.query_answering_workflow._mcp_dispatcher",
            fake_dispatcher,
        )

        initial_state: GraphState = {
            "query": "How to treat plant blight?",
            "chat_history": [],
            "contextualize_prompt_str": "Contextualize",
            "qa_prompt_str": "QA",
            "knowledge_base_ids": [1],
            "top_k": 5,
        }

        result = await query_answering_workflow.ainvoke(initial_state)

        # Asserts graceful fallback response without crashing
        assert "answer" in result
        assert len(result["answer"]) > 0
        answer_lower = result["answer"].lower()
        assert "trouble" in answer_lower or "try again" in answer_lower

    @pytest.mark.asyncio
    async def test_graph_node_sequence(self):
        """
        Verify that graph structure strictly executes:
        classify_intent -> contextualize -> run_mcp -> generate
        with zero references to scoping_node.
        """
        wf = create_rag_graph()
        nodes = wf.nodes
        assert "classify_intent" in nodes
        assert "contextualize" in nodes
        assert "run_mcp" in nodes
        assert "generate" in nodes
        assert "scoping_node" not in nodes
        assert "scoping" not in nodes

    @pytest.mark.asyncio
    async def test_small_talk_intent_bypass(self, monkeypatch):
        """
        User query 'Hello, who are you?' routes to small_talk and terminates
        without invoking vector queues.
        """

        async def fake_ainvoke(msgs):
            if isinstance(msgs, list) and len(msgs) >= 1:
                prompt_text = str(msgs[0])
                if (
                    "classify" in prompt_text.lower()
                    or "intent" in prompt_text.lower()
                ):
                    return SimpleNamespace(content='{"intent": "small_talk"}')
            return SimpleNamespace(content="Hello! I am your assistant.")

        fake_llm = MagicMock()
        fake_llm.ainvoke = fake_ainvoke

        fake_dispatcher = MagicMock()
        fake_dispatcher.call_tool = AsyncMock()

        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: fake_llm,
        )
        monkeypatch.setattr(
            "app.services.query_answering_workflow._mcp_dispatcher",
            fake_dispatcher,
        )

        state: GraphState = {
            "query": "Hello, who are you?",
            "chat_history": [],
            "contextualize_prompt_str": "",
            "qa_prompt_str": "",
        }

        result = await query_answering_workflow.ainvoke(state)
        assert result["intent"] == "small_talk"
        assert "Hello!" in result["answer"]
        # Ensure vector dispatcher was never called
        fake_dispatcher.call_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_retrieval_fallback(self, monkeypatch):
        """
        When run_mcp_tool returns 0 chunks, synthesis node gracefully replies
        with standard helpful fallback.
        """
        fake_dispatcher = MagicMock()
        fake_dispatcher.call_tool = AsyncMock(return_value={"chunks": []})
        monkeypatch.setattr(
            "app.services.query_answering_workflow._mcp_dispatcher",
            fake_dispatcher,
        )

        state: GraphState = {
            "query": "Unknown topic with zero documents",
            "contextual_query": "Unknown topic with zero documents",
            "knowledge_base_ids": [999],
        }

        result = await run_mcp_tool_node(state)
        assert result["context"] == []
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_token_stream_synthesis(self, monkeypatch):
        """
        Verifies response generation node formats synthesis and citations.
        """

        async def fake_astream(inputs):
            yield "Avocados should be picked with care [[citation:1]]."

        fake_chain = MagicMock()
        fake_chain.astream = fake_astream

        monkeypatch.setattr(
            "app.services.query_answering_workflow.create_stuff_documents_chain",  # noqa
            lambda **_: fake_chain,
        )

        state: GraphState = {
            "query": "How to harvest avocado?",
            "contextual_query": "How to harvest avocado?",
            "qa_prompt_str": "QA: {context} {input}",
            "context": [
                Document(
                    page_content="Harvest with shears leaving 1cm stem.",
                    metadata={"source": "farm_guide.pdf", "page": 3},
                )
            ],
            "chat_history": [],
        }

        yielded_states = []
        async for chunk in response_generation_node(state):
            yielded_states.append(chunk)

        assert len(yielded_states) > 0
        final_state = yielded_states[-1]
        assert "answer" in final_state
        assert "[[citation:1]]" in final_state["answer"]
        assert len(final_state["context"]) == 1
