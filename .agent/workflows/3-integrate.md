---
description: Integrate phase - test adapters with real infrastructure via Docker
---

# Phase 3: Integrate (FastAPI & Next.js)

## Purpose
Verify that adapter implementations (PostgreSQL, Redis, external APIs) interact correctly with real infrastructure. This ensures that the architectural decisions made previously are sound in a live environment.

## Prerequisites
- **Phase 2 (Implement)** completed with unit tests passing.
- Docker installed and running locally (all services managed via `./dev.sh`).
- Project setup files include necessary integration testing libraries.

## When Required
- Any code involving database persistence (SQLAlchemy models, Alembic migrations).
- Integration with external services (e.g., Twilio, email/SMTP, external AI).
- Message queues or cache implementations (Redis, Celery).

## Steps

### 1. Setup Integration Environment
Use the project's Docker Compose setup to run integration tests against real services.

```bash
# Ensure all services are running
./dev.sh up -d

# Run backend integration tests
./dev.sh exec backend ./test.sh tests/integration/ -v

# Verify database migrations
# Verify database migrations
./dev.sh exec backend alembic upgrade head
```

### 2. Backend Database Integration
Test real SQL execution against the project's PostgreSQL 17 database.

```python
import pytest
from sqlalchemy import create_engine

class TestPostgresIntegration:
    def test_database_connection(self, db_session):
        # Verify real SQL execution via the project's DB
        result = db_session.execute("SELECT 1")
        assert result.fetchone()[0] == 1
```

### 3. Frontend Integration (Next.js + Playwright/Cypress)
While backend uses Docker containers, frontend integration verifies API contracts with the containerized backend.

```typescript
// Example using Playwright to test API integration
test('should fetch and display real data from backend', async ({ page }) => {
  await page.goto('http://localhost:80/dashboard');
  const item = page.locator('.item-card');
  await expect(item).toBeVisible();
});
```

### 4. Run Integration Tests

```bash
# Backend: Run integration tests via Docker
./dev.sh exec backend ./test.sh tests/integration/ -v

# Frontend: Run Playwright/Cypress integration suite
./dev.sh exec frontend pnpm test:e2e
```

### 5. Manual Verification & UX Sync
- Verify that UX Patterns (loading states, success toasts) behave correctly under real network conditions.
- Check that the Responsive Strategy holds up when data is populated from the database.
- Access the API docs at http://localhost:8000/api/docs to verify endpoints.


### Completion Criteria
- [ ] Integration tests written for all adapters (DB, Cache, APIs).
- [ ] Backend queries verified against the project's PostgreSQL database.
- [ ] Environment variables and secrets handled securely for integration environments.
- [ ] No major regressions in Performance Considerations when hitting real infra.


### Next Phase
Proceed to **Phase 4: Verify** (`/4-verify`)