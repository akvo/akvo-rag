# Feature Specification: Chat Session Management, Inline Thread Actions & KaTeX Math Rendering

> **Feature ID:** `027_ui_603_chat_session_management_and_markdown_polish_spec`  
> **Issue Ref:** `[#173]` (`TASK-UI-603`)  
> **Target Base Branch:** `feature/170-modern-chat-canvas-and-citation-drawer`  
> **Status:** `APPROVED (/0-planning complete & grilled)`  
> **Estimated Effort:** `2.5 hrs (Vibe-Coding) / 1.5 days (Traditional)`  
> **Author:** Antigravity Fullstack Council (Sally, Winston, Amelia, Murat, Rachel)  
> **System Reference:** [`docs/lld/container_based_rag_platform_lld.md`](file:///Users/galihpratama/Sites/akvo-rag/docs/lld/container_based_rag_platform_lld.md)

---

## 1. Overview & 5W1H Requirements Discovery

### 1.1 Problem Statement
While the 2-pane chat canvas delivers a unified workspace, users still lack:
1. **Thread Renaming & Management**: Users cannot rename conversation threads or delete them directly from the left sidebar without leaving the chat.
2. **Markdown Polish & Code Copy**: Assistant messages lack one-click copy buttons on code blocks and formatted formula/metric rendering.
3. **Dialogue Export**: Users cannot export conversations as Markdown or JSON or copy full conversation transcripts for external reporting.

`TASK-UI-603` implements inline rename and delete in `ChatSidebar`, adds code block copy and math styling in `Answer`, and enables full dialogue export.

### 1.2 5W1H Requirements Breakdown

| Dimension | Specification |
|---|---|
| **Who** | End-Users, Agronomy Researchers, Team Leads. |
| **What** | Inline thread rename with Enter/Esc shortcuts, thread delete action, code copy buttons, and Markdown/JSON conversation export. |
| **Where** | `frontend/src/components/chat/chat-sidebar.tsx`, `frontend/src/components/chat/answer.tsx`, `frontend/src/app/dashboard/chat/[id]/page.tsx`, `backend/app/api/api_v1/chat.py`. |
| **When** | Sprint D14 (`Issue #173`). |
| **Why** | Gives users complete conversational lifecycle control and enables sharing and documenting RAG synthesis. |
| **How** | Next.js 14, React Hook inline editing, FastAPI `PUT /api/v1/chat/{id}`, Blob file export downloads. |

---

## 2. API & Component Specifications

### 2.1 Backend Endpoints
- **`PUT /api/v1/chat/{chat_id}`**:
  - Updates chat title with ownership validation (`chat.user_id == current_user.id`).
- **`DELETE /api/v1/chat/{chat_id}`**:
  - Deletes chat session and associated messages.

### 2.2 Frontend Components
1. **`ChatSidebar`**:
   - Inline Rename input mode triggered from row hover menu (`...`).
   - Delete confirmation dialog.
   - Smooth active thread redirect when deleting active conversation.
2. **`Answer`**:
   - Code block with language tag and clipboard copy button.
3. **Header Export Menu**:
   - Export dialogue as Markdown file (`.md`), JSON (`.json`), or Copy to Clipboard.

---

## 3. Verification & Quality Gates
- `pnpm lint` and `pnpm build`
- `pytest tests/unit/test_ws_chat_endpoints.py -v`

---

## 4. Vibe Coding Estimation Standard

| Task ID | Description | 💻 Vibe Dev | 🧪 Test | 🔍 QA | ⏱️ Total |
|---|---|:---:|:---:|:---:|:---:|
| `SUB-603.1` | Backend `PUT /api/v1/chat/{chat_id}` endpoint & unit test | 20m | 15m | 10m | **45m (0.75h)** |
| `SUB-603.2` | Inline Sidebar Thread Rename & Delete actions in `ChatSidebar` | 35m | 15m | 10m | **60m (1.0h)** |
| `SUB-603.3` | Code block copy, Markdown polish, and Export Conversation | 30m | 10m | 10m | **50m (0.8h)** |
| **TOTAL** | **TASK-UI-603: Chat Session Actions & Markdown Polish** | **85m** | **40m** | **30m** | **155m (2.55h)** |
