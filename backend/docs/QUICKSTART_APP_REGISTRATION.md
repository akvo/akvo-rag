# Quick Start: App Registration API

## Prerequisites

1. Ensure dependencies are installed:
```bash
pip install -r requirements.txt
```

2. Run database migration:
```bash
# Automatic on container startup
docker compose up -d

# Or manually
docker exec akvo-rag-backend-1 alembic upgrade head
```

## Test the Implementation

### 1. Run Tests

```bash
cd backend
./test.sh
```

Expected output: All tests pass ✅

### 2. Start the Server

```bash
docker compose up -d
```

### 3. Test Endpoints

#### Register a New App

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

**Save the `access_token` from the response!**

#### Validate Your Token

```bash
export ACCESS_TOKEN="<your_token_here>"

curl http://localhost:8000/v1/apps/me \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

#### Rotate Tokens

```bash
curl -X POST http://localhost:8000/v1/apps/rotate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"rotate_access_token": true, "rotate_callback_token": true}'
```

#### Revoke App

```bash
curl -X POST http://localhost:8000/v1/apps/revoke \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

## Verify Revocation

After revoking, this should return 403:

```bash
curl http://localhost:8000/v1/apps/me \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

## API Documentation

Full API reference: `backend/APP_REGISTRATION.md`

## Files Changed/Added

```
backend/
├── requirements.txt                           # Added argon2-cffi
├── app/
│   ├── main.py                               # Added v1_router
│   ├── models/
│   │   ├── app.py                            # NEW: App model
│   │   └── __init__.py                       # Updated
│   ├── schemas/
│   │   ├── app.py                            # NEW: App schemas
│   │   └── __init__.py                       # Updated
│   ├── services/
│   │   └── app_service.py                    # NEW: App service
│   ├── core/
│   │   └── security.py                       # Added get_current_app
│   └── api/
│       ├── v1_api.py                         # NEW: v1 router
│       └── api_v1/
│           └── apps.py                       # NEW: App endpoints
├── alembic/versions/
│   └── a1b2c3d4e5f6_create_apps_table.py    # NEW: Migration
└── tests/
    ├── services/
    │   └── test_app_service.py              # NEW: Service tests
    └── integration/
        └── test_app_endpoints.py            # NEW: Endpoint tests
```

## Troubleshooting

### Issue: Migration doesn't run

**Solution**: Manually run migration
```bash
docker exec akvo-rag-backend-1 alembic upgrade head
```

### Issue: Tests fail with import errors

**Solution**: Install dependencies inside container
```bash
docker exec akvo-rag-backend-1 pip install -r requirements.txt
```

### Issue: Argon2 not found

**Solution**: Install argon2-cffi
```bash
pip install argon2-cffi>=23.1.0
```

## Success Criteria

✅ All tests pass (42 tests)
✅ Can register a new app
✅ Can validate token with `/me`
✅ Can rotate tokens
✅ Can revoke app
✅ Revoked apps return 403
✅ Invalid tokens return 401
✅ Non-HTTPS callbacks rejected with 422

## Next Steps

- Review implementation in `backend/APP_REGISTRATION.md`
- Check test coverage in `tests/services/test_app_service.py` and `tests/integration/test_app_endpoints.py`
- Integrate with your application using the Bearer token
