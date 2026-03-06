---
trigger: model_decision
description: When implementing error handling, working with error types, or designing error recovery strategies
---

## Error Handling Principles

**1. Never Fail Silently:**
- All errors must be handled explicitly (no empty catch/except blocks)
- If you catch an error, do something with it (log, return, transform, retry)

**2. Fail Fast:**
- Detect and report errors as early as possible
- Validate at system boundaries before processing
- Don't process invalid data hoping it'll work out

**3. Provide Context:**
- Include error codes, correlation IDs, actionable messages
- Enough information for debugging without exposing sensitive details

**4. Separate Concerns:**
- Different handlers for different error types
- Business errors ≠ technical errors ≠ security errors

**5. Resource Cleanup:**
- Always clean up in error scenarios (close files, release connections)
- Python: use `try/finally` or context managers (`with` statements)
- TypeScript: use `try/finally` blocks

**6. No Information Leakage:**
- Sanitize error messages for external consumption
- Don't expose stack traces, SQL queries, file paths to users
- Log full details internally, show generic message externally

### Backend Error Format (FastAPI)

```python
from fastapi import HTTPException

raise HTTPException(
    status_code=400,
    detail={
        "code": "VALIDATION_ERROR",
        "message": "Invalid email format",
        "field": "email"
    }
)
```

### Frontend Error Handling (Next.js)

- Use `error.tsx` for route-level error boundaries
- Use `global-error.tsx` for app-level error boundaries
- Show user-friendly messages, log technical details

### Error Handling Checklist

- [ ] Are all error paths explicitly handled (no empty catch blocks)?
- [ ] Are sensitive details sanitized before returning to client?
- [ ] Are resources cleaned up in all error scenarios?
- [ ] Are errors logged at appropriate levels (warn for 4xx, error for 5xx)?
- [ ] Are error tests written (negative test cases)?

### Related Rules
- API Design @api-design.md
- Security Mandate @security-mandate.md
- Testing Strategy @testing-strategy.md
