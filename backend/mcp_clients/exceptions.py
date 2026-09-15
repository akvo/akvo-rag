"""MCP Client Custom Exception Hierarchy."""
from typing import Optional


class MCPException(Exception):
    """Base exception for all MCP client operations."""

    pass


class MCPTimeoutError(MCPException):
    """Raised when an MCP tool invocation times out."""

    def __init__(
        self,
        message: str,
        server_name: Optional[str] = None,
        tool_name: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        super().__init__(message)
        self.server_name = server_name
        self.tool_name = tool_name
        self.timeout = timeout


class MCPToolExecutionError(MCPException):
    """
    Raised when a remote MCP tool returns an error status or fails
    during execution.
    """

    def __init__(
        self,
        message: str,
        server_name: Optional[str] = None,
        tool_name: Optional[str] = None,
    ):
        super().__init__(message)
        self.server_name = server_name
        self.tool_name = tool_name


class MCPConfigurationError(MCPException):
    """
    Raised when an unknown server, tool, or unsupported transport is requested.
    """

    def __init__(
        self,
        message: str,
        server_name: Optional[str] = None,
        tool_name: Optional[str] = None,
    ):
        super().__init__(message)
        self.server_name = server_name
        self.tool_name = tool_name
