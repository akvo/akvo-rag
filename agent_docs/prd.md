# PRD: Akvo RAG

## 1. Vision & Goals
**Vision**: To be the most accessible and flexible self-hosted RAG platform for developers and small-to-medium enterprises.
**Goals**:
- Provide a seamless "Chat with your Docs" experience.
- Enable autonomous knowledge base selection (ASQ).
- Ensure high performance and scalability via async architectures.

## 2. Target Users
### 2.1 The Developer (Devin)
- **Pain Points**: Hard to integrate RAG into existing apps; vector DB management is tedious.
- **Needs**: Simple REST API, clear documentation, and easy data ingestion.

### 2.2 The Knowledge Worker (Kara)
- **Pain Points**: Overwhelmed by internal documents; can't find specific info quickly.
- **Needs**: Intuitive chat interface, "source of truth" citations.

### 2.3 The Admin (Arthur)
- **Pain Points**: Security concerns with cloud-based LLMs; monitoring system health.
- **Needs**: Self-hosting, local LLM support, dashboard for job monitoring.

## 3. User Journeys
### 3.1 Document Ingestion
1. User logs into the Web UI.
2. User creates a new "Knowledge Base" (KB).
3. User uploads multiple PDF/TXT files.
4. System triggers background jobs for chunking and embedding.
5. User monitors progress via a status bar or dashboard.

### 3.2 High-Performance Autonomous Querying (ASQ)
1. User asks a broad question: "How do we handle vacation requests?"
2. **System Fast-Path (Cache Hit)**: The semantic router detects a similar past question and streams the cached answer instantly (0 LLM tokens used).
3. **System Slow-Path (Cache Miss)**: System analyzes intent to identify KBs, retrieves broad context, re-ranks it to just the most critical sentences to save tokens, and streams the LLM response.
4. User receives the answer with citations with an initial response time under 1 second.

## 4. Feature Requirements

### 4.1 Knowledge Management
- **[MUST]** Create, Read, Update, Delete (CRUD) for Knowledge Bases.
- **[MUST]** Support for PDF, DOCX, and TXT uploads.
- **[SHOULD]** URL/Web scraping ingestion.

### 4.2 Query Interface & Optimization
- **[MUST]** Real-time streaming chat interface using Server-Sent Events (SSE).
- **[MUST]** Semantic Query Caching to return repeated or highly similar questions instantly, bypassing the LLM.
- **[MUST]** **Strict Cache Invalidation**: The system must automatically purge all associated semantic cache entries whenever a Knowledge Base is modified (documents added or removed) to prevent serving stale answers.
- **[MUST]** Source citations (showing which part of which doc was used).
- **[MUST]** Context Re-ranking pipeline to filter raw vector search results to only the top, most relevant chunks before sending to the LLM (minimizes prompt size).
- **[SHOULD]** History management (saving and naming conversations).

### 4.3 System Administration
- **[MUST]** Admin user creation via seeder.
- **[MUST]** Monitoring dashboard for background tasks (Flower integration).
- **[MUST]** Prompt management system (Dynamic Prompt Service).

## 5. Non-Functional Requirements
- **Performance**: Time-To-First-Token (TTFT) must be <1000ms. Semantic cache hits must respond within <300ms.
- **Efficiency**: RAG queries must enforce strict token budgets for Context inclusion (e.g., max 2048 context tokens via re-ranking) to control LLM provider costs.
- **Security**: JWT-based authentication; Argon2 password hashing.
- **Scalability**: Decoupled API and Worker processes via RabbitMQ.
- **Extensibility**: Support for custom LLM providers via standardized interfaces.

## 6. Success Metrics
- **RAGAS Score**: > 0.85 for Context Precision (high precision = less token waste) and Faithfulness.
- **Performance**: P95 TTFT under 1 second.
- **Efficiency**: >40% Cache Hit Rate on repeated organizational queries; 30% reduction in average token usage per query via re-ranking.
- **Uptime**: 99.9% for core API services.
- **User Satisfaction**: Implicit feedback (copying to clipboard) and explicit thumbs up/down integration.

## 7. Out of Scope
- Direct integration with multi-modal LLMs (Images/Video) for now.
- Enterprise-grade IAM (LDAP/AD) - will rely on built-in RBAC.
