import json
import os
from pathlib import Path
import re
from typing import Annotated, Any, Dict, List, Literal, Optional, Tuple, Union
from pydantic import BaseModel, Field


class InputSchemaProperty(BaseModel):
    """Represents a JSON Schema property definition."""

    type: str
    description: Optional[str] = None
    default: Optional[Any] = None
    items: Optional[Dict[str, Any]] = None


class InputSchema(BaseModel):
    """Represents a JSON Schema object for tool input parameters."""

    type: Literal["object"] = "object"
    properties: Dict[str, InputSchemaProperty] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)


class MCPToolDefinition(BaseModel):
    """Declarative definition of an MCP tool."""

    name: str
    description: str
    endpoint: Optional[str] = None  # Used for REST transport
    method: Optional[Literal["GET", "POST", "PUT", "DELETE"]] = "POST"
    inputSchema: InputSchema


class BaseServerConfig(BaseModel):
    """Base configuration common to all MCP servers."""

    name: str
    timeout_seconds: int = 30
    tools: List[MCPToolDefinition] = Field(default_factory=list)


class RedisQueueServerConfig(BaseServerConfig):
    """Configuration for microservices using native Redis Queue RPC."""

    transport: Literal["redis_queue"]
    request_queue: str = "mcp:vector:requests"
    response_queue_prefix: str = "mcp:vector:responses"


class RestServerConfig(BaseServerConfig):
    """Configuration for external tools using REST HTTP transport."""

    transport: Literal["rest"]
    endpoint_url: str


ServerConfigUnion = Annotated[
    Union[RedisQueueServerConfig, RestServerConfig],
    Field(discriminator="transport"),
]


class MCPConfig(BaseModel):
    """Root declarative MCP registry schema and static loader."""

    version: str = "1.0"
    servers: Dict[str, ServerConfigUnion] = Field(default_factory=dict)

    @classmethod
    def _resolve_config_path(cls, config_path: str) -> Path:
        """Resolves the configuration file path robustly."""
        candidate = Path(config_path)
        if candidate.is_file():
            return candidate

        # If relative, search relative to current file's backend directory
        backend_dir = Path(__file__).resolve().parent.parent.parent
        candidate_in_backend = backend_dir / config_path
        if candidate_in_backend.is_file():
            return candidate_in_backend

        # Check current working directory
        cwd_candidate = Path.cwd() / config_path
        if cwd_candidate.is_file():
            return cwd_candidate

        raise FileNotFoundError(
            f"MCP configuration file not found at: {config_path}"
        )

    @classmethod
    def load_from_file(
        cls, config_path: str = "mcp_config.json"
    ) -> "MCPConfig":
        """
        Loads and parses mcp_config.json with environment variable
        substitution (${VAR:-default}).
        """
        target_file = cls._resolve_config_path(config_path)

        with open(target_file, "r", encoding="utf-8") as f:
            raw_text = f.read()

        def env_replacer(match: re.Match) -> str:
            var_expr = match.group(1)
            if ":-" in var_expr:
                var_name, default_val = var_expr.split(":-", 1)
                return os.getenv(var_name, default_val)
            return os.getenv(var_expr, "")

        substituted_text = re.sub(r"\$\{([^}]+)\}", env_replacer, raw_text)
        data = json.loads(substituted_text)
        return cls.model_validate(data)

    def get_server(self, server_name: str) -> Optional[ServerConfigUnion]:
        """Retrieve server configuration by name."""
        return self.servers.get(server_name)

    def get_tool(
        self, server_name: str, tool_name: str
    ) -> Optional[MCPToolDefinition]:
        """Retrieve specific tool definition for a given server."""
        server = self.get_server(server_name)
        if not server:
            return None
        for tool in server.tools:
            if tool.name == tool_name:
                return tool
        return None

    def get_server_for_tool(
        self, tool_name: str
    ) -> Optional[Tuple[str, ServerConfigUnion, MCPToolDefinition]]:
        """Find server hosting a tool by tool name."""
        for server_name, server in self.servers.items():
            for tool in server.tools:
                if tool.name == tool_name:
                    return server_name, server, tool
        return None

    def list_tools(
        self, server_name: Optional[str] = None
    ) -> List[MCPToolDefinition]:
        """List all tools across all servers or for a specific server."""
        if server_name:
            server = self.get_server(server_name)
            return list(server.tools) if server else []

        tools: List[MCPToolDefinition] = []
        for server in self.servers.values():
            tools.extend(server.tools)
        return tools
