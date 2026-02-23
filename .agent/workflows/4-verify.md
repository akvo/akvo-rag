---
description: Verify phase - run full validation suite for FastAPI and Next.js
---

# Phase 4: Verify (FastAPI & Next.js)

## Purpose
Run all linters, type checkers, and test suites to ensure the implementation meets the technical and quality standards defined in the project architecture.

## Prerequisites
- **Phase 3 (Integrate)** completed with all integration tests passing.
- All backend and frontend unit tests passing.
- Code aligned with the **Architecture Decision Records (ADRs)**.

## If This Phase Fails
If any linting, type check, or build step fails:
1. **Do not proceed** to Phase 5 (Ship).
2. Address the failure in the relevant component (refer back to Phase 2/3).
3. Re-run the full verification suite until 100% success is achieved.

## Steps

**Set Mode:** Use `task_boundary` to set mode to **VERIFICATION**.

### 1. Backend Validation (FastAPI)
Run the full Python quality suite:

```bash
# 1. Linting (flake8)
./dev.sh exec backend flake8

# 2. Formatting (Black - 79 char line limit)
./dev.sh exec backend black --check --line-length 79 .

# 3. Full Test Suite (Unit + Integration)
./dev.sh exec backend ./test.sh -v
```

### 2. Frontend Validation (Next.js)
Run the TypeScript and Tailwind verification suite:

```bash
# 1. Linting (ESLint)
./dev.sh exec frontend pnpm lint

# 2. Formatting (Prettier)
./dev.sh exec frontend pnpm format

# 3. Component & Logic Tests
./dev.sh exec frontend pnpm test
```

### 3. Build Check
Ensure the code is production-ready and satisfies architectural constraints:

```bash
# Backend: Verify imports and dependencies
./dev.sh exec backend python -c "import app; print('Backend Import Successful')"

# Frontend: Production build
./dev.sh exec frontend pnpm build
```

### 4. Check Coverage
Verify that domain logic meets the project's coverage mandates.

# Python (pytest-cov):
./dev.sh exec backend ./test.sh --cov=app --cov-report=term-missing --cov-fail-under=85

# Next.js:
./dev.sh exec frontend pnpm test -- --coverage


## Completion Criteria
- [ ] All Python linting (flake8) and formatting (Black) checks pass.
- [ ] Next.js production build succeeds without warnings.
- [ ] Overall coverage meets the target (>85% on domain logic).
- [ ] Accessibility (WCAG) targets are verified for UI changes.


## On Success
Mark the current story/task as [x] in your task.md or epics.md file.


## Next Phase
Proceed to **Phase 5: Ship** (`/5-commit`)