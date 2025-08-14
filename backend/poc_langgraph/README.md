# PoC of LangGraph implementation for the MCP flow

---

## MCP Query Processing Flow

```bash
[Start Node]
    ↓
[Contextualization Node] → Makes the query self-contained (includes chat history)
    ↓
[Scoping Node] → Determines server_name, tool_name, parameters
    ↓
[Run MCP Tool Node] → Executes MCP call
    │
    ├─(error)──→ [Fallback Node]
    │
    ▼
[Post-Processing Node] → Decodes Base64 and extracts context
    ↓
[Response Generation Node] → LLM generates final answer from query + context
    ↓
[End Node] → Sends answer to UI
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

---

## Comparison: Pre-LangGraph vs. LangGraph Flow

### 📊 Visual Flow Comparison

#### Before LangGraph (Linear Flow)

```bash
User Query
    ↓
[Scoping Agent]
    ↓
[Query Dispatcher]
    ├─ Contextualize Query
    ├─ Call MCP Tool
    └─ Post-Process
    ↓
[MCP Client]
    ↓
[MCP Server → ChromaDB]
    ↓
[Query Dispatcher]
    ↓
[Response Generator]
    ↓
Answer to UI
```

#### With LangGraph (Node-Based Flow)

```bash
[Start Node]
    ↓
[Contextualization Node] → Makes the query self-contained (includes chat history)
    ↓
[Scoping Node] → Determines server_name, tool_name, parameters
    ↓
[Run MCP Tool Node] → Executes MCP call
    │
    ├─(error)──→ [Fallback Node]
    │
    ▼
[Post-Processing Node] → Decodes Base64 and extracts context
    ↓
[Response Generation Node] → LLM generates final answer from query + context
    ↓
[End Node] → Sends answer to UI
```

### 🔍 Detailed Differences

| Aspect              | Before LangGraph                                                             | With LangGraph                                                  |
| ------------------- | ---------------------------------------------------------------------------- | --------------------------------------------------------------- |
| **Structure**       | All logic is centralized in `QueryDispatcher`                                | Steps are modular and separated into distinct nodes             |
| **Error Handling**  | Errors in MCP calls must be manually handled in the middle of the dispatcher | A dedicated `Fallback Node` can handle MCP errors cleanly       |
| **Maintainability** | Changing one step can require touching unrelated logic                       | Each node can be updated independently without affecting others |
| **Debugging**       | Must sift through long log traces to locate issues                           | Can see exactly which node failed                               |
| **Reusability**     | Hard to reuse steps like contextualization or post-processing                | Nodes can be reused across different flows                      |
| **Flexibility**     | More rigid and tightly coupled                                               | Highly flexible and easy to extend                              |


### 💡 Summary
- **Before LangGraph**: Works, but tightly coupled. Harder to maintain, debug, and extend.
- **With LangGraph**: Clean modular design. Each processing step is isolated, reusable, and has clearer error handling.