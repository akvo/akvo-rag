## Story: Conversational Recall & Stylistic Follow-ups

- **Status**: COMPLETED ✅
- **Sprint**: 1
- **Developer**: Amelia 💻

### Timeline & Effort
- **Estimated Time**: 2.5 hours
- **Actual Time**: 2.5 hours
- **Effort Points**: 3

### Goal
**As a** chat widget user
**I want** the AI to remember our conversation and respect my follow-up instructions (like "explain simply")
**So that** I don't have to repeat context and can get answers in the format I need.

### Acceptance Criteria
#### User Acceptance Criteria (UAC)
- [x] Follow-up questions like "Explain in simple way" work on the same topic as the previous question.
- [x] Memory queries like "What did we just talk about?" correctly recall previous subjects.
- [x] Responses are consistent across Next.js frontend and WebSocket widget.

#### Technical Acceptance Criteria (TAC)
- [x] `classify_intent_node` correctly detects `memory_query` intent.
- [x] Workflow branches to bypass document retrieval for memory queries.
- [x] Specialized permissive prompt applied for memory intents with `{context}` placeholder.
- [x] `chat_history` standardized to exclude the current uncontextualized message pair.
- [x] Unit tests in `test_conversational_intent_and_memory.py` cover all logic.

### Technical Notes
- Resolved a critical `ValueError` in LangChain by adding a dummy `{context}` variable to the specialized memory prompt.
- Fixed history drift where the AI would lose the subject during stylistic follow-ups by refining the contextualization prompt.
- Ensured seeder synchronization adds new active versions instead of overwriting existing prompt records.

### Definition of Done
- [x] Intent classification updated.
- [x] Branching logic implemented.
- [x] Unit tests passed (3/3).
- [x] ADR-003 created.
- [x] Seeder synchronized.
