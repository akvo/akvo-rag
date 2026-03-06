# User Stories: RAG Follow-up Alignment (#RAG-FA)

## STORY-003: [BE] Enhance Contextualization Prompt
**Goal**: As an AI, I want to recognize when a user is asking for a stylistic change so that I can keep the search query focused on the subject.
- **Estimated Time**: 2h
- **UAC**:
    - User's "explain in easy way" is rewritten to include the previous topic.
    - Reformulated query for retrieval prioritizes topic keywords over "easy" or "simple".
- **TAC**:
    - Update `backend/app/services/prompt_service.py` to include a meta-instruction for the QA prompt.
    - Contextualized query should look like: `What is living income? (Instruction: explain in simple terms)`.

## STORY-004: [BE] Update QA Prompt for Stylistic Sensitivity
**Goal**: As an AI, I want to respect meta-instructions in the query so that I can adjust my tone accordingly.
- **Estimated Time**: 1h
- **UAC**:
    - AI provides a simplified explanation when requested.
- **TAC**:
    - Update `DEFAULT_QA_STRICT_PROMPT` in `backend/app/constants/prompt_constant.py`.
    - QA prompt should detect meta-instructions like `(Instruction: ...)` in the query and follow them.

## STORY-005: [QA] Verify Stylistic Follow-up Fix
**Goal**: Ensure that the "living income" example now passes.
- **Estimated Time**: 1h
- **UAC**:
    - "Can you explain in easy way?" after "What is living income?" results in a simple definition, not a list of pilots.
- **TAC**:
    - Add a unit test case in `backend/tests/unit/test_prompt_service.py`.
