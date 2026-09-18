# Feature Spec: Knowledge Base Directory & Vector Diagnostic UI/UX Modernization

- **Feature Code**: `UI-607`
- **Issue ID**: `#170`
- **Component**: Frontend (`frontend/src/app/dashboard/knowledge/page.tsx`, `frontend/src/app/dashboard/knowledge/new/page.tsx`, `frontend/src/app/dashboard/test-retrieval/[id]/page.tsx`)
- **Status**: Completed

---

## 1. Overview
Elevates the Knowledge Base Management directory (`/dashboard/knowledge`), repository creation workflow (`/dashboard/knowledge/new`), and semantic vector retrieval diagnostic suite (`/dashboard/test-retrieval/[id]`) to align with the modern Akvo RAG Chat Canvas and Administration design system.

---

## 2. Key Enhancements

### 2.1 KPI Metric Overview (`/dashboard/knowledge`)
- **Total Repositories**: Total count of configured knowledge bases.
- **Total Documents**: Aggregated count of all indexed document chunks.
- **Public Repositories**: Count of globally accessible public repositories.
- **Private Stores**: Count of tenant-isolated private knowledge bases.

### 2.2 Search & Scope Filtering
- Real-time client-side search across Knowledge Base names, descriptions, and indexed document filenames.
- Scope filter toggle buttons: **All**, **Public**, and **Private**.
- Search reset and filter clearing controls.

### 2.3 Elevated Knowledge Base Cards & Document Gallery
- Glassmorphic card styling (`bg-card/70 backdrop-blur-xl border-border/70 shadow-sm hover:shadow-md`).
- File extension icons (`PDF`, `DOCX`, `TXT`, `MD`, etc.) with truncated names and timestamp tooltips.
- Direct quick actions:
  - **Test Retrieval**: Quick link to `/dashboard/test-retrieval/:id` for semantic similarity testing.
  - **Manage Documents**: Quick link to `/dashboard/knowledge/:id` for uploading and inspecting chunks.
  - **Delete**: Protected by a Radix `AlertDialog` confirmation modal detailing the permanent deletion blast radius.

### 2.4 New Knowledge Base Form Polish (`/dashboard/knowledge/new`)
- Polished container card with back navigation, clear helper labels, validation alerts, and loading spinner state on creation.

### 2.5 Semantic Vector Retrieval Diagnostic (`/dashboard/test-retrieval/[id]`)
- Modernized search container with Top K chunk selector (1, 3, 5, 8, 10).
- Quick example prompt chips for rapid testing.
- Color-tiered cosine similarity match percentage badges (Emerald for ≥75%, Blue for ≥60%, Amber for <60%).
- 1-click chunk text copying with visual feedback and token length estimation.
- Direct links back to the Document Inspector and Knowledge Base directory.

---

## 3. Verification & Quality Gates
- `pnpm lint`: 0 errors / 0 warnings.
- Backend unit test suite: 130/130 PASSED.
- Layout persistence: Fully wrapped inside `<DashboardLayout>` ensuring sidebar navigation and responsive drawers remain intact.
