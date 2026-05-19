## Story: Unified Status Streaming

- **Status**: DEFERRED ⏸️
- **Sprint**: 2
- **Developer**: Amelia 💻
- **Repository**: `~/Sites/akvo-rag` (Root)

### Timeline & Effort
- **Estimated Time**: 3.0 hours
- **Actual Time**: 0.0 hours
- **Effort Points**: 5

### Goal
**As a** system architect
**I want** to report real-time status updates (searching, reranking, generating) to all clients
**So that** users understand what the AI is doing, improving the perceived performance.

### Acceptance Criteria
#### User Acceptance Criteria (UAC)
- [ ] Web Dashabord shows status text while waiting for response.
- [ ] JS Widget shows status text while waiting for response.
- [ ] Mobile App (Jobs) shows granular status instead of generic "running".

#### Technical Acceptance Criteria (TAC)
- [ ] Define standard status markers: `STATUS_INTENT`, `STATUS_SEARCHING`, `STATUS_RERANKING`, `STATUS_GENERATING`.
- [ ] Backend (SSE): Yield status events using `0:"STATUS_..."` prefix.
- [ ] Backend (WebSocket): Emit `status` events to the socket.
- [ ] Backend (Jobs): Update the `Job` record with granular status strings.
- [ ] Frontend (Web): Update `Answer` component to display active status.
- [ ] Widget (JS): Handle `status` message type in `chatbot.js`.

### Technical Notes
- Backward Compatibility: Use new fields/event names to avoid breaking existing Agriconnect clients.

### Definition of Done
- [ ] End-to-end verification for SSE, WS, and Jobs API.
- [ ] Unit tests for status yielding logic.
- [ ] No regression for non-updated clients.
