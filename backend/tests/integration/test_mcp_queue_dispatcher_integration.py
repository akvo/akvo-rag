import os
import pytest
import redis.asyncio as aioredis

from app.core.mcp_config import MCPConfig
from mcp_clients.queue_dispatcher import MCPQueueDispatcher


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_vector_kb_microservice_integration():
    """
    Verify MCPQueueDispatcher communicates with live vector-kb-mcp worker
    running in Docker over Redis broker.
    """
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    real_redis = aioredis.from_url(
        redis_url, decode_responses=True, max_connections=5
    )

    # Verify live broker connectivity
    assert await real_redis.ping() is True

    config = MCPConfig.load_from_file("mcp_config.json")
    dispatcher = MCPQueueDispatcher(config=config, redis_client=real_redis)

    # 1. Test create_knowledge_base RPC against live container
    create_result = await dispatcher.call_tool(
        server_name="knowledge_bases_mcp",
        tool_name="create_knowledge_base",
        arguments={
            "name": "Integration Test KB",
            "description": "Integration test created KB",
        },
        timeout=10.0,
    )
    assert create_result.get("status") == "created"
    created_id = create_result.get("kb_id")
    assert created_id is not None

    try:
        # 2. Test get_knowledge_base RPC against live container
        kb_result = await dispatcher.call_tool(
            server_name="knowledge_bases_mcp",
            tool_name="get_knowledge_base",
            arguments={"kb_id": created_id},
            timeout=10.0,
        )
        assert "knowledge_base" in kb_result
        assert kb_result["knowledge_base"]["name"] == "Integration Test KB"

        # 3. Test list_knowledge_bases RPC against live container
        list_result = await dispatcher.call_tool(
            server_name="knowledge_bases_mcp",
            tool_name="list_knowledge_bases",
            arguments={},
            timeout=10.0,
        )
        assert "knowledge_bases" in list_result
        assert isinstance(list_result["knowledge_bases"], list)
    finally:
        # 4. Clean up created test KB
        await dispatcher.call_tool(
            server_name="knowledge_bases_mcp",
            tool_name="delete_knowledge_base",
            arguments={"kb_id": created_id},
            timeout=10.0,
        )

    await dispatcher.close()
