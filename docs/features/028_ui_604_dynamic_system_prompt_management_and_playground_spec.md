# Feature Spec: Dynamic System Prompt Management UI & Live Model Playground

- **Feature Code**: `TASK-UI-604`
- **Issue**: [#174](https://github.com/akvo/akvo-rag/issues/174)
- **Status**: In Progress
- **Authors**: Winston (Architect), Amelia (Lead Dev), Sally (UX), Murat (Test), Rachel (Red Team)
- **Base Branch**: `feature/173-chat-session-management-inline-actions-katex`
- **Target Feature Branch**: `feature/174-dynamic-system-prompt-management-and-playground`

---

## 1. Executive Summary & Goals

Akvo RAG relies on centralized, database-driven system prompt templates (`contextualize_q_system_prompt`, `qa_strict_prompt`, `qa_flexible_prompt`) managed via `PromptService`.
This feature delivers a unified, production-grade **System Prompt Management & Live Playground Studio** within the Akvo RAG Web UI:
1. **Interactive Prompt Editor**: Template editor with real-time placeholder extraction (`{context}`, `{question}`, `{chat_history}`).
2. **Live Test Playground**: Instant variable binding simulation and test generation with live token counting.
3. **Audit Trail & Version History**: Complete version timeline with changelog reasons, active badge indicators, and 1-click rollback/reactivation.
4. **Global Retrieval & System Parameters**: Configurable Global Top-K and retrieval parameters.

---

## 2. Architecture & API Contracts

### Backend Endpoints (`backend/app/api/api_v1/prompt.py`)
- `GET /api/v1/prompt`: List all prompt definitions and their active versions.
- `GET /api/v1/prompt/{name}`: Retrieve prompt definition with full version history.
- `PUT /api/v1/prompt/{name}`: Create and activate a new version of the prompt template.
- `PUT /api/v1/prompt/{name}/reactivate/{version_id}`: Rollback/reactivate an existing version.
- `POST /api/v1/prompt/test`: Test prompt formatting and token estimation with arbitrary test variables.

### Request/Response Schemas
```json
// POST /api/v1/prompt/test
{
  "template": "Given context:\n{context}\n\nAnswer: {question}",
  "variables": {
    "context": "Akvo RAG is an intelligent system...",
    "question": "What is Akvo RAG?"
  }
}

// Response (200 OK)
{
  "formatted_prompt": "Given context:\nAkvo RAG is an intelligent system...\n\nAnswer: What is Akvo RAG?",
  "estimated_tokens": 18,
  "character_count": 78,
  "missing_variables": []
}
```

---

## 3. Frontend UI/UX Structure (`frontend/src/app/dashboard/fine-tuning/page.tsx`)

- **Header Studio Toolbar**:
  - Prompt selector tabs (`Contextualize Query`, `QA Strict`, `QA Flexible`).
  - Active version pill, last modified timestamp, and active author.
  - Global Top-K Retrieval Parameter badge.
- **2-Pane Editor & Playground**:
  - **Left Pane (Template & Variable Controls)**:
    - Textarea editor with detected variable badges.
    - Dynamic Variable Inputs table auto-extracted from `{variables}` in the template.
    - Activation reason input.
  - **Right Pane (Live Preview & Test Studio)**:
    - Live compiled preview showing bound variables.
    - Token count and character stats.
    - Version History Drawer with 1-click rollback and timestamp audit trail.

---

## 4. Verification & Testing

- **Backend Unit Tests**: `backend/tests/unit/test_prompt_and_callback_endpoints.py` testing prompt CRUD, reactivation, and test simulation.
- **Frontend Quality Gate**: `pnpm lint` and TypeScript compilation with 0 errors.
