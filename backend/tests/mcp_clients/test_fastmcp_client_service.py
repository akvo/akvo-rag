import pytest

from unittest.mock import AsyncMock, patch
from mcp_clients.fastmcp_client_service import FastMCPClientService

SERVER_URL = "http://fake-server.com"
API_KEY = "fake-api-key"


@pytest.fixture
def service():
    """Fixture to create FastMCPClientService instance."""
    return FastMCPClientService(SERVER_URL, API_KEY)


@pytest.fixture
def mock_client():
    """
    Patch the Client class properly to handle async context manager.
    Returns the object yielded by 'async with Client(...)'.
    """
    with patch("mcp_clients.fastmcp_client_service.Client") as MockClient:
        instance = AsyncMock()
        MockClient.return_value.__aenter__.return_value = instance
        MockClient.return_value.__aexit__.return_value = AsyncMock()
        yield instance


@pytest.mark.unit
@pytest.mark.asyncio
class TestFastMCPClientService:
    """Unit tests for FastMCPClientService."""

    async def test_ping(self, service, mock_client):
        """ping() calls Client.ping and returns expected result."""
        mock_client.ping.return_value = "pong"
        result = await service.ping()
        assert result == "pong"
        mock_client.ping.assert_awaited_once()

    async def test_list_tools(self, service, mock_client):
        """list_tools() calls Client.list_tools and returns tools list."""
        mock_client.list_tools.return_value = ["tool1", "tool2"]
        result = await service.list_tools()
        assert result == ["tool1", "tool2"]
        mock_client.list_tools.assert_awaited_once()

    async def test_list_resources(self, service, mock_client):
        """
        list_resources() calls Client.list_resources and
        returns resources list.
        """
        mock_client.list_resources.return_value = ["res1", "res2"]
        result = await service.list_resources()
        assert result == ["res1", "res2"]
        mock_client.list_resources.assert_awaited_once()

    async def test_read_resource(self, service, mock_client):
        """
        read_resource(uri) calls Client.read_resource with correct URI and
        returns data.
        """
        uri = "some-uri"
        mock_client.read_resource.return_value = {"data": 123}
        result = await service.read_resource(uri)
        assert result == {"data": 123}
        mock_client.read_resource.assert_awaited_once_with(uri)

    async def test_call_tool(self, service, mock_client):
        """
        call_tool(tool_name, params) calls Client.call_tool with correct
        args and returns result.
        """
        tool_name = "tool1"
        params = {"x": 1}
        mock_client.call_tool.return_value = {"result": 42}
        result = await service.call_tool(tool_name, params)
        assert result == {"result": 42}
        mock_client.call_tool.assert_awaited_once_with(tool_name, params)
