# PoC of LangGraph implementation for the MCP flow

## MCP Query Processing Flow

```bash
[Start Node]
↓
[Contextualization Node] → Ensure the query is self-contained (include chat history).
↓
[Scoping Node] → Determine `server_name`, `tool_name`, and `parameters`.
↓
[Run MCP Tool Node] → Retrieve context from the MCP server.
↓
[Post-Processing Node] → Decode Base64 and extract the text context.
↓
[Response Generation Node] → LLM generates the answer using the context + query.
↓
[End Node] → Send the final answer to the UI.
```

1. **Contextualization Node**
   - Rewrite the user query so it’s self-contained for more accurate retrieval.
   - Example:
     - Input: "Who discovered electricity?"
     - Output: "Who discovered electricity according to the documents available in the system?"

2. **Scoping Node**
   - Determine:
     - `server_name` (which MCP server to call)
     - `tool_name` (which tool to use)
     - `params` (parameters needed)
   - Output: JSON ready for `run_mcp_tool`.

3. **Run MCP Tool Node**
   - Call MCP server via `MultiMCPClientManager.run_tool()`.
   - Output: Raw MCP tool data (e.g., Base64 encoded context).

4. **Post-Processing Node**
   - Decode Base64 → plain text.
   - Clean/normalize context (trim spaces, fix formatting).

5. **Response Generation Node**
   - Input: Original user query + cleaned context.
   - Use LLM to generate natural, final answer.

6. **End Node**
   - Send the final answer to the UI.
