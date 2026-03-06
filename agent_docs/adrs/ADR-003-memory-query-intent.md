# ADR-003: Context-Only Branching Logic for Memory Queries

## Status
Proposed

## Context
The RAG system currently treats all non-small talk/non-weather queries as `knowledge_query`, which triggers a vector search via MCP. However, certain user queries like "do you remember what we talked about?" or "summarize our last conversation" rely entirely on the `chat_history` and do not require external document retrieval. Performing a retrieval for these queries is inefficient and can lead to "Retrieval Drift" (retrieving documents that happen to contain words like "remember" or "conversation").

## Decision
We will introduce a new intent classification called `memory_query` and a corresponding workflow branch that skips the retrieval steps.

### Implementation Details:
1.  **Intent Classification**: Update `classify_intent_node` to recognize queries about chat history or memory.
2.  **Workflow Routing**: Add a conditional edge from `classify_intent` to a new `memory_node` or directly to `generate` with a flag to indicate no context is needed.
3.  **Prompt Refinement**:
    *   Ensure the `contextualize_node` handles these queries by producing a meta-query that explicitly states it's a memory recall.
    *   Update the QA prompt to be allowed to use `chat_history` even when `context` is empty if the intent is `memory_query`.

## Consequences
- **Positive**: Faster response times for memory-related queries, higher accuracy for meta-conversational questions, and reduced LLM token usage for retrieval.
- **Negative**: Adds complexity to the intent classification prompt and the state machine.
