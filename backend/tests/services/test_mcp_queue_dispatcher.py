import asyncio
import json
from unittest.mock import AsyncMock, patch
import httpx
import pytest

from mcp_clients.exceptions import (
    MCPConfigurationError,
    MCPTimeoutError,
    MCPToolExecutionError,
)


@pytest.mark.unit
async def test_successful_redis_rpc_call(mcp_dispatcher, fake_redis):
    """Test full Redis Request-Reply flow with correlation ID."""

    async def mock_worker():
        res = await fake_redis.blpop("mcp:vector:requests", timeout=5)
        assert res is not None
        _, raw_payload = res
        payload = json.loads(raw_payload)

        assert payload["tool"] == "query_knowledge_base"
        assert payload["arguments"]["query"] == "water sanitation guidelines"
        assert "correlation_id" in payload
        assert "response_queue" in payload

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

    worker_task = asyncio.create_task(mock_worker())

    result = await mcp_dispatcher.call_tool(
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


@pytest.mark.unit
async def test_redis_rpc_timeout_handling(mcp_dispatcher, fake_redis):
    """Test that Redis RPC raises MCPTimeoutError on worker timeout."""
    with pytest.raises(MCPTimeoutError) as exc_info:
        await mcp_dispatcher.call_tool(
            server_name="knowledge_bases_mcp",
            tool_name="query_knowledge_base",
            arguments={"query": "timeout test"},
            timeout=0.05,
        )

    assert "timed out" in str(exc_info.value).lower()
    assert exc_info.value.server_name == "knowledge_bases_mcp"
    assert exc_info.value.tool_name == "query_knowledge_base"


@pytest.mark.unit
async def test_worker_error_propagation(mcp_dispatcher, fake_redis):
    """Test that worker-returned error raises MCPToolExecutionError."""

    async def mock_error_worker():
        res = await fake_redis.blpop("mcp:vector:requests", timeout=5)
        assert res is not None
        _, raw_payload = res
        payload = json.loads(raw_payload)

        response_payload = {
            "status": "error",
            "error": "ChromaDB connection lost",
        }
        await fake_redis.rpush(
            payload["response_queue"], json.dumps(response_payload)
        )

    worker_task = asyncio.create_task(mock_error_worker())

    with pytest.raises(MCPToolExecutionError) as exc_info:
        await mcp_dispatcher.call_tool(
            server_name="knowledge_bases_mcp",
            tool_name="query_knowledge_base",
            arguments={"query": "error test"},
            timeout=5.0,
        )

    await worker_task
    assert "ChromaDB connection lost" in str(exc_info.value)
    assert exc_info.value.server_name == "knowledge_bases_mcp"


@pytest.mark.unit
async def test_redis_queue_response_cleanup(mcp_dispatcher, fake_redis):
    """Test that temporary response key is cleaned up after reading."""

    async def mock_worker():
        res = await fake_redis.blpop("mcp:vector:requests", timeout=5)
        _, raw_payload = res
        payload = json.loads(raw_payload)
        resp = {"status": "ok", "data": {"result": "success"}}
        await fake_redis.rpush(payload["response_queue"], json.dumps(resp))
        return payload["response_queue"]

    worker_task = asyncio.create_task(mock_worker())
    _ = await mcp_dispatcher.call_tool(
        server_name="knowledge_bases_mcp",
        tool_name="list_knowledge_bases",
        arguments={},
        timeout=5.0,
    )
    response_queue = await worker_task

    exists = await fake_redis.exists(response_queue)
    assert exists == 0, f"Temporary queue {response_queue} was not cleaned up"


@pytest.mark.unit
async def test_rest_transport_dispatch_success(mcp_dispatcher):
    """Test REST HTTP dispatch using mock HTTP client."""
    req = httpx.Request("POST", "http://localhost:8080/weather/forecast")
    mock_response = httpx.Response(
        status_code=200,
        json={
            "latitude": -6.2,
            "longitude": 106.8,
            "forecast": "Scattered showers",
        },
        request=req,
    )

    with patch.object(
        mcp_dispatcher.http_client,
        "request",
        new=AsyncMock(return_value=mock_response),
    ) as mock_req:
        result = await mcp_dispatcher.call_tool(
            server_name="weather_mcp",
            tool_name="get_weather_forecast",
            arguments={
                "latitude": -6.2,
                "longitude": 106.8,
                "start_date": "2026-09-01",
                "end_date": "2026-09-07",
            },
        )

        assert result["forecast"] == "Scattered showers"
        assert result["latitude"] == -6.2
        mock_req.assert_called_once()


@pytest.mark.unit
async def test_rest_transport_timeout(mcp_dispatcher):
    """Test REST HTTP timeout raises MCPTimeoutError."""
    with patch.object(
        mcp_dispatcher.http_client,
        "request",
        new=AsyncMock(
            side_effect=httpx.TimeoutException("Connection timed out")
        ),
    ):
        with pytest.raises(MCPTimeoutError) as exc_info:
            await mcp_dispatcher.call_tool(
                server_name="weather_mcp",
                tool_name="get_weather_forecast",
                arguments={"latitude": 0.0, "longitude": 0.0},
            )

        assert "timed out" in str(exc_info.value).lower()
        assert exc_info.value.server_name == "weather_mcp"


@pytest.mark.unit
async def test_rest_transport_http_status_error(mcp_dispatcher):
    """Test non-200 HTTP response raises MCPToolExecutionError."""
    req = httpx.Request("POST", "http://localhost:8080/weather/forecast")
    mock_response = httpx.Response(
        status_code=500,
        text="Internal Server Error from upstream Open-Meteo",
        request=req,
    )

    with patch.object(
        mcp_dispatcher.http_client,
        "request",
        new=AsyncMock(return_value=mock_response),
    ):
        with pytest.raises(MCPToolExecutionError) as exc_info:
            await mcp_dispatcher.call_tool(
                server_name="weather_mcp",
                tool_name="get_weather_forecast",
                arguments={"latitude": 0.0, "longitude": 0.0},
            )

        assert "500" in str(exc_info.value)


@pytest.mark.unit
async def test_unconfigured_server_error(mcp_dispatcher):
    """Test calling an unconfigured server raises MCPConfigurationError."""
    with pytest.raises(MCPConfigurationError) as exc_info:
        await mcp_dispatcher.call_tool(
            server_name="unknown_server_name",
            tool_name="some_tool",
            arguments={},
        )
    assert "not configured" in str(exc_info.value).lower()


@pytest.mark.unit
async def test_undefined_tool_error(mcp_dispatcher):
    """Test calling an unconfigured tool raises MCPConfigurationError."""
    with pytest.raises(MCPConfigurationError) as exc_info:
        await mcp_dispatcher.call_tool(
            server_name="knowledge_bases_mcp",
            tool_name="undefined_tool_name",
            arguments={},
        )
    assert "not defined for server" in str(exc_info.value)


@pytest.mark.unit
async def test_dispatcher_close_cleanup(mcp_dispatcher):
    """Test that close() cleans up HTTP and Redis connections."""
    mcp_dispatcher.redis_client.aclose = AsyncMock()
    mcp_dispatcher.http_client.aclose = AsyncMock()

    await mcp_dispatcher.close()
    mcp_dispatcher.redis_client.aclose.assert_called_once()
    mcp_dispatcher.http_client.aclose.assert_called_once()
