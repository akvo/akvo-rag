# Legacy Data Migration Guide

This guide provides end-to-end instructions for migrating historical data from legacy deployments (standalone **Vector KB PostgreSQL** and **Backend MySQL**) into the unified **PostgreSQL 17** database (`akvo_rag`), supporting local Docker environments, live **Kubernetes (K8s)** production clusters, and **local-to-remote** CLI migration.

---

## 1. Architecture: Legacy vs. Unified PostgreSQL 17

| Component | Legacy Deployment | Target Location (Unified PostgreSQL 17) |
|---|---|---|
| **Vector Knowledge Base** | Standalone PostgreSQL (`vector-knowledge-base-mcp-server`)<br>• `knowledge_bases`<br>• `documents`<br>• `document_chunks` | **`akvo_rag` Database** (Table namespace: `vkb_*`)<br>• `vkb_knowledge_bases`<br>• `vkb_documents`<br>• `vkb_document_chunks`<br>• `vkb_processing_tasks` |
| **Backend Host Application** | Standalone MySQL (`akvo-rag-backend`)<br>• `users`<br>• `apps`<br>• `chats` / `messages`<br>• `prompt_definitions` | **`akvo_rag` Database** (Standard namespace)<br>• `users`<br>• `apps`<br>• `chats` / `messages`<br>• `prompt_definitions` / `prompt_versions` |

---

## 2. Network Prerequisites (Host Resolution)

### Local Docker Compose
- **macOS / Windows**: Use `host.docker.internal` instead of `localhost` or `127.0.0.1`.
- **Linux**: Use your host's gateway IP (e.g. `172.17.0.1`) or `--network host`.

### Kubernetes Cluster & Remote Execution
- **Kubernetes Port-Forwarding**: Map remote DB ports to `localhost` (`kubectl port-forward`).
- **Cluster Internal Services**: Use K8s Service DNS (e.g. `legacy-postgres-service.default.svc.cluster.local:5432`).
- **External Managed DBs (Cloud SQL / RDS)**: Use the private VPC Endpoint or DB Endpoint address.

---

## 3. Part A: Local Docker Migration Commands

### Step 3.1: Vector KB Data (from Legacy PostgreSQL)

```bash
# Preview via --dry-run
docker exec -it akvo-rag-vector-kb-mcp-1 python cli/migrate_legacy_data.py \
  --source-url "postgresql://postgres:password@host.docker.internal:5433/legacy_vkb" \
  --dry-run

# Live Migration
docker exec -it akvo-rag-vector-kb-mcp-1 python cli/migrate_legacy_data.py \
  --source-url "postgresql://postgres:password@host.docker.internal:5433/legacy_vkb" \
  --batch-size 500
```

### Step 3.2: Backend User & Chat Data (from Legacy MySQL)

```bash
# Preview via --dry-run
docker exec -it akvo-rag-backend-1 python cli/migrate_legacy_backend.py \
  --source-url "mysql+mysqlconnector://root:password@host.docker.internal:3306/ragwebui" \
  --dry-run

# Live Migration
docker exec -it akvo-rag-backend-1 python cli/migrate_legacy_backend.py \
  --source-url "mysql+mysqlconnector://root:password@host.docker.internal:3306/ragwebui"
```

---

## 4. Part B: Live Kubernetes (K8s) Pod Migration Protocol ☸️

In a live Kubernetes cluster, run the migration CLI directly inside active running Pods using `kubectl exec`.

### Step 4.1: Identify Target Pod Names & Namespace

```bash
NAMESPACE="akvo-rag"

# Get running Vector KB MCP pod
VKB_POD=$(kubectl get pods -n $NAMESPACE -l app=vector-kb-mcp -o jsonpath='{.items[0].metadata.name}')

# Get running Backend pod
BACKEND_POD=$(kubectl get pods -n $NAMESPACE -l app=akvo-rag-backend -o jsonpath='{.items[0].metadata.name}')

echo "Vector KB Pod: $VKB_POD"
echo "Backend Pod:   $BACKEND_POD"
```

### Step 4.2: Migrate Vector KB Data via `kubectl exec`

```bash
# Dry-run preview inside K8s Pod
kubectl exec -it -n $NAMESPACE $VKB_POD -- python cli/migrate_legacy_data.py \
  --source-url "postgresql://<LEGACY_PG_USER>:<LEGACY_PG_PASSWORD>@<LEGACY_PG_HOST>:5432/<LEGACY_PG_DB>" \
  --dry-run

# Live batch migration inside K8s Pod
kubectl exec -it -n $NAMESPACE $VKB_POD -- python cli/migrate_legacy_data.py \
  --source-url "postgresql://<LEGACY_PG_USER>:<LEGACY_PG_PASSWORD>@<LEGACY_PG_HOST>:5432/<LEGACY_PG_DB>" \
  --batch-size 500
```

### Step 4.3: Migrate Backend Users & Chats via `kubectl exec`

