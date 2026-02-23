---
trigger: model_decision
description: When implementing REST/HTTP APIs (endpoints, handlers, middleware, or response formatting)
---

## API Design Principles

### RESTful API Standards

**Resource-Based URLs:**
- Use plural nouns for resources: `/api/users`, `/api/orders`
- Hierarchical relationships: `/api/users/:userId/orders`
- Avoid verbs in URLs: `/api/getUser` ❌ → `/api/users/:id` ✅

**HTTP Methods:**
- GET: Read/retrieve (safe, idempotent, cacheable)
- POST: Create new resource (not idempotent)
- PUT: Replace entire resource (idempotent)
- PATCH: Partial update (idempotent)
- DELETE: Remove resource (idempotent)

**Pagination:**
- Limit results per page (default 20, max 100)
- Cursor-based: `?cursor=abc123` (better for real-time data)
- Offset-based: `?page=2&limit=20` (simpler)

**Filtering and Sorting:**
- Filtering: `?status=active&role=admin`
- Sorting: `?sort=created_at:desc,name:asc`
- Searching: `?q=search+term`

### HTTP Status Codes

| Code | When to Use |
|------|------------|
| 200 OK | Success (GET, PUT, PATCH) |
| 201 Created | Resource created (POST) |
| 204 No Content | Success with no body (DELETE) |
| 400 Bad Request | Validation errors |
| 401 Unauthorized | Missing/invalid authentication |
| 403 Forbidden | Lacks permission |
| 404 Not Found | Resource doesn't exist |
| 409 Conflict | Business rule violation |
| 422 Unprocessable | Domain rule violation |
| 429 Too Many Requests | Rate limited |
| 500 Internal Server Error | System issue |

### Success Response Format

```json
{
  "data": {},
  "meta": { "total": 100, "page": 1, "perPage": 20 },
  "links": { "self": "/api/users?page=1", "next": "/api/users?page=2" }
}
```

### Error Response Format

```json
{
  "status": "error",
  "code": 400,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid email format",
    "details": { "field": "email", "reason": "Must be a valid address" }
  }
}
```

### Related Rules
- Error Handling @error-handling.md
- Security Mandate @security-mandate.md
- FastAPI Backend @fastapi-backend.md
