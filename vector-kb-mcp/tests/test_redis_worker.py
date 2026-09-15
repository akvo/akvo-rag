import asyncio
import json
from unittest.mock import AsyncMock, patch
import pytest

from core.config import Settings
from main import VectorMCPWorker, main


@pytest.mark.asyncio
async def test_config_defaults():
    settings = Settings()
    assert settings.ENVIRONMENT == "development"
    assert settings.REQUEST_QUEUE == "mcp:vector:requests"
    assert settings.RESPONSE_PREFIX == "mcp:vector:responses"
    assert settings.RESPONSE_TTL_SECONDS == 60
    assert settings.CHROMA_HOST == "chromadb"
    assert settings.DEFAULT_EMBEDDING_MODEL == "text-embedding-3-small"


@pytest.mark.asyncio
async def test_worker_initialization_and_stubs(
    fake_redis, mock_chroma_client, mock_openai_client
):
    worker = VectorMCPWorker()
    worker.redis_client = fake_redis
    worker.chroma_client = mock_chroma_client
    worker.openai_client = mock_openai_client
    await worker.initialize(skip_connection_init=True)

    assert "query_knowledge_base" in worker.tool_handlers
    assert "list_knowledge_bases" in worker.tool_handlers
    assert "get_knowledge_base" in worker.tool_handlers
    assert "create_knowledge_base" in worker.tool_handlers
    assert "update_knowledge_base" in worker.tool_handlers
    assert "delete_knowledge_base" in worker.tool_handlers
    assert "list_documents" in worker.tool_handlers
    assert "get_document" in worker.tool_handlers
    assert "get_processing_tasks" in worker.tool_handlers

    # Test tool handlers directly
    res_kbs = await worker.tool_handlers["list_knowledge_bases"]({})
    assert "knowledge_bases" in res_kbs
    assert isinstance(res_kbs["knowledge_bases"], list)

    res_get_kb = await worker.tool_handlers["get_knowledge_base"](
        {"kb_id": 999999}
    )
    assert res_get_kb["knowledge_base"] is None

    res_create_kb = await worker.tool_handlers["create_knowledge_base"](
        {"name": "New KB Test"}
    )
    assert res_create_kb["status"] == "created"
    assert "knowledge_base" in res_create_kb
    created_id = res_create_kb["kb_id"]

    res_update_kb = await worker.tool_handlers["update_knowledge_base"](
        {"kb_id": created_id, "name": "Updated KB Test"}
    )
    assert res_update_kb["status"] == "updated"

    res_del_kb = await worker.tool_handlers["delete_knowledge_base"](
        {"kb_id": created_id}
    )
    assert res_del_kb == {"status": "deleted", "kb_id": created_id}

    res_docs = await worker.tool_handlers["list_documents"]({"kb_id": 999999})
    assert "documents" in res_docs
    assert isinstance(res_docs["documents"], list)

    res_doc = await worker.tool_handlers["get_document"]({"doc_id": 999999})
    assert res_doc["document"] is None

    res_tasks = await worker.tool_handlers["get_processing_tasks"]({})
    assert "tasks" in res_tasks
    assert isinstance(res_tasks["tasks"], list)


@pytest.mark.asyncio
async def test_worker_query_kb_uninitialized_retriever():
    worker = VectorMCPWorker()
    worker.retriever = None
    with pytest.raises(
        RuntimeError, match="ChromaRetriever is not initialized"
    ):
        await worker._handle_query_kb({"query": "test"})


@pytest.mark.asyncio
async def test_worker_rpc_query_kb_success(
    fake_redis, mock_chroma_client, mock_openai_client
):
    worker = VectorMCPWorker()
    worker.redis_client = fake_redis
    worker.chroma_client = mock_chroma_client
    worker.openai_client = mock_openai_client
    await worker.initialize(skip_connection_init=True)

    # Push request into Redis queue
    correlation_id = "req-uuid-1234"
    req_payload = {
        "correlation_id": correlation_id,
        "tool_name": "query_knowledge_base",
        "arguments": {
            "query": "document content",
            "kb_ids": [1],
            "top_k": 2,
        },
    }
    await fake_redis.rpush(
        worker.settings.REQUEST_QUEUE, json.dumps(req_payload)
    )

    # Process one message
    item = await fake_redis.blpop(worker.settings.REQUEST_QUEUE, timeout=1)
    assert item is not None
    _, raw_payload = item
    await worker._process_message(raw_payload)

    # Verify response on correlation key
    resp_key = f"{worker.settings.RESPONSE_PREFIX}:{correlation_id}"
    resp_raw = await fake_redis.lpop(resp_key)
    assert resp_raw is not None

    resp = json.loads(resp_raw)
    assert resp["status"] == "ok"
    assert "data" in resp
    assert "chunks" in resp["data"]
    assert len(resp["data"]["chunks"]) == 2
    assert resp["data"]["chunks"][0]["document_id"] == "doc-1"
    assert resp["data"]["chunks"][0]["score"] > 0


