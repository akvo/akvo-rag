## Story: MCP FlashRank Reranking

- **Status**: TO DO 📝
- **Sprint**: 2
- **Developer**: Amelia 💻
- **Repository**: `~/Sites/vector-knowledge-base-mcp-server`

### Timeline & Effort
- **Estimated Time**: 2.0 hours
- **Actual Time**: 0.0 hours
- **Effort Points**: 3

### Goal
**As a** system architect
**I want** the MCP server to rank retrieved chunks by relevance before returning them
**So that** the RAG orchestrator receives the highest quality context first, improving answer accuracy.

### Acceptance Criteria
#### User Acceptance Criteria (UAC)
- [ ] AI answers are more accurate and relevant to the specific query.
- [ ] Citations in the UI show the most relevant documents at the top.

#### Technical Acceptance Criteria (TAC)
- [ ] **TDD Method**: Write failing tests for reranking logic and integration before implementation.
- [ ] Integrate `flashrank` library into the MCP server.
- [ ] Add a `rerank` step in the search service that processes the top-N retrieved chunks.
- [ ] Ensure the reranker handles the `project_id` context if applicable.
- [ ] Return only the top-K reranked results to the RAG orchestrator.

### Technical Notes
- Core Library: [FlashRank GitHub](https://github.com/PrithivirajDamodaran/FlashRank)
- LangChain Integration: [FlashrankRerank Docs](https://python.langchain.com/docs/integrations/retrievers/flashrank-reranker)
- Performance: Lightweight re-ranking on CPU.
 optimized, fast for local execution).
- Benefit: Reduces "noise" in the LLM prompt.

### Definition of Done
- [ ] Unit tests passing
- [ ] Benchmark comparison (Pre vs Post Rerank)
- [ ] Code reviewed
