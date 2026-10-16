# 🚀 Master End-to-End Migration Guide: Akvo RAG Monorepo Cutover

> **Official Document:** `docs/end-to-end-monorepo-migration-guide.md`  
> **Status:** `APPROVED (BMAD Architect & Operations Council)`  
> **Target Environments:** `akvo-rag-namespace`, `agriconnect-rag-namespace`  
> **Target Architecture:** Unified Monorepo (`akvo-rag`) + PostgreSQL 18 + Redis 7.2 RPC Dispatcher  
> **GitOps Manifests:** `akvo-config` repository (Branch: `feature/384-akvo-rag-monorepo`)  
> **Downstream Impact:** `akvo-rag`, `agriconnect-rag`, `agriconnect` application, `akvo-rag-js`  

---

## 📊 1. Executive Summary: Legacy Architecture vs. Modern Monorepo

High-level architectural transformation overview for leadership and management:

```mermaid
flowchart LR
    subgraph BEFORE["1. BEFORE (Fragmented Legacy)"]
        direction TB
        L1["MySQL 8.0 (Backend Data)"]
        L2["Cloud SQL PostgreSQL (Vector KB)"]
        L3["RabbitMQ + Celery Workers"]
        L4["Multi-Repository Setup"]
    end

    subgraph TRANSITION["2. CUTOVER PROCESS"]
        direction TB
        T1["Keyring / Vault Secret Update"]
        T2["GitOps PR Merge (Automated CI/CD)"]
        T3["Direct In-Cluster Data ETL"]
    end

    subgraph AFTER["3. AFTER (Unified Monorepo)"]
        direction TB
        M1["PostgreSQL 18 Alpine (Single Consolidated DB)"]
        M2["Redis 7.2 RPC (Microsecond Latency)"]
        M3["FastAPI Monorepo (Backend + Query + Ingest)"]
    end

    subgraph IMPACT["4. DOWNSTREAM BUSINESS PLATFORMS"]
        direction TB
        P1["Akvo RAG (Admin & Web Portal)"]
        P2["AgriConnect RAG (Tenant AI Engine)"]
        P3["AgriConnect Mobile / Web Client"]
        P4["Climate Think and Do Tank (Embedded Widget)"]
    end

    BEFORE ==> TRANSITION
    TRANSITION ==> AFTER
    AFTER ==> IMPACT
```

### Key Business & Technical Value
1. **Cloud Cost & Resource Efficiency:** Eliminates legacy RabbitMQ, Celery worker nodes, and external Cloud SQL PostgreSQL instances. Replaced with lightweight, high-throughput in-memory Redis 7.2 RPC and unified PostgreSQL 18.
2. **Speed & Scalability:** Inter-process message dispatch latency drops from milliseconds (AMQP/RabbitMQ) to microseconds (Redis RPC).
3. **Operational Simplicity:** Backend services, document ingestion workers, and vector query microservices are consolidated into a single codebase (*monorepo*), streamlining deployments, testing, and dependency management.

---

## 🎯 2. Primary Objective of Database Migration

The primary objective of extracting and migrating the legacy database is **zero data loss for critical business assets**:
- 👤 **Registered Users:** Preserves existing accounts, admin permissions, and credentials (`users` table).
- 🔑 **Registered Applications:** Preserves client API tokens, authorized domains, and integration configurations (`apps` table).
- 💬 **Conversation History:** Preserves historical chat threads and user interaction logs (`chats`, `messages` tables).
- 📝 **Prompts & System Settings:** Preserves custom prompt templates, versions, and system configurations (`system_settings`, `prompt_definitions`, `prompt_versions`).

> [!NOTE]
> **Knowledge Base Document Strategy:**  
> Knowledge Base raw documents (PDFs, DOCX) will be re-uploaded directly via the modern Web UI once the new platform is live. This guarantees clean parsing, modernized tokenization, and fresh vector indexing into ChromaDB without carrying over legacy chunk fragmentation.

