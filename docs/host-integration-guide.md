# Host Application Integration Guide: Akvo RAG 🌐

This comprehensive guide details how external host applications (such as **AgriConnect**, **CoM**, or third-party web portals) integrate with **Akvo RAG** as a multi-tenant retrieval-augmented generation engine.

---

## 1. Architectural Overview & Security Model

Akvo RAG provides a multi-tenant API designed specifically for host applications. In this architecture:
- **Host applications** own their end users, permissions, and business logic.
- **Akvo RAG** acts as the backend AI/retrieval engine for knowledge ingestion, vector search, and answer synthesis.
- **Authentication**: Host applications authenticate to Akvo RAG using an application-scoped bearer token (`tok_...`). The token is hashed with **Argon2** inside Akvo RAG's database, ensuring zero plaintext token persistence.
- **Bidirectional Webhooks**: For long-running operations (such as document ingestion and streaming chat generation), Akvo RAG communicates back to the host application via secure webhooks signed with a shared `callback_token`.

```
 ┌────────────────────────────────┐                 ┌────────────────────────────────┐
 │     Host Application           │                 │       Akvo RAG Platform        │
 │   (e.g., AgriConnect / CoM)    │                 │                                │
 │                                │                 │  ┌──────────────────────────┐  │
 │  1. Register App               │── POST /apps ──▶│  │ Tenant App Service       │  │
 │     (Receive `tok_...`)        │◀─ 201 Created ──│  │ (Argon2 Hashed Storage)  │  │
 │                                │                 │  └─────────────┬────────────┘  │
 │  2. Create KB & Upload Docs    │── POST /jobs ──▶│                ▼               │
 │     (Bearer tok_...)           │                 │  ┌──────────────────────────┐  │
 │                                │                 │  │ Vector KB Worker         │  │
 │  3. Webhook Ingestion Callback │◀── POST /kb ────│  │ (ChromaDB + MinIO S3)    │  │
 │     (Bearer callback_token)    │                 │  └─────────────┬────────────┘  │
 │                                │                 │                ▼               │
 │  4. Submit Chat Query          │── POST /jobs ──▶│  ┌──────────────────────────┐  │
 │     (Bearer tok_...)           │                 │  │ Dual-Tier LangGraph      │  │
 │  5. Webhook Chat Response      │◀── POST /ai ────│  │ (FAST / SYNTHESIS LLM)   │  │
 └────────────────────────────────┘                 └────────────────────────────────┘
```

---

## 2. Network Topology & Base URLs

### Local Development (Docker-to-Docker)
When running both your host application and Akvo RAG locally in separate Docker Compose networks:
- **Container-to-Container**: `http://host.docker.internal:8000` (or `http://host.docker.internal:8010` if port-shifted).
- **Host Machine / Browser / Swagger**: `http://localhost:8000/docs` (or `http://localhost:8010/docs`).

> [!TIP]
> On Linux Docker setups, add `extra_hosts: ["host.docker.internal:host-gateway"]` to your host app's `docker-compose.yml` to enable `host.docker.internal` routing. On macOS and Windows Docker Desktop, this works out of the box.

### Production Environment
In production, use the fully qualified domain name (FQDN):
- **Base URL**: `https://rag.akvo.org/api/v1`
- **Webhooks**: Must use public HTTPS URLs (e.g. `https://your-host-app.org/api/callbacks/rag`).

---

## 3. Step-by-Step Integration Walkthrough

### Step 1: Register Your Application

To obtain API credentials, register your host application with Akvo RAG.

```bash
curl -X POST http://localhost:8000/api/v1/apps/register \
  -H "Content-Type: application/json" \
  -d '{
    "app_name": "AgriConnect",
    "domain": "agriconnect.akvo.org",
    "default_chat_prompt": "You are AgriConnect AI, an expert agronomy advisor supporting smallholder farmers.",
    "chat_callback": "https://agriconnect.akvo.org/api/callbacks/ai",
    "upload_callback": "https://agriconnect.akvo.org/api/callbacks/kb",
    "callback_token": "your_secure_random_callback_secret_token"
  }'
```

#### Request Payload Fields:
| Field | Type | Required | Description |
|:---|:---:|:---:|:---|
| `app_name` | `string` | ✅ | Unique name identifier for your host application. |
| `domain` | `string` | ✅ | Primary domain or hostname of your application. |
| `default_chat_prompt`| `string` | ❌ | Default system persona/prompt override for chat queries. |
| `chat_callback` | `string` | ❌ | HTTPS webhook URL where chat responses will be delivered. |
| `upload_callback` | `string` | ❌ | HTTPS webhook URL where document ingestion status updates will be delivered. |
| `callback_token` | `string` | ✅ | Shared secret token Akvo RAG sends in the `Authorization` header when calling your webhooks. |

