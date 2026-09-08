# QA & Host Integration Guide: AgriConnect and Akvo RAG Integration (TASK-INT-503)

This comprehensive guide documents the architecture, dual-route API contracts, exact endpoints used by **AgriConnect**, step-by-step local Swagger setup, end-to-end workflows, and automated verification suites.

---

## 1. Architectural Overview & Network Topology

Both projects run in independent Docker Compose networks on your local machine:

- **AgriConnect**: Runs on default host ports (`8000`, `3000`, `5432`, `6379`).
- **Akvo RAG**: Runs on offset host ports (`8010`, `3010`, `5433`, `6380`, `8002`, `9010/9011`).

Because each project operates in its own Docker network (`akvo-rag_default` and `agriconnect_default`), communication from the **AgriConnect backend container** to the **Akvo RAG backend container** routes through the Docker host gateway:

- **Internal Container Gateway**: `http://host.docker.internal:8010`
- **Host Machine / Browser**: `http://localhost:8010` (Backend API / Swagger) and `http://localhost:3010` (Web UI)

```
  ┌────────────────────────────────────────────────────────┐
  │                    Localhost / Mac                     │
  │                                                        │
  │   AgriConnect Containers        Akvo RAG Containers    │
  │   ┌────────────────────┐        ┌────────────────────┐ │
  │   │ backend:8000       │───────▶│ backend:8000       │ │
  │   │ (host port 8000)   │        │ (host port 8010)   │ │
  │   └────────────────────┘        └────────────────────┘ │
  │              ▲                             ▲           │
  │              │                             │           │
  │   http://host.docker.internal:8010         │           │
  │   (routes via host port 8010)              │           │
  │                                            │           │
  └────────────────────────────────────────────┼───────────┘
                                               │
                                      Browser / Frontend:
                                    http://localhost:3010
```

---

## 2. Which Routes Does AgriConnect Actually Use?

In AgriConnect's codebase (`backend/services/external_ai_service.py`), AgriConnect operates through 4 distinct configurable URLs stored in its `service_tokens` table:

1. **`chat_url` ➔ `POST /api/v1/apps/jobs` (or `/api/apps/jobs`)**:
   - **How AgriConnect calls it**: AgriConnect sends `multipart/form-data` with `payload={"job": "chat", "chats": [...], "prompt": "...", "callback_params": {...}}`.
   - **Akvo RAG handling**: Handled by the universal `jobs.router` mounted at `/api/v1/apps/jobs`. It dispatches asynchronous answer synthesis and posts results back to AgriConnect's `chat_callback` webhook.

2. **`upload_url` ➔ `POST /api/v1/apps/jobs` (or `POST /api/v1/apps/upload`)**:
   - **How AgriConnect calls it**:
     - *Preferred (Async Job)*: Sends `multipart/form-data` with `payload={"job": "upload", "knowledge_base_id": ...}` and `files=[...]` to `POST /api/v1/apps/jobs`. Notifies AgriConnect's `upload_callback` webhook on completion.
     - *Direct upload*: Sends `files=[...]` to `POST /api/v1/apps/upload`.

3. **`kb_url` ➔ `http://host.docker.internal:8010/api/v1/apps/knowledge-bases`**:
   - **How AgriConnect calls it**:
     - `POST {kb_url}`: Creates a new Knowledge Base under the app (`POST /api/v1/apps/knowledge-bases`).
     - `GET {kb_url}`: Lists all Knowledge Bases belonging to the app (`GET /api/v1/apps/knowledge-bases`).
     - `GET {kb_url}/{kb_id}`: Fetches KB details (`GET /api/v1/apps/knowledge-bases/{kb_id}`).
     - `PATCH {kb_url}/{kb_id}`: Updates KB metadata (`PATCH /api/v1/apps/knowledge-bases/{kb_id}`).
     - `DELETE {kb_url}/{kb_id}`: Deletes the KB (`DELETE /api/v1/apps/knowledge-bases/{kb_id}`).

