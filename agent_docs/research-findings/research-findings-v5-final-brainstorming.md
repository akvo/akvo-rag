# Research Findings: Finalized Unified Brainstorming (Akvo RAG + MCP Server)

- **Date**: 2026-03-09
- **Agents**: John (PM) 📋, Mary (Analyst) 📊, Winston (Architect) 🏗️
- **Status**: Research & Brainstorming Complete ✅

## 🚀 Pillar 1: Speed (The "Fast" System)
- **Parallel Retrieval Use Case - Technical Deep Dive**:
    - **Current Sequential Flow**:
        ```mermaid
        sequenceDiagram
            Akvo-RAG->>MCP: Query "Project X Sustainability"
            MCP->>Chroma (KB_Proj_Specs): Search (1200ms)
            Chroma (KB_Proj_Specs)-->>MCP: Results
            MCP->>Chroma (KB_Environmental): Search (1100ms)
            Chroma (KB_Environmental)-->>MCP: Results
            MCP->>Chroma (KB_Financials): Search (1300ms)
            Chroma (KB_Financials)-->>MCP: Results
            MCP-->>Akvo-RAG: Combined Results (3600ms+)
        ```
    - **Proposed Parallel Flow**:
        ```mermaid
        sequenceDiagram
            Akvo-RAG->>MCP: Query "Project X Sustainability"
            Parallel Execution Start:
            MCP->>Chroma (KB_Proj_Specs): Search (1200ms)
            MCP->>Chroma (KB_Environmental): Search (1100ms)
            MCP->>Chroma (KB_Financials): Search (1300ms)
            Parallel Execution End:
            MCP-->>Akvo-RAG: Combined Results (~1300ms)
        ```
    - **Impact**: In a real-world scenario where a user needs info from multiple departments (e.g., Specs, Env, Finance), the response time is no longer "KBs × Time", but simply the time of the single slowest KB. This scales perfectly as we add more knowledge sources.
- **Metadata Streaming**:
    - We will implement "Process Transparency." Before the tokens stream, the UI will display status updates (e.g., "Analyzing intent...", "Retrieving from KBs...", "Reranking candidates...") so the user knows the system is working.

## 🛡️ Pillar 2: Availability (The "Resilient" System)
- **Hybrid Search (Vector + BM25)**:
    - We will implement **Keyword Fallback**. If the vector embedding service (OpenAI/Ollama) is slow or the Vector DB (Chroma) fails, the MCP server will automatically switch to a standard SQL-based keyword search (BM25) over the stored document text.
    - *Result*: The system stays functional even if the "AI" retrieval layer is offline.

## 🌍 Pillar 3: Ease of Use (The "Scalable" System)
- **Deployment & Multi-Tenancy**:
    - **Current Policy**: We maintain the "1 Project = 1 RAG + 1 MCP" isolation for now (Akvo vs Agriconnect).
    - **MCP Research**: Current code supports multiple KBs but lacks `project_id` database-level isolation. Our separate deployments handle this perfectly today.
- **Unified Configuration**:
    - We will focus on a "Unified Environment Sync" script to ensure secrets and shared settings (like `TOP_K` or LLM API keys) are consistent across both repo deployments.

## 📌 Next Steps: Architect Phase
1.  **ADR-005**: Unified Parallel & Hybrid Search Architecture.
2.  **ADR-006**: Semantic Caching & Metadata Streaming Protocol.
3.  **User Stories**: Break these down for Amelia (Dev) to implement.
