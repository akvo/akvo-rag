# ADR-001: Robust Chat History and Workflow Management

- **Status**: Proposed
- **Date**: 2026-03-03
- **Architect**: Winston 🏗️

## Context

The Akvo RAG system currently suffers from "Context Bloat." Assistant messages stored in the database contain a base64-encoded prefix of the retrieved metadata and raw context (for frontend citation mapping). When these messages are retrieved for subsequent chat turns, the total token count exceeds the LLM's context window (8,192 tokens), causing a `400 BadRequest`.

Furthermore, the LangGraph-based `query_answering_workflow.py` lacks robust error handling between nodes, leading to cascading failures (`KeyError`, `ValueError`) when an LLM node fails.

## Decision

We will implement two architectural guardrails:

### 1. History Sanitization Utility
We will introduce a `strip_context_prefixes` utility in the service layer. This function will:
- Iterate through `chat_history`.
- Detect the `__LLM_RESPONSE__` delimiter.
- Remove the delimiter and all preceding text (the base64 context).
- This ensures the LLM only receives the literal dialogue, preserving the context window for actual conversation.

### 2. Fail-Safe Graph Nodes
We will modify the LangGraph nodes in `query_answering_workflow.py` to be "error-aware":
- Each node will begin by checking `state.get("error")`. If present, it will exit immediately without performing operations.
- We will replace direct dictionary access (`state["key"]`) with safe access (`state.get("key")`) or explicit validation to prevent `KeyError`.
- We will ensure the `error_handler_node` is reached whenever a terminal error occurs in the retrieval or contextualization steps.

## Alternatives Considered

- **Truncating History**: Simply reducing the number of messages (e.g., from 10 to 3) would mitigate the issue but lose valuable conversation context and still risk failure if a single turn's retrieval is very large.
- **Increasing Token Limit**: Moving to models with larger context windows (e.g., GPT-4o with 128k) is a temporary fix that increases costs and doesn't solve the underlying data-poisoning issue or the workflow fragility.

## Consequences

- **Pros**:
    - Dramatically increases the stability of multi-turn conversations.
    - Reduces latency by sending fewer tokens to the API.
    - Prevents system crashes during network or API failures.
- **Cons**:
    - Small overhead for string processing in the history-loading phase.
    - Requires developer discipline to ensure all new nodes follow the "error-aware" pattern.
