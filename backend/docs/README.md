# Backend Documentation

This directory contains detailed documentation for the Akvo RAG backend.

## App Registration & Authentication

Documentation for the server-to-server app registration and validation system:

- **[Quick Start Guide](QUICKSTART_APP_REGISTRATION.md)** - Get started in 5 minutes
- **[API Reference](APP_REGISTRATION.md)** - Complete endpoint documentation with examples
- **[Implementation Summary](IMPLEMENTATION_SUMMARY.md)** - Technical implementation details

## Quick Links

### Getting Started
👉 Start here: [Quick Start Guide](QUICKSTART_APP_REGISTRATION.md)

### API Endpoints
- `POST /api/apps/register` - Register new app
- `GET /api/apps/me` - Validate token
- `POST /api/apps/rotate` - Rotate tokens
- `POST /api/apps/revoke` - Revoke app

### Testing
```bash
cd backend
./test.sh  # Run all tests
```

### Files Reference
- Model: `app/models/app.py`
- Service: `app/services/app_service.py`
- Endpoints: `app/api/api_v1/apps.py`
- Tests: `tests/services/test_app_service.py`, `tests/integration/test_app_endpoints.py`

## Other Documentation

See the main [README.md](../../README.md) for general project documentation.
