## Story: Unified Setup Automation

- **Status**: TO DO 📝
- **Sprint**: 2
- **Developer**: Amelia 💻
- **Repository**: `~/Sites/akvo-rag` (Root)

### Timeline & Effort
- **Estimated Time**: 1.5 hours
- **Actual Time**: 0.0 hours
- **Effort Points**: 2

### Goal
**As a** developer
**I want** a single command to sync environment variables between RAG and MCP repos
**So that** setup is fast and resistant to configuration errors.

### Acceptance Criteria
#### User Acceptance Criteria (UAC)
- [ ] Getting started with the unified system takes less than 5 minutes.
- [ ] No "Connection Refused" errors caused by mismatched API keys.

#### Technical Acceptance Criteria (TAC)
- [ ] Create `scripts/unified-setup.sh` in the Akvo RAG repo.
- [ ] Scrip reads shared config (e.g., `project_id`, `mcp_key`) and populates `.env` in both folders.
- [ ] Script verifies container status before finishing.
- [ ] Update README with unified setup instructions.

### Technical Notes
- Script should handle default values for local development.

### Definition of Done
- [ ] Script successfully sets up a clean environment.
- [ ] Documentation updated.
