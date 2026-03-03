# STORY-001: Chat History Sanitization

- **Status**: COMPLETED ✅
- **Sprint**: 1
- **Developer**: Amelia 💻
- **Total Effort**: 1.5 hours

**As a** system developer
**I want** to strip internal context prefixes from chat history
**So that** the LLM context window is not overwhelmed by redundant metadata.

### Effort Breakdown
| Phase | Duration | Activities |
| :--- | :--- | :--- |
| **Analyze** | 15m | Identified trace-back and context bloat. |
| **Architect** | 15m | Designed `strip_context_prefixes` utility. |
| **Implement** | 40m | Utility implementation and service integration. |
| **Test** | 20m | Unit tests in `test_history_utils.py`. |

### Acceptance Criteria
- [x] Implement `strip_context_prefixes(messages: List[Dict]) -> List[Dict]` utility.
- [x] The utility must remove any text before and including the `__LLM_RESPONSE__` delimiter in assistant messages.
- [x] The utility must handle messages that do *not* contain the delimiter without modification.
- [x] Apply this utility in `stream_mcp_response` before passing history to the LangGraph `state`.

### Technical Notes
- File: `backend/app/services/chat_mcp_service.py`
- Delimiter: `__LLM_RESPONSE__`

### Definition of Done
- [x] Unit tests for the sanitization logic pass.
- [x] Integration test verifies the final LLM payload is clean.
- [x] Documentation updated in `architecture.md`.

---

# STORY-002: Robust Workflow Nodes

- **Status**: COMPLETED ✅
- **Sprint**: 1
- **Developer**: Amelia 💻
- **Total Effort**: 2.0 hours

**As a** system developer
**I want** LangGraph nodes to be error-aware and fail-safe
**So that** transient API errors do not cause internal server crashes like KeyError or ValueError.

### Effort Breakdown
| Phase | Duration | Activities |
| :--- | :--- | :--- |
| **Analyze** | 15m | Root cause of cascading node failures. |
| **Architect** | 15m | ADR-001: Error-checking node pattern. |
| **Implement** | 50m | Refactoring 6 workflow nodes for resiliency. |
| **Test** | 30m | 4 specialized integration tests in `test_resiliency_edge_cases.py`. |
| **Document** | 10m | Updated User Guide and README features. |

### Acceptance Criteria
- [x] Each node in `query_answering_workflow.py` must check `state.get("error")` at the start.
- [x] If an error is present, the node must return the state immediately.
- [x] Replace all direct key access (e.g., `state["contextual_query"]`) with safe `.get()` or guarded access.
- [x] `run_mcp_tool_node` must validate that `server_name` is present before calling the manager.

### Technical Notes
- File: `backend/app/services/query_answering_workflow.py`
- Nodes: `classify_intent_node`, `small_talk_node`, `contextualize_node`, `scoping_node`, `run_mcp_tool_node`, `post_processing_node`.

### Definition of Done
- [x] Unit tests for nodes with injected error state pass (verifying they skip logic).
- [x] System handles an LLM failure without raising a Python exception.
- [x] Integration test verifies that nodes handle missing state safely.
