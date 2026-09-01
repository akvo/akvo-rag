# Docker Compose Setup & Container Interaction Sequence Diagrams (Option C)

This document provides the complete **Mermaid Sequence Diagrams** illustrating the containers, volumes, background workers, and real-time interactions for **both deployment modes** in Option C:
1. **Mode 1: Standalone `akvo-rag` + `vector-kb`** (With Next.js UI, Chat Playground SSE streaming, Prompt Editor, and PDF Uploads).
2. **Mode 2: Embedded `xxxconnect` (AgriConnect / WASHConnect)** (In-process WhatsApp Bot with Celery Outbound Worker).

You can copy the code snippets directly into the [Mermaid Live Editor](https://dedenbangkit.github.io/mermaid-live-editor/) to view and export high-resolution PNG/SVG images.

---

## 1. Mode 1 Sequence Diagram: Standalone `akvo-rag` + `vector-kb`

> **Use Case:** Used by Product Admins, Prompt Engineers, and Developers for prompt lifecycle management, live chat playground testing, and managing Knowledge Bases.

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Admin / Developer

    box rgb(240, 248, 255) Akvo-RAG Web Application
        participant WebUI as Next.js Web Frontend<br/>(Playground & Prompt Editor)
        participant Backend as FastAPI Backend<br/>(In-Process Core Engine)
    end

    box rgb(255, 250, 240) Background Ingestion Worker
        participant IngWorker as Ingestion Worker<br/>(PDF Parse, Chunk, Embed)
    end

    box rgb(245, 245, 245) Datastores & Storage
        participant PG as PostgreSQL 17<br/>(Users, Prompts, KB Metadata)
        participant Chroma as ChromaDB<br/>(Vector Collections)
        participant MinIO as MinIO (S3)<br/>(Raw Document Files)
        participant Redis as Redis<br/>(Ingestion Queue)
    end

    box rgb(245, 255, 245) External Services
        participant OpenAI as OpenAI API<br/>(LLM & Embeddings)
    end

    %% FLOW A: PLAYGROUND LIVE CHAT
    rect rgb(230, 242, 255)
        note over Admin, OpenAI: FLOW A: Next.js Chat Playground & Prompt Testing (In-Process)
        Admin->>WebUI: 1. Send Test Prompt in Playground UI
        WebUI->>Backend: 2. SSE Stream Request (POST /api/chat/stream)
        Backend->>PG: 3. Load Selected Prompt Version from DB

        critical Direct In-Memory RAG Execution (akvo-rag-core + vector-kb-core)
            Backend->>OpenAI: 4. Generate Query Embedding (text-embedding-3-small)
            OpenAI-->>Backend: Return 1536-dim Query Vector
            Backend->>Chroma: 5. Query Target KB Collection (In-Process ChromaRetriever)
            Chroma-->>Backend: Return Matched Document Chunks (Cosine Similarity)
            Backend->>OpenAI: 6. Stream Answer with Citations & Context (gpt-4o-mini)
            OpenAI-->>Backend: Token Stream
        end

        Backend-->>WebUI: 7. Server-Sent Events (SSE Stream)
        WebUI-->>Admin: 8. Live Real-Time Token Output & Citations in UI
    end

    %% FLOW B: KB PDF UPLOAD
    rect rgb(255, 243, 230)
        note over Admin, OpenAI: FLOW B: Knowledge Base Document Ingestion
        Admin->>WebUI: 9. Upload Sector PDF Manual
        WebUI->>Backend: 10. POST /api/v1/knowledge-bases/{id}/documents
        Backend->>MinIO: 11. Save Raw PDF File (Bucket: documents/)
        Backend->>PG: 12. Create Record (Status: PROCESSING)
        Backend->>Redis: 13. Enqueue process_document(doc_id)
        Backend-->>WebUI: 14. 202 Accepted (Shows "Processing" in UI)

        Redis->>IngWorker: 15. Ingestion Worker Picks Up Task
        IngWorker->>MinIO: 16. Fetch Raw PDF
        IngWorker->>OpenAI: 17. Compute Chunk Embeddings
        IngWorker->>Chroma: 18. Store Vectors in Collection (kb_id)
        IngWorker->>PG: 19. Save Chunks & Set Status = INDEXED
        WebUI->>Backend: 20. Poll/Refresh KB List -> Shows "Indexed"
    end
```

### Mode 1 Docker Compose Containers (`akvo-rag/docker-compose.dev.yml`)

| Service Name | Container Image / Source | Role in Standalone Mode 1 | Ports |
|---|---|---|---|
| `frontend` | `akvo-rag/frontend` (Next.js 14) | Admin Web Dashboard, Prompt Editor & Chat Playground | `3000:3000` |
| `backend` | `akvo-rag/backend` (FastAPI) | Auth, Admin REST APIs, and in-process RAG engine | `8000:8000` |
| `ingestion-worker` | `vector-kb` Celery Worker | Background PDF chunking and Chroma embedding | Internal |
| `postgres` | `postgres:17-alpine` | Users, prompt versions, apps, document records | `5432:5432` |
| `chromadb` | `chromadb/chroma:latest` | Vector collections (`kb_{id}`) | `8000:8000` |
| `minio` | `minio/minio:latest` | Object storage for uploaded PDF files | `9000:9000`, `9001:9001` |
| `redis` | `redis:7-alpine` | Task queue broker for document ingestion | `6379:6379` |

---

## 2. Mode 2 Sequence Diagram: Embedded `xxxconnect` (AgriConnect / WASHConnect)

> **Use Case:** Production partner deployments serving farmers and citizens over WhatsApp with sub-second response times, zero internal network hops, and in-process `akvo-rag-core` + `vector-kb-core` execution.

```mermaid
sequenceDiagram
    autonumber
    actor Farmer as Farmer / WhatsApp User
    actor Admin as Sector Admin / Agronomist

    box rgb(240, 248, 255) Host App Container AgriConnect / WASHConnect
        participant HostAPI as Host FastAPI<br/>(WhatsApp Webhook & Business Logic)
        participant RAGCore as akvo-rag-core<br/>(In-Process LangGraph & Prompts)
        participant VKB as vector-kb-core<br/>(In-Process ChromaRetriever)
    end

    box rgb(255, 250, 240) Background Celery Workers
        participant AppWorker as Host App Worker<br/>(Outbound WhatsApp Dispatcher)
        participant IngWorker as vector-kb Ingestion Worker<br/>(PDF Parse, Chunk, Embed)
    end

    box rgb(245, 245, 245) Datastores & Storage (Docker Compose)
        participant PG as PostgreSQL 17<br/>(Host DB + Prompts + KB Metadata)
        participant Chroma as ChromaDB<br/>(Vector Collections: kb_id)
        participant MinIO as MinIO (S3)<br/>(Raw Sector PDFs)
        participant Redis as Redis<br/>(Task Queues & Broker)
    end

    box rgb(245, 255, 245) External APIs
        participant WhatsApp as WhatsApp Cloud API
        participant OpenAI as OpenAI API<br/>(Embeddings & Chat Models)
    end

    %% FLOW A: LIVE IN-PROCESS CONVERSATIONAL TURN
    rect rgb(230, 242, 255)
        note over Farmer, OpenAI: FLOW A: Real-Time WhatsApp Turn (In-Process Execution)
        Farmer->>WhatsApp: 1. "How do I manage Avocado root rot?"
        WhatsApp->>HostAPI: 2. Webhook Event (POST /whatsapp/webhook)
        HostAPI->>PG: 3. Fetch Farmer Profile & Active Sector KBs (e.g. kb_ids: [1, 2])
        PG-->>HostAPI: Farmer Profile & KB Settings

        HostAPI->>RAGCore: 4. In-Process Call: await rag_engine.run(request, retriever=VKB)
        RAGCore->>RAGCore: 5. Compose Multi-Tier Prompt (Base + Sector + Partner Overlays)

        RAGCore->>VKB: 6. Direct Function Call: retriever.retrieve(query, kb_ids=[1, 2])
        VKB->>OpenAI: 7. Get Query Embedding (text-embedding-3-small)
        OpenAI-->>VKB: 1536-dim Query Vector
        VKB->>Chroma: 8. Direct Vector Search across kb_1 & kb_2
        Chroma-->>VKB: Return Top-K Ranked Context Chunks
        VKB-->>RAGCore: Return List[RetrievedChunk]

        RAGCore->>OpenAI: 9. LLM Answer Generation with Grounding & Citations (gpt-4o-mini)
        OpenAI-->>RAGCore: Generated Answer with strict [citation:N] references
        RAGCore-->>HostAPI: Return RAGResponse(answer, citations, grounded=True)

        HostAPI->>Redis: 10. Enqueue Outbound Message Task (outbound_messages)
        HostAPI-->>WhatsApp: 11. 200 OK (Immediate Webhook Ack in < 1s)

        Redis->>AppWorker: 12. App Worker Consumes Outbound Task
        AppWorker->>WhatsApp: 13. Send Formatted WhatsApp Message with Citations
        WhatsApp->>Farmer: 14. Farmer receives verified agronomy advice
    end

    %% FLOW B: SECTOR KB DOCUMENT INGESTION
    rect rgb(255, 243, 230)
        note over Admin, OpenAI: FLOW B: Sector Knowledge Base Document Ingestion
        Admin->>HostAPI: 15. Upload Sector PDF Manual (POST /admin/kb/{id}/documents)
        HostAPI->>MinIO: 16. Store Raw PDF (Bucket: documents/)
        HostAPI->>PG: 17. Insert Document Record (Status: PROCESSING)
        HostAPI->>Redis: 18. Enqueue Ingestion Task (process_document)
        HostAPI-->>Admin: 19. 202 Accepted (Upload Successful)

        Redis->>IngWorker: 20. vector-kb Ingestion Worker Picks Up Task
        IngWorker->>MinIO: 21. Download Raw PDF
        IngWorker->>OpenAI: 22. Generate Chunk Embeddings
        OpenAI-->>IngWorker: Return Chunk Vectors
        IngWorker->>Chroma: 23. Upsert Vectors into Collection (kb_id)
        IngWorker->>PG: 24. Save Chunks & Set Status = INDEXED
    end
```

### Mode 2 Docker Compose Containers (`xxxconnect/docker-compose.yml`)

| Service Name | Container Image / Source | Role in Embedded Mode 2 | Ports |
|---|---|---|---|
| `app` | `xxxconnect/backend` | FastAPI WhatsApp webhook handler with embedded `akvo-rag-core` and `vector-kb-core` | `8000:8000` |
| `app-worker` | `xxxconnect` Celery Worker | Outbound WhatsApp message dispatcher with automatic retries | Internal |
| `ingestion-worker` | `vector-kb` Celery Worker | Background sector document parser & embedder (from `vector-kb` repository) | Internal |
| `postgres` | `postgres:17-alpine` | Partner CRM data, farmer profiles, and KB metadata | `5432:5432` |
| `chromadb` | `chromadb/chroma:latest` | Vector collections for partner domain manuals | `8000:8000` |
| `minio` | `minio/minio:latest` | Object storage for partner PDFs | `9000:9000` |
| `redis` | `redis:7-alpine` | Celery broker for outbound WhatsApp & ingestion | `6379:6379` |

---

## 3. Key Architectural Benefits of Option C

1. **Exact Parity Between Modes:**
   - Both Mode 1 (Standalone Web UI) and Mode 2 (Embedded Host App) execute the **identical in-process engine** (`akvo-rag-core` + `vector-kb-core`), ensuring that prompt behavior in the playground matches WhatsApp production 100%.
2. **Zero Internal HTTP / FastMCP Latency:**
   - Vector retrieval is performed via direct in-memory Python function calls to ChromaDB (`< 100ms`), completely eliminating the 4 internal HTTP hops and FastMCP SSE streaming bottlenecks.
3. **Resilient Circuit Breaker:**
   - If ChromaDB or OpenAI experiences transient downtime, the in-process engine safely catches exceptions and returns a graceful fallback message without crashing WhatsApp turns or leaving users hanging.
