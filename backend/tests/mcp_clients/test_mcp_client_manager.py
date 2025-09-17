import pytest
from unittest.mock import AsyncMock
from mcp_clients.mcp_client_manager import (
    MCPClientManager,
    FastMCPClientService,
)


@pytest.mark.unit
@pytest.mark.asyncio
class TestMCPClientManager:
    """Unit tests for MCPClientManager."""

    @pytest.fixture
    def manager(self):
        """
        Fixture to create MCPClientManager instance with mocked
        FastMCPClientService instances.
        """
        mngr = MCPClientManager()
        # Replace the service instances with AsyncMock preserving spec
        for key in mngr.services:
            mngr.services[key] = AsyncMock(spec=FastMCPClientService)
        return mngr

    # -------------------- Success scenarios --------------------

    async def test_ping_all_success(self, manager):
        """ping_all() returns 'ok' for all servers when ping succeeds."""
        for service in manager.services.values():
            service.ping.return_value = "pong"
        result = await manager.ping_all()
        assert all(v == "ok" for v in result.values())

    async def test_get_all_tools_success(self, manager):
        """get_all_tools() returns list of tools for all servers."""
        for service in manager.services.values():
            service.list_tools.return_value = ["tool1", "tool2"]
        result = await manager.get_all_tools()
        for tools in result.values():
            assert tools == ["tool1", "tool2"]

    async def test_get_all_resources_success(self, manager):
        """get_all_resources() returns list of resources for all servers."""
        for service in manager.services.values():
            service.list_resources.return_value = ["res1", "res2"]
        result = await manager.get_all_resources()
        for resources in result.values():
            assert resources == ["res1", "res2"]

    async def test_read_resource_success(self, manager):
        """read_resource() calls the correct service and returns data."""
        uri = "some-uri"
        service = list(manager.services.values())[0]
        service.read_resource.return_value = {"data": 123}
        server_name = list(manager.services.keys())[0]

        result = await manager.read_resource(server_name, uri)
        assert result == {"data": 123}
        service.read_resource.assert_awaited_once_with(uri)

    async def test_run_tool_success(self, manager):
        """run_tool() calls the correct service and returns result."""
        server_name = list(manager.services.keys())[0]
        service = manager.services[server_name]
        tool_name = "tool1"
        params = {"x": 1}
        service.call_tool.return_value = {"result": 42}

        result = await manager.run_tool(server_name, tool_name, params)
        assert result == {"result": 42}
        service.call_tool.assert_awaited_once_with(tool_name, params)

    # -------------------- Error handling scenarios --------------------

    async def test_ping_all_failure(self, manager):
        """
        ping_all() returns 'error: ...' if a service ping raises an exception.
        """
        for service in manager.services.values():
            service.ping.side_effect = Exception("Ping failed")
        result = await manager.ping_all()
        for val in result.values():
            assert val.startswith("error: Ping failed")

    async def test_get_all_tools_failure(self, manager):
        """
        get_all_tools() returns 'error: ...' if a service list_tools raises
        an exception.
        """
        for service in manager.services.values():
            service.list_tools.side_effect = Exception("Tools fetch failed")
        result = await manager.get_all_tools()
        for val in result.values():
            assert val.startswith("error: Tools fetch failed")

    async def test_get_all_resources_failure(self, manager):
        """
        get_all_resources() returns 'error: ...' if a service
        list_resources raises an exception.
        """
        for service in manager.services.values():
            service.list_resources.side_effect = Exception(
                "Resources fetch failed"
            )
        result = await manager.get_all_resources()
        for val in result.values():
            assert val.startswith("error: Resources fetch failed")

    # -------------------- Invalid server scenarios --------------------

    async def test_read_resource_invalid_server(self, manager):
        """read_resource() raises ValueError if server not found."""
        with pytest.raises(ValueError):
            await manager.read_resource("invalid_server", "uri")

    async def test_run_tool_invalid_server(self, manager):
        """run_tool() raises ValueError if server not found."""
        with pytest.raises(ValueError):
            await manager.run_tool("invalid_server", "tool")
