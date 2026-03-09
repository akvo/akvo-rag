## Story: RAG Redis Semantic Cache

- **Status**: TO DO 📝
- **Sprint**: 2
- **Developer**: Amelia 💻
- **Repository**: `~/Sites/akvo-rag` (Root)

### Timeline & Effort
- **Estimated Time**: 4.0 hours
- **Actual Time**: 0.0 hours
- **Effort Points**: 8

### Goal
**As a** system architect
**I want** the RAG orchestrator to cache previously answered high-similarity queries
**So that** repeating questions are answered instantly (<300ms) without hitting the LLM or Vector DB.

### Acceptance Criteria
#### User Acceptance Criteria (UAC)
- [ ] Frequently asked questions appear almost instantly for the user.
- [ ] System remains functional even if the backend retrieval is slow.
- [ ] Users see a "Cached" indicator or similar performance boost.

#### Technical Acceptance Criteria (TAC)
- [ ] Integrate Redis as a semantic vector store (using `redis-py` or `langchain-redis`).
- [ ] Implement a cache-aside pattern in `chat_mcp_service.py`.
- [ ] Threshold check: Only return cached answers if similarity score is > 0.95.
- [ ] TTL management: Cache entries expire after 24 hours to ensure freshness.
- [ ] Cache invalidation: Provide a way to clear the cache for specific `project_ids`.

### Technical Notes
- Pattern: Cache hits skip the entire LangGraph workflow.
- Dependencies: Requires Redis with RedisSearch module.

### Definition of Done
- [ ] Unit tests for cache hit/miss logic
- [ ] Performance benchmark (Cache Hit vs Miss)
- [ ] Redis container added to dev.sh (if missing)
