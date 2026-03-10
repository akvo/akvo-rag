## Story: Advanced PDF Extraction (Docling)

- **Status**: TO DO 📝
- **Sprint**: 2
- **Developer**: Amelia 💻
- **Repository**: `~/Sites/vector-knowledge-base-mcp-server`

### Timeline & Effort
- **Estimated Time**: 4.0 hours
- **Actual Time**: 0.0 hours
- **Effort Points**: 5

### Goal
**As a** system developer
**I want** the MCP server to use IBM's Docling for PDF parsing
**So that** tables, headers, and complex layouts are accurately extracted for the AI.

### Acceptance Criteria
#### User Acceptance Criteria (UAC)
- [ ] Uploaded PDFs with tables no longer result in garbled AI answers.
- [ ] Document structure (headers, lists) is preserved in the retrieved context.

#### Technical Acceptance Criteria (TAC)
- [ ] **TDD Method**: Write failing tests for Docling extraction on complex PDFs before implementation.
- [ ] Add `docling` and its dependencies to `main/requirements.txt`.
- [ ] Refactor `main/app/services/document_processor.py` to use `Docling` specifically for `.pdf` files.
- [ ] Ensure the extraction output is clean Markdown.
- [ ] Verify that document metadata is still correctly associated with the extracted text.

### Technical Notes
- Documentation: [Docling Official Site](https://www.docling.ai/)
- Library: `docling` (IBM Research)
- Fallback: Keep `PyPDFLoader` as a secondary fallback if Docling fails on specific files.

### Definition of Done
- [ ] Successful extraction of test PDF with complex tables.
- [ ] Integration tests passing.
- [ ] Code reviewed.
