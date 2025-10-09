# App Registration & Validation API

Server-to-server app registration and validation system for Akvo RAG.

## Overview

This feature enables external applications to register and obtain credentials for authenticating with the Akvo RAG API. Tokens never expire automatically and are only invalidated when apps are deactivated or revoked.

## Endpoints

### 1. POST `/v1/apps/register` - Register New App

Register a new application and receive credentials.

**Request:**
```bash
curl -X POST http://localhost:8000/v1/apps/register \
  -H 'Content-Type: application/json' \
  -d '{
    "app_name": "agriconnect",
    "domain": "agriconnect.akvo.org/api",
    "default_chat_prompt": "",
    "chat_callback": "https://agriconnect.akvo.org/api/ai/callback",
    "upload_callback": "https://agriconnect.akvo.org/api/kb/callback"
  }'
```

**Response (201):**
```json
{
  "app_id": "app_abc123...",
  "client_id": "ac_xyz789...",
  "access_token": "tok_...",
  "callback_token": "...",
  "scopes": ["jobs.write", "kb.read", "kb.write", "apps.read"]
}
```

**Validation:**
- Both `chat_callback` and `upload_callback` must be HTTPS URLs
- Returns 422 for invalid URLs

---

### 2. GET `/v1/apps/me` - Validate Token & Get App Info

Validate your access token and retrieve app metadata.

**Request:**
```bash
curl http://localhost:8000/v1/apps/me \
  -H "Authorization: Bearer tok_..."
```

**Response (200):**
```json
{
  "app_id": "app_abc123...",
  "app_name": "agriconnect",
  "domain": "agriconnect.akvo.org/api",
  "default_chat_prompt": "",
  "chat_callback_url": "https://agriconnect.akvo.org/api/ai/callback",
  "upload_callback_url": "https://agriconnect.akvo.org/api/kb/callback",
  "scopes": ["jobs.write", "kb.read", "kb.write", "apps.read"],
  "status": "active"
}
```

**Error Responses:**
- **401** - Invalid or missing token
- **403** - App is not active (revoked or suspended)

---

### 3. POST `/v1/apps/rotate` - Rotate Tokens

Rotate access token and/or callback token. Old tokens remain valid until app is revoked.

**Request:**
```bash
curl -X POST http://localhost:8000/v1/apps/rotate \
  -H "Authorization: Bearer tok_..." \
  -H 'Content-Type: application/json' \
  -d '{
    "rotate_access_token": true,
    "rotate_callback_token": true
  }'
```

**Response (200):**
```json
{
  "app_id": "app_abc123...",
  "access_token": "tok_new...",
  "callback_token": "new_callback_token...",
  "message": "Both tokens rotated successfully"
}
```

**Notes:**
- Set either flag to `false` to skip rotating that token
- If both are `false`, no tokens are rotated
- Old tokens remain valid until explicitly revoked

---

### 4. POST `/v1/apps/revoke` - Revoke App

Revoke the app immediately. After revocation, all API calls will return 401/403.

**Request:**
```bash
curl -X POST http://localhost:8000/v1/apps/revoke \
  -H "Authorization: Bearer tok_..."
```

**Response:** `204 No Content`

**Notes:**
- This operation is idempotent
- After revocation, the app status becomes "revoked"
- All subsequent API calls with this token will fail

---

## Security Features

### Token Generation
- **Access Token**: 48-byte URL-safe token with `tok_` prefix
- **Callback Token**: 48-byte URL-safe token (hashed with Argon2)
- **App ID**: Unique identifier with `app_` prefix
- **Client ID**: Unique identifier with `ac_` prefix

### Token Storage
- Access tokens stored in plaintext (indexed for fast lookup)
- Callback tokens hashed using Argon2id
- Constant-time comparison for token validation

### Token Lifecycle
- Tokens **never expire** automatically
- Tokens are invalidated only when:
  - App is explicitly revoked
  - App status is set to suspended
  - Tokens are rotated (old tokens remain valid)

### Authorization
- Bearer token authentication via `Authorization` header
- Status-based access control (only `active` apps can access protected endpoints)
- Scoped permissions (default: `jobs.write`, `kb.read`, `kb.write`, `apps.read`)

---

## Database Schema

### `apps` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `app_id` | String(64) | Unique app identifier (indexed) |
| `client_id` | String(64) | Unique client identifier (indexed) |
| `app_name` | String(255) | Application name |
| `domain` | String(255) | Application domain |
| `default_chat_prompt` | Text | Optional default prompt |
| `chat_callback_url` | String(512) | HTTPS callback URL for chat |
| `upload_callback_url` | String(512) | HTTPS callback URL for uploads |
| `access_token` | String(128) | Bearer token (indexed) |
| `callback_token_hash` | String(255) | Argon2 hash of callback token |
| `scopes` | JSON | Array of permission scopes |
| `status` | Enum | `active`, `revoked`, or `suspended` |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last update timestamp |

---

## Testing

### Run All Tests
```bash
cd backend
./test.sh
```

### Run Unit Tests Only
```bash
./test-unit.sh
```

### Test Coverage
- ✅ Service layer: Token generation, hashing, verification
- ✅ Registration: Happy path + HTTPS validation
- ✅ `/me` endpoint: Valid token, invalid token, inactive app
- ✅ Rotation: Access token, callback token, both, none
- ✅ Revocation: Success, idempotency

---

## Migration

Apply the database migration:

```bash
# Automatic (on app startup)
docker compose up -d

# Manual
docker exec akvo-rag-backend-1 alembic upgrade head
```

---

## Implementation Files

- **Model**: `backend/app/models/app.py`
- **Schemas**: `backend/app/schemas/app.py`
- **Service**: `backend/app/services/app_service.py`
- **Endpoints**: `backend/app/api/api_v1/apps.py`
- **Security**: `backend/app/core/security.py` (added `get_current_app`)
- **Migration**: `backend/alembic/versions/a1b2c3d4e5f6_create_apps_table.py`
- **Tests**:
  - `backend/tests/services/test_app_service.py`
  - `backend/tests/integration/test_app_endpoints.py`

---

## Dependencies Added

- `argon2-cffi>=23.1.0` (for secure callback token hashing)

Install with:
```bash
pip install -r requirements.txt
```
