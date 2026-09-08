# Admin Guide: Akvo RAG

This guide is for administrators managing knowledge bases, users, prompts, and application registrations in Akvo RAG.

> **Related docs**: [Developer Guide](dev-guide.md) | [Troubleshooting](troubleshooting.md) | [Architecture Map](architecture_map.md)

---

## 1. Knowledge Base Management

The Knowledge Base (KB) is the core of the RAG system — the document collection the AI uses to answer questions. Each KB stores semantic vector embeddings in ChromaDB and metadata in PostgreSQL.

### 1.1 Creating a Knowledge Base

1. Go to the **Knowledge Base** page in the sidebar.
2. Click **"New Knowledge Base"** (top right).
3. Fill in:
   - **Name**: Clear, descriptive title (used by the ASQ selector to choose the right KB).
   - **Description**: Brief explanation of the content. The LLM uses this to determine relevance.
   - **Privacy**: **Public** (team-wide) or **Private** (restricted).
4. Click **"Create"** — this initializes vector storage in ChromaDB and the DB entry in PostgreSQL.

### 1.2 Document Upload & Ingestion Pipeline

Uploading a document triggers a 3-stage async pipeline:

```
Upload → [MinIO S3 storage] → register_document (Redis RPC) → ingest_document (Redis queue) → ChromaDB index
```

**Supported formats**: PDF, DOCX, TXT, Markdown (MD)

**To upload documents**:
1. Click on a KB from the list.
2. Click **"Add Document"** (top right).
3. Drag and drop files or click to browse.
4. Click **"Upload Files"** — the system processes them asynchronously.

### 1.3 Document Indexing Status

Monitor document status in the KB detail view:

| Status | Colour | Meaning |
|--------|--------|---------|
| `INDEXED` | Green | Successfully indexed — ready for queries |
| `PROCESSING` | Yellow | Currently parsing and vectorizing |
| `FAILED` | Red | Ingestion failed — check format/size, then retry |
| `PENDING` | Grey | Queued, waiting for processing |

**Admin actions per document**:
- **Delete**: Removes document and all its ChromaDB vector chunks. Use the trash icon in the Action column.
- **Preview**: View parsed chunks before full indexing.
- **Test Retrieval**: Magnifying glass icon on the KB list page — tests search accuracy.
- **Delete KB**: Deletes the entire KB, all documents, and all ChromaDB collections.

### 1.4 Checking Stuck Documents via CLI

If documents are stuck in `PROCESSING`:

```bash
# Check Redis queue depth
docker exec akvo-rag-redis-1 redis-cli llen mcp:vector:requests

# View vector-kb-mcp logs for processing errors
docker compose logs vector-kb-mcp --tail=50

# Inspect MinIO for uploaded files
docker exec akvo-rag-minio-1 mc ls local/documents/ --recursive
```

---

## 2. Prompt Management

All RAG prompts (system prompt, synthesis instructions, routing prompts) are managed in the database. **No redeployment is needed** to update a prompt.

### 2.1 Via Admin UI

1. Navigate to **Settings → Prompts** in the sidebar.
2. Click a prompt definition to view its version history.
3. Click **"Edit"** to create a new version.
4. Click **"Activate"** on the new version to make it live immediately.

### 2.2 Via CLI

```bash
# List current prompt definitions
docker exec akvo-rag-backend-1 python -c "
from app.services.prompt_service import PromptService
from app.db.session import SessionLocal
db = SessionLocal()
svc = PromptService(db)
print(svc.list_definitions())
db.close()
"

# Re-seed all prompts from seed files (adds new, does not overwrite active versions)
docker compose exec backend python -m app.seeder.seed_prompts
```

---

## 3. User Management

### 3.1 Via Admin UI

Navigate to **Settings → Users**:

- **Enable/Disable** accounts using the toggle.
- **Role Assignment**: `user` (standard) or `superuser` (administrator with full access).
- **Approval Flow**: If self-registration is enabled, approve pending sign-ups here.

