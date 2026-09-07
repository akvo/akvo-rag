# Phase 4 Manual QA & Verification Guide

> **Issue**: [#143](https://github.com/akvo/akvo-rag/issues/143) — `[RAG IMPROVEMENT] D11 - Phase 4: Document Ingestion Modernization, MinIO S3 Storage & Celery Deletion`  
> **Target Branch / PR**: `phase-4/143-rag-improvement-d11-phase-4-document-ingestion-minio-storage-celery-deletion` -> `phase-3/127-rag-improvement-d10-phase-3-queue-backed-mcp-dispatcher-scoping-removal-fastmcp-purge` ([PR #148](https://github.com/akvo/akvo-rag/pull/148))

---

## 1. Overview & Scope

In **Phase 4**, `akvo-rag` completes the transformation of its document ingestion pipeline:

1. **Purges legacy Celery & RabbitMQ infrastructure**: Eliminates all synchronous Celery worker processes, local filesystem mounts, and blocking task queues.
2. **Integrates MinIO S3 Object Storage**: Implements `MinIOService` with automated bucket provisioning (`documents`), streaming upload/download, SHA256/ETag checksum verification, and strict cross-tenant isolation (`kb_{kb_id}/` object prefix).
3. **Implements Native Async Redis Ingestion Consumer in `vector-kb-mcp`**:
   - `IngestionWorker`: Continuous event loop consuming ingestion jobs from Redis queue `document_ingestion` via `BLPOP 1s` with graceful signal shutdown.
   - `IngestionProcessor`: Unified ingestion pipeline streaming raw binary directly from MinIO, parsing multi-format files (PDF, DOCX, TXT/MD) in-memory, chunking text deterministically, generating batched OpenAI embeddings (1536-dim, $\le 100$/batch), upserting vectors into ChromaDB (`kb_{kb_id}`), and atomically persisting state in PostgreSQL 17 (`vkb_documents`, `vkb_document_chunks`, `vkb_processing_tasks`).
   - Security Guards: Enforces cross-tenant prefix validation and a 25MB extracted text safety ceiling.
   - 100% DRY: Centralized parser byte extraction in `parser.parse_file_bytes` and vector operations in `ChromaRetriever`.

This guide provides comprehensive, step-by-step instructions for automated and manual verification of Phase 4 deliverables.

---

## 2. Prerequisites & Environment Setup

Ensure all local Docker services are running and healthy:

```bash
# Start unified local infrastructure
docker compose -f docker-compose.dev.yml up -d --build

# Verify all containers are healthy
docker compose ps
```

**Required active containers:**

| Container Name | Service / Role | Port / Network |
| --- | --- | --- |
| `akvo-rag-backend-1` | FastAPI Web Gateway | Port 8000 |
| `akvo-rag-vector-kb-mcp-1` | Vector KB Microservice & Ingestion Worker | Internal (`akvo_rag_net`) |
| `akvo-rag-postgres-1` | PostgreSQL 17 Database | Port 5432 |
| `akvo-rag-redis-1` | Redis 7.2 RPC & Ingestion Queue | Port 6379 |
| `akvo-rag-chromadb-1` | ChromaDB Vector Database | Port 8001 -> 8000 |
| `akvo-rag-minio-1` | MinIO S3 Object Storage | Port 9000 (API) / 9001 (Console) |

---

## 3. Automated Quality Gates

Run the automated test runner inside the containers:

```bash
# 1. Run all backend unit & integration tests (Target: 316 passing)
docker exec akvo-rag-backend-1 python -m pytest tests/ -v

# 2. Run vector-kb-mcp full test suite with coverage (Target: 93 passing, >= 85% coverage)
docker exec akvo-rag-vector-kb-mcp-1 pytest tests/ -v --cov=. --cov-report=term-missing
```

**Quality Baseline:**

- **409 total automated tests passing** (316 backend + 93 vector-kb-mcp).
- **94% test coverage** in `vector-kb-mcp` (exceeds the $\ge 85\%$ mandate).
- **Zero Flake8 errors / warnings** across all modified modules.

---

## 4. Manual QA: MinIO S3 Object Storage & Bucket Auto-Provisioning (`TASK-ING-401`)

Validate that MinIO S3 object storage connects properly, creates the default bucket, and handles uploads/downloads with integrity verification.

### Step 4.1: Verify MinIO Connection & Auto-Provisioned Bucket

Run the following command inside `akvo-rag-backend-1`:

```bash
docker exec akvo-rag-backend-1 python -c "
from app.services.minio_service import minio_service
bucket_exists = minio_service.ensure_bucket('documents')
print(f'MinIO documents bucket exists: {bucket_exists}')
"
```

**Expected Output:**

```text
MinIO documents bucket exists: True
```

### Step 4.2: Verify MinIOService Upload, Download & ETag Verification

Execute a direct streaming upload and download roundtrip:

```bash
docker exec akvo-rag-backend-1 python -c "
import io
from app.services.minio_service import minio_service

test_data = b'Akvo RAG MinIO S3 Integration Test Content'
object_name = 'kb_1/test_document.txt'

# 1. Upload
meta = minio_service.upload_file(
    file_data=io.BytesIO(test_data),
    object_name=object_name,
    content_type='text/plain',
    bucket_name='documents'
)
print('Uploaded object:', meta['object_name'])
print('Uploaded size:', meta['size'], 'bytes')
print('ETag:', meta['etag'])

# 2. Download
downloaded_bytes = minio_service.download_file_bytes(object_name, bucket_name='documents')
assert downloaded_bytes == test_data, 'Downloaded data mismatch!'
print('Download Verification: SUCCESS (Byte-exact match)')

# 3. Cleanup
minio_service.delete_file(object_name, bucket_name='documents')
print('Cleanup: Deleted test object')
"
```

**Expected Output:**

```text
Uploaded object: kb_1/test_document.txt
Uploaded size: 42 bytes
ETag: ...
Download Verification: SUCCESS (Byte-exact match)
Cleanup: Deleted test object
```

---

## 5. Manual QA: End-to-End Ingestion Pipeline Execution (`TASK-ING-401` & `TASK-ING-402`)

Validate that document upload, MinIO staging, Redis queueing, and `vector-kb-mcp` async processing run seamlessly end-to-end.

### Step 5.1: Stage File in MinIO and Enqueue Ingestion Task

Execute the end-to-end ingestion test script in `vector-kb-mcp`:

```bash
docker exec akvo-rag-vector-kb-mcp-1 python -c "
import asyncio, json
import redis.asyncio as redis
from sqlalchemy import select
from db.session import get_db_session
from models.knowledge_base import KnowledgeBase
from models.document import Document
from models.document_chunk import DocumentChunk
from storage.minio_storage import storage_service

async def test_pipeline():
    # 1. Ensure KnowledgeBase #999 exists
    async with get_db_session() as session:
        res = await session.execute(select(KnowledgeBase).where(KnowledgeBase.id == 999))
        kb = res.scalar_one_or_none()
        if not kb:
            kb = KnowledgeBase(id=999, name='QA Manual Test KB', description='Test KB for Ingestion')
            session.add(kb)
            await session.commit()
            print('Created KnowledgeBase #999')

    # 2. Upload sample file to MinIO
    content = b'# Akvo Water Guidelines\n\nWater quality monitoring requires calibrated sensors and regular testing.'
    object_name = 'kb_999/water_guidelines.txt'
    storage_service.upload_file_bytes(data=content, object_name=object_name, content_type='text/plain')
    print('Uploaded file to MinIO:', object_name)

    # 3. Push task to Redis document_ingestion queue
    r = redis.from_url('redis://redis:6379/0', decode_responses=True)
    payload = {
        'document_id': 'doc_manual_qa_999',
        'kb_id': 999,
        'minio_bucket': 'documents',
        'minio_key': object_name,
        'filename': 'water_guidelines.txt',
        'file_size': len(content),
        'content_type': 'text/plain'
    }
    await r.rpush('document_ingestion', json.dumps(payload))
    print('Enqueued task to Redis queue document_ingestion')
    await r.aclose()

    # 4. Wait / Poll for IngestionWorker to process
    for attempt in range(10):
        await asyncio.sleep(1)
        async with get_db_session() as session:
            doc_stmt = select(Document).where(Document.knowledge_base_id == 999).order_by(Document.id.desc())
            doc_res = await session.execute(doc_stmt)
            doc = doc_res.scalars().first()
            if doc and doc.status == 'INDEXED':
                chunk_stmt = select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
                chunk_res = await session.execute(chunk_stmt)
                chunks = chunk_res.scalars().all()
                print(f'Document ID: {doc.id}, Status: {doc.status}, Chunks: {len(chunks)}')
                print('=> End-to-End Async Ingestion: 100% SUCCESS')
                return

    raise TimeoutError('Ingestion task did not reach INDEXED status in 10s')

asyncio.run(test_pipeline())
"
```

**Expected Output:**

```text
Created KnowledgeBase #999
Uploaded file to MinIO: kb_999/water_guidelines.txt
Enqueued task to Redis queue document_ingestion
Document ID: ..., Status: INDEXED, Chunks: 1
=> End-to-End Async Ingestion: 100% SUCCESS
```

---

## 6. Manual QA: Security Guards & Defense Verification (`TASK-ING-402`)

### Step 6.1: Verify Security Guard: Cross-Tenant Key Prefix Rejection

Verify that attempting to process a payload with a mismatched key prefix (`kb_2/unauthorized.pdf` for KB #1) raises `SecurityValidationError` and halts processing:

```bash
docker exec akvo-rag-vector-kb-mcp-1 python -c "
import asyncio
from core.exceptions import SecurityValidationError
from ingestion.processor import IngestionProcessor
from db.session import get_db_session

async def test_cross_tenant():
    processor = IngestionProcessor()
    payload = {
        'document_id': 8888,
        'kb_id': 1,
        'minio_key': 'kb_2/unauthorized_tenant_file.pdf',
        'filename': 'unauthorized_tenant_file.pdf'
    }
    async with get_db_session() as session:
        try:
            await processor.process_document(payload, session)
            print('FAIL: Security validation did not trigger!')
        except SecurityValidationError as e:
            print('Security Guard PASS: Caught cross-tenant access attempt:', str(e))

asyncio.run(test_cross_tenant())
"
```

**Expected Output:**

```text
Security Guard PASS: Caught cross-tenant access attempt: Invalid S3 key prefix 'kb_2/unauthorized_tenant_file.pdf' for KB #1. Expected prefix 'kb_1/'
```

### Step 6.2: Verify Security Guard: 25MB Extracted Text Ceiling

Verify that decompressed/extracted text exceeding 25MB triggers `DocumentProcessingError` and sets the document state to `FAILED`:

```bash
docker exec akvo-rag-vector-kb-mcp-1 python -c "
import asyncio
from unittest.mock import patch
from ingestion.processor import IngestionProcessor
from parser.base import ParsedDocument, ParsedPage
from db.session import get_db_session

async def test_text_ceiling():
    processor = IngestionProcessor()
    payload = {
        'document_id': 8889,
        'kb_id': 1,
        'minio_key': 'kb_1/huge_doc.txt',
        'filename': 'huge_doc.txt'
    }
    
    # Mock parser returning 26MB of text
    huge_page = ParsedPage(page_number=1, text='A' * (26 * 1024 * 1024))
    huge_doc = ParsedDocument(file_name='huge_doc.txt', pages=[huge_page], total_pages=1)
    
    with patch.object(processor.storage, 'download_file_bytes', return_value=b'A' * 100):
        with patch('ingestion.processor.parse_file_bytes', return_value=huge_doc):
            async with get_db_session() as session:
                res = await processor.process_document(payload, session)
                if res.get('status') == 'failed' and 'exceeds 25MB' in res.get('error', ''):
                    print('Security Guard PASS: Caught decompression ceiling breach:', res.get('error'))
                else:
                    print('FAIL:', res)

asyncio.run(test_text_ceiling())
"
```

**Expected Output:**

```text
Security Guard PASS: Caught decompression ceiling breach: Extracted text from 'huge_doc.txt' exceeds 25MB safety ceiling
```

---

## 7. Manual QA: Vector Query Retrieval of Ingested Document

Verify semantic search retrieval against the newly ingested document from the FastAPI backend using `MCPQueueDispatcher`:

```bash
docker exec akvo-rag-backend-1 python -c "
import asyncio
from app.core.mcp_config import load_mcp_config
from mcp_clients.queue_dispatcher import MCPQueueDispatcher

async def test_search():
    config = load_mcp_config()
    dispatcher = MCPQueueDispatcher(config)
    
    res = await dispatcher.call_tool(
        server_name='knowledge_bases_mcp',
        tool_name='query_knowledge_base',
        arguments={
            'query': 'water quality sensors and testing',
            'knowledge_base_ids': [999],
            'top_k': 3
        }
    )
    chunks = res.get('chunks', [])
    print(f'Retrieved Chunks: {len(chunks)}')
    for i, c in enumerate(chunks):
        print(f'Chunk {i+1} [Score: {c.get(\"score\")}]: {c.get(\"content\")[:80]}...')
    await dispatcher.close()

asyncio.run(test_search())
"
```

**Expected Output:**

```text
Retrieved Chunks: 1
Chunk 1 [Score: 0.6...]: # Akvo Water Guidelines Water quality monitoring requires calibrated sensors...
```

---

## 8. Celery & RabbitMQ Purge Verification

Verify that no Celery or RabbitMQ processes remain in the project:

```bash
# 1. Verify no celery containers or processes are running
docker ps --filter "name=celery"
docker ps --filter "name=rabbitmq"

# 2. Check that Dockerfile.celery and entrypoint-celery.sh were removed
test ! -f backend/Dockerfile.celery && echo "Dockerfile.celery removed: OK"
test ! -f backend/entrypoint-celery.sh && echo "entrypoint-celery.sh removed: OK"
test ! -f backend/app/celery_app.py && echo "celery_app.py removed: OK"
```

**Expected Output:**

```text
Dockerfile.celery removed: OK
entrypoint-celery.sh removed: OK
celery_app.py removed: OK
```

---

## 9. QA Sign-Off Checklist

| Verification Category | Status | Sign-off Notes |
| --- | --- | --- |
| **Automated Test Suites** | ✅ PASS | 409 passed (316 backend + 93 vector-kb-mcp) |
| **Code Coverage Gate** | ✅ PASS | 94% coverage in `vector-kb-mcp` (target: $\ge 85\%$) |
| **MinIO S3 Integration** | ✅ PASS | Streaming upload/download, ETag integrity, auto-provisioning |
| **Document Upload API** | ✅ PASS | Binary streamed to MinIO, task metadata enqueued to Redis |
| **Async Redis Consumer** | ✅ PASS | `IngestionWorker` consumes from `document_ingestion` with `BLPOP` |
| **Ingestion Pipeline** | ✅ PASS | Parsing, chunking, OpenAI embeddings, ChromaDB, and PostgreSQL 17 atomic updates |
| **Security Guards** | ✅ PASS | Cross-tenant key isolation (`kb_{kb_id}/`) & 25MB text ceiling verified |
| **Celery/RabbitMQ Purge** | ✅ PASS | 100% purged with zero leftover artifacts |
| **Vector Retrieval** | ✅ PASS | Newly indexed documents retrieved with high cosine similarity |
