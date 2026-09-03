# Legacy Data Migration Guide

This guide provides end-to-end instructions for migrating historical data from legacy deployments (standalone **Vector KB PostgreSQL** and **Backend MySQL**) into the unified **PostgreSQL 17** database (`akvo_rag`).

---

## 1. Architecture: Legacy vs. Unified PostgreSQL 17

| Component | Legacy Deployment | Target Location (Unified PostgreSQL 17) |
|---|---|---|
| **Vector Knowledge Base** | Standalone PostgreSQL (`vector-knowledge-base-mcp-server`)<br>• `knowledge_bases`<br>• `documents`<br>• `document_chunks` | **`akvo_rag` Database** (Table namespace: `vkb_*`)<br>• `vkb_knowledge_bases`<br>• `vkb_documents`<br>• `vkb_document_chunks`<br>• `vkb_processing_tasks` |
| **Backend Host Application** | Standalone MySQL (`akvo-rag-backend`)<br>• `users`<br>• `apps`<br>• `chats` / `messages`<br>• `prompt_definitions` | **`akvo_rag` Database** (Standard namespace)<br>• `users`<br>• `apps`<br>• `chats` / `messages`<br>• `prompt_definitions` / `prompt_versions` |

---

## 2. Network Prerequisites (Docker Host Resolution)

When running the migration CLI inside a Docker container (`akvo-rag-vector-kb-mcp-1`), network hosts must be addressed properly:

- **If your legacy database is running on your local machine (outside Docker):**
  - **macOS / Windows**: Use `host.docker.internal` instead of `localhost` or `127.0.0.1`.
  - **Linux**: Use your host's gateway IP (e.g. `172.17.0.1`) or `--network host`.
- **If your legacy database is running in another Docker container:**
  - Attach the container to the same network (`akvo_rag_net`) or use the container name.
- **If your legacy database is hosted remotely (AWS RDS, Cloud SQL, etc.):**
  - Use the remote hostname or IP address and ensure security group/firewall allows access.

---

## 3. Part A: Migrating Vector KB Data (from Legacy PostgreSQL)

The `vector-kb-mcp` microservice provides an idempotent, batch-processing ETL CLI tool located at `vector-kb-mcp/cli/migrate_legacy_data.py`.

### Step 3.1: Preview Migration via `--dry-run`

Run the dry-run command to verify database connectivity and preview record counts without modifying any tables:

```bash
docker exec -it akvo-rag-vector-kb-mcp-1 python cli/migrate_legacy_data.py \
  --source-url "postgresql://<POSTGRES_USER>:<POSTGRES_PASSWORD>@<POSTGRES_HOST>:<PORT>/<LEGACY_DB>" \
  --dry-run
```

**Example (Local database running on macOS on port 5433):**
```bash
docker exec -it akvo-rag-vector-kb-mcp-1 python cli/migrate_legacy_data.py \
  --source-url "postgresql://postgres:mysecretpassword@host.docker.internal:5433/legacy_vkb" \
  --dry-run
```

**Expected Dry-Run Output:**
```text
2026-09-03 11:00:00 [INFO] [legacy_migrator] Starting legacy data migration (dry_run=True, batch_size=500)
2026-09-03 11:00:00 [INFO] [legacy_migrator] Extracted 3 knowledge bases from source
2026-09-03 11:00:00 [INFO] [legacy_migrator] Extracted 42 documents from source
2026-09-03 11:00:01 [INFO] [legacy_migrator] Extracted 1,280 document chunks from source
============================================================
MIGRATION SUMMARY (DRY RUN):
  • Knowledge Bases Migrated: 3
  • Documents Migrated:       42
  • Document Chunks Migrated: 1280
============================================================
```

---

### Step 3.2: Execute Full Live Migration

Once the dry run succeeds, execute the live migration:

```bash
docker exec -it akvo-rag-vector-kb-mcp-1 python cli/migrate_legacy_data.py \
  --source-url "postgresql://<POSTGRES_USER>:<POSTGRES_PASSWORD>@<POSTGRES_HOST>:<PORT>/<LEGACY_DB>" \
  --batch-size 500
```

> [!TIP]
> The migration script applies `ON CONFLICT (id) DO NOTHING` on primary keys, making it **100% idempotent**. You can safely re-run it multiple times without creating duplicate entries or corrupting existing data.

---