```bash
# Dry-run preview inside K8s Pod
kubectl exec -it -n $NAMESPACE $BACKEND_POD -- python cli/migrate_legacy_backend.py \
  --source-url "mysql+mysqlconnector://<LEGACY_MYSQL_USER>:<LEGACY_MYSQL_PASSWORD>@<LEGACY_MYSQL_HOST>:3306/<LEGACY_MYSQL_DB>" \
  --dry-run

# Live migration inside K8s Pod
kubectl exec -it -n $NAMESPACE $BACKEND_POD -- python cli/migrate_legacy_backend.py \
  --source-url "mysql+mysqlconnector://<LEGACY_MYSQL_USER>:<LEGACY_MYSQL_PASSWORD>@<LEGACY_MYSQL_HOST>:3306/<LEGACY_MYSQL_DB>"
```

---

## 5. Part C: Running Migration Locally targeting Remote Live DB 💻

You can run the migration CLI scripts directly from your local terminal targeting a live production or remote database using local Python or `kubectl port-forward`.

### Method 1: Local Terminal + Kubernetes Port-Forwarding (Recommended)

1. **Port-Forward Live Target PostgreSQL to Local Port 5432**:
   ```bash
   kubectl port-forward -n akvo-rag svc/postgres 5432:5432
   ```

2. **Port-Forward Legacy Source Database to Local Port 5433** (if source is inside K8s):
   ```bash
   kubectl port-forward -n akvo-rag svc/legacy-postgres 5433:5432
   ```

3. **Run Local Script Targeting `localhost`**:

   ```bash
   # Vector KB Migration
   python vector-kb-mcp/cli/migrate_legacy_data.py \
     --source-url "postgresql://<LEGACY_USER>:<LEGACY_PASS>@localhost:5433/legacy_vkb" \
     --target-pg-url "postgresql+asyncpg://postgres:<LIVE_PASS>@localhost:5432/akvo_rag" \
     --dry-run

   # Backend Migration
   python backend/cli/migrate_legacy_backend.py \
     --source-url "mysql+mysqlconnector://root:<LEGACY_PASS>@localhost:3306/ragwebui" \
     --target-url "postgresql+psycopg2://postgres:<LIVE_PASS>@localhost:5432/akvo_rag" \
     --dry-run
   ```

### Method 2: Direct Remote Connection (Cloud SQL / AWS RDS)

```bash
# Vector KB Migration
python vector-kb-mcp/cli/migrate_legacy_data.py \
  --source-url "postgresql://<LEGACY_USER>:<LEGACY_PASS>@<LEGACY_HOST>:5432/<LEGACY_DB>" \
  --target-pg-url "postgresql+asyncpg://<LIVE_USER>:<LIVE_PASS>@<LIVE_HOST>:5432/akvo_rag" \
  --batch-size 500

# Backend Migration
python backend/cli/migrate_legacy_backend.py \
  --source-url "mysql+mysqlconnector://<LEGACY_USER>:<LEGACY_PASS>@<LEGACY_HOST>:3306/<LEGACY_DB>" \
  --target-url "postgresql+psycopg2://<LIVE_USER>:<LIVE_PASS>@<LIVE_HOST>:5432/akvo_rag"
```

---

## 6. Storage & Verification

### Step 6.1: Verify Row Counts in PostgreSQL 17

```bash
# Docker Compose
docker exec akvo-rag-postgres-1 psql -U postgres -d akvo_rag -c "
SELECT 'vkb_knowledge_bases' AS table_name, count(*) FROM vkb_knowledge_bases
UNION ALL SELECT 'vkb_documents', count(*) FROM vkb_documents
UNION ALL SELECT 'vkb_document_chunks', count(*) FROM vkb_document_chunks
UNION ALL SELECT 'users', count(*) FROM users
UNION ALL SELECT 'chats', count(*) FROM chats;
"

# Kubernetes Cluster
POSTGRES_POD=$(kubectl get pods -n $NAMESPACE -l app=postgres -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it -n $NAMESPACE $POSTGRES_POD -- psql -U postgres -d akvo_rag -c "
SELECT 'vkb_knowledge_bases' AS table_name, count(*) FROM vkb_knowledge_bases
UNION ALL SELECT 'vkb_documents', count(*) FROM vkb_documents
UNION ALL SELECT 'vkb_document_chunks', count(*) FROM vkb_document_chunks
UNION ALL SELECT 'users', count(*) FROM users
UNION ALL SELECT 'chats', count(*) FROM chats;
"
```

---

## 7. Troubleshooting Common Migration Issues

### Error 1: `psycopg2.OperationalError: could not translate host name`
- **Cause**: Using placeholder text `<POSTGRES_HOST>` or `localhost` inside a Docker/K8s container.
- **Fix**: Use `host.docker.internal` (Docker local) or K8s Service DNS (e.g. `legacy-db.namespace.svc.cluster.local`) inside Kubernetes.

### Error 2: `ValueError: invalid literal for int() with base 10: '<PORT>'`
- **Cause**: Port placeholder was not replaced with a numeric value.
- **Fix**: Specify explicit numeric port (e.g. `5432` for PostgreSQL or `3306` for MySQL).

### Error 3: Foreign Key Violations
- **Cause**: Inserting child records before parent records.
- **Fix**: `migrate_legacy_data.py` and `migrate_legacy_backend.py` migrate tables automatically in topological dependency order (`knowledge_bases` ➔ `documents` ➔ `document_chunks`).
