---
trigger: model_decision
description: When working with MCP (Model Context Protocol) integration for knowledge base queries
---

## Model Context Protocol (MCP) Integration

Akvo RAG depends on an external MCP server for knowledge base discovery and querying.

### Implementation Pattern

- **Discovery Manager**: Use `backend/mcp_clients/mcp_discovery_manager.py` to discover tools and resources.
- **Client Manager**: Use `backend/mcp_clients/mcp_client_manager.py` for persistent connections (SSE).
- **Service Layer**: Business logic should use `chat_mcp_service.py` to interact with MCP clients.

### Tool Usage Rules

1. **Discovery First**: Always check `mcp_discovery.json` (or the manager) before assuming tool availability.
2. **Schema Validation**: Validate input against the `inputSchema` provided during discovery.
3. **Async SSE**: MCP connections are SSE-based. Handle timeouts and connection losses gracefully.

### Configuration

Ensure these environment variables are correctly configured:
- `KNOWLEDGE_BASES_MCP`: The SSE endpoint (e.g., `https://api.example.com/mcp/`).
- `KNOWLEDGE_BASES_API_KEY`: Auth token for the MCP server.

### Maintenance

If tool names or signatures change on the MCP server, re-run discovery or restart the backend to refresh `mcp_discovery.json`.
