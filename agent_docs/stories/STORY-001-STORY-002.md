# STORY-001: Chat History Sanitization

- **Status**: Approved
- **Sprint**: 1
- **Developer**: Amelia 💻

**As a** system developer
**I want** to strip internal context prefixes from chat history
**So that** the LLM context window is not overwhelmed by redundant metadata.

### Acceptance Criteria
- [ ] Implement `strip_context_prefixes(messages: List[Dict]) -> List[Dict]` utility.
- [ ] The utility must remove any text before and including the `__LLM_RESPONSE__` delimiter in assistant messages.
- [ ] The utility must handle messages that do *not* contain the delimiter without modification.
- [ ] Apply this utility in `stream_mcp_response` before passing history to the LangGraph `state`.

### Technical Notes
- File: `backend/app/services/chat_mcp_service.py`
- Delimiter: `__LLM_RESPONSE__`
- The prefix is usually a base64 encoded string.

### Definition of Done
- [ ] Unit tests for the sanitization logic pass.
- [ ] Integration test verifies the final LLM payload is clean.
- [ ] Documentation updated in `architecture.md`.
---

# STORY-002: Robust Workflow Nodes

- **Status**: Approved
- **Sprint**: 1
- **Developer**: Amelia 💻

**As a** system developer
**I want** LangGraph nodes to be error-aware and fail-safe
**So that** transient API errors do not cause internal server crashes like KeyError or ValueError.

### Acceptance Criteria
- [ ] Each node in `query_answering_workflow.py` must check `state.get("error")` at the start.
- [ ] If an error is present, the node must return the state immediately.
- [ ] Replace all direct key access (e.g., `state["contextual_query"]`) with safe `.get()` or guarded access.
- [ ] `run_mcp_tool_node` must validate that `server_name` is present before calling the manager.

### Technical Notes
- File: `backend/app/services/query_answering_workflow.py`
- Nodes: `classify_intent_node`, `small_talk_node`, `contextualize_node`, `scoping_node`, `run_mcp_tool_node`, `post_processing_node`.

### Definition of Done
- [ ] Unit tests for nodes with injected error state pass (verifying they skip logic).
- [ ] System handles an LLM failure without raising a Python exception.