---

## 📦 3. Pre-Flight Asset Inventory

| Component | Repository | Source Branch / Path | Role in Migration |
|---|---|---|---|
| **Akvo RAG Monorepo** | `akvo-rag` | `epic/rag-monorepo-mcp` ➔ `main` | Target monorepo application with PostgreSQL 18 & Redis RPC support |
| **K8s Manifests** | `akvo-config` | `feature/384-akvo-rag-monorepo` ➔ `master` | GitOps declarative manifests for PostgreSQL 18, Redis, and services |
| **Secrets & Keyring** | `akvo-config` | Vault / Keyring (`k8s-manifests/test/.../3-secrets.yml`) | Secure credentials for PostgreSQL 18, Redis, and API endpoints |
| **Dump Utility** | `akvo-rag` | `agent_docs/dump-k8s-legacy-db.sh` | Zero-lock data extraction script streaming directly from K8s pods |
| **ETL Engines** | `akvo-rag` | `backend/cli/migrate_legacy_backend.py`<br>`vector-kb-mcp/cli/migrate_legacy_data.py` | Schema transformation, data sanitization, and PostgreSQL 18 loader |

---

## 🔄 4. Step-by-Step Migration Execution Plan

```text
[Step 1: Keyring & Vault Update] ──► [Step 2: Merge PRs (Automated GitOps)]
                                                    │
[Step 5: Platform Validation] ◄── [Step 4: Manual Document Upload] ◄── [Step 3: Direct In-Cluster ETL]
```

---

### Step 1: Update Keyring & Vault Secrets (Pre-Requisite) 🔐

Before merging the manifest PR, update the secret credentials in **HashiCorp Vault / Cloud KMS Keyring** to ensure the new services boot with correct credentials:

1. **Update Secret Keys in Vault / Keyring:**
   - Path: `test/akvo-rag` and `test/agriconnect-rag`
   - Key attributes to add/verify:
     - `DATABASE_URL`: `postgresql+asyncpg://postgres:<PASSWORD>@postgres:5432/akvo_rag`
     - `REDIS_URL`: `redis://redis:6379/0`
     - `POSTGRES_PASSWORD`: Generated secure database password
2. **Verify VaultStaticSecret Sync:**
   Ensure `VaultStaticSecret` resources defined in `3-secrets.yml` will automatically sync new secrets to the target pods upon rollout.

---

### Step 2: Merge Pull Requests (Automated GitOps Deployment) ⚡

The infrastructure rollout and database schema initialization are **fully automated by CI/CD upon merging PRs**:

1. **Merge `akvo-config` PR (`feature/384-akvo-rag-monorepo` ➔ `master`):**
   - The GitOps automation pipeline (GitHub Actions / Semaphore) **automatically**:
     - Decommissions legacy StatefulSets (RabbitMQ, MySQL, Celery).
     - Deploys PostgreSQL 18 StatefulSet (`4-statefulset-postgres.yml`).
     - Deploys Redis 7.2 (`3-deployment-redis.yml`).
     - Reconfigures internal cluster services (`20-service.yml`).
