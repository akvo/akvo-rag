# Feature Spec: Tenant App Registration & API Key Management Portal

- **Feature Code**: `TASK-UI-605`
- **Issue**: [#175](https://github.com/akvo/akvo-rag/issues/175)
- **Status**: In Progress
- **Authors**: Winston (Architect), Amelia (Lead Dev), Sally (UX), Murat (Test), Rachel (Red Team)
- **Base Branch**: `feature/174-dynamic-system-prompt-management-and-playground`
- **Target Feature Branch**: `feature/175-tenant-app-registration-and-api-key-portal`

---

## 1. Executive Summary & Goals

Following Issue #168 where `/api/v1/apps/register` was secured with Super-Admin access, this feature delivers a complete **Tenant App Registration & API Key Management Portal** within the Akvo RAG Web UI:
1. **Tenant Application Management**: Super-admin registration of external consumer apps (AgriConnect, CoM) with domain, callbacks, and scoped knowledge base permissions.
2. **One-Time Token Disclosure Security**: Generates tenant access tokens (`tok_...`) and displays them **strictly once** upon creation in a copyable modal with cryptographic masking.
3. **Developer & Personal API Keys**: Management of personal developer API keys with active toggling, revocation, and quick cURL integration documentation.
4. **Credential Rotation & Scoped KB Matrix**: 1-click token rotation and KB access control.

---

## 2. Architecture & API Contracts

### Backend Endpoints (`backend/app/api/api_v1/apps.py` & `api_keys.py`)
- `POST /api/v1/apps/register`: Register new tenant app with scoped KBs (Super-Admin only).
- `GET /api/v1/apps`: List all registered tenant apps with metadata and assigned KBs (Super-Admin only).
- `PUT /api/v1/apps/{app_id}/status`: Toggle tenant app active/suspended status.
- `POST /api/v1/apps/rotate`: Rotate app access tokens.
- `GET /api/v1/api-keys`: List user API keys.
- `POST /api/v1/api-keys`: Generate new user API key.
- `PUT /api/v1/api-keys/{id}`: Update / revoke user API key.

---

## 3. Frontend UI/UX Structure (`frontend/src/app/dashboard/api-keys/page.tsx`)

- **2-Tab Segmented Portal**:
  - **Tab 1: Tenant Applications (Host Apps)**:
    - Super-admin app cards/table with live status (Active/Suspended), domain, assigned KBs count, and callbacks.
    - Register New App Modal with multi-KB selection and one-time token reveal dialog.
  - **Tab 2: Developer API Keys**:
    - Personal API key cards with masked keys, last used timestamps, and toggle switches.
    - Create Key Dialog & cURL Code Snippet Playground.

---

## 4. Verification & Testing

- **Backend Unit Tests**: `backend/tests/unit/test_security_core_extended.py` and apps route tests.
- **Frontend Quality Gate**: `pnpm lint` and TypeScript compilation with 0 errors.
