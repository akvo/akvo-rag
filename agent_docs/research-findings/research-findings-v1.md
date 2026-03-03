# Research Findings: Chat Context Length and Workflow Failures (v1)

- **Date**: 2026-03-03
- **Analyst**: Mary 📊
- **Subject**: Investigation into `context_length_exceeded` and cascading backend errors in the query answering workflow.

## 📋 Problem Statement

Users are experiencing critical chat failures when using the "Living Income KB". The errors manifest as inconsistent responses, followed by a complete system crash (`ValueError: Server None not found`) and fallback responses.

## 🔍 Investigation Methodology

1.  **Log Analysis**: Reviewed backend tracebacks to identify the sequence of node failures in `query_answering_workflow.py`.
2.  **State Inspection**: Analyzed `GraphState` and how `chat_history` is populated in `chat_mcp_service.py`.
3.  **Payload Review**: Examined the structure of assistant messages stored in the database.

## 💡 Findings

### 1. Cumulative Context Poisoning
The system uses a "grounding" mechanism that embeds retrieval context into the assistant's response.
- **Mechanism**: A base64-encoded prefix (e.g., `base64(json_context) + "__LLM_RESPONSE__"`) is prepended to the text.
- **Issue**: This prefix is meant for the frontend to render citations, but it remains in the database. When the next turn starts, `chat_mcp_service` pulls these raw strings into the `chat_history`.
- **Impact**: The LLM receives thousands of tokens of redundant, encoded data in every turn. The token count grows exponentially until it hits the 8,192 limit.

### 2. Workflow Fault Tolerance
The `LangGraph` implementation assumes success in every node.
- **Failed Step**: `contextualize_node` fails when the LLM returns a 400 error.
- **Cascading Failure**: The workflow continues to `scoping_node`. Since `contextualize_node` didn't set `contextual_query`, `scoping_node` raises a `KeyError`.
- **Termination Failure**: `run_mcp_tool_node` then tries to execute with an empty scope, leading to a `ValueError`.

## 📌 Requirements for Resolution

- **RQ.1 (Functional)**: Chat history must be "sanitized" before being sent to any LLM node. All `__LLM_RESPONSE__` markers and their preceding base64 text must be stripped.
- **RQ.2 (Non-Functional)**: The workflow must implement "Fail-Fast" behavior. If a node fails, subsequent logic nodes must be skipped, routing directly to the `error_handler`.
- **RQ.3 (Functional)**: Nodes must use safe dictionary access (`.get()`) to prevent `KeyError` during error states.

## 🚀 Recommendation
Hand off to **Winston (Architect)** to design the history-stripping utility and the fail-safe graph routing.