2. **Merge `akvo-rag` PR (`epic/rag-monorepo-mcp` ➔ `main`):**
   - Triggers the automated container image build and rolls out `backend`, `vector-kb-query`, and `vector-kb-ingestion`.
   - **Automatically executed during container startup ([`entrypoint.sh`](file:///Users/galihpratama/Sites/akvo-rag/backend/entrypoint.sh#L47-L58)):**
     - `alembic upgrade head` (initializes backend tables: `users`, `apps`, `chats`, `messages`).
     - `alembic upgrade head` (initializes isolated `vkb_*` tables).
     - `python -m app.seeder.seed_prompts` (seeds default prompt templates).

---

### Step 3: Seed Legacy Data into Monorepo Database (ETL Migration) 💾

To populate the new PostgreSQL 18 database with legacy users, apps, and chat history, two approaches are supported:

#### Option A: Direct In-Cluster Migration (Recommended — Zero Local Bandwidth)
Because the legacy MySQL pod (`akvo-rag-mysql-0` / `agriconnect-rag-mysql-0`) and the new PostgreSQL 18 pod reside within the **same Kubernetes cluster**, data can be streamed directly between pods through the internal cluster network:

```bash
# 1. Execute Backend ETL (Migrate Users, Apps, Chats, Messages):
kubectl exec -it -n akvo-rag-namespace deploy/backend-deployment -c backend -- \
  python cli/migrate_legacy_backend.py \
    --source-url "mysql+mysqlconnector://root:${LEGACY_MYSQL_PASSWORD}@akvo-rag-mysql:3306/ragwebui" \
    --target-url "postgresql+psycopg2://postgres:${POSTGRES_PASSWORD}@postgres:5432/akvo_rag"

# 2. Execute Vector KB Metadata ETL (if migrating legacy KB tables):
kubectl exec -it -n akvo-rag-namespace deploy/vector-kb-query-deployment -c vector-kb-query -- \
  python cli/migrate_legacy_data.py \
    --source-url "${LEGACY_CLOUD_SQL_POSTGRES_URL}" \
    --target-url "postgresql+asyncpg://postgres:${POSTGRES_PASSWORD}@postgres:5432/akvo_rag" \
    --batch-size 500
```
*(Repeat for `agriconnect-rag-namespace`)*.

---

#### Option B: Seed from Local Dump (Tested Staging & Remote K8s Flow)
If using the dump file already extracted and verified on your local workstation (`agent_docs/dumps/legacy_akvo-rag_ragwebui_latest.sql`):

##### B.1: Local Development / Staging Verification
1. **Start a Temporary Legacy MySQL Container (Port `3307` to avoid host collisions):**
   ```bash
   docker rm -f temp-legacy-mysql && docker run --name temp-legacy-mysql \
     -e MYSQL_ROOT_PASSWORD=root \
     -p 3307:3306 \
     -d mysql:8.0
   ```
2. **Create Target Database & Import Local Dump:**
   ```bash
   # Create database
   docker exec -i temp-legacy-mysql mysql -uroot -proot -e "CREATE DATABASE IF NOT EXISTS ragwebui;"

   # Import dump
   docker exec -i temp-legacy-mysql mysql -uroot -proot ragwebui < agent_docs/dumps/legacy_akvo-rag_ragwebui_latest.sql
   ```
3. **Ensure Modern Monorepo Environment is Running:**
   ```bash
   ./dc.sh up -d
   ```
4. **Execute Backend ETL from the Backend Container:**
   ```bash
   # (Optional) Dry-run check:
   docker exec akvo-rag-backend-1 python -m cli.migrate_legacy_backend \
     --source-url "mysql+mysqlconnector://root:root@host.docker.internal:3307/ragwebui" \
     --dry-run

   # Execute live migration:
   docker exec akvo-rag-backend-1 python -m cli.migrate_legacy_backend \
     --source-url "mysql+mysqlconnector://root:root@host.docker.internal:3307/ragwebui"
   ```

##### B.2: Seeding Remote Kubernetes Cluster via Secure Tunnel
To seed the remote Kubernetes cluster using this local MySQL container:
1. **Establish a secure port-forward tunnel from the cluster to local workstation:**
   ```bash
   kubectl port-forward -n akvo-rag-namespace svc/postgres 5433:5432
   ```
2. **Execute the Python ETL script locally targeting the tunnel:**
   ```bash
   python backend/cli/migrate_legacy_backend.py \
     --source-url "mysql+mysqlconnector://root:root@localhost:3307/ragwebui" \
     --target-url "postgresql+psycopg2://postgres:${POSTGRES_PASSWORD}@localhost:5433/akvo_rag"
   ```

---

#### Data Integrity Verification (Row Parity Check)
Run this parity query directly inside PostgreSQL 18 to verify that every user account, app token, and chat message was imported with 100% fidelity:

```bash
kubectl exec -it -n akvo-rag-namespace statefulset/postgres -- psql -U postgres -d akvo_rag -c "
SELECT 'users' AS table_name, count(*) AS total_rows FROM users
UNION ALL SELECT 'apps', count(*) FROM apps
UNION ALL SELECT 'chats', count(*) FROM chats
UNION ALL SELECT 'messages', count(*) FROM messages
UNION ALL SELECT 'prompt_definitions', count(*) FROM prompt_definitions
UNION ALL SELECT 'vkb_knowledge_bases', count(*) FROM vkb_knowledge_bases;
"
```

---

### Step 3.1: Callback URL Domain Synchronization (AgriConnect & Registered Apps) 🔄

> [!IMPORTANT]
> **Understanding Callbacks vs. RAG Inbound Endpoints (`/api/v1` vs `/api/callback`):**  
> In the architecture, there is a clear distinction between **inbound calls to Akvo RAG** and **outbound callbacks to client apps (AgriConnect)**:
> 1. **Inbound Calls to Akvo RAG** (`RAG_BASE_URL`): **YES, ALL modern RAG API endpoints use the `/api/v1` prefix.**
>    - Jobs: `POST https://agriconnect-rag.akvotest.org/api/v1/apps/jobs`
>    - Knowledge Bases: `GET/POST https://agriconnect-rag.akvotest.org/api/v1/apps/knowledge-bases`
>    - App Validation: `GET https://agriconnect-rag.akvotest.org/api/v1/apps/me`
> 2. **Outbound Callbacks to Client Apps** (`chat_callback_url` & `upload_callback_url` in the `apps` table):
>    - These are **webhooks hosted on AgriConnect's backend**, NOT on Akvo RAG.
>    - In AgriConnect's backend (`routers/callbacks.py`), routes are mounted at `/api/callback/ai` and `/api/callback/kb`.
>    - If an Ingress/API Gateway rewrite rule maps versioned paths (e.g. `/api/v1/callback/ai`), verify the live route on AgriConnect before updating.

Following database migration, synchronize the callback URLs in the `apps` table to ensure Akvo RAG can dispatch webhook events to AgriConnect:

1. **Inspect Current Registered Callbacks in PostgreSQL 18:**
   ```sql
   SELECT id, app_name, domain, chat_callback_url, upload_callback_url 
   FROM apps;
   ```

2. **Update Callback URLs for AgriConnect to the Versioned Application Endpoints (`/api/v1`):**
   ```sql
   -- For Staging / Test Environment (AgriConnect 2):
   UPDATE apps 
   SET 
     domain = 'agriconnect2.akvotest.org',
     chat_callback_url = 'https://agriconnect2.akvotest.org/api/v1/callback/ai',
     upload_callback_url = 'https://agriconnect2.akvotest.org/api/v1/callback/kb'
   WHERE app_name LIKE '%agriconnect%' AND (domain LIKE '%akvotest%' OR domain LIKE '%ngrok%');

   -- For Production Environment:
   UPDATE apps 
   SET 
     domain = 'agriconnect.akvo.org',
     chat_callback_url = 'https://agriconnect.akvo.org/api/v1/callback/ai',
     upload_callback_url = 'https://agriconnect.akvo.org/api/v1/callback/kb'
   WHERE app_name = 'agriconnect-production' OR app_name = 'agriconnect';
   ```

   *(Note: If running against a legacy AgriConnect build where routes are unversioned, fallback paths are `/api/callback/ai` and `/api/callback/kb`)*.

3. **Verify Inbound RAG Configuration in AgriConnect Application (`service_tokens` & `.env`):**
   In the **AgriConnect project**, ensure its outbound API client and `service_tokens` table point to the newly deployed RAG service with the `/api/v1` prefix:
   - Staging/Test:
     - `RAG_BASE_URL=https://agriconnect-rag.akvotest.org/api/v1`
     - `chat_url=https://agriconnect-rag.akvotest.org/api/v1/apps/jobs`
     - `upload_url=https://agriconnect-rag.akvotest.org/api/v1/apps/jobs`
     - `kb_url=https://agriconnect-rag.akvotest.org/api/v1/apps/knowledge-bases`
   - Production:
     - `RAG_BASE_URL=https://agriconnect-rag.akvo.org/api/v1`
     - `chat_url=https://agriconnect-rag.akvo.org/api/v1/apps/jobs`
     - `upload_url=https://agriconnect-rag.akvo.org/api/v1/apps/jobs`
     - `kb_url=https://agriconnect-rag.akvo.org/api/v1/apps/knowledge-bases`

---

### Step 4: Knowledge Base Document Ingestion (Via Platform UI) 📁

Once services and database records are verified:
1. Log in to the modern Akvo RAG Web UI (`https://akvo-rag.akvotest.org`).
2. Navigate to **Knowledge Bases**.
3. Upload the target documents (e.g. from `agriconnect/agent_docs/documents/`).
4. The monorepo `vector-kb-ingestion` worker will automatically process chunks, compute embeddings, and populate ChromaDB and MinIO with modern vector indexes.

---

## 🔍 5. Downstream Platform Validation Matrix

Validate all 4 affected platforms following cutover:

| Platform | Verification Action | Expected Outcome | Critical Checkpoint |
|---|---|---|---|
| **1. `akvo-rag`** | • Access Web UI (`https://akvo-rag.akvotest.org`)<br>• Login via admin account<br>• Verify past chats and user accounts | • HTTP 200 OK<br>• Historical users, apps, and chat logs are fully visible | Backend `/health` reports `database: ok`, `redis: ok` |
| **2. `agriconnect-rag`** | • Access tenant portal (`https://agriconnect-rag.akvotest.org`)<br>• Upload a test document (`.pdf`) | • Status updates: `PENDING` ➔ `PROCESSING` ➔ `INDEXED`<br>• Ingestion worker generates chunks in `vkb_document_chunks` | `vector-kb-ingestion` worker logs show Redis RPC queue events processing cleanly |
| **3. `agriconnect` App** | • Open AgriConnect client application (`https://agriconnect.akvo.org` / test)<br>• Submit an inquiry in the chat interface | • AI responses generate citations matching KB documents<br>• Historical chat threads load seamlessly without auth errors | Verify `agriconnect-production` in `apps` table retains active token and domain match |
| **4. `akvo-rag-js`** | • Open `https://tdt.akvotest.org`<br>• Test "Kenya Drylands Assistant" widget (KB ID: `36`)<br>• Open `demo-page/index.html` | • WebSocket connects cleanly (`wss://akvo-rag.akvotest.org/ws/chat`)<br>• Streaming Markdown responses render without delay | Browser DevTools console shows zero WebSocket handshake failures or CORS blocks |

---

## 🛡️ 6. Rollback Contingency Plan (Zero Data Loss)

In the event of an unforeseen blocker during cutover:

1. **Database Safety:** Legacy MySQL (`akvo-rag-mysql-0`) and Cloud SQL databases remain untouched in read-only snapshot mode. No legacy data is deleted.
2. **Kubernetes Rollback:**
   ```bash
   # Roll back deployments to previous revision if necessary
   kubectl rollout undo deployment/backend-deployment -n akvo-rag-namespace
   kubectl rollout undo deployment/backend-deployment -n agriconnect-rag-namespace
   ```
3. **Data Preservation:** Any new chat sessions or audit logs written to PostgreSQL 18 during testing remain safely persisted on the cluster's Persistent Volume Claims (PVC).
