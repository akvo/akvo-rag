# UX Design Specification: Akvo RAG

## 1. Design Vision
The Akvo RAG interface is designed to be **clean, professional, and accessible**. It prioritizes clarity in AI interactions, providing users with confidence through transparency (citations) and ease of use (automated KB selection).

## 2. Target Personas
- **Developer Devin**: Needs quick access to API keys and technical monitoring.
- **Knowledge Kara**: Needs a distraction-free chat environment with clear "source of truth" markers.
- **Admin Arthur**: Needs high-level overviews of system health and user management.

## 3. Design System
- **Framework**: Tailwind CSS + shadcn/ui.
- **Typography**: Inter (System Default).
- **Color Palette**:
    - **Primary**: Slate/Zinc (Neutral for professional feel).
    - **Success**: Emerald (Positive feedback).
    - **Error**: Rose (Critical alerts).
    - **Background**: White/Gray-50 (Light mode) and Zinc-950 (Dark mode).

## 4. Interaction Patterns

### 4.1 Chat Experience & Perceived Performance
- **Instant Response (Cache Hit)**: When a query hits the semantic cache, the response is injected into the chat feed instantly (<300ms) with a subtle "⚡ Cached" indicator.
- **Streaming Responses**: For new queries, AI messages stream token-by-token (SSE) to ensure a Time-to-First-Token (TTFT) under 1000ms.
- **Optimistic UI**: User messages appear in the chat log immediately upon pressing 'Enter'—do not wait for the backend to acknowledge receipt.
- **Skeleton Loaders**: While the MCP server is retrieving and re-ranking context (before TTFT), a subtle pulsing skeleton loader indicates the AI is "Thinking...".
- **Citation Tooltips**: Hovering over a citation number shows a snippet of the source document.
- **Error States**: Clear, non-technical error messages when the LLM or MCP server is unreachable.

### 4.2 Knowledge Management
- **Progress Indicators**: Real-time progress bars during document embedding/upload.
- **File Previews**: Ability to quickly view the content of uploaded documents.
- **KB Toggle**: Simple switch between USQ (Manual) and ASQ (Autonomous) modes.

## 5. User Journey Maps

### 5.1 Onboarding & Ingestion
1. **Entry**: User lands on Login/Register page.
2. **Dashboard**: Greets user with an overview of their Knowledge Bases.
3. **Action**: User clicks "New KB" -> Uploads files.
4. **Processing**: System shows "Processing..." state with percentage.
5. **Completion**: KB becomes "Active" and ready for chat.

### 5.2 The "Chat with Docs" Flow
1. **Selection**: User selects one or more KBs (or enables ASQ).
2. **Input**: User types a natural language query.
3. **Wait**: System shows a subtle loading animation.
4. **Output**: System displays the response with inline citations.
5. **Follow-up**: User can ask follow-up questions within the same thread.

## 6. Visual Design Standards
- **Consistency**: Use standardized `ui/` components for all buttons, inputs, and cards.
- **Responsiveness**: Mobile-first design principles (though primarily targeted at Desktop/Tablet).
- **Accessibility**: ARIA labels for all interactive elements; high contrast ratios.
