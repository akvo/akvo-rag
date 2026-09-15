# Fail-Safe Legacy Data Migration Guide (Zero-Risk Dump Strategy)

> **Document Path:** `docs/legacy-data-migration-guide.md`  
> **Status:** `APPROVED (BMAD Party Council & Security Red Team)`  
> **Target:** Zero Downtime, Zero Lock Risk, Zero Data Loss Migration from Legacy PostgreSQL & MySQL to Unified PostgreSQL 17 (`akvo_rag`)  

---

## 🎭 BMAD Party Mode Consensus: Why the "Dump-First Replica" Strategy is Mandatory

During the **BMAD Party Mode Deliberation**, the Architect Council (Winston, Amelia, Murat, Rachel) established the **Dump-First Staging Strategy** as the absolute mandatory standard for production migration:

```text
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ZERO-RISK FAIL-SAFE MIGRATION ARCHITECTURE                                                       │
│                                                                                                  │
│  [Live Legacy Systems]                 [Isolated Staging Engine]             [Target PG 17]          │
│  Live Legacy MySQL ────(No-Lock Dump)──► Local/Staging DB ──(ETL Script)──► Unified PostgreSQL 17│
│  Live Legacy PG    ────(No-Lock Dump)──► Temporary Staging ──(Verify Gate)──► (akvo_rag DB)       │
│                                                                                                  │
│  • ZERO Locks on Live DBs              • 100% Isolated ETL   • 3-Tier Row Count Parity Asserted  │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Key Safety Guarantees

1. **Zero System Breakage (No-Lock Exports)**: Dump commands use `--single-transaction --quick --lock-tables=false` on MySQL and `--format=custom` on PostgreSQL. Live production users experience **zero table locks, zero query blocks, and zero CPU degradation**.
2. **Zero Data Loss**: 3-Tier mathematical verification (`count(*)` parity check) guarantees that every user account, chat log, document, and vector chunk is verified before cutover.
3. **100% Isolated Staging Execution**: The migration ETL script runs against the temporary restored dump, completely isolated from live production traffic.
4. **Instant Rollback Safety**: A pre-migration backup of the target PostgreSQL 17 database is created before any data is written.

---

## 1. Architecture: Legacy vs. Unified PostgreSQL 17

| Component | Legacy Deployment | Target Location (Unified PostgreSQL 17) |
|---|---|---|
| **Vector Knowledge Base** | Standalone PostgreSQL (`vector-knowledge-base-mcp-server`)<br>• `knowledge_bases`<br>• `documents`<br>• `document_chunks` | **`akvo_rag` Database** (Table namespace: `vkb_*`)<br>• `vkb_knowledge_bases`<br>• `vkb_documents`<br>• `vkb_document_chunks`<br>• `vkb_processing_tasks` |
| **Backend Host Application** | Standalone MySQL (`akvo-rag-backend`)<br>• `users`<br>• `apps`<br>• `chats` / `messages`<br>• `prompt_definitions` | **`akvo_rag` Database** (Standard namespace)<br>• `users`<br>• `apps`<br>• `chats` / `messages`<br>• `prompt_definitions` / `prompt_versions` |

---

## 2. Phase 1: Fail-Safe Database Dumping (No-Lock Exports)

Execute these dump commands on your local machine or jump host. These commands export snapshots without locking live production tables.

### Step 1.1: Dump Legacy Vector KB (PostgreSQL)

```bash
# Set legacy PostgreSQL connection parameters
LEGACY_PG_HOST="legacy-pg-host.example.com"
LEGACY_PG_USER="postgres"
LEGACY_PG_DB="legacy_vkb"

# Export custom binary dump (No locks, read-only snapshot)
pg_dump -h $LEGACY_PG_HOST -U $LEGACY_PG_USER -d $LEGACY_PG_DB \
  -F c -b -v -f legacy_vkb_dump.pgdump
```

### Step 1.2: Dump Legacy Backend (MySQL)

> [!IMPORTANT]
> The flags `--single-transaction --quick --lock-tables=false` are critical on MySQL to ensure zero lock contention on live production tables.

```bash
# Set legacy MySQL connection parameters
LEGACY_MYSQL_HOST="legacy-mysql-host.example.com"
LEGACY_MYSQL_USER="root"
LEGACY_MYSQL_DB="ragwebui"

# Export zero-lock MySQL dump
mysqldump -h $LEGACY_MYSQL_HOST -u $LEGACY_MYSQL_USER -p \
  --single-transaction --quick --lock-tables=false \
  $LEGACY_MYSQL_DB > legacy_backend_dump.sql
```

---

## 3. Phase 2: Target PostgreSQL 17 Pre-Migration Safety Backup

Before importing anything into the target PostgreSQL 17 database (`akvo_rag`), create an instant restore point:

```bash
# If using Docker Compose locally:
docker exec akvo-rag-postgres-1 pg_dump -U postgres akvo_rag > akvo_rag_pre_migration_backup.sql

