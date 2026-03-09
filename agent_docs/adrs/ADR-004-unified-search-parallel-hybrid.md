# ADR-004: Unified Search Architecture (Parallel & Hybrid)

## Status
Proposed

## Context
The current RAG system queries multiple Knowledge Bases (KBs) sequentially in the MCP server. This leads to linear latency increases as the number of KBs grows. Additionally, the system currently relies solely on vector similarity search, which can fail if the embedding service is down or if exact keyword matches (e.g., project IDs) are required.

## Decision
We will transition to a **Unified Search Architecture** implemented within the `vector-knowledge-base-mcp-server`:

1.  **Parallel Multi-KB Retrieval**: Use `asyncio.gather` to perform concurrent searches across all target collections.
2.  **Hybrid Search (Vector + BM25)**: Every query will trigger both a vector similarity search and a keyword-based search (BM25 fallback).
3.  **Server-Side Re-ranking**: Initial retrieval will return a larger set of candidates (e.g., top 50), which will be re-ranked using `FlashRank` directly on the MCP server before being returned to the RAG orchestrator.

## Consequences

### Pros
- **Consistent Latency**: Querying multiple KBs takes only as long as the slowest individual search.
- **Resilience**: The system remains functional via keyword search even if embedding models fail.
- **Payload Efficiency**: Only the most relevant re-ranked chunks are sent over the network.

### Cons
- **Compute Overhead**: The MCP server requires more CPU for local re-ranking and keyword indexing.
- **Implementation Complexity**: Requires managing concurrent database connections and merging results from hybrid sources.
