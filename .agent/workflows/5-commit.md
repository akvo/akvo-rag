---
description: Ship phase - Commit changes using [#issue] Conventional Commits for FastAPI/Next.js
---

# Phase 5: Ship (Commit)

## Purpose
Finalize the feature by committing verified code using the **Conventional Commits** standard. This ensures a readable, machine-parseable history that aligns with the project's documentation standards.

## Prerequisites
- **Phase 4 (Verify)** completed with 100% pass rate on linters (flake8/Black/ESLint) and tests.
- Code follows the project's **Architecture Decision Records (ADRs)**.
- Any new dependencies are correctly documented in `requirements.txt` (backend) or `package.json` (frontend).

## Steps

### 1. Final Review
Conduct a final diff to ensure no debug logs or temporary comments remain.

```bash
git status
git diff --staged
```

### 2. Stage Changes
Stage your changes by vertical slice or specific stack component.

```bash
# Stage backend changes
git add backend/

# Stage frontend changes
git add frontend/
```

### 3. Commit Format
Use the format: `[#issue_number] <type>(<scope>): <description>`. Common scopes for this stack include api, schema, ui, hook, or specific feature names.

Examples:
- Backend: `[#123] feat(api): add FastAPI endpoint for user profile`
- Frontend: `[#123] feat(ui): implement Tailwind-styled dashboard card`
- Testing: `[#123] test(backend): add class-based integration tests for Auth`
- Fix: `[#123] fix(schema): update Pydantic model to allow optional bio`


```bash
git commit -m "[#issue_number] feat(scope): brief description of changes"
```

### 4. Update Project Tracking
Mark the completed items as [x] in task.md and update the PRD.md if applicable.


## Completion Criteria
- [ ] Commits follow the `[#issue_number] <type>(<scope>): <description>` format.
- [ ] No linting or type errors are present in the committed code.
- [ ] task.md reflects 100% completion of the targeted story.


## Final Step
If working in a team, push your branch and open a Pull Request (PR) referencing the relevant Epic or Story ID.