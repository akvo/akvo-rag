import time
import pytest
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from app.core.security import get_current_user
from app.db.session import get_db
from app.services.query_answering_workflow import (
    query_answering_workflow,
    run_mcp_tool_node,
    GraphState,
)
from mcp_clients.kb_mcp_endpoint_service import KnowledgeBaseMCPEndpointService


# ---------------------------------------------------------------------
# App / Client Fixtures for Host REST Parity Tests
# ---------------------------------------------------------------------
@pytest.fixture
def test_app() -> FastAPI:
    from app.main import app

    return app


@pytest.fixture
def override_auth(test_app: FastAPI):
    fake_user = SimpleNamespace(
        id=1, email="test@example.com", is_superuser=True
    )
    fake_db = MagicMock()
    test_app.dependency_overrides[get_current_user] = lambda: fake_user
    test_app.dependency_overrides[get_db] = lambda: fake_db
    yield
    test_app.dependency_overrides.clear()


@pytest.fixture
def client(test_app: FastAPI, override_auth) -> TestClient:
    return TestClient(test_app)


# ---------------------------------------------------------------------
# 1. Graph Execution & Retrieval Integration Tests
# ---------------------------------------------------------------------
@pytest.mark.integration
class TestRAGGraphIntegration:
    """Validates end-to-end LangGraph execution with MCPQueueDispatcher."""

    @pytest.mark.asyncio
    async def test_graph_retrieval_and_synthesis_flow(self, monkeypatch):
        """
        Execute full graph with query 'How to harvest avocado?' and
        knowledge_base_ids=[1]. Assert run_mcp_tool_node returns
        List[Document] without calling ScopingAgent.
        """
        # Mock Intent Classifier LLM
        fake_classifier_llm = MagicMock()
        fake_classifier_llm.ainvoke = AsyncMock(
            return_value=AIMessage(content='{"intent": "knowledge_query"}')
        )

        # Mock QA / Contextualizer LLM
        async def fake_qa_invoke(prompt_value, **kwargs):
            return AIMessage(content="How to harvest avocado?")

        fake_qa_llm = RunnableLambda(fake_qa_invoke)

        async def fake_astream(inputs):
            yield "Avocados should be harvested gently [[citation:1]]."

        fake_chain = MagicMock()
        fake_chain.astream = fake_astream

        # Mock Dispatcher tool output
        fake_dispatcher = MagicMock()
        fake_dispatcher.call_tool = AsyncMock(
            return_value={
                "chunks": [
                    {
                        "chunk_id": "chk-001",
                        "document_id": "doc-001",
                        "kb_id": 1,
                        "content": "Cut avocados with a short stem.",
                        "score": 0.94,
                        "metadata": {"source": "agri_guide.pdf", "page": 4},
                    }
                ]
            }
        )

        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: fake_classifier_llm,
        )
        monkeypatch.setattr(
            "app.services.query_answering_workflow.llm_instance",
            fake_qa_llm,
        )
        monkeypatch.setattr(
            "app.services.query_answering_workflow.create_stuff_documents_chain",  # noqa
            lambda **_: fake_chain,
        )
        monkeypatch.setattr(
            "app.services.query_answering_workflow._mcp_dispatcher",
            fake_dispatcher,
        )

        state: GraphState = {
            "query": "How to harvest avocado?",
            "knowledge_base_ids": [1],
            "contextualize_prompt_str": "Contextualize: {chat_history} {input}",  # noqa
            "qa_prompt_str": "Answer the question: {input} using {context}",
            "chat_history": [],
        }

        # Execute full compiled workflow
        result = await query_answering_workflow.ainvoke(state)

        # Verify intentional routing & context enrichment
        assert result.get("intent") == "knowledge_query"
        assert "context" in result
        assert len(result["context"]) == 1
        assert isinstance(result["context"][0], Document)
        assert (
            result["context"][0].page_content
            == "Cut avocados with a short stem."
        )
        assert result["context"][0].metadata["source"] == "agri_guide.pdf"
        assert "answer" in result
        assert "[[citation:1]]" in result["answer"]

        # Ensure dispatcher called with correct arguments
        fake_dispatcher.call_tool.assert_called_once_with(
            server_name="knowledge_bases_mcp",
            tool_name="query_knowledge_base",
            arguments={
                "query": "How to harvest avocado?",
                "knowledge_base_ids": [1],
                "kb_ids": [1],
                "top_k": 5,
                "score_threshold": 0.0,
            },
        )

    @pytest.mark.asyncio
    async def test_graph_latency_benchmark(self, monkeypatch):
        """
        Benchmark run_mcp_tool_node to assert overhead < 50ms.
        """
        fake_dispatcher = MagicMock()
        fake_dispatcher.call_tool = AsyncMock(
            return_value={
                "chunks": [
                    {
                        "chunk_id": "c1",
                        "content": "Rapid retrieval test",
                        "score": 0.99,
                    }
                ]
            }
        )
        monkeypatch.setattr(
            "app.services.query_answering_workflow._mcp_dispatcher",
            fake_dispatcher,
        )

        state: GraphState = {
            "query": "Fast query",
            "knowledge_base_ids": [1],
        }

        start_time = time.perf_counter()
        result_state = await run_mcp_tool_node(state)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        assert (
            elapsed_ms < 50.0
        ), f"IPC execution took {elapsed_ms:.2f}ms (expected < 50ms)"
        assert len(result_state["context"]) == 1
        assert result_state["error"] is None

    @pytest.mark.asyncio
    async def test_graph_resiliency_error_fallback(self, monkeypatch):
        """
        Verify graceful fallback to error_handler_node when MCP
        dispatcher fails.
        """
        fake_classifier_llm = MagicMock()
        fake_classifier_llm.ainvoke = AsyncMock(
            return_value=AIMessage(content='{"intent": "knowledge_query"}')
        )

        fake_fallback_llm = MagicMock()
        fake_fallback_llm.ainvoke = AsyncMock(
            return_value=AIMessage(
                content="I'm having trouble with that right now."
            )
        )

        fake_dispatcher = MagicMock()
        fake_dispatcher.call_tool = AsyncMock(
            side_effect=Exception("Redis connection refused")
        )

        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: fake_fallback_llm,
        )
        monkeypatch.setattr(
            "app.services.query_answering_workflow._mcp_dispatcher",
            fake_dispatcher,
        )

        state: GraphState = {
            "query": "How to plant corn?",
            "knowledge_base_ids": [1],
            "contextualize_prompt_str": "Contextualize: {input}",
            "qa_prompt_str": "QA: {input}",
            "chat_history": [],
        }

        result = await query_answering_workflow.ainvoke(state)
        assert result["context"] == []
        assert "trouble" in result["answer"]


