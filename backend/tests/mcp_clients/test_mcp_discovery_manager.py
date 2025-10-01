import json
import pytest
from unittest.mock import AsyncMock, patch
from mcp_clients.mcp_discovery_manager import (
    MCPDiscoveryManager,
    to_serializable,
)


@pytest.mark.unit
@pytest.mark.asyncio
class TestMCPDiscoveryManager:
    """Unit tests for MCPDiscoveryManager."""

    @pytest.fixture
    def mock_tools(self):
        """Fixture that returns fake MCP tools for testing."""

        class MockTool:
            def __init__(self, name, desc, schema):
                self.name = name
                self.description = desc
                self.inputSchema = schema

        return {
            "server1": [
                MockTool("tool1", "desc1", {"type": "string"}),
                MockTool("tool2", "desc2", {"type": "int"}),
            ]
        }

    @pytest.fixture
    def mock_resources(self):
        """Fixture that returns fake MCP resources for testing."""

        class MockResource:
            def __init__(self, uri, name, desc):
                self.uri = uri
                self.name = name
                self.description = desc

        return {
            "server1": [
                MockResource("http://res1", "res1", "res desc1"),
                MockResource("http://res2", "res2", "res desc2"),
            ]
        }

    @pytest.fixture
    def discovery_file(self, tmp_path):
        """Fixture that provides a temporary file path for discovery output."""
        return tmp_path / "mcp_discovery.json"

    # -------------------- Success scenarios --------------------

    async def test_discover_and_save_success(
        self, mock_tools, mock_resources, discovery_file
    ):
        """
        discover_and_save() writes valid JSON when MCPClientManager returns
        tools/resources.
        """
        with patch(
            "mcp_clients.mcp_discovery_manager.MCPClientManager"
        ) as MockManager:
            mock_manager = MockManager.return_value
            mock_manager.get_all_tools = AsyncMock(return_value=mock_tools)
            mock_manager.get_all_resources = AsyncMock(
                return_value=mock_resources
            )

            manager = MCPDiscoveryManager(discovery_file=str(discovery_file))
            await manager.discover_and_save()

        # Verify JSON file contents
        assert discovery_file.exists()
        data = json.loads(discovery_file.read_text())

        assert "tools" in data and "resources" in data
        assert data["tools"]["server1"][0]["name"] == "tool1"
        assert data["resources"]["server1"][0]["uri"] == "http://res1"

    # -------------------- Edge cases --------------------

    async def test_discover_and_save_empty(self, discovery_file):
        """
        discover_and_save() writes empty structures if MCPClientManager
        returns no data.
        """
        with patch(
            "mcp_clients.mcp_discovery_manager.MCPClientManager"
        ) as MockManager:
            mock_manager = MockManager.return_value
            mock_manager.get_all_tools = AsyncMock(return_value={})
            mock_manager.get_all_resources = AsyncMock(return_value={})

            manager = MCPDiscoveryManager(discovery_file=str(discovery_file))
            await manager.discover_and_save()

        data = json.loads(discovery_file.read_text())
        assert data == {"tools": {}, "resources": {}}

    # -------------------- to_serializable tests --------------------

    def test_to_serializable_various(self):
        """
        to_serializable() correctly converts models, lists, dicts, and scalars.
        """

        class MockModel:
            def dict(self):
                return {"a": 1}

        # Pydantic-like object
        assert to_serializable(MockModel()) == {"a": 1}

        # List of values
        assert to_serializable([1, 2]) == ["1", "2"]

        # Dict with values
        assert to_serializable({"x": 1}) == {"x": "1"}

        # Scalar fallback
        assert to_serializable(123) == "123"
