---
description: Implement phase - Red-Green-Refactor with Class-Based Python testing
---

# Phase 2: Implement (FastAPI & Next.js)

## Purpose
Write production code following Test-Driven Development (TDD) principles to ensure high-quality, maintainable features for both the FastAPI backend and Next.js frontend.

## Prerequisites
- **Phase 1 (Research)** completed with a documented research log.
- **Technical Specification** finalized, detailing the specific file changes and API contracts.
- **Task.md** updated to reflect the current story in progress.

## Steps

**Set Mode:** Use `task_boundary` to set mode to **EXECUTION**.

### 1. Create Test Files
- **Backend (Python):** Create `backend/tests/test_{feature_name}.py`.
- **Frontend (Next.js):** Co-locate `*.test.tsx` within the component folder or `frontend/src/tests/`.

### 2. Write Failing Test (Red)
**Backend: Class-Based pytest**
Group related behaviors into classes to share setup logic and improve organization.

```python
import pytest
from fastapi.testclient import TestClient

class TestItemFeature:
    @pytest.fixture(autouse=True)
    def setup(self, client: TestClient):
        self.client = client
        self.url = "/api/v1/items/"

    def test_create_item_success(self, auth_headers):
        # Arrange
        payload = {"title": "Discovery", "description": "TDD via Class"}
        # Act
        response = self.client.post(self.url, json=payload, headers=auth_headers)
        # Assert
        assert response.status_code == 201
        assert response.json()["title"] == payload["title"]
```

**Frontend: Jest + React Testing Library**
```typescript
describe('FeatureComponent', () => {
    it('should render the success state after submission', async () => {
        render(<FeatureComponent />);
        // Red: Test fails because component or logic doesn't exist yet
    });
});
```

### 3. Write Minimal Code (Green)
Write only the code necessary to make the tests pass:
- Define FastAPI routes and Pydantic schemas in `backend/routers/`.
- Implement React components and Tailwind CSS styling in `frontend/`.


### 4. Refactor (Blue)
Improve the code while keeping the tests green:
- Python: Ensure Pydantic v2 compliance, proper type hinting, and FastAPI dependency usage.
- Next.js: Optimize Tailwind classes and ensure Server/Client component boundaries are correct.
- Conventions: Verify snake_case for Python and PascalCase for React components.
- Observability: Implement logging per the project's tech spec.

### 5. Repeat
Continue the Red-Green-Refactor cycle for each story requirement.

### Unit Test Requirements
- Mocks: Use pytest-mock for Python services and msw for frontend API mocking.
- Coverage: Target >85% coverage on domain logic and critical paths.


## Development Commands

```bash
# Python: Run tests (via Docker)
./dev.sh exec backend ./test.sh -v

# Python: Coverage report
# Python: Coverage report
./dev.sh exec backend ./test.sh --cov=app --cov-report=html

# Frontend: Run tests
./dev.sh exec frontend pnpm test
```


## Completion Criteria
- [ ] Unit tests written and passing
- [ ] Implementation complete
- [ ] Error handling follows principles
- [ ] Logging added to operations
- [ ] Code follows project patterns


## Next Phase
Proceed to **Phase 3: Integrate** (`/3-integrate`)