@pytest.mark.asyncio
async def test_worker_rpc_tool_alias(
    fake_redis, mock_chroma_client, mock_openai_client
):
    """Test compatibility with 'tool' key in addition to 'tool_name'."""
    worker = VectorMCPWorker()
    worker.redis_client = fake_redis
    worker.chroma_client = mock_chroma_client
    worker.openai_client = mock_openai_client
    await worker.initialize(skip_connection_init=True)

    correlation_id = "req-alias-123"
    req_payload = {
        "correlation_id": correlation_id,
        "tool": "list_knowledge_bases",
        "arguments": {},
    }
    await fake_redis.rpush(
        worker.settings.REQUEST_QUEUE, json.dumps(req_payload)
    )

    item = await fake_redis.blpop(worker.settings.REQUEST_QUEUE, timeout=1)
    _, raw_payload = item
    await worker._process_message(raw_payload)

    resp_key = f"{worker.settings.RESPONSE_PREFIX}:{correlation_id}"
    resp_raw = await fake_redis.lpop(resp_key)
    resp = json.loads(resp_raw)
    assert resp["status"] == "ok"
    assert "knowledge_bases" in resp["data"]
    assert isinstance(resp["data"]["knowledge_bases"], list)


@pytest.mark.asyncio
async def test_worker_rpc_unknown_tool(
    fake_redis, mock_chroma_client, mock_openai_client
):
    worker = VectorMCPWorker()
    worker.redis_client = fake_redis
    worker.chroma_client = mock_chroma_client
    worker.openai_client = mock_openai_client
    await worker.initialize(skip_connection_init=True)

    correlation_id = "req-unknown-tool"
    req_payload = {
        "correlation_id": correlation_id,
        "tool_name": "non_existent_tool_123",
        "arguments": {},
    }
    await worker._process_message(json.dumps(req_payload))

    resp_key = f"{worker.settings.RESPONSE_PREFIX}:{correlation_id}"
    resp_raw = await fake_redis.lpop(resp_key)
    assert resp_raw is not None
    resp = json.loads(resp_raw)
    assert resp["status"] == "error"
    assert "Unknown tool" in resp["error"]


@pytest.mark.asyncio
async def test_worker_rpc_missing_correlation_id(
    fake_redis, mock_chroma_client, mock_openai_client
):
    worker = VectorMCPWorker()
    worker.redis_client = fake_redis
    worker.chroma_client = mock_chroma_client
    worker.openai_client = mock_openai_client
    await worker.initialize(skip_connection_init=True)

    # Missing correlation_id
    req_payload = {
        "tool_name": "query_knowledge_base",
        "arguments": {},
    }
    # Should not crash, and should not push anywhere invalid
    await worker._process_message(json.dumps(req_payload))
    keys = await fake_redis.keys("*")
    assert len(keys) == 0


@pytest.mark.asyncio
async def test_worker_rpc_malformed_json(
    fake_redis, mock_chroma_client, mock_openai_client
):
    worker = VectorMCPWorker()
    worker.redis_client = fake_redis
    worker.chroma_client = mock_chroma_client
    worker.openai_client = mock_openai_client
    await worker.initialize(skip_connection_init=True)

    # Malformed JSON
    await worker._process_message("{invalid-json-string")
    keys = await fake_redis.keys("*")
    assert len(keys) == 0


@pytest.mark.asyncio
async def test_worker_rpc_handler_exception(
    fake_redis, mock_chroma_client, mock_openai_client
):
    worker = VectorMCPWorker()
    worker.redis_client = fake_redis
    worker.chroma_client = mock_chroma_client
    worker.openai_client = mock_openai_client
    await worker.initialize(skip_connection_init=True)

    # Force retriever to fail
    worker.retriever.search = AsyncMock(
        side_effect=RuntimeError("Chroma cluster unreachable")
    )

    correlation_id = "req-fail-123"
    req_payload = {
        "correlation_id": correlation_id,
        "tool_name": "query_knowledge_base",
        "arguments": {"query": "test", "kb_ids": [1]},
    }
    await worker._process_message(json.dumps(req_payload))

    resp_key = f"{worker.settings.RESPONSE_PREFIX}:{correlation_id}"
    resp_raw = await fake_redis.lpop(resp_key)
    assert resp_raw is not None
    resp = json.loads(resp_raw)
    assert resp["status"] == "error"
    assert "Chroma cluster unreachable" in resp["error"]


@pytest.mark.asyncio
async def test_worker_run_and_graceful_shutdown(
    fake_redis, mock_chroma_client, mock_openai_client
):
    worker = VectorMCPWorker()
    worker.redis_client = fake_redis
    worker.chroma_client = mock_chroma_client
    worker.openai_client = mock_openai_client
    await worker.initialize(skip_connection_init=True)

    # Start run task in background
    run_task = asyncio.create_task(worker.run())
    await asyncio.sleep(0.05)
    assert worker.running is True

    # Trigger shutdown
    await worker.shutdown()
    await asyncio.sleep(0.05)
    assert worker.running is False
    assert run_task.done() or run_task.cancelled()


@pytest.mark.asyncio
async def test_worker_run_no_redis():
    worker = VectorMCPWorker()
    worker.redis_client = None
    # Should exit loop immediately without crashing
    await worker.run()
    assert worker.running is True


def test_main_entrypoint():
    with patch(
        "main.VectorMCPWorker.initialize", new_callable=AsyncMock
    ) as mock_init, patch(
        "main.VectorMCPWorker.run", new_callable=AsyncMock
    ) as mock_run:
        main()
        mock_init.assert_awaited_once()
        mock_run.assert_awaited_once()
