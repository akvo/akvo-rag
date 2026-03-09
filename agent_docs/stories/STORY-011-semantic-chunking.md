## Story: Semantic Chunking Strategy

- **Status**: TO DO 📝
- **Sprint**: 2
- **Developer**: Amelia 💻
- **Repository**: `~/Sites/vector-knowledge-base-mcp-server`

### Timeline & Effort
- **Estimated Time**: 4.0 hours
- **Actual Time**: 0.0 hours
- **Effort Points**: 8

### Goal
**As a** system developer
**I want** to split documents based on semantic coherence rather than character count
**So that** retrieved chunks contained complete, meaningful thoughts.

### Acceptance Criteria
#### User Acceptance Criteria (UAC)
- [ ] AI answers are more accurate because the context provided is not cut off mid-sentence.
- [ ] Retrieval relevance is higher (measured by hit-rate on benchmark queries).

#### Technical Acceptance Criteria (TAC)
- [ ] Implement `SemanticChunker` in `main/app/services/document_processor.py`.
- [ ] Configure the chunker to use the project's default embedding model for break-point calculation.
- [ ] Add a configuration setting to toggle between "Recursive" and "Semantic" chunking.
- [ ] Verify that chunks do not exceed a safety limit (e.g., 2000 tokens) to prevent context window overflow.

### Technical Notes
- Library: Uses LangChain's semantic chunker or `Chonkie`.
- Performance: Note that semantic chunking is slower during ingestion (requires embeddings).

### Definition of Done
- [ ] Comparative test: "Recursive" vs "Semantic" chunking quality.
- [ ] Unit tests for chunk boundary logic.
- [ ] Documentation updated.
