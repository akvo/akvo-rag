# ADR-005: Orchestrator Performance (Caching & Streaming)

## Status
Proposed

## Context
Repeated queries for the same information result in redundant LLM costs and latency. Furthermore, the user experience during long-running retrieval/reranking phases is opaque, with users seeing only a generic loading spinner.

## Decision
We will implement performance and UX optimizations in the **Akvo RAG Backend** (the Orchestrator):

1.  **Semantic Query Caching**: Use Redis to store query embeddings and their respective answers. Use a 0.95 similarity threshold for instant cache hits.
2.  **Auto-Invalidation**: Hook into the `upload_task` to purge cache entries for specific Knowledge Base IDs whenever new documents are processed.
3.  **Metadata Streaming Protocol**: Extend the Server-Sent Events (SSE) stream to include "Process Transparency" markers (e.g., `searching`, `reranking`, `generating`) before the final text tokens begin.

## Consequences

### Pros
- **Instant Responses**: TTFT < 300ms for common questions.
- **Improved UX**: Users feel the system is "thinking" and "working" due to real-time status updates.
- **Cost Savings**: Drastically reduced LLM generation costs for repeated queries.

### Cons
- **Cache Staleness**: Risk of serving outdated info if invalidation logic fails or is delayed.
- **State Management**: The UI must now handle mixed streams of metadata and content tokens.
