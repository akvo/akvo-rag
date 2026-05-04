# Product Brief: Akvo RAG Intelligence Layer

**Status**: Ideation / Approved
**Owner**: John (PM)
**Sprint**: Sprint 3 (Intelligence & Optimization)

## 1. Problem Statement
As Akvo RAG matures, we face two primary bottlenecks:
1. **Redundancy & Cost**: Common organizational questions are processed repeatedly, leading to unnecessary LLM costs and latency.
2. **Precision & Noise**: Raw vector retrieval (Stage 1) often returns contextually irrelevant "noisy" chunks that confuse the LLM and bloat the token window.

## 2. Target Users
- **Enterprise Users**: Who require instantaneous answers to common questions and highly precise citations.
- **System Admins**: Who need to control LLM token budgets and maintain system efficiency.

## 3. Value Proposition
This phase introduces the "Intelligence Layer" to bridge the gap between raw retrieval and generation:
1. **Semantic Cache**: Returns answers for previously seen queries in <300ms, bypassing the expensive LLM generation step.
2. **Context Reranker**: Filters the top-50 vector results down to the top-5 most relevant chunks using high-precision cross-encoders (FlashRank), reducing hallucinations and token waste.

## 4. Core Features (MVP)
- **[MUST] Semantic Query Caching**: Redis-based storage for embeddings and answers with a strict (0.95+) similarity threshold.
- **[MUST] Event-Driven Cache Invalidation**: Automatic purge of cache entries when a Knowledge Base is updated.
- **[MUST] Server-Side Reranking**: Integration of FlashRank in the MCP server to provide Stage-2 precision filtering.
- **[MUST] Hybrid Fallback**: BM25 keyword search as a fallback for pure vector search failures.
- **[SHOULD] RAGAS Integration**: Automated evaluation of retrieval precision (Hit Rate) and faithfulness.

## 5. Success Metrics
- **Performance**: 40%+ reduction in average TTFT for repeated queries.
- **Accuracy**: 20% improvement in "Faithfulness" RAGAS score.
- **Cost**: 30% reduction in average tokens per query via strict reranking selection.

## 6. Constraints & Assumptions
- Requires Redis for semantic caching.
- Reranking will be performed on the MCP server to keep the orchestrator lightweight.
- Assumes vector embeddings are consistent across queries.

## 7. Out of Scope
- Personalized caching (user-specific answers).
- Real-time learning from user corrections (Post-MVP).
