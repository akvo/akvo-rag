# Feature Document: Semantic Query Caching

**Status**: Ideation

## 1. Problem Statement
As Akvo RAG scales, common questions (e.g., "What is a Living Income?", "Show me the project timeline") are asked repeatedly by different users. Currently, every single query triggers:
1. Contextualization (LLM Call)
2. Vector Retrieval (MCP/VDB Call)
3. Final Answer Generation (LLM Call)

This results in unnecessary latency (Time-to-First-Token > 1s), redundant token costs, and increased load on our vector database. We lack a "fast path" for semantically similar queries.

## 2. Proposed Solution: The "Fast Path" (Orchestrator-Side)
Implement a Redis-based **Semantic Cache** in the Akvo RAG backend that intercepts queries before they hit the LLM or Knowledge Engine (MCP).
- **Mechanism**: Store the embedding of a successful query-answer pair in Redis.
- **Threshold**: When a new query arrives, calculate its similarity to cached queries. If the similarity score is above a strict threshold (e.g., 0.95), return the cached answer instantly.

## 3. Analysis for Management

### Pros
- **Lightning Fast Response**: TTFT drops from ~1200ms to <300ms for cached hits.
- **Cost Reduction**: Bypasses LLM generation, potentially saving 40-60% on token costs for common organizational queries.
- **Consistency**: Ensures the "official" best answer is consistently delivered for standard questions.
- **Scalability**: Reduces the number of concurrent LLM requests, allowing the system to handle more users on fixed credit limits.

### Cons
- **Stale Answers**: If the Knowledge Base is updated, the cache might serve an old answer. (Mitigation: Implement strict cache invalidation on KB updates).
- **Storage Overhead**: Requires Redis and storage for vector embeddings (though small compared to the full KB).
- **False Positives**: Risk of returning a "close but wrong" answer if the similarity threshold is too low.

### Alternatives
| Alternative | Description | Comparison |
| :--- | :--- | :--- |
| **Simple KV Cache** | Exact string matching only. | **Lower Hit Rate**: Questions like "What is X?" and "Define X" wouldn't match. |
| **LLM-Based Router** | Use a cheap model (GPT-3.5) to check if we should use cache. | **Higher Latency**: Still requires one LLM call before the answer. |
| **Client-Side Cache** | Cache locally in the user's browser. | **Siloed**: Doesn't benefit from other users' queries; no shared "company knowledge" speedup. |

## 4. Industry Context & Best Practices
How others solve this:
- **GPTCache (Zilliz)**: The most popular open-source library for this. It uses a separate vector store (like Milvus or FAISS) just for the cache to enable lightning-fast similarity lookups.
- **LangChain/LlamaIndex**: Both frameworks offer built-in `RedisSemanticCache` modules that standardize how embeddings are stored and compared.
- **Best Practice: "The 0.95 Rule"**: Industry leaders typically set a very high similarity threshold (0.95+) for direct cache returns. If the similarity is between 0.85 and 0.95, the system might use the cache as a "hint" but still run a cheap LLM check.
- **Best Practice: Explicit Invalidation**: Unlike web caching (Time-to-Live), RAG caching is "Event-Driven." The cache MUST be purged immediately when the source Knowledge Base changes.

## 5. Goals & Requirements
- **[MUST]** Integrate Redis as the semantic storage layer.
- **[MUST]** Implement a `SemanticCacheService` with `get` and `set` methods.
- **[MUST]** Define a configurable similarity threshold.
- **[MUST]** **Auto-Invalidation**: Purge cache entries associated with a Knowledge Base ID whenever documents are added/deleted.
- **[SHOULD]** Dashboard view for "Cache Hit Rate" in Flower or a custom admin page.

## 5. User Impact
- **End Users**: Immediate "wow" factor when the system replies instantly to common questions.
- **Organization**: Predictable LLM costs and reduced infrastructure strain.

## 6. Risks & Mitigations
- **Risk**: Cache Invalidation failure.
- **Mitigation**: Hook the invalidation logic directly into the Celery `upload_task` completion signal.
