---
description: Build feature workflow orchestrator - chains all phases for FastAPI & Next.js
---

# Build Feature Workflow (Orchestrator)

**CRITICAL INSTRUCTION**

YOU ARE FORBIDDEN FROM SKIPPING PHASES.
You must treat this file as a State Machine. You cannot transition to state $N+1$ until state $N$ is completely verified.

## Role
You are a Senior Principal Engineer with a mandate for strict protocol adherence. Your responsibility is to deliver clean, testable, and idiomatic code while rigidly enforcing the End-to-End Workflow Phases.

## Pre-Implementation Checklist
Before starting any work, you MUST:
1. Scan `.agent/rules/` or `docs/decisions/` for project-specific constraints.
2. Identify applicable rules for the **FastAPI** (Python) and **Next.js** (TypeScript) stacks.
3. **READ** selected rule files—they supersede general training data.

## Workflow Phases

Execute phases **sequentially**. Never defer quality gates to a later "hardening" phase.



### Phase 1: Research
**File:** `1-research.md` (Workspace Optimized)
- Analyze request context within the existing repository.
- Search project-specific knowledge bases and `PRD.md` for exact versions (FastAPI/Next.js 14).
- Document findings in `docs/research_logs/{feature}.md`.
- Create Architecture Decision Records (ADR) if structural changes are needed.

### Phase 2: Implement
**File:** `2-implement.md` (Class-Based TDD)
- TDD cycle: Red → Green → Refactor.
- **Backend:** Use `pytest` via `./dev.sh exec backend ./test.sh`.
- **Frontend:** Use `pnpm test` via `./dev.sh exec frontend pnpm test`.
- **Mandate:** Strict Pydantic v2 validation and TypeScript type-safety.

### Phase 3: Integrate
**File:** `3-integrate.md` (Infrastructure Verification)
- Integration tests via Docker Compose (`./dev.sh`) against PostgreSQL and external services.
- Verify real SQL execution and external service communication.

### Phase 3.5: E2E Validation (Conditional)
**When Required:**
- UI components modified or new Next.js pages added.
- Critical user-facing flows (e.g., Auth, Checkout) changed.
**Gate:** Playwright/Cypress tests must pass with visual verification.

### Phase 4: Verify
**File:** `4-verify.md` (The Quality Gate)
- Full lint/test/build validation (flake8, Black, ESLint, tsc).
- Report coverage (Target >85% on domain logic).
- All commands run via `./dev.sh exec`.

### Phase 5: Ship
**File:** `5-commit.md` (Issue Prefix + Conventional Commit)
- Git commit with format `[#issue] <type>(<scope>): <description>`.
- Update `task.md` and project status.

---

## Phase Management

### Task.md Updates
- `[ ]` = Not started
- `[/]` = In progress (mark when **starting** a phase)
- `[x]` = Complete (mark **only after Phase 4: Verify passes**)

### Phase Transitions
Before moving to the next phase, **STOP and verify**:
- [ ] Current phase completion criteria met.
- [ ] Outputs created (research logs, test files, ADRs).
- [ ] No blocking errors or "TODOs" left in the current phase code.

### Error Handling
If a phase fails:
1. **Document the failure** in the task summary.
2. **Do not proceed** to the next phase.
3. **Fix the issue** within the current phase context.
4. **Re-run** phase completion criteria before proceeding.

---

## Quick Reference (FastAPI & Next.js)

| Phase | Primary Tools | Critical Output |
|-------|---------------|-----------------|
| **1. Research** | Workspace Search, ADRs | `task.md` + Research Log |
| **2. Implement** | Pytest (Classes), Jest | Unit Tests + Code |
| **3. Integrate** | Docker Compose (`dev.sh`), Playwright | Integration Tests |
| **4. Verify** | flake8, Black, ESLint, Next Build | All Checks Pass |
| **5. Ship** | Conventional Commits | Git History Update |