#### Response (`201 Created`):
```json
{
  "app_id": "app_H6quogDyGNxQQgIKdg2sog",
  "client_id": "ac_wClwAYUnO5mIM8DFuztKYQ",
  "access_token": "tok_1a2b3c4d5e6f7g8h9i0j_example_token",
  "scopes": ["jobs.write", "kb.read", "kb.write", "apps.read"],
  "knowledge_bases": [
    {
      "knowledge_base_id": 101,
      "name": "AgriConnect Default KB",
      "is_default": true
    }
  ]
}
```

> [!CAUTION]
> The `access_token` (`tok_...`) is shown **only once** upon registration. Akvo RAG stores only its Argon2 hash. Store this token securely in your host application's environment configuration (e.g. `RAG_APP_TOKEN`).

---

### Step 2: Validate Authentication

Verify that your token is valid and inspect registered metadata:

```bash
curl -X GET http://localhost:8000/api/v1/apps/me \
  -H "Authorization: Bearer tok_1a2b3c4d5e6f7g8h9i0j_example_token"
```

---

### Step 3: Knowledge Base Management

Host applications can manage their own isolated Knowledge Bases (KBs).

#### 1. List All Accessible Knowledge Bases
```bash
curl -X GET http://localhost:8000/api/v1/apps/knowledge-bases \
  -H "Authorization: Bearer tok_..."
```

#### 2. Create a New Knowledge Base
```bash
curl -X POST http://localhost:8000/api/v1/apps/knowledge-bases \
  -H "Authorization: Bearer tok_..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Kenya Avocado Extension Guide",
    "description": "Agronomy knowledge base for avocado pest management and soil health."
  }'
```

#### 3. Update Knowledge Base
```bash
curl -X PATCH http://localhost:8000/api/v1/apps/knowledge-bases/101 \
  -H "Authorization: Bearer tok_..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Kenya Avocado & Macadamia Guide"
  }'
```

#### 4. Delete Knowledge Base
```bash
curl -X DELETE http://localhost:8000/api/v1/apps/knowledge-bases/101 \
  -H "Authorization: Bearer tok_..."
```

---

### Step 4: Document Ingestion & Uploads

Documents (PDF, DOCX, TXT) uploaded by your host application are processed asynchronously via MinIO S3 and ChromaDB vector indexing.

#### Option A: Submit Asynchronous Upload Job (Recommended)
```bash
curl -X POST http://localhost:8000/api/v1/apps/jobs \
  -H "Authorization: Bearer tok_..." \
  -F 'payload={"job": "upload", "knowledge_base_id": 101, "callback_params": {"external_doc_id": "doc_991"}}' \
  -F 'files=@/path/to/avocado_sop.pdf'
```

#### Option B: Direct Document Upload Endpoint
```bash
curl -X POST http://localhost:8000/api/v1/apps/knowledge-bases/101/documents/upload \
  -H "Authorization: Bearer tok_..." \
  -F 'file=@/path/to/avocado_sop.pdf'
```

---

### Step 5: AI Chat & Advisory Queries

Submit questions to Akvo RAG to perform vector search, reranking, and contextual LLM generation.

#### 1. Submit Query Job (SSE or Async Webhook)
```bash
curl -X POST http://localhost:8000/api/v1/apps/jobs \
  -H "Authorization: Bearer tok_..." \
  -F 'payload={
    "job": "chat",
    "knowledge_base_ids": [101],
    "prompt": "How do I manage False Codling Moth (FCM) on avocado crops?",
    "chats": [
      {"role": "user", "content": "What are common pests in Kenya?"},
      {"role": "assistant", "content": "Common pests include FCM, thrips, and fruit flies."}
    ],
    "callback_params": {
      "session_id": "sess_abc123",
      "user_id": "usr_farmer_45"
    }
  }'
```

---

## 4. Implementing Webhook Receivers in Your Host App

When long-running jobs complete, Akvo RAG posts results to the `upload_callback` and `chat_callback` URLs defined during registration.

### 1. Document Upload Callback Payload (`upload_callback`)

Akvo RAG sends a `POST` request with the following JSON structure:

```json
{
  "event": "document_indexed",
  "app_id": "app_H6quogDyGNxQQgIKdg2sog",
  "knowledge_base_id": 101,
  "document_id": "doc_8f93a1c2",
  "filename": "avocado_sop.pdf",
  "status": "COMPLETED",
  "chunks_indexed": 42,
  "callback_params": {
    "external_doc_id": "doc_991"
  },
  "error": null
}
```

### 2. Chat Query Callback Payload (`chat_callback`)