4. **`document_url` ➔ `http://host.docker.internal:8010/api/v1/apps/documents`**:
   - **How AgriConnect calls it**:
     - `GET {document_url}?kb_id={id}`: Lists indexed documents in a knowledge base.
     - `DELETE {document_url}?kb_id={id}&doc_id={id}`: Deletes a document from the KB.

---

## 3. Step-by-Step Local Integration Walkthrough (Swagger UI)

### Step 3.1: Register AgriConnect in Akvo RAG

1. Open **[http://localhost:8010/docs](http://localhost:8010/docs)**.
2. Under the **`apps`** section, expand **`POST /api/v1/apps/register`** (or `POST /api/apps/register`).
3. Click **"Try it out"**, provide the registration payload:

   ```json
   {
     "app_name": "AgriConnect Local",
     "domain": "agriconnect.local",
     "default_chat_prompt": "You are AgriConnect AI, an expert agronomy advisor supporting smallholder farmers.",
     "chat_callback": "https://akvo.ngrok.dev:8000/api/callback/ai",  // or "http://host.docker.internal:8000/api/callback/ai"
     "upload_callback": "https://akvo.ngrok.dev:8000/api/callback/kb", // or "http://host.docker.internal:8000/api/callback/kb"
     "callback_token": "local_agriconnect_secret_token"
   }
   ```

4. Click **"Execute"**.
5. In the **`201 Created`** response, copy the **`access_token`** (starts with `tok_...`):

   ```json
   {
     "app_id": "app_H6quogDyGNxQQgIKdg2sog",
     "client_id": "ac_wClwAYUnO5mIM8DFuztKYQ",
     "access_token": "tok_example_token_value_here",
     "scopes": ["jobs.write", "kb.read", "kb.write", "apps.read"],
     "knowledge_bases": [{"knowledge_base_id": 215, "is_default": true}]
   }
   ```

---

### Step 3.2: Configure the Service Token in AgriConnect Swagger

1. Open **[http://localhost:8000/api/docs](http://localhost:8000/api/docs)** in your browser.
2. **Authorize as Admin**:
   - Expand `POST /api/auth/login`, click **"Try it out"**, enter your admin credentials, and click **"Execute"**.
   - Copy the `access_token` from the response.
   - Click the green **"Authorize"** button at the top of the Swagger page, paste the token into **HTTPBearer**, and click **"Authorize"**.
3. **Inspect Existing Tokens**:
   - Under `service-tokens`, expand **`GET /api/admin/service-tokens/`** ➔ Click **"Try it out"** ➔ **"Execute"**.
4. **Create or Update the `akvo-rag` Entry**:
   - **If creating new**: Expand **`POST /api/admin/service-tokens/`** ➔ **"Try it out"**.
   - **If updating**: Expand **`PUT /api/admin/service-tokens/{token_id}`** ➔ **"Try it out"** with the token ID.
   - Enter the exact URLs using the `apps` routes:

     ```json
     {
       "service_name": "akvo-rag",
       "access_token": "tok_PASTE_YOUR_COPIED_TOKEN_HERE",
       "chat_url": "http://host.docker.internal:8010/api/v1/apps/jobs",
       "upload_url": "http://host.docker.internal:8010/api/v1/apps/jobs",
       "kb_url": "http://host.docker.internal:8010/api/v1/apps/knowledge-bases",
       "document_url": "http://host.docker.internal:8010/api/v1/apps/documents",
       "default_prompt": "You are AgriConnect AI agronomy advisor supporting smallholder farmers.",
       "active": 1
     }
     ```

   - Click **"Execute"** (returns `200 OK`).

---

## 4. Verification & Testing

### 4.1 End-to-End Testing via the Web UI

You can verify the integration directly through the browser UIs of both systems:

#### Step 4.1.1: AgriConnect UI — Knowledge Base & Document Management

1. Open the **AgriConnect Web UI** at **[http://localhost:3000](http://localhost:3000)** and log in.
2. Navigate to the **Knowledge Base** section.
3. **Verify KB List**: Confirm that the Knowledge Bases associated with your AgriConnect App in Akvo RAG are displayed in the list.
4. **Create a Knowledge Base**:
   - Click **"Create Knowledge Base"** / **"New KB"**.
   - Enter a name (e.g., `Kenya Avocado Extension`) and description.
   - Change the KB status to active.
   - Save the KB. AgriConnect calls `POST /api/v1/apps/knowledge-bases` on Akvo RAG.
5. **Upload Agronomy Documents**:
   - Open the newly created Knowledge Base.
   - Click **"Upload Documents"** and select an agricultural PDF/DOCX (e.g., `avocado_fcm_sop.pdf`).
   - Click **"Upload"**. AgriConnect dispatches an upload job to `POST /api/v1/apps/jobs` on Akvo RAG.
   - Confirm the document status chip transitions from `Processing` to `Completed` (via background ingestion and webhook callback).

#### Step 4.1.2: AgriConnect UI — Chat & Advisory Simulation

1. In **AgriConnect UI**, navigate to the **Chat Playground** interface.
2. Start a new conversation linked to the agronomy Knowledge Base.
3. Ask a domain-specific question based on your uploaded document, for example:
   > *"How do I control false codling moth in my avocado orchard?"*
4. **Verify Response & Citations**:
   - AgriConnect calls Akvo RAG's `POST /api/v1/apps/jobs` (`job: "chat"`).
   - Akvo RAG processes RAG retrieval, runs citation filtering, and sends the answer back via the chat callback.
   - Confirm the AI response appears in the chat along with document citations (e.g., `avocado_fcm_sop.pdf`).

#### Step 4.1.3: Akvo RAG Dashboard Verification

1. Open the **Akvo RAG Web UI** at **[http://localhost:3010](http://localhost:3010)** and log in.
2. Navigate to **Knowledge Bases**:
   - Confirm the KB created from AgriConnect is listed.
   - Click into the KB to see the uploaded document chunks and metadata.

---

### 4.2 Verify Knowledge Base Sync from AgriConnect Swagger

1. In AgriConnect Swagger ([http://localhost:8000/docs](http://localhost:8000/docs)), navigate to **`knowledge-bases`**.
2. Expand **`GET /api/knowledge-bases/`** ➔ Click **"Try it out"** ➔ **"Execute"**.
3. AgriConnect will request `GET http://host.docker.internal:8010/api/v1/apps/knowledge-bases` with `Authorization: Bearer tok_...`.
4. It will return the list of knowledge bases linked to the AgriConnect app.

### 4.3 Automated Verification Suites

Run the automated test suites:

```bash
# 1. Host App registration, token auth & upload lifecycle
docker exec akvo-rag-backend-1 python -m pytest tests/integration/test_app_endpoints.py -v

# 2. AgriConnect specific end-to-end integration suite
docker exec akvo-rag-backend-1 python -m pytest tests/integration/test_agriconnect_integration.py -v

# 3. Host API backwards compatibility suite (both /api and /api/v1)
docker exec akvo-rag-backend-1 python -m pytest tests/api/test_host_api_backwards_compatibility.py -v
```

---

## 5. Troubleshooting & Gotchas

1. **Routing 404s:**
   Ensure requests go to port `8010` on the host, or `http://host.docker.internal:8010` from within Docker containers.
2. **Document Upload Rejections:**
   Ensure uploaded PDF headers start with `%PDF-`. Files with invalid magic bytes will be rejected with `400 Bad Request`.
3. **Ingestion Latency / Stuck Queue:**
   If `task_status` remains `processing`, inspect the ingestion worker logs:

   ```bash
   docker logs akvo-rag-ingestion-worker-1 --tail 50
   ```

4. **Linux Host Gateway (`host.docker.internal`):**
   If running Docker on Linux, ensure `extra_hosts: ["host.docker.internal:host-gateway"]` is present in `docker-compose.override.yml`. (On macOS Docker Desktop, this works automatically).
