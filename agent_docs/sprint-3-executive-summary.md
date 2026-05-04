# 🚀 Phase 2 & Scale: Sprint 3 Executive Summary (Deferred)

**Initiative**: Unified System Improvement (Akvo RAG + Vector KB MCP Server)
**Target**: Performance (Caching), UX (Status Streaming), and DevEx (Automation)

---

## 1. The Strategy: "Scale & Resilience"
Once the **Hybrid Foundation** (Sprint 2) is verified and accurate, Sprint 3 focuses on making the system significantly faster, more transparent to the user, and easier to deploy. We deferred these features to ensure we don't scale or cache inaccurate data.

---

## 2. Key Technical Implementations

### A. Performance & UX
*   **Semantic Caching (Akvo RAG)**: Integrating Redis to cache high-similarity query answers. If a user asks a question that has already been answered (e.g., >0.95 similarity), the system instantly returns the cached answer (<300ms) without hitting the LLM or vector DB, saving severe processing time and API costs.
*   **Unified Status Streaming (Akvo RAG)**: Implementing a real-time status protocol via SSE and WebSockets. Users will no longer see a generic "Loading" spinner. Instead, they will see granular steps: *Searching -> Reranking -> Generating*. This drastically improves the perceived speed and user trust.

### B. Developer Experience (DevEx)
*   **Unified Setup Automation**: Creating a master `unified-setup.sh` script to synchronize environment variables and API keys (`.env`) between the Akvo RAG interface and the MCP Server. This guarantees that new team members or new deployments can spin up the entire multi-repo architecture in under 5 minutes without "Connection Refused" errors.

---

## 3. Sprint 3 Backlog & Estimation
**Total Estimated Effort**: ~8.5 Hours (1.5 Days for a single developer)
**Total Story Points**: 15

| Story ID | Feature | Goal | Est. Time |
| :--- | :--- | :--- | :--- |
| **STORY-007** | RAG Redis Semantic Cache | Instant answers for frequent questions. | ~4.0 hrs |
| **STORY-008** | Unified Status Streaming | Real-time UI updates (Searching, Generating). | ~3.0 hrs |
| **STORY-009** | Unified Setup Automation | 5-minute local spin-up script. | ~1.5 hrs |

*All User Stories and Acceptance Criteria are documented in `agent_docs/stories/`.*

---

## 4. Pros, Cons & Risks

### ✅ Pros (The "Why")
- **Massive Cost Savings**: Bypassing the LLM for repeated questions drops API costs to $0 for those queries.
- **Instantaneous UX**: Cached answers return in <300ms, making the app feel incredibly fast.
- **User Trust**: Granular status streaming (Search -> Rerank -> Generate) prevents users from thinking the app is "stuck".
- **Frictionless Onboarding**: The unified setup script eliminates hours of configuration debugging for new developers.

### ⚠️ Cons & Trade-offs
- **Memory Overhead**: Requires Redis to be continuously running, demanding more RAM on both local and production servers.
- **Cache Invalidation Complexity**: If a source document is deleted or updated, the cache MUST be strictly invalidated to prevent the RAG from serving "stale" or incorrect answers.
- **Client Sync**: Updating the status protocol requires careful coordination across multiple clients (Next.js, Widget, Mobile App) to prevent visual bugs.

---

## 5. Transition Criteria
Work on Sprint 3 should **not** begin until Sprint 2 (Hybrid Foundation) is:
1.  Deployed to staging.
2.  Verified via the AI Answer Accuracy benchmark (proving Docling and Semantic Chunking are working flawlessly).

---
*Status: Deferred & Waiting for Sprint 2 Completion.*