```json
{
  "event": "chat_completed",
  "app_id": "app_H6quogDyGNxQQgIKdg2sog",
  "response": "To control False Codling Moth (FCM), implement an integrated pest management (IPM) approach including sanitation, pheromone traps, and targeted biological treatments.",
  "citations": [
    {
      "document_name": "avocado_sop.pdf",
      "chunk_id": "chunk_12",
      "page_number": 4,
      "snippet": "Field sanitation is critical: collect and bury all fallen avocado fruits at least 50 cm deep."
    }
  ],
  "usage": {
    "prompt_tokens": 820,
    "completion_tokens": 115,
    "model_tier": "SYNTHESIS"
  },
  "callback_params": {
    "session_id": "sess_abc123",
    "user_id": "usr_farmer_45"
  }
}
```

### 3. Webhook Authentication Verification

To ensure webhook authenticity, verify the incoming `Authorization` header:

```python
# FastAPI Webhook Receiver Example
from fastapi import FastAPI, Header, HTTPException, Request

app = FastAPI()
EXPECTED_CALLBACK_TOKEN = "your_secure_random_callback_secret_token"

@app.post("/api/callbacks/ai")
async def handle_rag_ai_callback(request: Request, authorization: str = Header(None)):
    if not authorization or authorization != f"Bearer {EXPECTED_CALLBACK_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized callback request")
    
    data = await request.json()
    print(f"Received RAG response for user {data['callback_params']['user_id']}: {data['response']}")
    return {"status": "received"}
```

---

## 5. Ready-to-Use Host Client SDK Examples

### Python Example (`httpx` / `asyncio`)

```python
import httpx
import json

class AkvoRAGClient:
    def __init__(self, base_url: str, app_token: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {app_token}"}

    async def list_knowledge_bases(self):
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{self.base_url}/api/v1/apps/knowledge-bases", headers=self.headers)
            res.raise_for_status()
            return res.json()

    async def ask_question(self, kb_id: int, question: str, session_id: str):
        payload = {
            "job": "chat",
            "knowledge_base_ids": [kb_id],
            "prompt": question,
            "callback_params": {"session_id": session_id}
        }
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{self.base_url}/api/v1/apps/jobs",
                headers=self.headers,
                data={"payload": json.dumps(payload)}
            )
            res.raise_for_status()
            return res.json()
```

### TypeScript / Node.js Example

```typescript
import axios from 'axios';
import FormData from 'form-data';
import fs from 'fs';

export class AkvoRAGClient {
  constructor(private baseUrl: string, private appToken: string) {}

  private get headers() {
    return { Authorization: `Bearer ${this.appToken}` };
  }

  async getKnowledgeBases() {
    const response = await axios.get(`${this.baseUrl}/api/v1/apps/knowledge-bases`, {
      headers: this.headers
    });
    return response.data;
  }

  async uploadDocument(kbId: number, filePath: string) {
    const form = new FormData();
    form.append('payload', JSON.stringify({ job: 'upload', knowledge_base_id: kbId }));
    form.append('files', fs.createReadStream(filePath));

    const response = await axios.post(`${this.baseUrl}/api/v1/apps/jobs`, form, {
      headers: { ...this.headers, ...form.getHeaders() }
    });
    return response.data;
  }
}
```

---

## 6. Verification, Testing & QA Playbook

To test and verify host application endpoints against a live local instance:

1. **Interactive Swagger**:
   - Navigate to `http://localhost:8000/docs` (or `http://localhost:8010/docs`).
   - Click the green **Authorize** button, type `Bearer tok_...`, and execute requests under the `apps` section.

2. **Automated Integration Test Suites**:
   Run the backend verification suite to validate host contracts:
   ```bash
   # Test App registration & tenant token auth
   docker exec akvo-rag-backend-1 python -m pytest tests/integration/test_app_endpoints.py -v

   # Test AgriConnect specific end-to-end integration lifecycle
   docker exec akvo-rag-backend-1 python -m pytest tests/integration/test_agriconnect_integration.py -v

   # Test Host API backward compatibility
   docker exec akvo-rag-backend-1 python -m pytest tests/api/test_host_api_backwards_compatibility.py -v
   ```

---

## 7. Troubleshooting & Common Pitfalls

| Issue | Root Cause | Solution |
|:---|:---|:---|
| **`401 Unauthorized`** | Missing or malformed `Authorization` header. | Pass `Authorization: Bearer tok_...` (ensure the `Bearer ` prefix is included). |
| **`403 Forbidden`** | App token is attempting to access a KB owned by another app. | Ensure requests only target KBs returned by `GET /api/v1/apps/knowledge-bases`. |
| **`400 Bad Request` on Upload** | Unsupported file format or invalid magic bytes. | Ensure files are valid PDF (`%PDF-`), DOCX, or TXT format. |
| **Webhook Callbacks Failing** | Host app container not reachable from RAG container. | Use `http://host.docker.internal:<port>` in local Docker development, or ngrok (`https://....ngrok.dev`). |
| **`422 Unprocessable Entity`** | Invalid registration callback URL format. | Ensure callback URLs are valid URI strings (HTTPS required in production). |
