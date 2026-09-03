import asyncio
import json
from unittest.mock import AsyncMock, patch
import fakeredis.aioredis as fake_aioredis
import httpx
import pytest

from app.core.mcp_config import (
    BaseServerConfig,
    InputSchema,
    MCPConfig,
    MCPToolDefinition,
)
from mcp_clients.exceptions import (
    MCPConfigurationError,
    MCPTimeoutError,
    MCPToolExecutionError,
)
from mcp_clients.queue_dispatcher import MCPQueueDispatcher


@pytest.fixture
def fake_redis():
    """Isolated fake async Redis instance with decoded responses."""
    return fake_aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def mcp_config():
    """Loads declarative mcp_config.json for test executions."""
    return MCPConfig.load_from_file("mcp_config.json")


@pytest.fixture
def dispatcher(mcp_config, fake_redis):
    """MCPQueueDispatcher instance with injected config and fake Redis."""
    return MCPQueueDispatcher(config=mcp_config, redis_client=fake_redis)


@pytest.mark.asyncio
async def test_redis_queue_rpc_happy_path(dispatcher, fake_redis):
    """Test full Redis Request-Reply flow with correlation ID."""

    async def mock_worker():
        # Pop request from the request queue
        res = await fake_redis.blpop("mcp:vector:requests", timeout=5)
        assert res is not None
        _, raw_payload = res
        payload = json.loads(raw_payload)

        assert payload["tool"] == "query_knowledge_base"
        assert payload["arguments"]["query"] == "water sanitation guidelines"
        assert "correlation_id" in payload
        assert "response_queue" in payload

        # Send successful response
        response_payload = {
            "status": "ok",
            "data": {
                "chunks": [
                    {
                        "chunk_id": "chk-001",
                        "content": (
                            "SOP for handpump maintenance and chlorination."
                        ),
                        "score": 0.94,
                    }
                ]
            },
        }
        await fake_redis.rpush(
            payload["response_queue"], json.dumps(response_payload)
        )

    # Spawn worker task
    worker_task = asyncio.create_task(mock_worker())

    result = await dispatcher.call_tool(
        server_name="knowledge_bases_mcp",
        tool_name="query_knowledge_base",
        arguments={
            "query": "water sanitation guidelines",
            "knowledge_base_ids": [1],
        },
        timeout=5.0,
    )

    await worker_task

    assert "chunks" in result
    assert len(result["chunks"]) == 1
    assert result["chunks"][0]["chunk_id"] == "chk-001"
    assert "SOP for handpump" in result["chunks"][0]["content"]


@pytest.mark.asyncio
async def test_redis_queue_rpc_timeout(dispatcher, fake_redis):
    """Test that Redis RPC raises MCPTimeoutError on worker timeout."""
    with pytest.raises(MCPTimeoutError) as exc_info:
        await dispatcher.call_tool(
            server_name="knowledge_bases_mcp",
            tool_name="query_knowledge_base",
            arguments={
                "query": "test query timeout",
                "knowledge_base_ids": [1],
            },
            timeout=1.0,
        )

    assert "timed out after 1.0s" in str(exc_info.value)
    assert "corr_id:" in str(exc_info.value)


@pytest.mark.asyncio
async def test_redis_queue_rpc_remote_error(dispatcher, fake_redis):
    """Test that remote worker error status raises MCPToolExecutionError."""

    async def mock_error_worker():
        res = await fake_redis.blpop("mcp:vector:requests", timeout=5)
        assert res is not None
        _, raw_payload = res
        payload = json.loads(raw_payload)

        # Worker responds with error
        error_payload = {
            "status": "error",
            "error": "Knowledge base ID 999 does not exist.",
        }
        await fake_redis.rpush(
            payload["response_queue"], json.dumps(error_payload)
        )

    worker_task = asyncio.create_task(mock_error_worker())

    with pytest.raises(MCPToolExecutionError) as exc_info:
        await dispatcher.call_tool(
            server_name="knowledge_bases_mcp",
            tool_name="query_knowledge_base",
            arguments={"query": "test query", "knowledge_base_ids": [999]},
            timeout=5.0,
        )

    await worker_task
    assert "Knowledge base ID 999 does not exist." in str(exc_info.value)


@pytest.mark.asyncio
async def test_redis_queue_response_cleanup(dispatcher, fake_redis):
    """Verify that temporary response queue keys are cleaned up in Redis."""

    async def mock_worker():
        res = await fake_redis.blpop("mcp:vector:requests", timeout=5)
        _, raw_payload = res
        payload = json.loads(raw_payload)
        resp_q = payload["response_queue"]

        await fake_redis.rpush(
            resp_q,
            json.dumps({"status": "ok", "data": {"status": "ACTIVE"}}),
        )
        return resp_q

    worker_task = asyncio.create_task(mock_worker())

    result = await dispatcher.call_tool(
        server_name="knowledge_bases_mcp",
        tool_name="get_knowledge_base",
        arguments={"knowledge_base_id": 1},
        timeout=5.0,
    )

    resp_queue = await worker_task
    assert result == {"status": "ACTIVE"}

    # Assert that the response queue was deleted from Redis
    assert not await fake_redis.exists(resp_queue)


