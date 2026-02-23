---
name: guardrails
description: Pre-flight checklist and post-implementation self-review protocol. Use before generating any code (pre-flight) and after writing code but before verification (self-review) to catch issues early.
---

# Agent Guardrails Skill

## Purpose

Structured checklists that ensure all applicable rules are considered before and after writing code. Catches issues that would otherwise only surface during verification.

## When to Invoke

- **Pre-Flight:** At the start of implementation, before writing any code
- **Self-Review:** After writing code but before running tests/verification

---

## Pre-Flight Checklist

Run through this checklist **before writing any code**:

- [ ] Identified all applicable rules from `.agent/rules/`
- [ ] Searched for existing patterns in codebase
- [ ] Confirmed commands use `./dev.sh exec` (not bare commands)
- [ ] Identified I/O boundaries that need abstraction
- [ ] Determined test strategy (unit/integration/E2E)
- [ ] Reviewed `rule-priority.md` for any potential conflicts

If any item cannot be checked, **stop and resolve** before proceeding.

---

## Post-Implementation Self-Review

Run through this checklist **after writing code, before verification**:

### Security
- [ ] No hardcoded secrets or configuration values
- [ ] All user input validated at system boundaries
- [ ] Backend: Parameterized queries via SQLAlchemy (no string SQL)
- [ ] Frontend: No API keys exposed in client-side code

### Testability
- [ ] All I/O operations behind interfaces/abstractions
- [ ] Business logic is pure (no side effects in calculations)
- [ ] Dependencies injected, not hardcoded

### Error Handling
- [ ] Error paths handled explicitly (no empty catch/except blocks)
- [ ] Errors provide context (wrapped with additional info)
- [ ] Resources cleaned up in error paths

### Testing
- [ ] Tests cover happy path
- [ ] Tests cover at least 2 error paths
- [ ] Tests cover edge cases relevant to the domain
- [ ] Backend: `./dev.sh exec backend ./test.sh`
- [ ] Frontend: `./dev.sh exec frontend pnpm test`

### Consistency
- [ ] Follows existing codebase patterns (>80% consistency)
- [ ] Naming conventions match the codebase
- [ ] Backend: PEP 8, Black 79-char, flake8 clean
- [ ] Frontend: ESLint clean, Prettier formatted

## Rule Compliance

This skill enforces:
- Security Mandate @security-mandate.md (always_on)
- Docker Commands @docker-commands.md (always_on)
- Testing Strategy @testing-strategy.md
- Rule Priority @rule-priority.md
