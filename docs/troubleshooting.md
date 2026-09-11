# Troubleshooting Guide: Akvo RAG

Debugging playbooks for all 7 containers in the Akvo RAG stack.

> **Quick reference**: [Architecture Map](architecture_map.md) | [Developer Guide](dev-guide.md) | [Admin Guide](admin-guide.md)

---

## Quick Diagnostics

Before diving into a specific container's playbook, run these first:

```bash
# Check all 7 containers are running
docker compose ps

# Tail all container logs simultaneously
docker compose logs -f --tail=20

# View logs for a specific service
docker compose logs backend --tail=50
docker compose logs vector-kb-mcp --tail=50
```

---

## 1. PostgreSQL Issues

### 1.1 Database Tables Not Found / Migration Errors

```bash
# Verify postgres is healthy
docker compose ps postgres

# Check postgres logs for startup errors
docker compose logs postgres --tail=30

# Connect and verify tables exist
docker exec -it akvo-rag-postgres-1 psql -U postgres -d akvo_rag -c "\dt"
```

If tables are missing, run migrations manually:

```bash
# Core backend schema
docker exec akvo-rag-backend-1 alembic upgrade head

# Vector KB schema
docker exec akvo-rag-vector-kb-mcp-1 alembic upgrade head
```

### 1.2 Connection Refused

Check `.env` settings match container environment:

```dotenv
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=akvo_rag
```

Restart postgres if needed:

```bash
docker compose restart postgres
```

Wait 10 seconds, then restart dependent services:

```bash
docker compose restart backend vector-kb-mcp
```

### 1.3 Migration Conflict Between Services

**Symptom**: `alembic.util.exc.CommandError: Target database is not up to date`

The two migration chains (`alembic_version` for backend, `alembic_version_vkb` for vector-kb-mcp) are independent. Never run backend's alembic inside the vector-kb-mcp container or vice versa.

```bash
# Verify each service manages its own table only
docker exec akvo-rag-backend-1 alembic current
docker exec akvo-rag-vector-kb-mcp-1 alembic current
```

---

## 2. Redis Issues

### 2.1 MCP Dispatcher Timeout / Tool Calls Failing

**Symptom**: Backend logs show `TimeoutError` or tool calls never resolve; `vector-kb-mcp` is unresponsive.

```bash
# Check Redis is running
docker compose ps redis
docker exec akvo-rag-redis-1 redis-cli ping  # Should return: PONG

# Check queue depth (should be 0 if processed normally)
docker exec akvo-rag-redis-1 redis-cli llen mcp:vector:requests

# View all active MCP keys
docker exec akvo-rag-redis-1 redis-cli keys "mcp:*"

# Check vector-kb-mcp worker logs
docker compose logs vector-kb-mcp --tail=50
```

If queue is backed up (llen > 0 and not draining):

```bash
# Restart the worker
docker compose restart vector-kb-mcp

# If still stuck, flush the queues (drops pending requests)
docker exec akvo-rag-redis-1 redis-cli del mcp:vector:requests
```

### 2.2 Redis Connection Refused

Verify `REDIS_URL` in `.env`:

```dotenv
REDIS_URL=redis://redis:6379/0
```

The hostname `redis` refers to the Docker service name — do not use `localhost` inside containers.

```bash
docker compose restart redis
docker compose restart backend vector-kb-mcp
```

---

## 3. ChromaDB Issues

### 3.1 Permission Error / Collection Not Found

```bash
# Check ChromaDB logs
docker compose logs chromadb --tail=30

# Restart with fresh volume (WARNING: deletes all vectors — re-ingest required)
docker compose stop chromadb
docker compose rm -f chromadb
docker volume rm akvo-rag_chromadb_data   # adjust volume name to match your compose project
docker compose up -d chromadb
```

After volume reset, re-ingest all documents through the Admin UI or via the `ingest_document` API.

### 3.2 ChromaDB Not Reachable from vector-kb-mcp

```bash
# Test ChromaDB health from vector-kb-mcp container
docker exec akvo-rag-vector-kb-mcp-1 curl -s http://chromadb:8000/api/v1/heartbeat

# Should return: {"nanosecond heartbeat": <timestamp>}
```

If this fails, check `CHROMA_HOST` environment variable in `docker-compose.yml` / `.env`.

---

## 4. MinIO Issues

### 4.1 MinIO Unreachable

```bash
# Health check
curl http://localhost:9000/minio/health/live   # Should return HTTP 200

# Check MinIO logs
docker compose logs minio --tail=30

# Check if port is already in use
lsof -i :9000
lsof -i :9001
```

Set `MINIO_PORT` and `MINIO_CONSOLE_PORT` in `.env` if defaults conflict.

### 4.2 Document Upload Fails / S3 Errors

**Symptom**: Backend logs show `S3Error` or `NoSuchBucket`.

```bash
# Verify MinIO credentials match backend env
# In .env: MINIO_ROOT_USER and MINIO_ROOT_PASSWORD
# In backend env: MINIO_ACCESS_KEY and MINIO_SECRET_KEY must match

# List buckets via MinIO CLI
docker exec akvo-rag-minio-1 mc ls local/

# Create the documents bucket manually if missing
docker exec akvo-rag-minio-1 mc mb local/documents
```

