# STORY-001: Chat History Sanitization

- **Status**: COMPLETED ✅
- **Sprint**: 1
- **Developer**: Amelia 💻

## ⏱️ Effort Tracking
- **Estimated Time**: 2.0 hours
- **Actual Time**: 1.5 hours

## 🎯 Goal
**As a** system developer
**I want** to strip internal context prefixes from chat history
**So that** the LLM context window is not overwhelmed by redundant metadata.

## 📝 Acceptance Criteria

### UAC (User Acceptance Criteria)
- [x] Chat history remains readable across multiple turns.
- [x] No `context_length_exceeded` errors when using knowledge bases with large document context.
- [x] Citations still appear correctly in the UI.

### TAC (Technical Acceptance Criteria)
- [x] Implement `strip_context_prefixes(messages: List[Dict]) -> List[Dict]` utility in `backend/app/services/utils/history_utils.py`.
- [x] The utility removes all text before and including `__LLM_RESPONSE__` in assistant messages.
- [x] Integrate utility in `stream_mcp_response` (`chat_mcp_service.py`).
- [x] 100% test pass rate for sanitization logic.

## 🛠️ Technical Notes
- Delimiter: `__LLM_RESPONSE__`
- Impact: Reduces token count per multi-turn message by ~2KB-50KB.

---

# STORY-002: Robust Workflow Nodes

- **Status**: COMPLETED ✅
- **Sprint**: 1
- **Developer**: Amelia 💻

## ⏱️ Effort Tracking
- **Estimated Time**: 2.5 hours
- **Actual Time**: 2.0 hours

## 🎯 Goal
**As a** system developer
**I want** LangGraph nodes to be error-aware and fail-safe
**So that** transient API errors do not cause internal server crashes like KeyError or ValueError.

## 📝 Acceptance Criteria

### UAC (User Acceptance Criteria)
- [x] System provides a friendly fallback message ("I'm having trouble with that right now") instead of a silent failure or broken UI.
- [x] Retrying the message works if the second attempt succeeds.

### TAC (Technical Acceptance Criteria)
- [x] Each node in `query_answering_workflow.py` checks `state.get("error")` at the start.
- [x] Use safe dictionary access (`.get()`) for all state keys.
- [x] `run_mcp_tool_node` validates `server_name` presence.
- [x] Unit tests simulate failure states to verify "fail-fast" behavior.

## 🛠️ Technical Notes
- Core fix: Prevent cascading errors in the LangGraph execution flow.
- Files: `backend/app/services/query_answering_workflow.py`
