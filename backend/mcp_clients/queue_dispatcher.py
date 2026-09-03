import asyncio
import json
import logging
from typing import Any, Dict, Optional
import uuid

import httpx
import redis.asyncio as aioredis

from app.core.config import settings
from app.core.mcp_config import (
    MCPConfig,
    MCPToolDefinition,
    RedisQueueServerConfig,
    RestServerConfig,
)
from mcp_clients.exceptions import (
    MCPConfigurationError,
    MCPTimeoutError,
    MCPToolExecutionError,
)

logger = logging.getLogger("mcp_dispatcher")


class MCPQueueDispatcher:
    """
    Unified high-performance MCP tool dispatcher supporting:
    1. Native async Redis Request-Reply queues (for internal microservices)
    2. Standard Async HTTP REST requests (for external tool providers)
    """

    def __init__(
        self,
        config: Optional[MCPConfig] = None,
        redis_client: Optional[aioredis.Redis] = None,
    ):
        self.config = config or MCPConfig.load_from_file()
        self._redis = redis_client
        self._http_client: Optional[httpx.AsyncClient] = None

    @property
    def redis_client(self) -> Optional[aioredis.Redis]:
        """Expose current Redis client instance."""
        return self._redis

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Expose current shared async HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def get_redis(self) -> aioredis.Redis:
        """Lazily initialize Redis connection pool."""
        if self._redis is None:
            self._redis = aioredis.from_url(
                settings.REDIS_URL, decode_responses=True, max_connections=20
            )
        return self._redis

    async def get_http_client(self) -> httpx.AsyncClient:
        """Lazily initialize shared async HTTP client."""
        return self.http_client

    async def close(self):
        """Cleanly close all open network and broker connections."""
        if self._redis is not None:
            if hasattr(self._redis, "aclose"):
                await self._redis.aclose()
            elif hasattr(self._redis, "close"):
                res = self._redis.close()
                if asyncio.iscoroutine(res):
                    await res
        if self._http_client is not None and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Dispatches a tool call to the appropriate transport.

        Args:
            server_name: Server namespace
            ('knowledge_bases_mcp', 'weather_mcp')
            tool_name: Specific tool name (e.g. 'query_knowledge_base')
            arguments: Dictionary of parameters matching tool inputSchema
            timeout: Optional override for operation timeout in seconds

        Returns:
            Dictionary containing the tool execution output data.

        Raises:
            MCPConfigurationError: Unknown server, tool, or transport.
            MCPTimeoutError: Timeout occurred while awaiting reply.
            MCPToolExecutionError: Remote execution failed or returned error.
        """
        server = self.config.servers.get(server_name)
        if not server:
            raise MCPConfigurationError(
                f"Server '{server_name}' not configured in mcp_config.json",
                server_name=server_name,
                tool_name=tool_name,
            )

        tool_def = self.config.get_tool(server_name, tool_name)
        if not tool_def:
            raise MCPConfigurationError(
                f"Tool '{tool_name}' not defined for server '{server_name}'",
                server_name=server_name,
                tool_name=tool_name,
            )

        effective_timeout = (
            timeout if timeout is not None else float(server.timeout_seconds)
        )

        if isinstance(server, RedisQueueServerConfig):
            return await self._call_redis_queue(
                server_name, server, tool_name, arguments, effective_timeout
            )
        elif isinstance(server, RestServerConfig):
            return await self._call_rest(
                server_name, server, tool_def, arguments, effective_timeout
            )
        else:
            transport = getattr(server, "transport", "unknown")
            raise MCPConfigurationError(
                f"Unsupported transport: {transport}",
                server_name=server_name,
                tool_name=tool_name,
            )

    async def _call_redis_queue(
        self,
        server_name: str,
        server: RedisQueueServerConfig,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: float,
    ) -> Dict[str, Any]:
        """Dispatches an RPC call over Redis queue with correlation ID."""
        redis = await self.get_redis()
        correlation_id = str(uuid.uuid4())
        response_queue = f"{server.response_queue_prefix}:{correlation_id}"

        payload = {
            "correlation_id": correlation_id,
            "tool": tool_name,
            "arguments": arguments,
            "response_queue": response_queue,
        }

        logger.debug(
            f"Dispatching RPC {correlation_id} to queue {server.request_queue}"
        )
        await redis.lpush(server.request_queue, json.dumps(payload))

        try:
            # Await response with timeout via BLPOP wrapped in asyncio.wait_for
            blpop_timeout = max(1, int(timeout))
            try:
                result = await asyncio.wait_for(
                    redis.blpop(response_queue, timeout=blpop_timeout),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                result = None

            if not result:
                msg = (
                    f"RPC call to '{tool_name}' on '{server.name}' timed out "
                    f"after {timeout}s (corr_id: {correlation_id})"
                )
                raise MCPTimeoutError(
                    msg,
                    server_name=server_name,
                    tool_name=tool_name,
                    timeout=timeout,
                )

            _, raw_response = result
            data = json.loads(raw_response)

            if data.get("status") == "error":
                raise MCPToolExecutionError(
                    data.get("error", "Unknown remote tool execution error"),
                    server_name=server_name,
                    tool_name=tool_name,
                )

            return data.get("data", {})

        finally:
            # Ensure temporary correlation response key is deleted
            await redis.delete(response_queue)

    async def _call_rest(
        self,
        server_name: str,
        server: RestServerConfig,
        tool_def: MCPToolDefinition,
        arguments: Dict[str, Any],
        timeout: float,
    ) -> Dict[str, Any]:
        """Dispatches an asynchronous HTTP REST request to external tool."""
        http_client = await self.get_http_client()
        url = f"{server.endpoint_url.rstrip('/')}{tool_def.endpoint or ''}"

        try:
            response = await http_client.request(
                method=tool_def.method or "POST",
                url=url,
                json=arguments,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise MCPTimeoutError(
                f"HTTP request to '{url}' timed out after {timeout}s",
                server_name=server_name,
                tool_name=tool_def.name,
                timeout=timeout,
            )
        except httpx.HTTPStatusError as e:
            msg = (
                f"HTTP error {e.response.status_code} from '{url}': "
                f"{e.response.text}"
            )
            raise MCPToolExecutionError(
                msg,
                server_name=server_name,
                tool_name=tool_def.name,
            )
        except Exception as e:
            raise MCPToolExecutionError(
                f"Failed to execute REST tool '{tool_def.name}': {str(e)}",
                server_name=server_name,
                tool_name=tool_def.name,
            )
