## Story: MCP Parallel Retrieval

- **Status**: TO DO 📝
- **Sprint**: 2
- **Developer**: Amelia 💻
- **Repository**: `~/Sites/vector-knowledge-base-mcp-server`

### Timeline & Effort
- **Estimated Time**: 3.0 hours
- **Actual Time**: 0.0 hours
- **Effort Points**: 5

### Goal
**As a** system architect
**I want** the MCP server to query multiple knowledge bases concurrently
**So that** retrieval time remains constant regardless of the number of connected data sources.

### Acceptance Criteria
#### User Acceptance Criteria (UAC)
- [ ] User receives search results faster when multiple KBs are active.
- [ ] No "timeout" errors when querying more than 3 large knowledge bases at once.
- [ ] Search results are combined correctly from all sources.

#### Technical Acceptance Criteria (TAC)
- [ ] **TDD Method**: Write failing tests for concurrent execution and timeouts *before* refactoring.
- [ ] Refactor `query_vector_kbs` in the MCP server to use `asyncio.gather`.
- [ ] Implement a global timeout for the parallel gathering to prevent single-KB hangs from blocking the whole request.
- [ ] Merge results into a single list while preserving metadata.
- [ ] Verify concurrency via logs (ensure requests start at the same timestamp).

### Technical Notes
- Target Repo: `~/Sites/vector-knowledge-base-mcp-server`
- Pattern: `await asyncio.gather(*[search_kb(kb_id) for kb_id in kb_ids])`

### Definition of Done
- [ ] Unit tests passing
- [ ] Integration tests for MCP endpoint
- [ ] Code reviewed
- [ ] Documentation updated
