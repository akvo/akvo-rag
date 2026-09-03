import json
import time
import pytest
from pydantic import ValidationError

from app.core.mcp_config import (
    MCPConfig,
    RedisQueueServerConfig,
    RestServerConfig,
)


@pytest.mark.unit
def test_valid_mcp_config_parsing():
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

    # Verify all 9 vector tools are present
    expected_kb_tools = [
        "query_knowledge_base",
        "list_knowledge_bases",
        "get_knowledge_base",
        "create_knowledge_base",
        "update_knowledge_base",
        "delete_knowledge_base",
        "list_documents",
        "get_document",
        "get_processing_tasks",
    ]
    tool_names = [tool.name for tool in kb_server.tools]
    for expected_tool in expected_kb_tools:
        assert expected_tool in tool_names, f"Missing tool: {expected_tool}"

    # Verify REST transport config
    weather_server = config.servers["weather_mcp"]
    assert isinstance(weather_server, RestServerConfig)
    assert weather_server.transport == "rest"
    assert weather_server.name == "Open-Meteo Weather MCP Service"
    assert weather_server.timeout_seconds == 10
    assert weather_server.endpoint_url.startswith("http")

    forecast_tool = config.get_tool("weather_mcp", "get_weather_forecast")
    assert forecast_tool is not None
    assert forecast_tool.endpoint == "/forecast"
    assert forecast_tool.method == "POST"
    assert "latitude" in forecast_tool.inputSchema.properties
    assert "longitude" in forecast_tool.inputSchema.properties


@pytest.mark.unit
def test_missing_required_fields(tmp_path):
    """Test that missing required fields raise Pydantic ValidationError."""
    # Missing 'transport'
    invalid_no_transport = {
        "version": "1.0",
        "servers": {
            "bad_server": {
                "name": "Bad Server",
                "tools": [],
            }
        },
    }
    f1 = tmp_path / "no_transport.json"
    f1.write_text(json.dumps(invalid_no_transport), encoding="utf-8")
    with pytest.raises(ValidationError):
        MCPConfig.load_from_file(str(f1))

    # Missing tool 'name'
    invalid_tool_no_name = {
        "version": "1.0",
        "servers": {
            "bad_server": {
                "name": "Bad Server",
                "transport": "redis_queue",
                "request_queue": "mcp:test:requests",
                "response_queue_prefix": "mcp:test:responses",
                "tools": [
                    {
                        "description": "Missing name",
                        "inputSchema": {"type": "object"},
                    }
                ],
            }
        },
    }
    f2 = tmp_path / "tool_no_name.json"
    f2.write_text(json.dumps(invalid_tool_no_name), encoding="utf-8")
    with pytest.raises(ValidationError):
        MCPConfig.load_from_file(str(f2))


@pytest.mark.unit
def test_custom_timeout_defaults(tmp_path):
    """Verify fallback to default timeout_seconds when omitted."""
    config_data = {
        "version": "1.0",
        "servers": {
            "default_timeout_server": {
                "name": "Default Timeout Server",
                "transport": "redis_queue",
                "request_queue": "mcp:test:requests",
                "response_queue_prefix": "mcp:test:responses",
                "tools": [
                    {
                        "name": "sample_tool",
                        "description": "Sample",
                        "inputSchema": {"type": "object"},
                    }
                ],
            }
        },
    }
    f = tmp_path / "default_timeout.json"
    f.write_text(json.dumps(config_data), encoding="utf-8")

    config = MCPConfig.load_from_file(str(f))
    server = config.servers["default_timeout_server"]
    assert server.timeout_seconds == 30  # Default Redis queue timeout is 30s


@pytest.mark.unit
def test_env_var_substitution(tmp_path, monkeypatch):
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

    # 1. Default expansion
    monkeypatch.delenv("CUSTOM_SERVICE_URL", raising=False)
    config = MCPConfig.load_from_file(str(config_file))
    server = config.servers["custom_service"]
    assert isinstance(server, RestServerConfig)
    assert server.endpoint_url == "http://default:8000"

    # 2. Override expansion
    monkeypatch.setenv("CUSTOM_SERVICE_URL", "http://overridden:9999")
    config_overridden = MCPConfig.load_from_file(str(config_file))
    server_overridden = config_overridden.servers["custom_service"]
    assert isinstance(server_overridden, RestServerConfig)
    assert server_overridden.endpoint_url == "http://overridden:9999"


@pytest.mark.unit
def test_missing_file_raises_filenotfound():
    """Test that loading a non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        MCPConfig.load_from_file("non_existent_mcp_config_path_12345.json")


@pytest.mark.unit
def test_lookup_helpers():
    """Test get_server, get_tool, and list_servers helpers."""
    config = MCPConfig.load_from_file("mcp_config.json")

    assert config.get_server("knowledge_bases_mcp") is not None
    assert config.get_server("non_existent") is None

    assert (
        config.get_tool("knowledge_bases_mcp", "query_knowledge_base")
        is not None
    )
    assert config.get_tool("knowledge_bases_mcp", "non_existent_tool") is None
    assert config.get_tool("non_existent_server", "any_tool") is None

    server_names = config.list_servers()
    assert "knowledge_bases_mcp" in server_names
    assert "weather_mcp" in server_names


@pytest.mark.unit
def test_parsing_speed_benchmark():
    """Benchmark mcp_config.json parsing speed to ensure < 10ms execution."""
    start_time = time.perf_counter()
    iterations = 100
    for _ in range(iterations):
        _ = MCPConfig.load_from_file("mcp_config.json")
    elapsed_ms = ((time.perf_counter() - start_time) / iterations) * 1000

    assert (
        elapsed_ms < 10.0
    ), f"Average parsing time was {elapsed_ms:.2f}ms (expected < 10ms)"