### Step 3.3: Verify Imported Vector Data in PostgreSQL 17

Check the imported row counts directly in the target PostgreSQL 17 container:

```bash
docker exec akvo-rag-postgres-1 psql -U postgres -d akvo_rag -c "
SELECT 'vkb_knowledge_bases' AS table_name, count(*) AS total_rows FROM vkb_knowledge_bases
UNION ALL
SELECT 'vkb_documents', count(*) FROM vkb_documents
UNION ALL
SELECT 'vkb_document_chunks', count(*) FROM vkb_document_chunks;
"
```

---

## 4. Part B: Initializing & Migrating Backend Data

### Scenario 1: Fresh Initialization (Recommended for Standard Setups)

If you do not need historical chat logs from MySQL and only require standard admin access and prompts:

1. **Seed System Prompts & Dynamic Overlays**:
   ```bash
   docker exec akvo-rag-backend-1 python -m app.seeder.seed_prompts
   ```

2. **Seed Default Super-Admin User**:
   ```bash
   docker exec akvo-rag-backend-1 python -m app.seeder.seed_admin_user
   ```

---

### Scenario 2: Migrating Historical Users & Chats from Legacy MySQL

If you have existing historical users, registered apps, and chat histories in a legacy MySQL database, use the following procedure:

#### Step 4.2.1: Test MySQL Connectivity from Backend
Verify connection to your MySQL instance:

```bash
docker exec -it akvo-rag-backend-1 python -c "
import pymysql
conn = pymysql.connect(
    host='<MYSQL_HOST>', # Use 'host.docker.internal' for host machine
    user='<MYSQL_USER>',
    password='<MYSQL_PASSWORD>',
    database='<MYSQL_DATABASE>',
    port=<MYSQL_PORT> # e.g. 3306
)
print('MySQL Connection Successful!')
conn.close()
"
```

#### Step 4.2.2: Run Backend Table ETL Script
You can pipe data directly from MySQL into PostgreSQL using Python:

```bash
docker exec -it akvo-rag-backend-1 python -c "
import os
import pandas as pd
from sqlalchemy import create_engine

mysql_url = 'mysql+pymysql://<USER>:<PASS>@<HOST>:<PORT>/<MYSQL_DB>'
pg_url = 'postgresql+psycopg2://postgres:postgres@postgres:5432/akvo_rag'

mysql_engine = create_engine(mysql_url)
pg_engine = create_engine(pg_url)

tables = ['users', 'apps', 'app_knowledge_bases', 'chats', 'messages']

for tbl in tables:
    print(f'Migrating table: {tbl}...')
    try:
        df = pd.read_sql_table(tbl, mysql_engine)
        if not df.empty:
            df.to_sql(tbl, pg_engine, if_exists='append', index=False)
            print(f' -> Successfully migrated {len(df)} rows to {tbl}')
        else:
            print(f' -> Table {tbl} is empty, skipping.')
    except Exception as e:
        print(f' -> Notice for {tbl}: {e}')

print('Backend MySQL migration completed!')
"
```

---

## 5. Part C: Storage Verification (ChromaDB & MinIO)

1. **Verify ChromaDB Collections**:
   ```bash
   curl -s http://localhost:8001/api/v2/heartbeat
   ```

2. **Verify MinIO Object Storage**:
   Access the MinIO Web Console at [http://localhost:9001](http://localhost:9001) using credentials:
   - **Username:** `minioadmin`
   - **Password:** `minioadmin`

---

## 6. Troubleshooting Common Migration Issues

### Error 1: `psycopg2.OperationalError: could not translate host name`
- **Cause**: Using placeholder text `<POSTGRES_HOST>` or `localhost` inside a Docker container.
- **Fix**: Replace with `host.docker.internal` (macOS/Windows) or the specific reachable IP address of your database server.

### Error 2: `ValueError: invalid literal for int() with base 10: '<PORT>'`
- **Cause**: The `<PORT>` placeholder was not replaced with an actual numeric port.
- **Fix**: Specify the numeric port (e.g. `5432` for PostgreSQL or `3306` for MySQL).

### Error 3: Foreign Key Violations
- **Cause**: Attempting to insert child records (`documents`, `messages`) before parent records (`knowledge_bases`, `chats`).
- **Fix**: `migrate_legacy_data.py` automatically migrates tables in topological dependency order (`knowledge_bases` ➔ `documents` ➔ `document_chunks`).
