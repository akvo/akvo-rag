# Feature Specification: Knowledge Base & Document Ingestion Lifecycle Management

> **Feature ID:** `026_ui_602_knowledge_base_and_document_ingestion_lifecycle_spec`  
> **Issue Ref:** `[#172]` (`TASK-UI-602`)  
> **Target Base Branch:** `feature/170-modern-chat-canvas-and-citation-drawer`  
> **Status:** `APPROVED (/0-planning complete & grilled)`  
> **Estimated Effort:** `3.0 hrs (Vibe-Coding) / 2.0 days (Traditional)`  
> **Author:** Antigravity Fullstack Council (Sally, Winston, Amelia, Murat, Rachel)  
> **System Reference:** [`docs/lld/container_based_rag_platform_lld.md`](file:///Users/galihpratama/Sites/akvo-rag/docs/lld/container_based_rag_platform_lld.md)

---

## 1. Overview & 5W1H Requirements Discovery

### 1.1 Problem Statement
When administrators and researchers upload files to a Knowledge Base, processing into MinIO S3 and ChromaDB vectors occurs asynchronously via background Redis consumers (`document_ingestion` queue). However, the frontend lacks:
1. **Live Ingestion Feedback**: Users must manually refresh the page to see if a document changed from `PROCESSING` to `INDEXED` or `FAILED`.
2. **Chunk Visibility**: Administrators cannot inspect the generated text chunks, token splits, or metadata stored in PostgreSQL `vkb_document_chunks`.
3. **Batch Drag & Drop Upload with Retry**: Multi-file upload lacks a modern dropzone and the ability to re-index or retry failed documents with one click.

`TASK-UI-602` delivers a modern document management experience with auto-polling status indicators, a slide-over **Chunk Inspector Drawer**, and a batch drag-and-drop dropzone.

### 1.2 5W1H Requirements Breakdown

| Dimension | Specification |
|---|---|
| **Who** | Agronomy Researchers, Content Curators, System Administrators. |
| **What** | Real-time status polling (`PROCESSING` ➔ `INDEXED` / `FAILED`), Chunk Inspector slide-over drawer, batch drag-and-drop dropzone, and retry failed ingestion button. |
| **Where** | `frontend/src/components/knowledge-base/document-list.tsx`, `frontend/src/components/knowledge-base/chunk-inspector-drawer.tsx`, `backend/app/api/api_v1/knowledge_base.py`, `vector-kb-mcp/handlers/doc_handlers.py`. |
| **When** | Sprint D14 (`Issue #172`). |
| **Why** | Provides full transparency into the RAG ingestion pipeline, improves UX, and enables quick debugging of document chunking. |
| **How** | Next.js 14 App Router, auto-polling hook (`useInterval`), Radix Sheet drawer, FastAPI REST endpoint, Redis RPC handler. |

---

## 2. Architecture Overview & Data Flow

```mermaid
sequenceDiagram
    autonumber
    actor User as Admin / Researcher
    participant UI as Next.js 14 DocumentList
    participant API as FastAPI Backend (/api/v1/knowledge-bases)
    participant Redis as Redis RPC Dispatcher
    participant VKB as vector-kb-mcp Worker
    participant PG as PostgreSQL 17 (vkb_document_chunks)

    User->>UI: Uploads file(s) via Drag & Drop
    UI->>API: POST /{kb_id}/documents/upload
    API-->>UI: 202 Accepted (doc_id, status: PROCESSING)
    
    loop Every 3s while documents in PROCESSING
        UI->>API: GET /{kb_id}/documents/{doc_id}
        API->>Redis: call_tool("get_document")
        Redis->>VKB: handle_get_doc
        VKB-->>API: {status: "INDEXED", chunk_count: 14}
        API-->>UI: Document updated (Badge: Indexed)
    end

    User->>UI: Clicks "Inspect Chunks" [Eye icon]
    UI->>API: GET /{kb_id}/documents/{doc_id}/chunks
    API->>Redis: call_tool("list_document_chunks")
    Redis->>VKB: SELECT * FROM vkb_document_chunks WHERE document_id = :doc_id
    VKB->>PG: Query chunks & metadata
    PG-->>VKB: Returns chunk records
    VKB-->>API-->>UI: Chunk array (text, chunk_index, tokens, page)
    UI->>User: Displays Slide-Over Chunk Inspector Drawer
```

---

## 3. Component & API Specifications

### 3.1 Backend & MCP Endpoints

#### 1. `GET /api/v1/knowledge-bases/{kb_id}/documents/{doc_id}/chunks`
- **Description**: Returns all persisted text chunks for a given document with token/character counts and page numbers.

#### 2. `POST /api/v1/knowledge-bases/{kb_id}/documents/{doc_id}/retry`
- **Description**: Re-enqueues a failed document for ingestion via Redis `document_ingestion` queue.

### 3.2 Frontend Components
1. **`ChunkInspectorDrawer` (`frontend/src/components/knowledge-base/chunk-inspector-drawer.tsx`)**:
   - Slide-over panel (Radix UI / Sheet) showing total chunk count, average chunk size, and a scrollable list of chunk cards.
   - Each card displays `Chunk #N`, page number badge, character count, and formatted text content.
2. **`DocumentList` (`frontend/src/components/knowledge-base/document-list.tsx`)**:
   - Auto-polling: When any document has `status === 'processing' || status === 'in_progress'`, polls `/api/v1/knowledge-bases/{id}` every 3.5 seconds until settled.
   - Inspect action button (Eye icon) opening `ChunkInspectorDrawer`.
   - Retry action button (RefreshCcw icon) for documents with `status === 'failed'`.

---

## 4. Verification & Quality Gates

### 4.1 Automated Tests
- `backend`: `pytest tests/unit/test_knowledge_base_endpoints.py -v`
- `vector-kb-mcp`: `pytest tests/test_handlers.py -v`
- `frontend`: `pnpm lint` and `pnpm build`

---

## 5. Vibe Coding Estimation Standard

| Task ID | Description | 💻 Vibe Dev | 🧪 Test | 🔍 QA | ⏱️ Total |
|---|---|:---:|:---:|:---:|:---:|
| `SUB-602.1` | Backend `list_document_chunks` & `retry_document` handlers in `vector-kb-mcp` and FastAPI router | 30m | 15m | 10m | **55m (0.9h)** |
| `SUB-602.2` | Slide-Over `ChunkInspectorDrawer` component in Next.js 14 | 35m | 15m | 10m | **60m (1.0h)** |
| `SUB-602.3` | Live Ingestion Auto-Polling, Retry action, and Batch Dropzone in `DocumentList` | 35m | 20m | 10m | **65m (1.1h)** |
| **TOTAL** | **TASK-UI-602: KB & Ingestion Lifecycle Management** | **100m** | **50m** | **30m** | **180m (3.0h)** |
