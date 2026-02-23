---
trigger: model_decision
description: When creating branches, committing code, managing PRs, or working with version control
---

## Git Workflow Principles

### Commit Messages — Conventional Commits

**Format:**
```
[#issue_number] <type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
| Type | Purpose |
|------|---------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, semicolons, etc. |
| `refactor` | Code change (no new feature/fix) |
| `test` | Adding or updating tests |
| `chore` | Maintenance, dependencies |
| `perf` | Performance improvement |
| `ci` | CI/CD configuration changes |

**Rules:**
- Description is imperative mood ("add" not "added", "fix" not "fixes")
- Scope matches the feature area (e.g., `backend`, `frontend`, `auth`, `api`)
- Description is concise (<72 characters)
- Body explains **why**, not what (the diff shows what)
- **Always** include the issue number in square brackets (e.g., `[#123]`)

### Branch Naming

**Format:** `<type>/<ticket-or-short-description>`

**Examples:**
```
feat/user-crud-api
fix/auth-token-expiry
refactor/storage-layer
chore/update-deps
```

### Commit Hygiene

- **One logical change per commit** — don't mix unrelated changes
- **Never commit broken tests** — all tests must pass before committing
- **Don't commit debug code** — remove console.log, print statements, TODO hacks
- **Don't commit secrets** — use `.gitignore` and environment variables

### PR Size Guidelines

- **Ideal:** <400 lines changed
- **Acceptable:** 400-800 lines
- **Too large:** >800 lines — split into smaller PRs

### Git Workflow Checklist

- [ ] Branch named with correct type prefix?
- [ ] All commits follow the `[#issue]` conventional format?
- [ ] No debug code or secrets committed?
- [ ] All tests pass before committing?
- [ ] PR is <400 lines (or justified if larger)?
- [ ] Commit messages explain why, not just what?

### Related Rules
- Testing Strategy @testing-strategy.md
- Docker Commands @docker-commands.md
