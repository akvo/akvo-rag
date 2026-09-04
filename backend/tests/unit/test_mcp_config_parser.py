import json
import time
import pytest
from pydantic import ValidationError

from app.core.mcp_config import (
    MCPConfig,
    RedisQueueServerConfig,
    RestServerConfig,
)


def test_load_mcp_config_valid():
    """Test loading and parsing the standard backend/mcp_config.json file."""
    config = MCPConfig.load_from_file("mcp_config.json")

    assert config.version == "1.0"
    assert "knowledge_bases_mcp" in config.servers
    assert "weather_mcp" in config.servers

    # Verify Redis Queue transport config
    kb_server = config.servers["knowledge_bases_mcp"]
    assert isinstance(kb_server, RedisQueueServerConfig)
    assert kb_server.transport == "redis_queue"
    assert kb_server.name == "Vector Knowledge Base Microservice"
    assert kb_server.request_queue == "mcp:vector:requests"
    assert kb_server.response_queue_prefix == "mcp:vector:responses"
    assert kb_server.timeout_seconds == 30

    # Verify all 14 vector tools are present
    expected_kb_tools = [
        "query_knowledge_base",
        "list_knowledge_bases",
        "get_knowledge_base",
        "create_knowledge_base",
        "update_knowledge_base",
        "delete_knowledge_base",
        "list_documents",
        "get_document",
        "register_document",
        "ingest_document",
        "process_document",
        "delete_document",
        "preview_documents",
        "get_processing_tasks",
    ]
    tool_names = [tool.name for tool in kb_server.tools]
    for expected_tool in expected_kb_tools:
        assert expected_tool in tool_names, f"Missing tool: {expected_tool}"


def test_weather_mcp_rest_config():
    """Test REST transport configuration for weather_mcp."""
    config = MCPConfig.load_from_file("mcp_config.json")
    weather_server = config.servers["weather_mcp"]

    assert isinstance(weather_server, RestServerConfig)
    assert weather_server.transport == "rest"
    assert weather_server.name == "Open-Meteo Weather MCP Service"
    assert weather_server.timeout_seconds == 10
    assert weather_server.endpoint_url.startswith("http")

    # Verify weather forecast tool
    forecast_tool = config.get_tool("weather_mcp", "get_weather_forecast")
    assert forecast_tool is not None
    assert forecast_tool.endpoint == "/forecast"
    assert forecast_tool.method == "POST"
    assert "latitude" in forecast_tool.inputSchema.properties
    assert "longitude" in forecast_tool.inputSchema.properties
    assert "latitude" in forecast_tool.inputSchema.required
    assert "longitude" in forecast_tool.inputSchema.required


def test_env_var_substitution_default_and_override(tmp_path, monkeypatch):
    """Test environment variable expansion with defaults and overrides."""
    config_data = {
        "version": "1.0",
        "servers": {
            "custom_service": {
                "name": "Custom Service",
                "transport": "rest",
                "endpoint_url": "${CUSTOM_SERVICE_URL:-http://default:8000}",
                "timeout_seconds": 15,
                "tools": [
                    {
                        "name": "custom_tool",
                        "description": "Custom test tool",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "param1": {
                                    "type": "string",
                                    "description": "Test parameter",
                                }
                            },
                            "required": ["param1"],
                        },
                    }
                ],
            }
        },
    }

    config_file = tmp_path / "test_env_mcp_config.json"
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    # 1. Test when env var is NOT set -> default value used
    monkeypatch.delenv("CUSTOM_SERVICE_URL", raising=False)
    loaded_config = MCPConfig.load_from_file(str(config_file))
    server = loaded_config.servers["custom_service"]
    assert isinstance(server, RestServerConfig)
    assert server.endpoint_url == "http://default:8000"

    # 2. Test when env var IS set -> overridden value used
    monkeypatch.setenv(
        "CUSTOM_SERVICE_URL", "https://prod-cluster.internal:9000/api"
    )
    loaded_config_override = MCPConfig.load_from_file(str(config_file))
    server_override = loaded_config_override.servers["custom_service"]
    assert isinstance(server_override, RestServerConfig)
    assert (
        server_override.endpoint_url
        == "https://prod-cluster.internal:9000/api"
    )


def test_schema_validation_error_boundaries(tmp_path):
    """Test schema validation errors when invalid configs are provided."""
    # Missing required 'transport' field
    invalid_data = {
        "version": "1.0",
        "servers": {
            "bad_server": {
                "name": "Bad Server",
                "timeout_seconds": 10,
                "tools": [],
            }
        },
    }
    config_file = tmp_path / "invalid_mcp_config.json"
    config_file.write_text(json.dumps(invalid_data), encoding="utf-8")

    with pytest.raises(ValidationError):
        MCPConfig.load_from_file(str(config_file))

    # Invalid transport type
    invalid_transport_data = {
        "version": "1.0",
        "servers": {
            "bad_server": {
                "name": "Bad Server",
                "transport": "unsupported_protocol",
                "tools": [],
            }
        },
    }
    config_file_transport = tmp_path / "invalid_transport_config.json"
    config_file_transport.write_text(
        json.dumps(invalid_transport_data), encoding="utf-8"
    )

    with pytest.raises(ValidationError):
        MCPConfig.load_from_file(str(config_file_transport))


def test_missing_file_raises_filenotfound():
    """Test that loading a non-existent config raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        MCPConfig.load_from_file("non_existent_config_12345.json")


def test_lookup_helpers():
    """Test get_tool, get_server, get_server_for_tool, and list_tools."""
    config = MCPConfig.load_from_file("mcp_config.json")

    # get_tool
    tool = config.get_tool("knowledge_bases_mcp", "query_knowledge_base")
    assert tool is not None
    assert tool.name == "query_knowledge_base"
    assert "query" in tool.inputSchema.properties
    assert "knowledge_base_ids" in tool.inputSchema.required

    # get_tool on non-existent server / tool
    assert (
        config.get_tool("non_existent_server", "query_knowledge_base") is None
    )
    assert config.get_tool("knowledge_bases_mcp", "non_existent_tool") is None

    # get_server
    kb_server = config.get_server("knowledge_bases_mcp")
    assert kb_server is not None
    assert kb_server.name == "Vector Knowledge Base Microservice"
    assert config.get_server("unknown_server") is None

    # get_server_for_tool
    result = config.get_server_for_tool("query_knowledge_base")
    assert result is not None
    srv_name, srv_conf, tool_def = result
    assert srv_name == "knowledge_bases_mcp"
    assert srv_conf.transport == "redis_queue"
    assert tool_def.name == "query_knowledge_base"

    # get_server_for_tool on unknown tool
    assert config.get_server_for_tool("unknown_tool_xyz") is None

    # list_tools
    all_tools = config.list_tools()
    assert len(all_tools) >= 17  # 14 KB tools + 3 weather tools

    kb_tools = config.list_tools("knowledge_bases_mcp")
    assert len(kb_tools) == 14

    empty_tools = config.list_tools("unknown_server")
    assert len(empty_tools) == 0


def test_parsing_speed_benchmark():
    """Verify static parsing execution time is sub-5ms."""
    start_time = time.perf_counter()
    iterations = 50
    for _ in range(iterations):
        MCPConfig.load_from_file("mcp_config.json")
    duration = (time.perf_counter() - start_time) / iterations

    # Assert duration per parse is under 5ms (0.005s)
    assert (
        duration < 0.005
    ), f"Parsing took {duration * 1000:.2f}ms, expected < 5ms"
