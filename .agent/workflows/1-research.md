---
description: Research phase - deep context discovery and workspace knowledge gathering
---

# Phase 1: Research (Workspace Optimized)

## Purpose
Understand the request context by analyzing the existing codebase and gathering project-specific technical knowledge before implementation.

## Steps

### 1. Analyze Request & Workspace Context
Parse the user's request and cross-reference with the project state:
- **Scope:** Define what is being asked.
- **Context:** Check `PRD.md` or existing documentation to align with the project's current phase.

### 2. Repository Reconnaissance (Internal KB)
Search the current workspace to understand:
- **Architecture:** Identify relevant modules in `backend/` or `frontend/`.
- **Patterns:** Locate similar implementations (e.g., existing CRUD logic, routers, services) to ensure consistency.
- **Dependencies:** Review `requirements.txt` (backend) and `package.json` (frontend) for specific versions.

### 3. Build Mental Model
Inventory the "Knowns":
- **Business Logic:** Derived from existing requirements.
- **Technical Constraints:** Limitations of the current stack (FastAPI, Next.js 14, PostgreSQL).
- **Integration Points:** Where exactly the new code touches the old.

### 4. Define Scope & Task Boundary
Create a plan with bite-sized atomic tasks in `task.md`:
- Use `task_boundary` to set mode to **PLANNING**.
- Map tasks to specific files identified in Step 2.

### 5. Identify Research Topics
List specific technologies and internal patterns that need verification.

### 6. Technical & Documentation Research
Instead of generic searches, perform targeted queries for the project's specific versions:
- Use **Web Search** to find official documentation for the **exact versions** found in your setup files (e.g., "Next.js 14 App Router patterns", "FastAPI dependency injection").
- Search for "Migration Guides" or "Breaking Changes" if touching older dependencies.

### 7. Document Findings (Research Logs)
Create `docs/research_logs/{feature_name}.md`. **Must Include:**
- **Internal References:** "Follows pattern found in `backend/routers/auth.py`."
- **API Signatures:** Verified from current documentation.
- **Workspace Gotchas:** Specific issues found in this repo's history/code.

### 8. Architectural Decision Records (ADRs)
If the research leads to a change in the established project structure, create an ADR at `docs/decisions/NNNN-title.md`.

## Completion Criteria
- [ ] Workspace analyzed (Patterns & Versions identified)
- [ ] `task.md` created with file-specific atomic tasks
- [ ] Research log created referencing internal and external sources created at docs/research_logs/{feature_name}.md
- [ ] All major technologies researched
- [ ] Code examples documented
- [ ] ADR created if architectural patterns are deviated from

## Next Phase
Proceed to **Phase 2: Implement** (`/2-implement`)