---

## 5. Backend (FastAPI) Issues

### 5.1 Backend Won't Start

```bash
docker compose logs backend --tail=50
```

Common causes:
- **Missing `.env` variable**: Look for `KeyError` or `ValidationError` in logs.
- **PostgreSQL not ready**: Backend starts before postgres — wait and restart: `docker compose restart backend`.
- **OpenAI API key invalid**: Look for `AuthenticationError` from OpenAI.

### 5.2 JWT Token Errors (401 Unauthorized)

- Verify `SECRET_KEY` in `.env` is set and has not changed between container restarts.
- Token expiry: default is 7 days (`ACCESS_TOKEN_EXPIRE_MINUTES=10080`). Ask user to log in again.

### 5.3 RAG Responses Are Empty / Low Quality

```bash
# Check if the correct model is configured
grep -E "OPENAI_MODEL|CHAT_PROVIDER" .env

# Verify knowledge bases are indexed
docker exec -it akvo-rag-postgres-1 psql -U postgres -d akvo_rag \
  -c "SELECT status, COUNT(*) FROM vkb_documents GROUP BY status;"
```

If documents show `FAILED` status — check vector-kb-mcp logs and retry ingestion.

### 5.4 SSE Streaming Not Working

- Verify the frontend `NEXT_PUBLIC_API_URL` points to the correct backend URL.
- Ensure no reverse proxy is buffering responses (add `X-Accel-Buffering: no` header for Nginx).

---

## 6. Vector KB MCP Issues

### 6.1 Worker Not Processing Requests

```bash
# Check worker is running
docker compose ps vector-kb-mcp
docker compose logs vector-kb-mcp --tail=30

# Test Redis connectivity from the worker container
docker exec akvo-rag-vector-kb-mcp-1 redis-cli -h redis ping
```

If logs show `ConnectionRefusedError` to Redis, restart services in order:

```bash
docker compose restart redis
sleep 5
docker compose restart vector-kb-mcp
```

### 6.2 Document Processing Stuck in PROCESSING

```bash
# Check queue depth
docker exec akvo-rag-redis-1 redis-cli llen mcp:vector:requests

# Tail worker logs for the processing error
docker compose logs vector-kb-mcp -f --tail=100

# Force reset a stuck document via psql
docker exec -it akvo-rag-postgres-1 psql -U postgres -d akvo_rag \
  -c "UPDATE vkb_documents SET status='FAILED' WHERE status='PROCESSING' AND created_at < NOW() - INTERVAL '1 hour';"
```

---

## 7. Frontend Issues

### 7.1 Frontend Not Loading

```bash
docker compose logs frontend --tail=30
```

In dev mode (`docker-compose.dev.yml`), Next.js compiles on first request — wait ~30 seconds for initial page load.

### 7.2 API Errors in Browser

Open browser DevTools → Network tab. Common issues:

| Error | Cause | Fix |
|-------|-------|-----|
| `ERR_CONNECTION_REFUSED` on API calls | Backend not running or wrong port | Check `NEXT_PUBLIC_API_URL` in `.env` |
| `401 Unauthorized` | Expired JWT | Log out and log back in |
| `404 Not Found` for API routes | Wrong `NEXT_PUBLIC_API_URL` | Verify backend port matches `.env` |
| CORS error | Frontend domain not in CORS allow list | Add `FRONTEND_URL` to backend CORS config |

### 7.3 Build Errors

```bash
docker exec akvo-rag-frontend-1 pnpm lint
docker exec akvo-rag-frontend-1 pnpm build
```

---

## 8. General Container Commands

```bash
# Restart a single service without rebuilding
docker compose restart <service>

# Rebuild and restart a single service
docker compose up -d --build <service>

# View resource usage (CPU/RAM) for all containers
docker stats

# Inspect a container's environment variables
docker inspect akvo-rag-backend-1 | grep -A 50 '"Env"'

# Full clean reset (WARNING: destroys all volumes/data)
docker compose down -v
docker compose up -d --build
```

---

## 9. Ollama (Local LLM) on macOS

When using Ollama as the LLM provider inside Docker on macOS:

```dotenv
# Use host.docker.internal instead of localhost
OLLAMA_API_BASE=http://host.docker.internal:11434
CHAT_PROVIDER=ollama
```

Verify Ollama is running on the host:

```bash
curl http://localhost:11434/api/tags   # Should list available models
```

If models are missing:

```bash
ollama pull deepseek-r1:7b
ollama pull qwen2.5:3b
```

---

## 10. RAG Evaluation Issues

```bash
# Start the RAGAS evaluation dashboard
./rag-evaluate

# Stop cleanly (prevents Docker artifact accumulation)
./rag-evaluate-stop

# Run E2E evaluation headlessly
cd backend/RAG_evaluation && ./run_e2e_tests_headless_container.sh
```

If evaluation scores drop below thresholds (Faithfulness < 0.85, Relevancy < 0.85, Groundedness < 0.90):
1. Check that KBs have successfully indexed all documents.
2. Review active prompt versions — roll back to a previous version if a recent change degraded quality.
3. Re-run with a larger `top_k` value to increase retrieval recall.
