# 🌟 Hybrid Foundation: Sprint 2 Executive Summary

**Date**: March 10, 2026
**Initiative**: Unified System Improvement (Akvo RAG + Vector KB MCP Server)
**Target**: Maximize Data Quality (Accuracy) & Retrieval Speed

---

## 1. The Core Strategy: "Data Quality First"
During our ideation phase, we identified that while caching and streaming provide immediate UI speedups, they do not solve root issues with AI answer accuracy. If the underlying data is poorly extracted or chunked, the AI will confidently serve bad answers faster.

**The Pivot**: The "Hybrid Foundation" strategy defers performance-only features (Semantic Caching, Status Streaming) to Sprint 3. Instead, Sprint 2 guarantees **world-class data quality** combined with **parallel search speed**.

---

## 2. Key Technical Implementations

### A. The Foundation (Data Quality)
*   **Docling PDF Extraction**: Replacing naive character parsing with IBM Research's Docling. This allows the system to visually understand page layouts, preserving complex tables, lists, and headers perfectly.
*   **Semantic Chunking**: Moving away from arbitrary character limits. Documents will now be split based on "semantic boundaries" (complete thoughts/sentences) using embeddings, ensuring the LLM always receives full, coherent context.

### B. The Engine (Speed & Relevance)
*   **Parallel Retrieval**: Refactoring the MCP server to query all connected Knowledge Bases simultaneously via `asyncio.gather`. This turns a slow, sequential multi-KB search (e.g., 3 seconds) into a fast, sub-second search.
*   **FlashRank Reranking**: Integrating a lightweight, CPU-optimized reranker (FlashRank via LangChain). After retrieving the top chunks from all KBs, FlashRank instantly sorts them, feeding only the absolute highest-relevance context to the LLM.

---

## 3. Sprint 2 Backlog & Estimation
**Total Estimated Effort**: ~13.0 Hours (2-3 Days for a single developer)
**Total Story Points**: 21

| Story ID | Feature | Goal | Est. Time |
| :--- | :--- | :--- | :--- |
| **STORY-010** | Advanced Extraction | Implement IBM Docling for flawless PDF tables. | ~4.0 hrs |
| **STORY-011** | Semantic Chunking | Split context by "thought", not by character count. | ~4.0 hrs |
| **STORY-005** | Parallel Retrieval | Query multiple KBs simultaneously. | ~3.0 hrs |
| **STORY-006** | FlashRank Reranking | Sort context by absolute relevance before generation. | ~2.0 hrs |

*All User Stories and Acceptance Criteria are documented in `agent_docs/stories/`.*

---

## 4. Quality Gates & TDD Methodology
To ensure this critical foundation is rock-solid, we have mandated a strict testing protocol:

*   **Test-Driven Development (TDD)**: Developers must write failing unit and integration tests *before* writing any feature code.
*   **Coverage Requirement**: **90%+ test coverage** is mandatory for all new logic.
*   **Performance Benchmark**: Parallel retrieval must clock in at **<500ms** (excluding LLM generation time).
*   **Zero-Break Rollout**: All updates are strictly backward-compatible to ensure no disruption to Agriconnect mobile/playground clients.

## 5. Pros, Cons & Risks

### ✅ Pros (The "Why")
- **Massive Accuracy Boost**: Eliminates AI hallucinations caused by poorly formatted tables or cut-off sentences.
- **Global Speed**: Queries every connected Knowledge Base simultaneously, keeping retrieval time under 1.5s regardless of scale.
- **Highest Context Quality**: Guarantees the LLM only sees the absolute best information, reducing token usage and API costs.

### ⚠️ Cons & Trade-offs
- **Slower Ingestion**: Uploading and parsing new documents will take longer due to the heavy layout detection (Docling) and embedding generation (Semantic Chunking).
- **Higher CPU Usage (MCP Server)**: Running local reranking (FlashRank) requires more compute power during the search phase.

---
*Status: Ready for Team Review & Approval for Implementation.*
