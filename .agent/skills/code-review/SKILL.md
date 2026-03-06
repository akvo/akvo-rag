---
name: code-review
description: Structured code review protocol against the full rule set. Use when reviewing code for quality, security, and consistency — either for a feature, PR, or full audit.
---

# Code Review Skill

## Purpose

Systematic code review process that evaluates code against the project's rule set. Produces structured findings with severity tags.

## When to Invoke

- Feature review — all files in a feature directory
- PR review — only changed files
- Full codebase audit — all features
- Via `/4-verify` workflow

---

## Review Process

### 1. Scope the Review

Identify the files/features to review and the review scope.

### 2. Load the Rule Set

Read all applicable rules from `.agent/rules/`. Use `rule-priority.md` for severity classification.

### 3. Review Categories (Priority Order)

#### Critical (Must Fix)
- **Security** — injection, hardcoded secrets, broken auth
- **Data loss** — missing error handling on writes, no transactions
- **Resource leaks** — unclosed connections, missing cleanup

#### Major (Should Fix)
- **Testability** — I/O not behind interfaces, untested error paths
- **Error handling** — empty catch/except blocks, swallowed errors
- **Architecture** — circular dependencies, wrong layer access

#### Minor (Nice to Fix)
- **Pattern consistency** — deviation from established patterns
- **Naming** — unclear variable/function names
- **Code organization** — functions too long, mixed responsibilities

#### Nit (Optional)
- **Style** — formatting issues linters would catch
- **Documentation** — missing comments on complex logic

### 4. Produce Findings

```markdown
# Code Review: {Feature/Module Name}
Date: {date}

## Summary
- **Files reviewed:** N
- **Issues found:** N (X critical, Y major, Z minor, W nit)

## Critical Issues
- [ ] **[SEC]** {description} — {file}:{line}
- [ ] **[DATA]** {description} — {file}:{line}

## Major Issues
- [ ] **[TEST]** {description} — {file}:{line}
- [ ] **[ERR]** {description} — {file}:{line}

## Minor Issues
- [ ] **[PAT]** {description} — {file}:{line}

## Nit
- [ ] {description} — {file}:{line}

## Rules Applied
- List of rules referenced during this review
```

### 5. Severity Tags

| Tag | Category | Rule Source |
|-----|----------|------------|
| `[SEC]` | Security | `security-mandate.md` |
| `[DATA]` | Data integrity | `error-handling.md` |
| `[TEST]` | Testability | `testing-strategy.md` |
| `[ERR]` | Error handling | `error-handling.md` |
| `[ARCH]` | Architecture | `fastapi-backend.md` / `nextjs-frontend.md` |
| `[PAT]` | Pattern consistency | `fastapi-backend.md` / `nextjs-frontend.md` |
| `[API]` | API design | `api-design.md` |

## Rule Compliance

This skill references:
- All rules in `.agent/rules/`
- Rule Priority @rule-priority.md for severity classification