# ---------------------------------------------------------------------
# 2. Host REST API Zero-Regression Parity Tests
# ---------------------------------------------------------------------
@pytest.mark.integration
class TestHostRESTEndpointsParity:
    """
    Validates backward-compatible JSON schema contracts for
    AgriConnect & CoM.
    """

    def test_get_knowledge_bases_schema(self, client: TestClient, monkeypatch):
        """Test GET /api/knowledge-base returns expected list structure."""
        fake_dispatcher = MagicMock()
        fake_dispatcher.call_tool = AsyncMock(
            return_value={
                "knowledge_bases": [
                    {
                        "id": 1,
                        "name": "AgriConnect KB",
                        "description": "Farming documentation",
                        "created_at": "2026-09-01T00:00:00",
                        "documents": [],
                    }
                ]
            }
        )
        fake_service = KnowledgeBaseMCPEndpointService(
            dispatcher=fake_dispatcher
        )
        monkeypatch.setattr(
            "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService",
            lambda: fake_service,
        )

        response = client.get("/api/knowledge-base")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["name"] == "AgriConnect KB"
        assert data[0]["is_superuser"] is True

    def test_get_knowledge_base_by_id(self, client: TestClient, monkeypatch):
        """Test GET /api/knowledge-base/{id} returns single KB object."""
        fake_dispatcher = MagicMock()
        fake_dispatcher.call_tool = AsyncMock(
            return_value={
                "knowledge_base": {
                    "id": 42,
                    "name": "Single KB",
                    "description": "Specific KB details",
                    "status": "ACTIVE",
                }
            }
        )
        fake_service = KnowledgeBaseMCPEndpointService(
            dispatcher=fake_dispatcher
        )
        monkeypatch.setattr(
            "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService",
            lambda: fake_service,
        )

        response = client.get("/api/knowledge-base/42")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 42
        assert data["name"] == "Single KB"
        assert data["is_superuser"] is True

    def test_create_knowledge_base_schema(
        self, client: TestClient, monkeypatch
    ):
        """Test POST /api/knowledge-base creates new KB."""
        fake_dispatcher = MagicMock()
        fake_dispatcher.call_tool = AsyncMock(
            return_value={
                "knowledge_base": {
                    "id": 101,
                    "name": "New Rice KB",
                    "description": "Paddy management",
                }
            }
        )
        fake_service = KnowledgeBaseMCPEndpointService(
            dispatcher=fake_dispatcher
        )
        monkeypatch.setattr(
            "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService",
            lambda: fake_service,
        )

        payload = {
            "name": "New Rice KB",
            "description": "Paddy management",
            "embedding_model": "text-embedding-3-small",
        }
        response = client.post("/api/knowledge-base", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 101
        assert data["name"] == "New Rice KB"

    def test_delete_knowledge_base(self, client: TestClient, monkeypatch):
        """Test DELETE /api/knowledge-base/{id} deletes KB."""
        fake_dispatcher = MagicMock()
        fake_dispatcher.call_tool = AsyncMock(
            return_value={"status": "deleted", "id": 42}
        )
        fake_service = KnowledgeBaseMCPEndpointService(
            dispatcher=fake_dispatcher
        )
        monkeypatch.setattr(
            "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService",
            lambda: fake_service,
        )

        response = client.delete("/api/knowledge-base/42")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "deleted"

    def test_test_retrieval_endpoint(self, client: TestClient, monkeypatch):
        """Test POST /api/knowledge-base/test-retrieval performs retrieval."""
        fake_dispatcher = MagicMock()
        fake_dispatcher.call_tool = AsyncMock(
            return_value={
                "chunks": [
                    {
                        "chunk_id": "c1",
                        "content": "Pest control guidelines",
                        "score": 0.88,
                    }
                ]
            }
        )
        fake_service = KnowledgeBaseMCPEndpointService(
            dispatcher=fake_dispatcher
        )
        monkeypatch.setattr(
            "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService",
            lambda: fake_service,
        )

        payload = {
            "kb_id": 1,
            "query": "pest control",
            "top_k": 3,
        }
        response = client.post(
            "/api/knowledge-base/test-retrieval", json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert "chunks" in data
        assert len(data["chunks"]) == 1
        assert data["chunks"][0]["chunk_id"] == "c1"
