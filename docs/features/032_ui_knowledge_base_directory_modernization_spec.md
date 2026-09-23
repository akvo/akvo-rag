# Feature Spec: Knowledge Base Directory, Vector Diagnostics & Root Dashboard UI/UX Modernization

- **Feature Code**: `UI-607`
- **Issue ID**: `#170`
- **Component**: Frontend (`frontend/src/app/dashboard/page.tsx`, `frontend/src/app/dashboard/knowledge/page.tsx`, `frontend/src/app/dashboard/knowledge/new/page.tsx`, `frontend/src/app/dashboard/test-retrieval/[id]/page.tsx`, `frontend/src/app/dashboard/api-keys/page.tsx`)
- **Status**: Completed

---

## 1. Overview
Elevates the Root Dashboard Landing Page (`/dashboard`), Knowledge Base Management directory (`/dashboard/knowledge`), repository creation workflow (`/dashboard/knowledge/new`), semantic vector retrieval diagnostic suite (`/dashboard/test-retrieval/[id]`), and portal modals (`/dashboard/api-keys`) to align with the modern Akvo RAG Chat Canvas and Administration design system.

---

## 2. Key Enhancements

### 2.1 Root Dashboard Landing Page (`/dashboard`)
- **Modern Glassmorphic Hero**: Personalized greeting with quick launch buttons for starting new conversations or creating repositories.
- **4 Real-Time KPI Stats**: Dynamic counters for **Knowledge Bases**, **Chat Sessions**, **Tenant Applications**, and **Infrastructure Health (7 Microservices)**.
- **Platform Modules Launchpad**: 6 interactive launch cards for AI Chat Workspace, Knowledge Repositories, Semantic Vector Diagnostics, Dynamic Prompt Studio, Tenant Apps & API Keys, and Observability & Evals.
- **RAG Architecture & Workflow Guide**: 3-step interactive onboarding explaining Document Ingestion, Vector Diagnostics, and Conversational Synthesis.
- **Client Routing Parity**: Replaced full-page reload `<a>` tags with Next.js `<Link>` components to maintain client router cache.
- **Container Width Parity**: Unified container width (`space-y-8 pb-12`) matching all other dashboard interfaces.

### 2.2 KPI Metric Overview (`/dashboard/knowledge`)
- **Total Repositories**: Total count of configured knowledge bases.
- **Total Documents**: Aggregated count of all indexed document chunks.
- **Public Repositories**: Count of globally accessible public repositories.
- **Private Stores**: Count of tenant-isolated private knowledge bases.

### 2.3 Search & Scope Filtering (`/dashboard/knowledge`)
- Real-time client-side search across Knowledge Base names, descriptions, and indexed document filenames.
- Scope filter toggle buttons: **All**, **Public**, and **Private**.
- Search reset and filter clearing controls.

### 2.4 Elevated Knowledge Base Cards & Document Gallery
- Glassmorphic card styling (`bg-card/70 backdrop-blur-xl border-border/70 shadow-sm hover:shadow-md`).
- File extension icons (`PDF`, `DOCX`, `TXT`, `MD`, etc.) with truncated names and timestamp tooltips.
- Direct quick actions:
  - **Test Retrieval**: Quick link to `/dashboard/test-retrieval/:id` for semantic similarity testing.
  - **Manage Documents**: Quick link to `/dashboard/knowledge/:id` for uploading and inspecting chunks.
  - **Delete**: Protected by a Radix `AlertDialog` confirmation modal detailing the permanent deletion blast radius.

### 2.5 New Knowledge Base Form Polish (`/dashboard/knowledge/new`)
- Polished container card with back navigation, clear helper labels, validation alerts, and loading spinner state on creation.

### 2.6 Semantic Vector Retrieval Diagnostic (`/dashboard/test-retrieval/[id]`)
- Modernized search container with Top K chunk selector (1, 3, 5, 8, 10).
- Quick example prompt chips for rapid testing.
- Color-tiered cosine similarity match percentage badges (Emerald for ≥75%, Blue for ≥60%, Amber for <60%).
- 1-click chunk text copying with visual feedback and token length estimation.
- Direct links back to the Document Inspector and Knowledge Base directory.

### 2.7 Portal Modals & Radix Dialog Overlay Alignment (`/dashboard/api-keys`)
- Converted raw custom modal overlays to Radix `Dialog` / `DialogPortal` components.
- Fixes viewport overlay clipping and eliminates top-of-screen white background bleed.

### 2.8 System Observability & RAG Evaluations Width Alignment (`/dashboard/evaluations`)
- Standardized page root wrapper from restrictive `p-8 max-w-7xl mx-auto space-y-8` to universal dashboard container `space-y-8 pb-12`.
- Aligns full-width responsive telemetry grid and benchmark cards with the rest of the application dashboard.

---

## 3. Verification & Quality Gates
- `pnpm lint`: 0 errors / 0 warnings.
- Backend unit test suite: 313 PASSED with 84% coverage.
- Layout persistence: Fully wrapped inside `<DashboardLayout>` ensuring sidebar navigation and responsive drawers remain intact.
