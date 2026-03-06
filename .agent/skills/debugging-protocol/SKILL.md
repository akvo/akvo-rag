---
name: debugging-protocol
description: Systematic protocol for debugging complex issues. Use when facing bugs, test failures, unexpected behavior, or performance problems. Provides a structured hypothesis-driven approach to find root causes.
---

# Debugging Protocol

## Overview

This skill provides a rigorous framework for debugging complex software issues. It moves beyond ad-hoc troubleshooting to a structured process of hypothesis generation and validation.

Use this skill to:
1. Formalize a debugging session
2. Systematically eliminate potential root causes
3. Document findings for future reference

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## Protocol Workflow

### Phase 1: Root Cause Investigation

**BEFORE attempting ANY fix:**

1. **Read Error Messages Carefully**
   - Don't skip past errors or warnings
   - Read stack traces completely
   - Note line numbers, file paths, error codes

2. **Reproduce Consistently**
   - Can you trigger it reliably?
   - Check backend logs: `./dev.sh logs backend`
   - Check frontend logs: `./dev.sh logs frontend`

3. **Check Recent Changes**
   - What changed? `git diff`, recent commits
   - New dependencies, config changes?

4. **Gather Evidence in Multi-Component Systems**
   ```
   For EACH component boundary (Frontend → Backend → Database):
     - Log what data enters component
     - Log what data exits component
     - Verify environment/config propagation
   ```

5. **Trace Data Flow**
   - Where does the bad value originate?
   - Keep tracing up until you find the source
   - Fix at source, not at symptom

### Phase 2: Pattern Analysis

1. **Find Working Examples** — Locate similar working code in the codebase
2. **Compare Against References** — Read reference implementations COMPLETELY
3. **Identify Differences** — List every difference, however small
4. **Understand Dependencies** — What settings, config, environment needed?

### Phase 3: Hypothesis and Testing

1. **Form Single Hypothesis** — "I think X is the root cause because Y"
2. **Test Minimally** — Make the SMALLEST possible change
3. **Verify Before Continuing** — Worked? → Phase 4. Didn't? → New hypothesis
4. **Don't stack fixes** — If it didn't work, revert and try a new approach

### Phase 4: Implementation

1. **Create Failing Test Case**
   - Backend: `./dev.sh exec backend ./test.sh -k "test_name"`
   - Frontend: `./dev.sh exec frontend pnpm lint` (or relevant test command)
   - MUST exist before fixing and MUST run inside Docker

2. **Implement Single Fix** — ONE change at a time

3. **Verify Fix** — Test passes? No regressions?

4. **If 3+ Fixes Failed: Question Architecture**
   - Each fix reveals new problem? → Architectural issue
   - Discuss with team before attempting more fixes

## Red Flags — STOP and Return to Phase 1

- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "I don't fully understand but this might work"
- Proposing solutions before tracing data flow
- Already tried 2+ fixes without success

## Quick Reference

| Phase | Key Activities | Success Criteria |
|-------|---------------|------------------|
| 1. Root Cause | Read errors, reproduce, check changes | Understand WHAT and WHY |
| 2. Pattern | Find working examples, compare | Identify differences |
| 3. Hypothesis | Form theory, test minimally | Confirmed or new hypothesis |
| 4. Implementation | Create test, fix, verify | Bug resolved, tests pass |

## Rule Compliance

When debugging, verify against:
- Error Handling @error-handling.md (proper error propagation)
- Testing Strategy @testing-strategy.md (regression test for the fix)
- Docker Commands @docker-commands.md (all commands via `./dev.sh exec`)
