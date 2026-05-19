# Research Findings: Joint System Improvement Plan (Akvo RAG + MCP Server)

- **Date**: 2026-03-09
- **Agents**: John (PM) 📋, Mary (Analyst) 📊, Winston (Architect) 🏗️
- **Subject**: Strategic improvements for system availability, speed, and portability across the coupled projects.

## 🔍 Architecture Analysis
The current system is split into:
1.  **Akvo RAG (Client)**: Manages UI, Chat History, and LangGraph workflow.
2.  **Vector KB MCP Server (Server)**: Manages Vector Search (ChromaDB), Embeddings, and Document Storage (MinIO).

### Observed Bottlenecks
- **Sequential Retrieval**: The MCP server queries multiple Knowledge Bases in a `for` loop, leading to linear latency increase as more KBs are added.
- **Client-Side Reranking**: The original plan to rerank in Akvo RAG requires transferring large amounts of base64 context over the wire.
- **Single Point of Failure**: If ChromaDB is slow or unresponsive, the retrieval process blocks and eventually times out.

## 🚀 Proposed Improvements

### 1. Speed (Latency & Throughput)
- **[MCP Server] Parallel KB Querying**: Use `asyncio.gather` in `kb_query_service.py` to query multiple KBs concurrently.
- **[MCP Server] Server-Side Reranking**: Introduce a new tool `query_knowledge_base_with_rerank`.
    - Allows the server to use high-speed cross-encoders like `FlashRank` directly on the retrieved chunks.
    - Only the top-5 (reranked) chunks are sent back to Akvo RAG, significantly reducing payload size.
- **[Both] Streaming Retrieval**: Investigate if MCP can stream retrieved chunks back as they are found, though current `FastMCP` implements a request-response pattern.

### 2. Availability (Resilience)
- **[MCP Server] Fallback Search**: Implement a keyword-based (BM25) fallback in the MCP server for when ChromaDB is unavailable.
- **[Akvo RAG] Local Feature Flags**: Move the "Top-K" and "Rerank Model" settings to a dynamic configuration that can be adjusted without code changes.
- **[MCP Server] Connection Pooling**: Optimize how ChromaDB and PostgreSQL connections are persisted during high concurrent load.

### 3. Ease of Use (Portability & UX)
- **[MCP Server] Multi-Project Scoping**: Allow passing a `project_id` or `tenant_id` to further isolate Knowledge Bases, making it easier to serve multiple "other projects" from a single instance.
- **[Akvo RAG] Auto-Discovery**: Improve the `MCPClientManager` to automatically detect available tools and their schemas from the MCP server during startup.
- **[Both] Standardized Deployment**: Create a unified `docker-compose` setup for "Rapid Deployment" of the entire stack for new projects.

## 📌 Implementation Roadmap
1.  **v1.1 (Speed)**: Implement Parallel Retrieval and Server-Side Reranking (FlashRank).
2.  **v1.2 (Availability)**: Add BM25 Fallback and better error handling in the MCP server.
3.  **v1.3 (Portability)**: Standardize environment variables and deployment scripts for multi-project support.
