import json
import pytest
import asyncio
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
                MockTool(
                    "tool1",
                    "desc1",
                    {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                    },
                ),
                MockTool(
                    "tool2",
                    "desc2",
                    {
                        "type": "object",
                        "properties": {"id": {"type": "integer"}},
                    },
                ),
            ],
            "server2": [
                MockTool(
                    "tool3",
                    "desc3",
                    {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                    },
                ),
            ],
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
                MockResource(
                    "mcp://server1/server_info", "server_info", "Server 1 info"
                ),
                MockResource("mcp://server1/resource1", "res1", "res desc1"),
            ],
            "server2": [
                MockResource(
                    "mcp://server2/server_info", "server_info", "Server 2 info"
                ),
            ],
        }

    @pytest.fixture
    def discovery_file(self, tmp_path):
        """Fixture that provides a temporary file path for discovery output."""
        return tmp_path / "mcp_discovery.json"

    @pytest.fixture
    def lock_file(self, tmp_path):
        """Fixture that provides a temporary file path for lock file."""
        return tmp_path / "mcp_discovery.lock"

    # -------------------- Success scenarios --------------------

    async def test_discover_and_save_success(
        self, mock_tools, mock_resources, discovery_file, lock_file
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

            manager = MCPDiscoveryManager(
                discovery_file=str(discovery_file), lock_file=str(lock_file)
            )
            result = await manager.discover_and_save(max_retries=1)

            # Verify success
            assert result is True

            # Verify JSON file contents
            assert discovery_file.exists()
            data = json.loads(discovery_file.read_text())

            assert "tools" in data and "resources" in data
            assert len(data["tools"]) == 2
            assert len(data["resources"]) == 2
            assert data["tools"]["server1"][0]["name"] == "tool1"
            assert (
                data["resources"]["server1"][0]["uri"]
                == "mcp://server1/server_info"
            )

            # Verify lock was removed
            assert not lock_file.exists()

    async def test_discover_and_save_with_retries(
        self, mock_tools, mock_resources, discovery_file, lock_file
    ):
        """
        discover_and_save() retries on failure and eventually succeeds.
        """
        with patch(
            "mcp_clients.mcp_discovery_manager.MCPClientManager"
        ) as MockManager:
            mock_manager = MockManager.return_value

            # First two calls fail, third succeeds
            mock_manager.get_all_tools = AsyncMock(
                side_effect=[
                    Exception("Connection failed"),
                    Exception("Timeout"),
                    mock_tools,
                ]
            )
            mock_manager.get_all_resources = AsyncMock(
                return_value=mock_resources
            )

            manager = MCPDiscoveryManager(
                discovery_file=str(discovery_file), lock_file=str(lock_file)
            )

            # Should succeed on third attempt
            result = await manager.discover_and_save(
                max_retries=3,
                retry_delay=0.1,  # Fast retry for testing
                exponential_backoff=False,
            )

            assert result is True
            assert discovery_file.exists()

            # Verify get_all_tools was called 3 times
            assert mock_manager.get_all_tools.call_count == 3

    async def test_discover_and_save_validation_failure_then_success(
        self, mock_resources, discovery_file, lock_file
    ):
        """
        discover_and_save() retries when validation fails,
        then succeeds with valid data.
        """
        # First attempt: empty tools (validation fails)
        empty_tools = {}

        # Second attempt: valid tools
        class MockTool:
            def __init__(self, name, desc, schema):
                self.name = name
                self.description = desc
                self.inputSchema = schema

        valid_tools = {
            "server1": [MockTool("tool1", "desc1", {"type": "object"})]
        }

        with patch(
            "mcp_clients.mcp_discovery_manager.MCPClientManager"
        ) as MockManager:
            mock_manager = MockManager.return_value
            mock_manager.get_all_tools = AsyncMock(
                side_effect=[empty_tools, valid_tools]
            )
            mock_manager.get_all_resources = AsyncMock(
                return_value=mock_resources
            )

            manager = MCPDiscoveryManager(
                discovery_file=str(discovery_file), lock_file=str(lock_file)
            )

            result = await manager.discover_and_save(
                max_retries=2, retry_delay=0.1, exponential_backoff=False
            )

            assert result is True
            assert discovery_file.exists()

    # -------------------- Edge cases --------------------

    async def test_discover_and_save_all_retries_exhausted(
        self, discovery_file, lock_file
    ):
        """
        discover_and_save() returns False when all retries are exhausted.
        """
        with patch(
            "mcp_clients.mcp_discovery_manager.MCPClientManager"
        ) as MockManager:
            mock_manager = MockManager.return_value
            mock_manager.get_all_tools = AsyncMock(
                side_effect=Exception("Persistent failure")
            )
            mock_manager.get_all_resources = AsyncMock(return_value={})

            manager = MCPDiscoveryManager(
                discovery_file=str(discovery_file), lock_file=str(lock_file)
            )

            result = await manager.discover_and_save(
                max_retries=2, retry_delay=0.1, exponential_backoff=False
            )

            # Should fail after all retries
            assert result is False

            # Lock should be removed
            assert not lock_file.exists()

    async def test_discover_and_save_empty_data_fails_validation(
        self, discovery_file, lock_file
    ):
        """
        discover_and_save() fails validation and
        returns False when both tools and resources are empty.
        """
        with patch(
            "mcp_clients.mcp_discovery_manager.MCPClientManager"
        ) as MockManager:
            mock_manager = MockManager.return_value
            mock_manager.get_all_tools = AsyncMock(return_value={})
            mock_manager.get_all_resources = AsyncMock(return_value={})

            manager = MCPDiscoveryManager(
                discovery_file=str(discovery_file), lock_file=str(lock_file)
            )

            result = await manager.discover_and_save(
                max_retries=1, retry_delay=0.1
            )

            assert result is False

    async def test_discover_and_save_with_existing_lock(
        self, mock_tools, mock_resources, discovery_file, lock_file
    ):
        """
        discover_and_save() waits for existing lock. When wait times out,
        it removes the lock, takes over, and completes discovery successfully.
        """
        # Ensure parent directory exists first
        lock_file.parent.mkdir(parents=True, exist_ok=True)

        # Create an existing lock file (fresh, not stale)
        lock_file.touch()

        with patch(
            "mcp_clients.mcp_discovery_manager.MCPClientManager"
        ) as MockManager:

            mock_manager = MockManager.return_value
            mock_manager.get_all_tools = AsyncMock(return_value=mock_tools)
            mock_manager.get_all_resources = AsyncMock(
                return_value=mock_resources
            )

            manager = MCPDiscoveryManager(
                discovery_file=str(discovery_file), lock_file=str(lock_file)
            )

            # Mock _wait_for_discovery as a SYNC method that returns False
            with patch.object(
                manager, "_wait_for_discovery", return_value=False
            ):
                result = await manager.discover_and_save(max_retries=1)

            # After wait fails, code removes lock and takes over
            # Discovery should succeed ✅
        assert result is True  # ✅ THIS IS CORRECT
        assert discovery_file.exists()

    async def test_discover_and_save_removes_stale_lock(
        self, mock_tools, mock_resources, discovery_file, lock_file
    ):
        """
        discover_and_save() removes stale lock and proceeds with discovery.
        """
        # Ensure parent directory exists first
        lock_file.parent.mkdir(parents=True, exist_ok=True)

        # Create a stale lock file
        lock_file.touch()

        # Make the lock file old by modifying its mtime
        import os
        import time

        # Set lock file to be 400 seconds old (stale)
        stale_time = time.time() - 400
        os.utime(lock_file, (stale_time, stale_time))

        with patch(
            "mcp_clients.mcp_discovery_manager.MCPClientManager"
        ) as MockManager:

            mock_manager = MockManager.return_value
            mock_manager.get_all_tools = AsyncMock(return_value=mock_tools)
            mock_manager.get_all_resources = AsyncMock(
                return_value=mock_resources
            )

            manager = MCPDiscoveryManager(
                discovery_file=str(discovery_file), lock_file=str(lock_file)
            )

            result = await manager.discover_and_save(max_retries=1)

            assert result is True
            # Verify lock was removed
            assert not lock_file.exists()

    async def test_discover_and_save_exponential_backoff(
        self, mock_tools, mock_resources, discovery_file, lock_file
    ):
        """
        discover_and_save() uses exponential backoff when enabled.
        """
        call_times = []

        async def track_time(*args, **kwargs):
            call_times.append(asyncio.get_event_loop().time())
            raise Exception("Test failure")

        with patch(
            "mcp_clients.mcp_discovery_manager.MCPClientManager"
        ) as MockManager:
            mock_manager = MockManager.return_value
            mock_manager.get_all_tools = AsyncMock(side_effect=track_time)
            mock_manager.get_all_resources = AsyncMock(
                return_value=mock_resources
            )

            manager = MCPDiscoveryManager(
                discovery_file=str(discovery_file), lock_file=str(lock_file)
            )

            result = await manager.discover_and_save(
                max_retries=3, retry_delay=0.1, exponential_backoff=True
            )

            assert result is False
            assert len(call_times) == 3

            # With exponential backoff: 0.1s, 0.2s delays
            # Allow some tolerance for test timing
            if len(call_times) >= 2:
                delay1 = call_times[1] - call_times[0]
                assert 0.08 < delay1 < 0.15  # ~0.1s with tolerance

            if len(call_times) >= 3:
                delay2 = call_times[2] - call_times[1]
                assert 0.15 < delay2 < 0.25  # ~0.2s with tolerance

    # -------------------- Validation tests --------------------

    def test_validate_discovery_data_valid(self, discovery_file, lock_file):
        """
        _validate_discovery_data() returns True for valid data structure.
        """
        manager = MCPDiscoveryManager(
            discovery_file=str(discovery_file), lock_file=str(lock_file)
        )

        valid_data = {
            "tools": {
                "server1": [
                    {
                        "name": "tool1",
                        "description": "desc",
                        "inputSchema": {"type": "object"},
                    }
                ]
            },
            "resources": {
                "server1": [
                    {
                        "uri": "mcp://test",
                        "name": "res1",
                        "description": "desc",
                    }
                ]
            },
        }

        is_valid, error = manager._validate_discovery_data(valid_data)
        assert is_valid is True
        assert error == "Valid"

    def test_validate_discovery_data_not_dict(self, discovery_file, lock_file):
        """
        _validate_discovery_data() fails when data is not a dict.
        """
        manager = MCPDiscoveryManager(
            discovery_file=str(discovery_file), lock_file=str(lock_file)
        )

        is_valid, error = manager._validate_discovery_data([])
        assert is_valid is False
        assert "not a dict" in error

    def test_validate_discovery_data_missing_keys(
        self, discovery_file, lock_file
    ):
        """
        _validate_discovery_data() fails when required keys are missing.
        """
        manager = MCPDiscoveryManager(
            discovery_file=str(discovery_file), lock_file=str(lock_file)
        )

        is_valid, error = manager._validate_discovery_data({"tools": {}})
        assert is_valid is False
        assert "resources" in error

    def test_validate_discovery_data_empty(self, discovery_file, lock_file):
        """
        _validate_discovery_data() fails when both tools
        and resources are empty.
        """
        manager = MCPDiscoveryManager(
            discovery_file=str(discovery_file), lock_file=str(lock_file)
        )

        is_valid, error = manager._validate_discovery_data(
            {"tools": {}, "resources": {}}
        )
        assert is_valid is False
        assert "empty" in error

    def test_validate_discovery_data_invalid_tool_structure(
        self, discovery_file, lock_file
    ):
        """
        _validate_discovery_data() fails when tool structure is invalid.
        """
        manager = MCPDiscoveryManager(
            discovery_file=str(discovery_file), lock_file=str(lock_file)
        )

        invalid_data = {
            "tools": {
                "server1": [
                    {"name": "tool1"}  # Missing description and inputSchema
                ]
            },
            "resources": {
                "server1": [
                    {
                        "uri": "mcp://test",
                        "name": "res1",
                        "description": "desc",
                    }
                ]
            },
        }

        is_valid, error = manager._validate_discovery_data(invalid_data)
        assert is_valid is False
        assert "missing required key" in error.lower()

    def test_validate_discovery_data_tools_not_list(
        self, discovery_file, lock_file
    ):
        """
        _validate_discovery_data() fails when tools is not a list.
        """
        manager = MCPDiscoveryManager(
            discovery_file=str(discovery_file), lock_file=str(lock_file)
        )

        invalid_data = {
            "tools": {"server1": "not a list"},  # Should be a list
            "resources": {
                "server1": [
                    {
                        "uri": "mcp://test",
                        "name": "res1",
                        "description": "desc",
                    }
                ]
            },
        }

        is_valid, error = manager._validate_discovery_data(invalid_data)
        assert is_valid is False
        assert "not a list" in error

    def test_validate_discovery_data_resources_not_list(
        self, discovery_file, lock_file
    ):
        """
        _validate_discovery_data() fails when resources is not a list.
        """
        manager = MCPDiscoveryManager(
            discovery_file=str(discovery_file), lock_file=str(lock_file)
        )

        invalid_data = {
            "tools": {
                "server1": [
                    {
                        "name": "tool1",
                        "description": "desc",
                        "inputSchema": {"type": "object"},
                    }
                ]
            },
            "resources": {"server1": "not a list"},  # Should be a list
        }

        is_valid, error = manager._validate_discovery_data(invalid_data)
        assert is_valid is False
        assert "not a list" in error

    def test_validate_discovery_data_invalid_resource_structure(
        self, discovery_file, lock_file
    ):
        """
        _validate_discovery_data() fails when resource structure is invalid.
        """
        manager = MCPDiscoveryManager(
            discovery_file=str(discovery_file), lock_file=str(lock_file)
        )

        invalid_data = {
            "tools": {
                "server1": [
                    {
                        "name": "tool1",
                        "description": "desc",
                        "inputSchema": {"type": "object"},
                    }
                ]
            },
            "resources": {
                "server1": [
                    {"uri": "mcp://test"}  # Missing name and description
                ]
            },
        }

        is_valid, error = manager._validate_discovery_data(invalid_data)
        assert is_valid is False
        assert "missing required key" in error.lower()

    # -------------------- verify_discovery_file tests --------------------

    def test_verify_discovery_file_valid(
        self, mock_tools, mock_resources, discovery_file, lock_file
    ):
        """
        verify_discovery_file() returns True for valid discovery file.
        """
        # Create a valid discovery file
        valid_data = {
            "tools": {
                "server1": [
                    {
                        "name": "tool1",
                        "description": "desc",
                        "inputSchema": {"type": "object"},
                    }
                ]
            },
            "resources": {
                "server1": [
                    {
                        "uri": "mcp://test",
                        "name": "res1",
                        "description": "desc",
                    }
                ]
            },
        }

        discovery_file.write_text(json.dumps(valid_data))

        manager = MCPDiscoveryManager(
            discovery_file=str(discovery_file), lock_file=str(lock_file)
        )

        is_valid, error = manager.verify_discovery_file()
        assert is_valid is True
        assert error is None

    def test_verify_discovery_file_not_exists(self, discovery_file, lock_file):
        """
        verify_discovery_file() returns False when file doesn't exist.
        """
        manager = MCPDiscoveryManager(
            discovery_file=str(discovery_file), lock_file=str(lock_file)
        )

        is_valid, error = manager.verify_discovery_file()
        assert is_valid is False
        assert "does not exist" in error

    def test_verify_discovery_file_invalid_json(
        self, discovery_file, lock_file
    ):
        """
        verify_discovery_file() returns False for invalid JSON.
        """
        discovery_file.write_text("invalid json {")

        manager = MCPDiscoveryManager(
            discovery_file=str(discovery_file), lock_file=str(lock_file)
        )

        is_valid, error = manager.verify_discovery_file()
        assert is_valid is False
        assert "not valid JSON" in error

    # -------------------- ensure_discovery_ready tests --------------------

    async def test_ensure_discovery_ready_already_valid(
        self, discovery_file, lock_file
    ):
        """
        ensure_discovery_ready() returns True immediately
        if file is already valid.
        """
        # Create a valid discovery file
        valid_data = {
            "tools": {
                "server1": [
                    {
                        "name": "tool1",
                        "description": "desc",
                        "inputSchema": {"type": "object"},
                    }
                ]
            },
            "resources": {
                "server1": [
                    {
                        "uri": "mcp://test",
                        "name": "res1",
                        "description": "desc",
                    }
                ]
            },
        }

        discovery_file.write_text(json.dumps(valid_data))

        manager = MCPDiscoveryManager(
            discovery_file=str(discovery_file), lock_file=str(lock_file)
        )

        result = await manager.ensure_discovery_ready()
        assert result is True

    async def test_ensure_discovery_ready_triggers_discovery(
        self, mock_tools, mock_resources, discovery_file, lock_file
    ):
        """
        ensure_discovery_ready() triggers discovery when file is invalid.
        """
        with patch(
            "mcp_clients.mcp_discovery_manager.MCPClientManager"
        ) as MockManager:
            mock_manager = MockManager.return_value
            mock_manager.get_all_tools = AsyncMock(return_value=mock_tools)
            mock_manager.get_all_resources = AsyncMock(
                return_value=mock_resources
            )

            manager = MCPDiscoveryManager(
                discovery_file=str(discovery_file), lock_file=str(lock_file)
            )

            result = await manager.ensure_discovery_ready()
            assert result is True
            assert discovery_file.exists()

    # -------------------- to_serializable tests --------------------

    def test_to_serializable_pydantic_model(self):
        """
        to_serializable() correctly converts Pydantic-like objects.
        """

        class MockModel:
            def dict(self):
                return {"a": 1, "b": "test"}

        result = to_serializable(MockModel())
        assert result == {"a": 1, "b": "test"}

    def test_to_serializable_list(self):
        """
        to_serializable() correctly converts lists.
        """
        assert to_serializable([1, 2, 3]) == ["1", "2", "3"]
        assert to_serializable(["a", "b"]) == ["a", "b"]

    def test_to_serializable_tuple(self):
        """
        to_serializable() correctly converts tuples.
        """
        assert to_serializable((1, 2, 3)) == ["1", "2", "3"]

    def test_to_serializable_dict(self):
        """
        to_serializable() correctly converts dicts recursively.
        """
        input_dict = {"x": 1, "y": {"z": 2}}
        expected = {"x": "1", "y": {"z": "2"}}
        assert to_serializable(input_dict) == expected

    def test_to_serializable_nested_structures(self):
        """
        to_serializable() handles nested structures correctly.
        """

        class MockModel:
            def dict(self):
                return {"inner": "value"}

        input_data = {
            "models": [MockModel(), MockModel()],
            "numbers": (1, 2, 3),
            "nested": {"a": [1, 2]},
        }

        result = to_serializable(input_data)
        assert result["models"] == [{"inner": "value"}, {"inner": "value"}]
        assert result["numbers"] == ["1", "2", "3"]
        assert result["nested"] == {"a": ["1", "2"]}

    def test_to_serializable_scalar(self):
        """
        to_serializable() converts scalars to strings.
        """
        assert to_serializable(123) == "123"
        assert to_serializable(45.67) == "45.67"
        assert to_serializable(True) == "True"
        assert to_serializable(None) == "None"