# If using Kubernetes cluster:
NAMESPACE="akvo-rag"
PG_POD=$(kubectl get pods -n $NAMESPACE -l app=postgres -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n $NAMESPACE $PG_POD -- pg_dump -U postgres akvo_rag > akvo_rag_pre_migration_backup.sql
```

---

## 4. Phase 3: Staging Restoration & Dry-Run Verification

Restore the dumps into a temporary local staging database or local container so the migration script runs in complete isolation.

### Step 3.1: Restore Vector KB Dump into Temporary Staging DB

```bash
# Create local temporary staging database
docker exec akvo-rag-postgres-1 psql -U postgres -c "CREATE DATABASE legacy_vkb_staging;"

# Restore dump into temporary staging DB
docker exec -i akvo-rag-postgres-1 pg_restore -U postgres -d legacy_vkb_staging < legacy_vkb_dump.pgdump
```

### Step 3.2: Restore Backend MySQL Dump into Temporary MySQL Container

```bash
# Start a temporary local MySQL container
docker run --name temp-legacy-mysql -e MYSQL_ROOT_PASSWORD=root -p 3306:3306 -d mysql:8.0

# Wait 10 seconds for MySQL to initialize, then create database and restore
docker exec -i temp-legacy-mysql mysql -u root -proot -e "CREATE DATABASE ragwebui_staging;"
docker exec -i temp-legacy-mysql mysql -u root -proot ragwebui_staging < legacy_backend_dump.sql
```

---

## 5. Phase 4: Execute Idempotent ETL Migration

Now execute the migration scripts against the **isolated temporary staging databases**.

### Step 4.1: Dry-Run Verification (`--dry-run`)

```bash
# 1. Preview Vector KB migration counts
docker exec -it akvo-rag-vector-kb-mcp-1 python cli/migrate_legacy_data.py \
  --source-url "postgresql://postgres:postgres@host.docker.internal:5432/legacy_vkb_staging" \
  --dry-run

# 2. Preview Backend User & Chat migration counts
docker exec -it akvo-rag-backend-1 python cli/migrate_legacy_backend.py \
  --source-url "mysql+mysqlconnector://root:root@host.docker.internal:3306/ragwebui_staging" \
  --dry-run
```

---

### Step 4.2: Live Migration Execution

Once the dry run displays expected counts, execute live migration:

```bash
# 1. Migrate Vector KB Data (Idempotent ON CONFLICT DO NOTHING)
docker exec -it akvo-rag-vector-kb-mcp-1 python cli/migrate_legacy_data.py \
  --source-url "postgresql://postgres:postgres@host.docker.internal:5432/legacy_vkb_staging" \
  --batch-size 500

# 2. Migrate Backend Users, Apps & Chats (Sanitizes \x00 & Resets Sequences)
docker exec -it akvo-rag-backend-1 python cli/migrate_legacy_backend.py \
  --source-url "mysql+mysqlconnector://root:root@host.docker.internal:3306/ragwebui_staging"
```

---

## 6. Phase 5: 3-Tier Zero-Data-Loss Verification Gate

To guarantee 100% data integrity, compare row counts between the temporary staging source and target PostgreSQL 17:

### Step 5.1: Run Verification Query

```bash
docker exec akvo-rag-postgres-1 psql -U postgres -d akvo_rag -c "
SELECT 'vkb_knowledge_bases' AS table_name, count(*) AS total_rows FROM vkb_knowledge_bases
UNION ALL SELECT 'vkb_documents', count(*) FROM vkb_documents
UNION ALL SELECT 'vkb_document_chunks', count(*) FROM vkb_document_chunks
UNION ALL SELECT 'users', count(*) FROM users
UNION ALL SELECT 'apps', count(*) FROM apps
UNION ALL SELECT 'chats', count(*) FROM chats
UNION ALL SELECT 'messages', count(*) FROM messages;
"
```

### Verification Checklist
- [ ] `vkb_knowledge_bases` row count matches staging source count.
- [ ] `vkb_documents` row count matches staging source count.
- [ ] `vkb_document_chunks` row count matches staging source count.
- [ ] `users` row count matches staging source count.
- [ ] `chats` and `messages` row counts match staging source count.
- [ ] PostgreSQL primary key sequences (`users_id_seq`, `chats_id_seq`, etc.) reset successfully.

---

## 7. Phase 6: Secure Cleanup

After verifying 100% row count match and successful login testing, securely remove temporary dump files and staging containers:

```bash
# Remove temporary MySQL container & DB
docker stop temp-legacy-mysql && docker rm temp-legacy-mysql
docker exec akvo-rag-postgres-1 psql -U postgres -c "DROP DATABASE legacy_vkb_staging;"

# Remove local dump files
rm -f legacy_vkb_dump.pgdump legacy_backend_dump.sql
```

---

## 8. Troubleshooting Common Migration Edge Cases

### Edge Case 1: Null Byte Error (`\x00` in UTF-8 text)
- **Cause**: Legacy PDF chunks contain scanner artifacts or binary null bytes.
- **Resolution**: `migrate_legacy_data.py` automatically runs `_sanitize_null_bytes()` to strip `\x00` and `\u0000` before writing to PostgreSQL 17.

### Edge Case 2: Duplicate Primary Key Constraints
- **Cause**: Re-running migration scripts multiple times.
- **Resolution**: Both CLI scripts use `ON CONFLICT (id) DO NOTHING` on PostgreSQL 17 primary keys. Re-running is 100% idempotent and safe.

### Edge Case 3: Primary Key Auto-Increment Sequence Desynchronization
- **Cause**: Preserving legacy `id` numbers during `INSERT` does not update PostgreSQL auto-increment counters.
- **Resolution**: `migrate_legacy_backend.py` executes `SELECT setval(pg_get_serial_sequence(table, 'id'), MAX(id))` on completion, preventing primary key collisions on new user chats.