### 3.2 Creating Admin User via CLI

```bash
docker compose exec backend python -m app.seeder.seed_admin_user
```

### 3.3 Password Reset

Users can request password resets via the login page (requires SMTP configuration in `.env`).

---

## 4. Application (Tenant) Registration

Host applications (e.g. AgriConnect, CoM) integrate with Akvo RAG via a tenant API secured by Argon2-hashed application tokens (`tok_...`).

### 4.1 Registering an Application

```bash
curl -X POST http://localhost:8000/api/v1/apps/register \
  -H "Authorization: Bearer <admin-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "AgriConnect",
    "description": "Akvo AgriConnect host application"
  }'
```

**Response**: Returns `token` (the plaintext `tok_...` value shown once) and `app_id`. Store the token securely — it cannot be retrieved again.

### 4.2 Tenant API Endpoints

All tenant endpoints use `Authorization: Bearer tok_...` (not a user JWT):

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/apps/knowledge-bases` | List accessible KBs for this app |
| `POST` | `/api/v1/apps/knowledge-bases/{id}/documents/upload` | Upload document to a KB |
| `POST` | `/api/v1/apps/jobs` | Submit a RAG query (SSE streaming) |

Full reference: [`docs/host-integration-guide.md`](host-integration-guide.md) and [`backend/docs/APP_REGISTRATION.md`](../backend/docs/APP_REGISTRATION.md)

### 4.3 Token Security Notes

- Tokens are hashed with **Argon2** before storage — the database never holds plaintext tokens.
- Rotate a token by re-registering the app (generating a new token) and updating the host application's config.
- Tokens are scoped to their registered app's permitted knowledge bases only.

---

## 5. MinIO Storage Administration

Documents are stored at **MinIO** (S3-compatible) at `http://localhost:9001` (console).

**Default credentials**: configured via `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` in `.env`

### 5.1 Storage Layout

```
documents/            ← root bucket
└── kb_{kb_id}/
    └── {doc_id}_{filename}
```

### 5.2 CLI Administration

```bash
# List all documents in a KB
docker exec akvo-rag-minio-1 mc ls local/documents/kb_3/

# Check MinIO health
curl http://localhost:9000/minio/health/live

# Clean up orphaned document files (if KB was deleted without proper cleanup)
docker exec akvo-rag-minio-1 mc rm local/documents/kb_3/ --recursive --force
```

---

## 6. Database Administration

### 6.1 Backups

```bash
# Backup PostgreSQL
docker exec akvo-rag-postgres-1 pg_dump -U postgres akvo_rag > backup_$(date +%Y%m%d).sql

# Restore
docker exec -i akvo-rag-postgres-1 psql -U postgres akvo_rag < backup_20260908.sql
```

### 6.2 Migration Status

```bash
# Backend schema (alembic_version)
docker exec akvo-rag-backend-1 alembic current
docker exec akvo-rag-backend-1 alembic history

# Vector KB schema (alembic_version_vkb)
docker exec akvo-rag-vector-kb-mcp-1 alembic current
docker exec akvo-rag-vector-kb-mcp-1 alembic history
```

### 6.3 Direct Database Access

```bash
docker exec -it akvo-rag-postgres-1 psql -U postgres -d akvo_rag
```

Useful queries:

```sql
-- Check all KBs and document counts
SELECT kb.id, kb.name, COUNT(d.id) AS doc_count
FROM vkb_knowledge_bases kb
LEFT JOIN vkb_documents d ON d.kb_id = kb.id
GROUP BY kb.id, kb.name;

-- Find failed documents
SELECT id, file_name, status, created_at
FROM vkb_documents
WHERE status = 'FAILED';

-- Check active prompt versions
SELECT pd.name, pv.version, pv.is_active, LEFT(pv.content, 80) AS preview
FROM prompt_definitions pd
JOIN prompt_versions pv ON pv.definition_id = pd.id
WHERE pv.is_active = true;
```
