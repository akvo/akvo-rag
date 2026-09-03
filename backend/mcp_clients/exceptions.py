"""MCP Client Custom Exception Hierarchy."""


class MCPException(Exception):
    """Base exception for all MCP client operations."""

    pass


class MCPTimeoutError(MCPException):
    """Raised when an MCP tool invocation times out."""

    pass


class MCPToolExecutionError(MCPException):
    """
    Raised when a remote MCP tool returns an error status or fails
    during execution.
    """

    pass


class MCPConfigurationError(MCPException):
    """
    Raised when an unknown server, tool, or unsupported transport is requested.
    """

    pass