@pytest.mark.asyncio
async def test_rest_transport_dispatch_success(dispatcher):
    """Test successful REST tool invocation with mock HTTP client."""
    mock_response = httpx.Response(
        status_code=200,
        json={
            "latitude": -1.286389,
            "longitude": 36.817223,
            "current": {"temperature_2m": 22.5, "weather_code": 1},
        },
        request=httpx.Request(
            "POST", "http://localhost:8080/weather/forecast"
        ),
    )

    with patch.object(
        httpx.AsyncClient, "request", new_callable=AsyncMock
    ) as mock_req:
        mock_req.return_value = mock_response

        result = await dispatcher.call_tool(
            server_name="weather_mcp",
            tool_name="get_weather_forecast",
            arguments={"latitude": -1.286389, "longitude": 36.817223},
        )

        assert result["latitude"] == -1.286389
        assert result["current"]["temperature_2m"] == 22.5
        mock_req.assert_awaited_once()


@pytest.mark.asyncio
async def test_rest_transport_timeout(dispatcher):
    """Test REST tool invocation timeout raises MCPTimeoutError."""
    with patch.object(
        httpx.AsyncClient, "request", new_callable=AsyncMock
    ) as mock_req:
        mock_req.side_effect = httpx.TimeoutException("Read timeout")

        with pytest.raises(MCPTimeoutError) as exc_info:
            await dispatcher.call_tool(
                server_name="weather_mcp",
                tool_name="get_weather_forecast",
                arguments={"latitude": 0.0, "longitude": 0.0},
                timeout=2.0,
            )

        assert "timed out after 2.0s" in str(exc_info.value)


@pytest.mark.asyncio
async def test_rest_transport_http_status_error(dispatcher):
    """
    Test REST tool invocation with 502 error raises MCPToolExecutionError.
    """
    mock_response = httpx.Response(
        status_code=502,
        text="Bad Gateway",
        request=httpx.Request(
            "POST", "http://localhost:8080/weather/forecast"
        ),
    )

    with patch.object(
        httpx.AsyncClient, "request", new_callable=AsyncMock
    ) as mock_req:
        mock_req.side_effect = httpx.HTTPStatusError(
            "Bad Gateway",
            request=mock_response.request,
            response=mock_response,
        )

        with pytest.raises(MCPToolExecutionError) as exc_info:
            await dispatcher.call_tool(
                server_name="weather_mcp",
                tool_name="get_weather_forecast",
                arguments={"latitude": 0.0, "longitude": 0.0},
            )

        assert "HTTP error 502" in str(exc_info.value)


@pytest.mark.asyncio
async def test_rest_transport_generic_error(dispatcher):
    """Test REST invocation with network error raises MCPToolExecutionError."""
    with patch.object(
        httpx.AsyncClient, "request", new_callable=AsyncMock
    ) as mock_req:
        mock_req.side_effect = httpx.ConnectError("Failed to connect to host")

        with pytest.raises(MCPToolExecutionError) as exc_info:
            await dispatcher.call_tool(
                server_name="weather_mcp",
                tool_name="get_weather_forecast",
                arguments={"latitude": 0.0, "longitude": 0.0},
            )

        assert "Failed to execute REST tool" in str(exc_info.value)


@pytest.mark.asyncio
async def test_unconfigured_server_error(dispatcher):
    """Test that requesting an unknown server raises MCPConfigurationError."""
    with pytest.raises(MCPConfigurationError) as exc_info:
        await dispatcher.call_tool(
            server_name="unknown_server_xyz",
            tool_name="query_knowledge_base",
            arguments={},
        )

    assert (
        "Server 'unknown_server_xyz' not configured in mcp_config.json"
        in str(exc_info.value)
    )


@pytest.mark.asyncio
async def test_undefined_tool_error(dispatcher):
    """Test that requesting an undefined tool raises MCPConfigurationError."""
    with pytest.raises(MCPConfigurationError) as exc_info:
        await dispatcher.call_tool(
            server_name="knowledge_bases_mcp",
            tool_name="non_existent_tool_abc",
            arguments={},
        )

    expected_msg = (
        "Tool 'non_existent_tool_abc' not defined for server "
        "'knowledge_bases_mcp'"
    )
    assert expected_msg in str(exc_info.value)


@pytest.mark.asyncio
async def test_unsupported_transport_error(dispatcher):
    """Test that an unhandled transport raises MCPConfigurationError."""

    class MockCustomServer(BaseServerConfig):
        transport: str = "grpc"

    custom_server = MockCustomServer(
        name="Custom gRPC Server",
        timeout_seconds=10,
        tools=[
            MCPToolDefinition(
                name="custom_tool",
                description="test",
                inputSchema=InputSchema(),
            )
        ],
    )
    dispatcher.config.servers["grpc_server"] = custom_server

    with pytest.raises(MCPConfigurationError) as exc_info:
        await dispatcher.call_tool(
            server_name="grpc_server",
            tool_name="custom_tool",
            arguments={},
        )

    assert "Unsupported transport: grpc" in str(exc_info.value)


@pytest.mark.asyncio
async def test_dispatcher_close_cleanup(dispatcher):
    """Test that close() cleanly closes Redis and HTTP client instances."""
    redis = await dispatcher.get_redis()
    http_client = await dispatcher.get_http_client()

    assert redis is not None
    assert http_client is not None
    assert not http_client.is_closed

    await dispatcher.close()

    assert http_client.is_closed
