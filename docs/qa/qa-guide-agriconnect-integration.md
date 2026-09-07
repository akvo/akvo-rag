# QA & Host Integration Guide: AgriConnect and Host Integration (TASK-INT-503)

This guide documents the API contracts, backwards compatibility expectations, and manual verification procedures for integrating AgriConnect with the Akvo RAG service.

---

## 1. Overview & Dual Route Mount

To maintain 100% backward compatibility with existing mobile clients, web dashboards, and partner host systems like AgriConnect, Akvo RAG exposes dual endpoint mounts:
- Legacy `/api/...` prefix
- Standard Section 7.3 `/api/v1/...` prefix

Both prefixes route to identical FastAPI application routers with identical behavior, headers, serialization schemas, and status codes.

| Resource | Legacy Endpoint | Section 7.3 Canonical Endpoint |
|---|---|---|
| Knowledge Bases | `GET /api/knowledge-bases` | `GET /api/v1/knowledge-bases` |
| Create Knowledge Base | `POST /api/knowledge-bases` | `POST /api/v1/knowledge-bases` |
| Upload Document | `POST /api/knowledge-bases/{id}/upload` | `POST /api/v1/knowledge-bases/{id}/upload` |
| Task Status Polling | `GET /api/knowledge-bases/tasks/{task_id}` | `GET /api/v1/knowledge-bases/tasks/{task_id}` |
| RAG Chat / Dialogue | `POST /api/chat/` | `POST /api/v1/chat/` |
| Prompt Versioning | `GET /api/prompt` | `GET /api/v1/prompt` |
| API Keys | `GET /api/api-keys` | `GET /api/v1/api-keys` |

---

## 2. Authentication

Requests must include a Bearer token or API key depending on the service tier.

```bash
# Using JWT Bearer token:
Authorization: Bearer eyJhbGciOi...

# Using API Key header (when configured):
X-API-KEY: akvo_key_...
```

---

## 3. End-to-End AgriConnect Workflows

### 3.1 Create Knowledge Base for Crop Pest Management

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/knowledge-bases" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Pest Management & Crop Advisory",
    "description": "Integrated pest management guidelines and disease diagnostics for smallholder farmers"
  }'
```

**Expected Response (`200 OK` or `201 Created`):**
```json
{
  "id": 1,
  "name": "Pest Management & Crop Advisory",
  "description": "Integrated pest management guidelines and disease diagnostics for smallholder farmers",
  "created_at": "2026-09-07T05:50:00Z"
}
```

---

### 3.2 Upload Technical Advisory Document (Multipart)

Documents must be standard PDF, TXT, or DOCX files. The ingestion worker verifies magic bytes (e.g. `%PDF-1.4`).

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/knowledge-bases/1/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@fall_armyworm_control_guide.pdf;type=application/pdf"
```

**Expected Response (`202 Accepted` or `200 OK`):**
```json
{
  "task_id": "c6a71cb0-4e31-40be-9852-5a907106fe98",
  "message": "File upload accepted and queued for processing",
  "status": "processing"
}
```

---

### 3.3 Poll Ingestion Task Status

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/knowledge-bases/tasks/c6a71cb0-4e31-40be-9852-5a907106fe98" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response (`200 OK`):**
```json
{
  "task_id": "c6a71cb0-4e31-40be-9852-5a907106fe98",
  "status": "completed",
  "progress": 100,
  "result": {
    "total_chunks": 42,
    "vector_count": 42
  }
}
```

---

### 3.4 Query Crop Pest Advisory via RAG Chat

Farmers and extension agents ask questions. The system returns an answer enriched with source citations and document references.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/chat/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How should I treat Fall Armyworm on young maize?",
    "knowledge_base_ids": [1],
    "app_id": "agriconnect-mobile-app",
    "stream": false
  }'
```

**Expected Response (`200 OK`):**
```json
{
  "response": "For young maize infested by Fall Armyworm, apply bio-pesticides such as Bacillus thuringiensis (Bt) or neem-based extracts at the early whorl stage. Ensure spraying is targeted into the leaf whorls during early morning or late evening.",
  "citations": [
    {
      "source": "fall_armyworm_control_guide.pdf",
      "page": 4,
      "text": "Apply neem extract (5%) or Bt into the whorls of maize seedlings..."
    }
  ]
}
```

---

## 4. Automated Integration Verification Suite

Run the full AgriConnect end-to-end integration and backwards compatibility tests inside the container:

```bash
# 1. AgriConnect specific end-to-end suite
docker exec akvo-rag-backend-1 python -m pytest tests/integration/test_agriconnect_integration.py -v

# 2. Host API backwards compatibility suite (both /api and /api/v1)
docker exec akvo-rag-backend-1 python -m pytest tests/api/test_host_api_backwards_compatibility.py -v
```

---

## 5. Troubleshooting & Gotchas

1. **Routing 404s:**
   Ensure your reverse proxy (Nginx or Traefik) passes `/api/` and `/api/v1/` routes to the backend without stripping leading path elements.
2. **Document Upload Rejections:**
   Ensure uploaded PDF headers start with `%PDF-`. Files with invalid magic bytes will be rejected with `400 Bad Request`.
3. **Task Queue Latency:**
   If `task_status` remains `processing` for more than 30 seconds, inspect the ingestion worker logs:
   ```bash
   docker logs akvo-rag-ingestion-worker-1 --tail 50
   ```
