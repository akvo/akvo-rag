# Container-Based RAG Platform & Monorepo Consolidation LLD
**System Low-Level Design (LLD): Decoupled Multi-Container RAG Platform with Queue-Driven MCP Extensibility**

- **Document Identifier:** `LLD-002`
- **Target Repository:** `akvo-rag` (Consolidated Monorepo)
- **Author / Roles:** System Architect, Tech Leads, Engineering Management
- **Status:** APPROVED / READY FOR IMPLEMENTATION
- **Date:** 2026-09-01

---

## 1. Executive Summary & Management Directives

Based on architectural reviews and management directives, the RAG platform is transitioning to a **Container-Based Monorepo Architecture** with **Queue-Driven MCP Extensibility**:

```text
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ CONTAINER-BASED MONOREPO ARCHITECTURE (Option C Target)                                          │
│                                                                                                  │
│  ┌────────────────────────┐      ┌─────────────────────────┐      ┌───────────────────────────┐  │
│  │   akvo-rag-frontend    │      │    akvo-rag-backend     │      │       REDIS QUEUE         │  │
│  │      (Next.js 14)      │─────►│        (FastAPI)        │─────►│ • mcp:vector:requests     │  │
│  │ • Prompt & KB Web UI   │ HTTP │ • RAG LangGraph Orchestr│      │ • mcp:image:requests      │  │
│  │ • Chat Playground      │      │ • mcp_config Dispatcher │      │ • document_ingestion      │  │
│  └────────────────────────┘      └────────────┬────────────┘      └─────────────┬─────────────┘  │
│                                               │                                 │                │
│           ┌───────────────────────────────────┼─────────────────────────────────┼──────────┐     │
│           ▼                                   ▼                                 ▼          ▼     │
│  ┌─────────────────┐                 ┌─────────────────┐             ┌──────────────┐ ┌────────┐ │
│  │  PostgreSQL 17  │                 │      MinIO      │             │vector-kb-mcp │ │ Other  │ │
│  │ (Multi-Schema:  │                 │ (Object Storage:│             │  Container   │ │ MCPs   │ │
│  │  Core + VKB)    │                 │  documents/     │             │ (ChromaRetr) │ │(Image, │ │
│  └─────────────────┘                 └─────────────────┘             └──────┬───────┘ │Weathr) │ │
│                                                                             │         └────────┘ │
│                                                                             ▼                    │
│                                                                      ┌──────────────┐            │
│                                                                      │   ChromaDB   │            │
│                                                                      │ (Vector Store│            │
│                                                                      └──────────────┘            │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Core Architectural Decisions:
1. **Discontinuation of Standalone `vector-knowledge-base-mcp-server` Repo:**
   - All document ingestion, chunking, OpenAI embeddings, and ChromaDB retrieval code is migrated directly into `akvo-rag/vector-kb-mcp/`.
2. **Container-Based Microservice Isolation:**
   - `akvo-rag-backend`, `akvo-rag-frontend`, `vector-kb-mcp`, and any `other_mcp` (e.g. image recognition, weather) run as dedicated, isolated Docker containers within the same Docker Compose / Kubernetes network.
3. **Replacement of HTTP/SSE MCP Calls with High-Speed Redis Queue Request-Reply:**
   - Internal HTTP/HTTPS FastMCP streaming hops between `akvo-rag` and MCP servers are eliminated.
   - Requests are published to designated Redis queues (`mcp:vector:requests`) with correlation IDs, returning results in $< 5\text{ms}$.
4. **Declarative MCP Extensibility via `mcp_config`:**
   - A static configuration file (`mcp_config.json` / `mcp_config.yaml`) defines all active MCP tools and their request/reply queues.
   - New external tools (e.g., Image Recognition, Weather, Sensor APIs) can be attached dynamically as independent containers without modifying the core RAG engine.
5. **Unified Data Layer (PostgreSQL 17 + MinIO + ChromaDB):**
   - Single PostgreSQL 17 database replaces MySQL and handles all tables (`users`, `apps`, `api_keys`, `prompts`, `knowledge_bases`, `documents`, `document_chunks`).
   - MinIO provides dedicated S3-compatible document storage.
   - ChromaDB serves as the dedicated vector database.

> [!IMPORTANT]
> **HOST APPLICATION STABILITY MANDATE (Zero Regressions for AgriConnect & CoM):**
> All endpoints currently used by **AgriConnect** or **CoM Tenant** (e.g. `/api/v1/chat`, `/api/v1/knowledge-bases`, `/api/v1/knowledge-bases/{id}/documents`, `/api/v1/knowledge-bases/{id}/documents/upload`) MUST remain **100% available and backwards-compatible** with identical request and response schemas. Small configuration adjustments in the AgriConnect repo are fine, but breaking API alterations are strictly avoided to ensure uninterrupted service across live deployments.

---

## 2. System Architecture Blueprint

This section provides 4 comprehensive, color-coded Mermaid sequence diagrams covering every standalone and host-embedded operational mode.

---

### 2.1 Mode 1: `akvo-rag` + `vector-kb-mcp` Only (Base RAG Platform)
*Standalone deployment with Next.js web playground, FastAPI RAG backend, document ingestion, and internal queue-backed vector retrieval.*

```mermaid
sequenceDiagram
    autonumber
    
    box rgb(240, 248, 255) Web Client
        actor User as Admin / Developer<br/>(Next.js Web UI :3000)
    end
    
    box rgb(255, 250, 240) Core Akvo-RAG Backend
        participant Backend as akvo-rag-backend<br/>(FastAPI :8000)
        participant PG as PostgreSQL 17<br/>(Users, Prompts)
    end
    
    box rgb(255, 245, 245) Message Broker
        participant Redis as Redis Queue<br/>(RPC & Tasks :6379)
    end
    
    box rgb(245, 255, 245) Vector Microservice
        participant VectorMCP as vector-kb-mcp<br/>(Vector Worker & Ingestion)
    end
    
    box rgb(245, 245, 245) Datastores & AI APIs
        participant Chroma as ChromaDB<br/>(Vector DB :8000)
        participant MinIO as MinIO<br/>(PDF Storage :9000)
        participant OpenAI as OpenAI API<br/>(Embeddings & LLM)
    end

    %% FLOW 1: RAG CHAT
    rect rgb(230, 242, 255)
        note over User, OpenAI: FLOW 1: Live Chat Query with Queue-Backed Vector Search
        User->>Backend: 1. POST /api/chat { query, kb_ids: [1] }
        Backend->>PG: 2. Load Prompt Template (alembic_version)
        
        critical Queue Request-Reply (< 5ms)
            Backend->>Redis: 3. RPUSH mcp:vector:requests { tool: "query_knowledge_base", correlation_id, query, kb_ids }
            Redis->>VectorMCP: 4. BLPOP mcp:vector:requests
            VectorMCP->>OpenAI: 5. Generate Query Vector (text-embedding-3-small)
            OpenAI-->>VectorMCP: Return Vector
            VectorMCP->>Chroma: 6. Search Collection: kb_1
            Chroma-->>VectorMCP: Top Chunks
            VectorMCP->>Redis: 7. RPUSH mcp:vector:responses:{correlation_id} { chunks }
            Redis-->>Backend: 8. BLPOP Return Chunks
        end
        
        Backend->>OpenAI: 9. Generate Grounded Answer (gpt-4o-mini)
        OpenAI-->>Backend: Grounded Answer with Citations
        Backend-->>User: 10. Stream / Return RAGResponse
    end

    %% FLOW 2: GET DOCUMENT LIST
    rect rgb(255, 255, 240)
        note over User, VectorMCP: FLOW 2: Get Document List in Knowledge Base
        User->>Backend: 11. GET /api/v1/knowledge-bases/1/documents
        Backend->>Redis: 12. RPUSH mcp:vector:requests { tool: "list_documents", kb_id: 1, correlation_id: "xyz" }
        Redis->>VectorMCP: 13. BLPOP mcp:vector:requests
        VectorMCP->>PG: 14. SELECT * FROM vkb_documents WHERE kb_id = 1
        VectorMCP->>Redis: 15. RPUSH mcp:vector:responses:xyz { documents: [...] }
        Redis-->>Backend: 16. BLPOP Return Document List (< 5ms)
        Backend-->>User: 17. 200 OK [ { id, title, status, doc_version, effective_date }, ... ]
    end

    %% FLOW 3: DOCUMENT INGESTION
    rect rgb(240, 255, 240)
        note over User, OpenAI: FLOW 3: Asynchronous PDF Document Ingestion
        User->>Backend: 18. Upload PDF (POST /api/v1/knowledge-bases/1/documents/upload)
        Backend->>MinIO: 19. Save Raw PDF in Bucket: documents/
        Backend->>PG: 20. Insert Document Row (Status: PROCESSING)
        Backend->>Redis: 21. RPUSH document_ingestion { document_id, kb_id: 1 }
        Backend-->>User: 22. 202 Accepted { document_id, status: "PROCESSING" }
        
        Redis->>VectorMCP: 23. Ingest Task Consumed from document_ingestion
        VectorMCP->>MinIO: 24. Fetch Raw PDF
        VectorMCP->>VectorMCP: 25. Parse Pages, OCR & Chunk Text
        VectorMCP->>OpenAI: 26. Batch Compute Chunk Embeddings (1536-dim)
        OpenAI-->>VectorMCP: Chunk Vectors
        VectorMCP->>Chroma: 27. Upsert Vectors to kb_1
        VectorMCP->>PG: 28. Save Chunk Records & Update Status = INDEXED (alembic_version_vkb)
        User->>Backend: 29. Poll Document Status -> Shows "INDEXED"
    end
```

---

### 2.2 Mode 2: `akvo-rag` + `vector-kb-mcp` + `other-mcp` (Multi-MCP Extended Platform)
*Standalone deployment dynamically executing multiple MCPs (Vector + Image Recognition) via `mcp_config.json`, plus document management.*

```mermaid
sequenceDiagram
    autonumber
    
    box rgb(240, 248, 255) Web Client
        actor User as Admin / Developer<br/>(Next.js Web UI :3000)
    end
    
    box rgb(255, 250, 240) Core Akvo-RAG Backend
        participant Backend as akvo-rag-backend<br/>(FastAPI :8000)
        participant PG as PostgreSQL 17<br/>(Users, Prompts)
    end
    
    box rgb(255, 245, 245) Message Broker
        participant Redis as Redis Queue<br/>(RPC Broker :6379)
    end
    
    box rgb(245, 255, 245) Pluggable MCP Tier
        participant VectorMCP as vector-kb-mcp<br/>(Vector Retrieval & Ingestion)
        participant OtherMCP as other-mcp<br/>(image_recognition / weather)
    end
    
    box rgb(245, 245, 245) Datastores & AI APIs
        participant Chroma as ChromaDB<br/>(Vector DB :8000)
        participant MinIO as MinIO<br/>(PDF Storage :9000)
        participant OpenAI as OpenAI API<br/>(Embeddings & LLM)
    end

    %% FLOW 1: MULTI-MCP ORCHESTRATION
    rect rgb(230, 242, 255)
        note over User, OpenAI: FLOW 1: Composite Query (Vector Retrieval + Image Analysis)
        User->>Backend: 1. POST /api/chat { query, image_url, kb_ids: [1] }
        Backend->>PG: 2. Load Prompts
        
        par Parallel Queue MCP Invocations via mcp_config.json
            Backend->>Redis: 3a. RPUSH mcp:vector:requests { correlation_id_1, query, kb_ids }
            Redis->>VectorMCP: 4a. BLPOP Request
            VectorMCP->>Chroma: 5a. Query Vector Chunks
            Chroma-->>VectorMCP: Chunks
            VectorMCP->>Redis: 6a. RPUSH mcp:vector:responses:{id_1}
        and
            Backend->>Redis: 3b. RPUSH mcp:image:requests { correlation_id_2, image_url }
            Redis->>OtherMCP: 4b. BLPOP Request
            OtherMCP->>OtherMCP: 5b. Analyze Image Features
            OtherMCP->>Redis: 6b. RPUSH mcp:image:responses:{id_2}
        end
        
        Redis-->>Backend: 7. Collect Chunks & Image Diagnostics
        Backend->>OpenAI: 8. Synthesize Grounded Composite Response
        OpenAI-->>Backend: Grounded Answer
        Backend-->>User: 9. Return Multimodal RAG Response
    end

    %% FLOW 2: DOCUMENT INGESTION & LISTING
    rect rgb(240, 255, 240)
        note over User, MinIO: FLOW 2: Document Ingestion & Listing
        User->>Backend: 10. POST /api/v1/knowledge-bases/1/documents/upload (Multipart PDF)
        Backend->>MinIO: 11. Save PDF in documents/
        Backend->>Redis: 12. RPUSH document_ingestion { document_id, kb_id: 1 }
        Backend-->>User: 13. 202 Accepted
        
        Redis->>VectorMCP: 14. Ingestion Worker processes PDF
        VectorMCP->>MinIO: 15. Fetch File
        VectorMCP->>OpenAI: 16. Batch Embeddings
        VectorMCP->>Chroma: 17. Upsert to Chroma
        VectorMCP->>VectorMCP: 18. Update Status = INDEXED
        
        User->>Backend: 19. GET /api/v1/knowledge-bases/1/documents
        Backend->>Redis: 20. RPUSH mcp:vector:requests { tool: "list_documents", kb_id: 1 }
        Redis->>VectorMCP: 21. Query vkb_documents
        VectorMCP->>Redis: 22. Return Documents
        Redis-->>Backend: 23. Return Documents List
        Backend-->>User: 24. 200 OK [ { id, title, status }, ... ]
    end
```

---

### 2.3 Mode 3: Host (`xxxconnect`) + `akvo-rag` + `vector-kb-mcp`
*Embedded WhatsApp CRM integration: Meta Cloud API webhook, FastAPI RAG REST invocation, queue vector search, and partner document management.*

```mermaid
sequenceDiagram
    autonumber
    
    box rgb(240, 248, 255) WhatsApp Farmers & Host Admin
        actor Farmer as Farmer / Citizen<br/>(WhatsApp Mobile App)
        actor HostAdmin as Extension Officer / Admin<br/>(Host Web Portal)
        participant WA as Meta WhatsApp Cloud API<br/>(graph.facebook.com:443)
    end
    
    box rgb(255, 240, 240) Partner Host Application
        participant HostApp as xxxconnect Host Backend<br/>(WhatsApp Webhook Router)
        participant HostWorker as xxxconnect Celery Worker<br/>(Outbound Message Dispatcher)
    end
    
    box rgb(255, 250, 240) Akvo-RAG Microservice
        participant Backend as akvo-rag-backend<br/>(FastAPI API Gateway :8000)
        participant Redis as Redis Queue<br/>(Request-Reply Broker :6379)
        participant VectorMCP as vector-kb-mcp<br/>(Vector Retrieval & Ingestion)
    end
    
    box rgb(245, 245, 245) Datastores & AI APIs
        participant Chroma as ChromaDB<br/>(Vector Store :8000)
        participant MinIO as MinIO<br/>(PDF Storage :9000)
        participant OpenAI as OpenAI API<br/>(LLM Generation)
    end

    %% FLOW 1: INBOUND WHATSAPP CHAT
    rect rgb(230, 242, 255)
        note over Farmer, OpenAI: FLOW 1: Host Inbound Flow & Sub-Second RAG Generation
        Farmer->>WA: 1. WhatsApp Text Message ("How to treat avocado root rot?")
        WA->>HostApp: 2. Webhook Event (POST /whatsapp/webhook)
        HostApp-->>WA: 3. 200 OK (Immediate Webhook Ack in < 1s)
        
        HostApp->>Backend: 4. POST /api/v1/chat { query, kb_ids: [1] } (Intra-cluster REST: ~5ms)
        
        critical Akvo-RAG Internal Queue Retrieval (< 5ms)
            Backend->>Redis: 5. RPUSH mcp:vector:requests { tool: "query_knowledge_base", correlation_id, query, kb_ids }
            Redis->>VectorMCP: 6. BLPOP Request
            VectorMCP->>Chroma: 7. Cosine Search on Avocado Manuals (kb_1)
            Chroma-->>VectorMCP: Agronomy Context Chunks
            VectorMCP->>Redis: 8. RPUSH mcp:vector:responses:{correlation_id}
            Redis-->>Backend: 9. Return Context Chunks
        end
        
        Backend->>OpenAI: 10. Generate Grounded Farmer Answer (gpt-4o-mini)
        OpenAI-->>Backend: Agronomy Advice with Citations
        Backend-->>HostApp: 11. Return RAGResponse { answer, citations }
        
        HostApp->>HostWorker: 12. Enqueue Outbound WhatsApp Task
        HostWorker->>WA: 13. POST /v18.0/messages { to: Farmer, text: answer }
        WA->>Farmer: 14. Deliver WhatsApp Response to Farmer
    end

    %% FLOW 2: HOST DOCUMENT MANAGEMENT
    rect rgb(240, 255, 240)
        note over HostAdmin, OpenAI: FLOW 2: Host Partner Document Upload & KB Listing
        HostAdmin->>HostApp: 15. Upload New National Farming Standard PDF
        HostApp->>Backend: 16. POST /api/v1/knowledge-bases/1/documents/upload (Multipart PDF)
        Backend->>MinIO: 17. Save Raw File to documents/avocado_standard_2024.pdf
        Backend->>Redis: 18. RPUSH document_ingestion { document_id: "doc-50", kb_id: 1 }
        Backend-->>HostApp: 19. 202 Accepted { document_id: "doc-50", status: "PROCESSING" }
        
        Redis->>VectorMCP: 20. Ingestion Consumer pulls task
        VectorMCP->>MinIO: 21. Download PDF
        VectorMCP->>VectorMCP: 22. Parse & Chunk Text
        VectorMCP->>OpenAI: 23. Compute Vectors (1536-dim)
        VectorMCP->>Chroma: 24. Upsert to Chroma Collection kb_1
        VectorMCP->>VectorMCP: 25. Mark Document Status = INDEXED
        
        HostAdmin->>HostApp: 26. View Updated Document List
        HostApp->>Backend: 27. GET /api/v1/knowledge-bases/1/documents
        Backend->>Redis: 28. RPUSH mcp:vector:requests { tool: "list_documents", kb_id: 1 }
        Redis->>VectorMCP: 29. Query vkb_documents
        VectorMCP->>Redis: 30. Return Documents Array
        Redis-->>Backend: 31. Return Documents List
        Backend-->>HostApp: 32. 200 OK [ { id: "doc-50", title: "avocado_standard_2024.pdf", status: "INDEXED" }, ... ]
    end
```

---

### 2.4 Mode 4: Host (`xxxconnect`) + `akvo-rag` + `vector-kb-mcp` + `other-mcp`
*Full multimodal WhatsApp Turn: Farmer uploads crop disease photo + text query; system concurrently invokes Vector MCP (manuals) & Vision MCP (leaf diagnosis), plus document lifecycle.*

```mermaid
sequenceDiagram
    autonumber
    
    box rgb(240, 248, 255) WhatsApp Farmers & Host Admin
        actor Farmer as Farmer / Citizen<br/>(WhatsApp Mobile App)
        actor HostAdmin as Extension Officer / Admin<br/>(Host Web Portal)
        participant WA as Meta WhatsApp Cloud API<br/>(graph.facebook.com:443)
    end
    
    box rgb(255, 240, 240) Partner Host Application
        participant HostApp as xxxconnect Host Backend<br/>(WhatsApp Webhook Router)
        participant HostWorker as xxxconnect Celery Worker<br/>(Outbound Message Dispatcher)
    end
    
    box rgb(255, 250, 240) Akvo-RAG Microservice
        participant Backend as akvo-rag-backend<br/>(FastAPI API Gateway :8000)
        participant Redis as Redis Queue<br/>(Request-Reply Broker :6379)
        participant VectorMCP as vector-kb-mcp<br/>(Vector Retrieval & Ingestion)
        participant OtherMCP as other-mcp<br/>(image_recognition)
    end
    
    box rgb(245, 245, 245) Datastores & AI APIs
        participant Chroma as ChromaDB<br/>(Vector Store :8000)
        participant MinIO as MinIO<br/>(PDF Storage :9000)
        participant OpenAI as OpenAI API<br/>(LLM Generation)
    end

    %% FLOW 1: INBOUND MULTIMODAL WHATSAPP
    rect rgb(230, 242, 255)
        note over Farmer, OpenAI: FLOW 1: Host Multimodal Turn (Photo + Text Advice)
        Farmer->>WA: 1. Send Photo of Diseased Leaf + Text ("What is attacking my crop?")
        WA->>HostApp: 2. Webhook Event with media_url
        HostApp-->>WA: 3. 200 OK Ack
        
        HostApp->>Backend: 4. POST /api/v1/chat { query, image_url: media_url, kb_ids: [1] }
        
        par Parallel Queue Dispatch
            Backend->>Redis: 5a. RPUSH mcp:vector:requests { correlation_id_1, query, kb_ids }
            Redis->>VectorMCP: 6a. Search Sector Crop Manuals
            VectorMCP->>Chroma: 7a. Query Vectors
            Chroma-->>VectorMCP: Relevant Treatment Chunks
            VectorMCP->>Redis: 8a. Reply Chunks
        and
            Backend->>Redis: 5b. RPUSH mcp:image:requests { correlation_id_2, image_url }
            Redis->>OtherMCP: 6b. Run Pest/Disease Vision Classifier
            OtherMCP-->>OtherMCP: 7b. Identify "Anthracnose Fungal Lesions (96% conf)"
            OtherMCP->>Redis: 8b. Reply Vision Diagnosis
        end
        
        Redis-->>Backend: 9. Collect Vision Diagnosis + Manual Treatment Chunks
        Backend->>OpenAI: 10. Generate Comprehensive Grounded Action Plan
        OpenAI-->>Backend: Complete Agronomy Diagnosis & Remediation Advice
        Backend-->>HostApp: 11. Return RAGResponse { answer, citations }
        
        HostApp->>HostWorker: 12. Enqueue Outbound WhatsApp Task
        HostWorker->>WA: 13. POST Formatted WhatsApp Message
        WA->>Farmer: 14. Farmer receives verified diagnosis and treatment steps
    end

    %% FLOW 2: HOST INGESTION & DOCUMENT LISTING
    rect rgb(240, 255, 240)
        note over HostAdmin, OpenAI: FLOW 2: Host Partner Ingestion & Document Verification
        HostAdmin->>HostApp: 15. Upload Pest Identification Manual PDF
        HostApp->>Backend: 16. POST /api/v1/knowledge-bases/1/documents/upload
        Backend->>MinIO: 17. Store Raw File in documents/
        Backend->>Redis: 18. RPUSH document_ingestion { document_id: "doc-88", kb_id: 1 }
        Backend-->>HostApp: 19. 202 Accepted { document_id: "doc-88", status: "PROCESSING" }
        
        Redis->>VectorMCP: 20. Process Document & Extract Chunks
        VectorMCP->>OpenAI: 21. Compute Embeddings
        VectorMCP->>Chroma: 22. Index in Chroma Collection kb_1
        VectorMCP->>VectorMCP: 23. Update Status = INDEXED
        
        HostAdmin->>HostApp: 24. Fetch Knowledge Base Document List
        HostApp->>Backend: 25. GET /api/v1/knowledge-bases/1/documents
        Backend->>Redis: 26. RPUSH mcp:vector:requests { tool: "list_documents", kb_id: 1 }
        Redis->>VectorMCP: 27. Query vkb_documents
        VectorMCP->>Redis: 28. Return Documents Array
        Redis-->>Backend: 29. Return Documents List
        Backend-->>HostApp: 30. 200 OK [ { id: "doc-88", title: "Pest Manual.pdf", status: "INDEXED" }, ... ]
    end
```

---

## 3. Container Topology & Service Breakdown

The Docker Compose file (`docker-compose.yml`) defines 7 primary containers:

| Container Name | Build / Image | Option C Role | Port Mapping | Storage Volumes |
|---|---|---|---|---|
| **`frontend`** | `akvo-rag/frontend` (Next.js 14) | Admin Web Dashboard, Prompt Editor, Chat Playground UI | `3000:3000` | Code bind mount |
| **`backend`** | `akvo-rag/backend` (FastAPI) | Core API, Auth, LangGraph RAG Workflow, `mcp_config` Dispatcher | `8000:8000` | Code bind mount |
| **`vector-kb-mcp`** | `akvo-rag/vector-kb-mcp` | Vector similarity search worker and PDF document ingestion worker | Internal | Code bind mount |
| **`postgres`** | `postgres:17-alpine` | Unified relational database for users, prompts, KB metadata, and document chunks | `5432:5432` | `postgres_data:/var/lib/postgresql/data` |
| **`chromadb`** | `chromadb/chroma:latest` | Vector database storing embeddings per knowledge base collection | `8000:8000` | `chroma_data:/chroma/chroma` |
| **`minio`** | `minio/minio:latest` | S3-compatible object storage for uploaded PDF files | `9000:9000`, `9001:9001` | `minio_data:/data` |
| **`redis`** | `redis:7-alpine` | Ultra-fast message broker for MCP request-reply RPC and ingestion queues | `6379:6379` | `redis_data:/data` |

---

## 4. `mcp_config` & Queue-Based Request-Reply Dispatcher

### 4.1 Configuration Schema (`mcp_config.json`)

The `mcp_config.json` file is mounted into `akvo-rag-backend` at startup:

```json
{
  "mcp_servers": [
    {
      "id": 1,
      "mcp_name": "vector",
      "request_queue": "mcp:vector:requests",
      "response_prefix": "mcp:vector:responses",
      "timeout_ms": 5000,
      "tools": [
        {
          "name": "query_knowledge_base",
          "description": "Perform semantic similarity search over document chunks in target knowledge bases",
          "parameters": {
            "query": "string",
            "kb_ids": "array[integer]",
            "top_k": "integer",
            "score_threshold": "number"
          }
        }
      ],
      "enabled": true
    },
    {
      "id": 2,
      "mcp_name": "image_recognition",
      "request_queue": "mcp:image:requests",
      "response_prefix": "mcp:image:responses",
      "timeout_ms": 10000,
      "tools": [
        {
          "name": "analyze_crop_image",
          "description": "Detect pest and disease symptoms from uploaded plant photos",
          "parameters": {
            "image_url": "string",
            "crop_type": "string"
          }
        }
      ],
      "enabled": false
    }
  ]
}
```

### 4.2 Ultra-Fast Queue Request-Reply Protocol (Correlation ID)

```mermaid
sequenceDiagram
    autonumber
    participant RAG as akvo-rag-backend (FastAPI)
    participant Redis as Redis Queue Broker
    participant Worker as vector-kb-mcp Container
    participant Chroma as ChromaDB

    Note over RAG, Worker: Step 1: Dispatch Tool Request
    RAG->>RAG: Generate correlation_id = uuid4()
    RAG->>Redis: RPUSH mcp:vector:requests { correlation_id, tool, input }
    
    Note over RAG, Worker: Step 2: Worker Processing
    Redis->>Worker: BLPOP mcp:vector:requests
    Worker->>Chroma: Query Vector Collection (kb_ids: [1, 2])
    Chroma-->>Worker: Return Top Chunks
    
    Note over Worker, RAG: Step 3: Reply via Correlation Key
    Worker->>Redis: RPUSH mcp:vector:responses:{correlation_id} { status: 'ok', data: chunks }
    Worker->>Redis: EXPIRE mcp:vector:responses:{correlation_id} 60
    
    Note over RAG, Redis: Step 4: Await & Return Result
    RAG->>Redis: BLPOP mcp:vector:responses:{correlation_id} (timeout=5s)
    Redis-->>RAG: Return Chunks (< 5ms queue overhead)
    RAG->>RAG: Continue LangGraph Answer Generation
```

### 4.3 Python MCP Queue Dispatcher Implementation

```python
# backend/app/services/mcp_queue_dispatcher.py
import json
import uuid
import asyncio
import redis.asyncio as redis
from typing import Dict, Any, Optional

class MCPQueueDispatcher:
    def __init__(self, redis_url: str, config_path: str = "mcp_config.json"):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        with open(config_path, "r") as f:
            self.config = json.load(f)
        self.servers = {s["mcp_name"]: s for s in self.config.get("mcp_servers", []) if s.get("enabled")}

    async def call_tool(self, mcp_name: str, tool_name: str, arguments: Dict[str, Any], timeout_seconds: float = 5.0) -> Dict[str, Any]:
        server = self.servers.get(mcp_name)
        if not server:
            raise ValueError(f"MCP Server '{mcp_name}' is not configured or disabled.")

        correlation_id = str(uuid.uuid4())
        request_queue = server["request_queue"]
        response_queue = f"{server['response_prefix']}:{correlation_id}"

        payload = {
            "correlation_id": correlation_id,
            "tool": tool_name,
            "arguments": arguments,
            "response_queue": response_queue
        }

        # 1. Push request to worker queue
        await self.redis.rpush(request_queue, json.dumps(payload))

        # 2. Wait for response on unique correlation key
        raw_resp = await self.redis.blpop(response_queue, timeout=int(timeout_seconds))
        if not raw_resp:
            raise TimeoutError(f"MCP tool '{mcp_name}.{tool_name}' timed out after {timeout_seconds}s")

        _, data = raw_resp
        return json.loads(data)
```

### 4.4 Scoping Agent Removal & Latency Optimization

In the legacy system, `ScopingAgent` (`backend/app/services/scoping_agent.py`) invoked an LLM to choose which MCP tool or Knowledge Base ID to call. This introduced major drawbacks:
1. **Redundant LLM Call:** Added **1.5s–3.0s of latency** and extra OpenAI API cost per user question.
2. **Discarded Output:** Partner applications (e.g. `AgriConnect`, Next.js UI) already explicitly send the target `knowledge_base_ids: [1, 2]` in the request payload.

#### Deterministic Direct Graph Routing
In the new Container-Based Option C LangGraph workflow, `scoping_node` is **removed from the default path**. The execution flow transitions directly:
$$\text{Classify Intent Node} \longrightarrow \text{Contextualize Node} \longrightarrow \text{Queue Vector Retrieval (Redis RPC)} \longrightarrow \text{Grounded Answer Node}$$

This eliminates 1 full LLM roundtrip per question while maintaining 100% retrieval accuracy.

### 4.5 Legacy Code Purge & Clean Deletion Plan

To ensure zero technical debt, the following legacy components will be completely deleted from `akvo-rag`:
1. **Legacy FastMCP HTTP Client:** `backend/mcp_clients/fastmcp_client_service.py` & `mcp_discovery_manager.py` (Replaced by `MCPQueueDispatcher`).
2. **Legacy Celery & RabbitMQ Infrastructure:** `backend/app/celery_app.py`, `backend/app/tasks/upload_task.py`, and `backend/app/tasks/chat_task.py` (Replaced by Native Async Redis Workers).
3. **Hardcoded MCP Configs:** `backend/mcp_clients/mcp_servers_config.py` (Replaced by `mcp_config.json`).

---

## 5. Repository Consolidation Plan (`vector-knowledge-base-mcp-server` $\rightarrow$ `akvo-rag`)

### 5.1 Monorepo Folder Structure

```text
akvo-rag/
├── backend/                  # FastAPI Core Backend & LangGraph RAG
│   ├── app/
│   │   ├── api/              # FastAPI REST & SSE endpoints
│   │   ├── core/             # Config & Security
│   │   ├── models/           # Core Models (Users, Apps, ApiKeys, Prompts, Chats)
│   │   ├── services/         # RAG LangGraph & Prompt Services
│   │   │   └── mcp_queue_dispatcher.py # Dynamic Queue-backed MCP caller
│   │   └── seeder/           # Seed admin, prompts
│   ├── alembic/              # Core Alembic Migrations (version_table = 'alembic_version')
│   └── mcp_config.json       # Static MCP configuration file
├── frontend/                 # Next.js 14 Web Dashboard & Chat Playground
├── vector-kb-mcp/            # Merged Vector MCP Container (Self-Contained Microservice)
│   ├── Dockerfile            # Container build for vector-kb-mcp
│   ├── requirements.txt      # PDF parsing & ChromaDB dependencies
│   ├── main.py               # Redis Queue Worker entrypoint
│   ├── alembic/              # Vector-KB Alembic Migrations (version_table = 'alembic_version_vkb')
│   ├── models/               # Vector-KB Models (KnowledgeBase, Document, DocumentChunk)
│   ├── parser/               # PDF, DOCX, OCR extraction
│   ├── chunker/              # Token chunking & metadata enrichment
│   └── retriever/            # Direct ChromaDB vector querying
├── other-mcp/                # (Optional) Future external/internal MCP container (e.g. image-recognition)
└── docker-compose.yml        # Complete 7-container local composition
```

### 5.2 Discontinuation & Porting Checklist
1. Copy `vector-knowledge-base-mcp-server/main/app/services/` (document parsers, chunkers, text extractors) directly into `akvo-rag/vector-kb-mcp/`.
2. Port `knowledge_bases`, `documents`, and `document_chunks` models directly from `vector-knowledge-base-mcp-server` into `akvo-rag/vector-kb-mcp/models/`.
3. Port existing Vector-KB migrations into `akvo-rag/vector-kb-mcp/alembic/` with `version_table = "alembic_version_vkb"`.
4. Convert the FastMCP HTTP listener into a high-performance **Redis Queue Worker** (`vector-kb-mcp/main.py`) that listens on `mcp:vector:requests`.
5. Archive `vector-knowledge-base-mcp-server` repository in GitHub upon cutover.

---

## 6. Database Consolidation & Multi-Tenant Migration (PostgreSQL 17)

### 6.1 Service-Owned Schema Ownership & Alembic Version Isolation

Both `backend` and `vector-kb-mcp` connect to the same consolidated **PostgreSQL 17** database instance, but each service owns its own tables and migration revision tree:

```text
Consolidated PostgreSQL 17 Database
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. Core Akvo-RAG Schema (Managed by backend/alembic/ -> version_table: alembic_version)│
│    • users, apps, api_keys, prompt_definitions, prompt_versions, chats, chat_messages  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. Vector-KB Schema (Managed by vector-kb-mcp/alembic/ -> version_table: alembic_version_vkb)│
│    • knowledge_bases, documents, document_chunks                                       │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Why Service-Owned Migrations?
1. **True Container Autonomy:** `vector-kb-mcp` is 100% self-contained. Schema changes to parsing, chunking, or metadata columns are managed entirely within `vector-kb-mcp/` without modifying `backend/`.
2. **Pluggable Blueprint for Future MCPs:** Any new MCP (e.g. `image-recognition-mcp` or `weather-mcp`) can follow the exact same pattern with its own `img_` table prefix and `alembic_version_img` table.
3. **Independent Startup Lifecycle:**
   - On boot, `akvo-rag-backend` executes: `alembic -c alembic.ini upgrade head`
   - On boot, `vector-kb-mcp` executes: `alembic -c alembic.ini upgrade head`
   - Since each uses a dedicated `version_table`, they never conflict or overwrite each other.

### 6.2 Schema Registry

```mermaid
erDiagram
    USERS ||--o{ CHATS : owns
    APPS ||--o{ API_KEYS : has
    APPS ||--o{ CHATS : records
    PROMPT_DEFINITIONS ||--o{ PROMPT_VERSIONS : tracks
    
    KNOWLEDGE_BASES ||--o{ DOCUMENTS : contains
    DOCUMENTS ||--o{ DOCUMENT_CHUNKS : splits
    
    USERS {
        int id PK
        string email
        string hashed_password
        string role
    }
    PROMPT_DEFINITIONS {
        int id PK
        string name
        string prompt_type
    }
    KNOWLEDGE_BASES {
        int id PK
        string name
        string description
        boolean is_active
    }
    DOCUMENTS {
        string id PK
        int kb_id FK
        string title
        string file_path
        string status
    }
    DOCUMENT_CHUNKS {
        string id PK
        string document_id FK
        int chunk_index
        text content
        json metadata_
    }
```

### 6.3 Automated Legacy Data Migration Script (`migrate_legacy_to_consolidated_postgres.py`)

A single Python CLI command extracts all data from legacy MySQL 8 and legacy `vector-knowledge-base-mcp-server` PostgreSQL and populates the consolidated PostgreSQL 17 instance:

```bash
python -m app.scripts.migrate_legacy_to_consolidated_postgres \
  --mysql-url "mysql+pymysql://user:pass@mysql:3306/akvo_rag" \
  --legacy-pg-url "postgresql://user:pass@legacy_vkb:5432/vector_kb" \
  --target-pg-url "postgresql+asyncpg://postgres:postgres@postgres:5432/akvo_rag"
```

---

## 7. Runtime Interaction Sequence Diagrams

### 7.1 Real-Time Conversational Turn with Queue-Backed Vector Retrieval

```mermaid
sequenceDiagram
    autonumber
    actor User as User / WhatsApp / Web
    participant Backend as akvo-rag-backend (FastAPI)
    participant Redis as Redis Queue (Broker)
    participant VectorMCP as vector-kb-mcp Container
    participant Chroma as ChromaDB
    participant OpenAI as OpenAI API

    User->>Backend: 1. POST /api/chat { query, kb_ids: [1, 2] }
    Backend->>Backend: 2. Load Prompts from PostgreSQL 17
    
    critical Queue-Backed Vector Retrieval
        Backend->>Redis: 3. RPUSH mcp:vector:requests { correlation_id: 'abc-123', tool: 'query_knowledge_base', kb_ids: [1, 2], query }
        Redis->>VectorMCP: 4. BLPOP mcp:vector:requests
        VectorMCP->>OpenAI: 5. Generate Query Embedding (text-embedding-3-small)
        OpenAI-->>VectorMCP: Return 1536-dim Vector
        VectorMCP->>Chroma: 6. Parallel Query Collections: kb_1, kb_2
        Chroma-->>VectorMCP: Return Ranked Document Chunks
        VectorMCP->>Redis: 7. RPUSH mcp:vector:responses:abc-123 { chunks }
        Redis-->>Backend: 8. BLPOP Return Chunks (< 5ms latency)
    end
    
    Backend->>OpenAI: 9. LLM Grounded Answer Generation (gpt-4o-mini)
    OpenAI-->>Backend: Return Answer with [citation:N] references
    Backend-->>User: 10. Return RAGResponse { answer, citations, grounded: true }
```

### 7.2 Asynchronous Document Ingestion Flow

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Admin / Manager
    participant Frontend as akvo-rag-frontend (Next.js)
    participant Backend as akvo-rag-backend (FastAPI)
    participant MinIO as MinIO Object Storage
    participant PG as PostgreSQL 17
    participant Redis as Redis Queue
    participant VectorMCP as vector-kb-mcp Container
    participant Chroma as ChromaDB
    participant OpenAI as OpenAI API

    Admin->>Frontend: 1. Upload PDF Manual
    Frontend->>Backend: 2. POST /api/v1/knowledge-bases/{id}/documents (Multipart)
    Backend->>MinIO: 3. Save Raw PDF to Bucket: documents/
    Backend->>PG: 4. Insert Record (Status: PROCESSING)
    Backend->>Redis: 5. RPUSH document_ingestion { document_id, kb_id }
    Backend-->>Frontend: 6. 202 Accepted (Shows "Processing" in UI)
    
    Redis->>VectorMCP: 7. Worker Consumes Task from document_ingestion
    VectorMCP->>MinIO: 8. Download Raw PDF File
    VectorMCP->>VectorMCP: 9. Parse Pages, OCR & Chunk Text
    VectorMCP->>OpenAI: 10. Compute Batch Embeddings
    OpenAI-->>VectorMCP: Return Chunk Vectors
    VectorMCP->>Chroma: 11. Upsert Embeddings into Collection kb_{id}
    VectorMCP->>PG: 12. Save Chunk Records & Update Status = INDEXED (vkb_documents / alembic_version_vkb)
    Frontend->>Backend: 13. Poll KB Status -> Shows "Indexed"
```

### 7.3 Host Application API Contract & Backwards Compatibility (AgriConnect & CoM)

> [!IMPORTANT]
> **CRITICAL HOST API STABILITY & ZERO-REGRESSION POLICY:**
> All endpoints currently utilized by **AgriConnect** or **CoM Tenant** (host applications) MUST remain completely available and 100% backwards-compatible. Minor configuration or parameter changes in the AgriConnect repo are acceptable, but we strictly steer clear of major or breaking API revisions to ensure seamless continuity for live sector operations.

To ensure **zero breaking changes or regressions** for partner applications (e.g. `AgriConnect`, `CoM`, or external Web UIs), `akvo-rag-backend` preserves the exact REST/SSE API contract. Partner applications continue calling the same routes with the same request/response payloads:

| Route Path | Method | Host / Caller Role | Legacy Implementation | Option C Container Implementation |
|---|---|---|---|---|
| `/api/v1/chat` or `/api/chat` | `POST` | Conversational RAG Query | FastMCP HTTP hop $\rightarrow$ `vector-kb` | Redis Queue RPC (`mcp:vector:requests`) |
| `/api/v1/knowledge-bases` | `GET` | List tenant KBs | HTTP Proxy $\rightarrow$ `vector-kb` | Redis Queue RPC `list_kbs` (or direct scoped read) |
| `/api/v1/knowledge-bases` | `POST` | Create new Knowledge Base | HTTP Proxy $\rightarrow$ `vector-kb` | Redis Queue RPC `create_kb` |
| `/api/v1/knowledge-bases/{id}` | `GET` | Get KB details & doc count | HTTP Proxy $\rightarrow$ `vector-kb` | Redis Queue RPC `get_kb` |
| `/api/v1/knowledge-bases/{id}` | `PUT` | Update KB metadata/prompts | HTTP Proxy $\rightarrow$ `vector-kb` | Redis Queue RPC `update_kb` |
| `/api/v1/knowledge-bases/{id}` | `DELETE` | Delete KB & vector collections | HTTP Proxy $\rightarrow$ `vector-kb` | Redis Queue RPC `delete_kb` |
| `/api/v1/knowledge-bases/{id}/documents` | `GET` | List documents in a KB | HTTP Proxy $\rightarrow$ `vector-kb` | Redis Queue RPC `list_documents` |
| `/api/v1/knowledge-bases/{id}/documents/upload` | `POST` | Multipart PDF/DOCX Upload | Celery task $\rightarrow$ HTTP upload | Stream to **MinIO** $\rightarrow$ Redis `document_ingestion` |
| `/api/v1/knowledge-bases/{id}/documents/tasks` | `GET` | Poll async ingestion status | HTTP Proxy $\rightarrow$ `vector-kb` | Redis Queue RPC `get_processing_tasks` |
| `/api/v1/prompts` | `GET`/`POST` | Manage versioned prompts | MySQL database query | PostgreSQL 17 `prompt_definitions` query |

#### Detailed Flow: Host KB Creation & Document Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor Host as Host App (AgriConnect / CoM)
    participant Backend as akvo-rag-backend (FastAPI)
    participant MinIO as MinIO Object Storage
    participant Redis as Redis Queue Broker
    participant VectorMCP as vector-kb-mcp (Owns Schema)
    participant PG as PostgreSQL 17 (alembic_version_vkb)

    %% Flow 1: Create KB
    Note over Host, PG: 1. Host creates a Knowledge Base
    Host->>Backend: POST /api/v1/knowledge-bases { name: "WASH SOPs", description: "Handpump O&M" }
    Backend->>Backend: Validate App API Key & Tenant ID
    Backend->>Redis: RPUSH mcp:vector:requests { tool: 'create_kb', name, description }
    Redis->>VectorMCP: BLPOP mcp:vector:requests
    VectorMCP->>PG: INSERT INTO vkb_knowledge_bases (...)
    VectorMCP->>Redis: RPUSH mcp:vector:responses:{id} { status: 'ok', kb_id: 10 }
    Redis-->>Backend: Return new KB metadata
    Backend-->>Host: 201 Created { id: 10, name: "WASH SOPs", status: "ACTIVE" }

    %% Flow 2: Upload Document
    Note over Host, PG: 2. Host uploads a PDF Document
    Host->>Backend: POST /api/v1/knowledge-bases/10/documents/upload (Multipart PDF)
    Backend->>MinIO: Save raw file to documents/wash_sop_2024.pdf
    Backend->>PG: Insert Document row (status: "PROCESSING")
    Backend->>Redis: RPUSH document_ingestion { document_id: "doc-99", kb_id: 10 }
    Backend-->>Host: 202 Accepted { document_id: "doc-99", status: "PROCESSING" }

    %% Flow 3: List Documents
    Note over Host, PG: 3. Host lists documents in KB #10
    Host->>Backend: GET /api/v1/knowledge-bases/10/documents
    Backend->>Redis: RPUSH mcp:vector:requests { tool: 'list_documents', kb_id: 10 }
    Redis->>VectorMCP: BLPOP mcp:vector:requests
    VectorMCP->>PG: SELECT * FROM vkb_documents WHERE kb_id = 10
    VectorMCP->>Redis: RPUSH mcp:vector:responses:{id} { documents: [...] }
    Redis-->>Backend: Return documents list
    Backend-->>Host: 200 OK [ { id: "doc-99", title: "wash_sop_2024.pdf", status: "INDEXED", ... } ]
```

---

## 8. Master Task Matrix & Implementation Phases (Developer-First Sequence)

| Task Code | Title | Component / Path | Vibe-Coding Est. | Traditional Est. |
|---|---|---|---|---|
| **Phase 1** | **Environment Orchestration, Monorepo Setup & Vector Microservice** | | | |
| `TASK-MONO-101` | Author Unified `docker-compose.yml` & Local Infrastructure (`postgres:17`, `redis:7`, `chromadb`, `minio`) | Root `docker-compose.yml` | **2.0 hrs** | 1.5 days |
| `TASK-MONO-102` | Migrate `vector-kb` Parsing, Chunking & Chroma Direct Search into `vector-kb-mcp/` | `vector-kb-mcp/` | **2.5 hrs** | 2.0 days |
| `TASK-MONO-103` | Build `vector-kb-mcp` Dockerfile & Native Async Redis Worker Entrypoint | `vector-kb-mcp/Dockerfile` | **2.0 hrs** | 1.5 days |
| `TASK-TEST-104` | Unit & Integration Test Suite for `vector-kb-mcp` (Parser, Chunker, Retriever & Redis Worker) | `vector-kb-mcp/tests/` | **1.5 hrs** | 1.0 day |
| **Phase 2** | **Unified Database, Schema Isolation & Metadata Hardening** | | | |
| `TASK-DB-201` | Port Vector-KB SQLAlchemy Models into `vector-kb-mcp/models/` | `vector-kb-mcp/models/` | **1.5 hrs** | 1.0 day |
| `TASK-DB-202` | Enrich `KnowledgeBase` & `Document` Models with Metadata & 1536-dim Embedding Guard | `vector-kb-mcp/models/` | **1.5 hrs** | 1.0 day |
| `TASK-DB-203` | Setup Service-Owned Alembic Migrations (`alembic_version_vkb`) | `vector-kb-mcp/alembic/` | **1.5 hrs** | 1.0 day |
| `TASK-DB-204` | PostgreSQL Adapter (`asyncpg`) & Automated Legacy Data Migration CLI | `backend/app/scripts/` | **2.0 hrs** | 1.5 days |
| **Phase 3** | **Queue-Backed MCP Dispatcher, Scoping Removal & FastMCP Purge** | | | |
| `TASK-MCP-301` | Implement `mcp_config.json` Declarative Schema & Static Parser | `backend/app/core/` | **1.0 hr** | 1.0 day |
| `TASK-MCP-302` | Build `MCPQueueDispatcher` (Redis Request-Reply with Correlation ID) | `backend/app/services/` | **3.0 hrs** | 2.5 days |
| `TASK-MCP-303` | Integrate `MCPQueueDispatcher` into RAG Graph & Host REST Endpoints (`apps.py`, `knowledge_base.py`) | `backend/app/` | **2.0 hrs** | 1.5 days |
| `TASK-MCP-304` | Remove `ScopingAgent` Redundant LLM Call & Route Directly to Vector Queue | `backend/app/services/` | **1.5 hrs** | 1.0 day |
| `TASK-MCP-305` | Dynamic Prompt Resolver (`PromptService`) with PostgreSQL 17 Overlays | `backend/app/services/` | **1.5 hrs** | 1.0 day |
| `TASK-TEST-306` | Backend Unit & Integration Test Suite (Dispatcher, RAG Graph, Host Endpoints, Session) | `backend/tests/` | **2.0 hrs** | 1.5 days |
| **Phase 4** | **Document Ingestion, MinIO Storage & Celery Deletion** | | | |
| `TASK-ING-401` | Integrate MinIO S3 Client in FastAPI & Purge Legacy Celery/RabbitMQ Code | `backend/app/services/` | **1.5 hrs** | 1.0 day |
| `TASK-ING-402` | Build Native Async Redis Ingestion Consumer in `vector-kb-mcp` | `vector-kb-mcp/` | **2.0 hrs** | 1.5 days |
| **Phase 5** | **Quality Gates, Golden Set Evaluation & Developer Onboarding** | | | |
| `TASK-OPS-501` | End-to-End Golden Set Accuracy & Legacy Test Gate (Faithfulness $\ge 0.85$) | `backend/RAG_evaluation/` | **2.5 hrs** | 2.0 days |
| `TASK-DOC-502` | Comprehensive Developer Onboarding & Architecture Documentation Alignment | `docs/` & `README.md` | **1.5 hrs** | 1.0 day |
| **TOTAL** | | | **32.0 hrs (~4.0 working days)** | **24.5 days** |

---

## 9. Detailed Task Specifications & Acceptance Criteria

### Phase 1: Environment Orchestration, Monorepo Setup & Vector Microservice

#### `TASK-MONO-101`: Author Unified `docker-compose.yml` & Local Infrastructure (`postgres:17`, `redis:7`, `chromadb`, `minio`)
* **Target Path:** Root `docker-compose.yml` & `.env.example`
* **Vibe-Coding Estimate:** `2.0 hours`
* **Detailed Description:**  
  Author the unified 7-container Docker Compose file (`frontend`, `backend`, `vector-kb-mcp`, `postgres`, `redis`, `chromadb`, `minio`) as the foundation of the development environment. Include strict healthchecks (`pg_isready`, `redis-cli ping`, ChromaDB heartbeat), volumes, code bind-mounts for hot-reloading, and `.env.example`. This allows developers to run `docker compose up -d postgres redis chromadb minio` immediately on Day 1 to back all subsequent implementation phases.
* **Key Touchpoints:**
  - `docker-compose.yml` `[NEW / OVERWRITE]`
  - `.env.example` `[MODIFY]`
* **User Acceptance Criteria (UAC):**
  - Executing `docker compose up -d` starts core infrastructure services (`postgres`, `redis`, `chromadb`, `minio`) with healthy status in $< 30\text{s}$.
* **Technical Acceptance Criteria (TAC):**
  - Volume definitions persist `postgres_data`, `redis_data`, `chroma_data`, and `minio_data`.
  - Service definitions support independent container spinning (`docker compose up -d postgres redis`).

---

#### `TASK-MONO-102`: Migrate `vector-kb` Parsing, Chunking & Chroma Direct Search into `vector-kb-mcp/`
* **Target Path:** `vector-kb-mcp/`
* **Vibe-Coding Estimate:** `2.5 hours`
* **Detailed Description:**  
  Extract document parsing (PDF, DOCX), token chunking (`RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)`), and direct ChromaDB similarity search from `vector-knowledge-base-mcp-server` into `vector-kb-mcp/`. Implement direct Chroma collection search without FastMCP or base64 wrappers.
* **Key Touchpoints:**
  - `vector-kb-mcp/parser/pdf_parser.py` `[NEW]`
  - `vector-kb-mcp/chunker/text_chunker.py` `[NEW]`
  - `vector-kb-mcp/retriever/chroma_retriever.py` `[NEW]`
  - `vector-kb-mcp/requirements.txt` `[NEW]`
* **Code Specification:**
  ```python
  # vector-kb-mcp/retriever/chroma_retriever.py
  from dataclasses import dataclass, field
  from typing import List, Dict, Any, Optional
  import chromadb
  from openai import AsyncOpenAI

  @dataclass(frozen=True)
  class RetrievedChunk:
      content: str
      kb_id: int
      document_id: str
      chunk_id: str
      score: float
      metadata: Dict[str, Any] = field(default_factory=dict)

  class ChromaRetriever:
      def __init__(self, chroma_client: chromadb.ClientAPI, openai_client: AsyncOpenAI, embedding_model: str = "text-embedding-3-small"):
          self.chroma = chroma_client
          self.openai = openai_client
          self.embedding_model = embedding_model

      async def search(self, query: str, kb_ids: List[int], top_k: int = 4, score_threshold: Optional[float] = None) -> List[RetrievedChunk]:
          emb_resp = await self.openai.embeddings.create(input=[query], model=self.embedding_model)
          query_vector = emb_resp.data[0].embedding
          # Multi-KB parallel query and score ranking
          ...
  ```
* **User Acceptance Criteria (UAC):**
  - Vector similarity search returns relevant document chunks from multiple knowledge bases in $< 50\text{ms}$.
* **Technical Acceptance Criteria (TAC):**
  - Zero dependencies on FastMCP or HTTP client wrappers inside `vector-kb-mcp/retriever/`.
  - Type annotations pass `mypy --strict`.

---

#### `TASK-MONO-103`: Build `vector-kb-mcp` Dockerfile & Native Async Redis Worker Entrypoint
* **Target Path:** `vector-kb-mcp/`
* **Vibe-Coding Estimate:** `2.0 hours`
* **Detailed Description:**  
  Build the container runtime for `vector-kb-mcp`. Implement the main Redis event loop (`main.py`) that uses `BLPOP` to listen for tool requests on `mcp:vector:requests`, dispatches to the corresponding handler (`query_knowledge_base`, `list_knowledge_bases`, `get_knowledge_base`, `create_knowledge_base`, `update_knowledge_base`, `delete_knowledge_base`, `list_documents`, `get_document`, `get_processing_tasks`), and returns results via `RPUSH` to `mcp:vector:responses:{correlation_id}` with TTL expiry.
* **Key Touchpoints:**
  - `vector-kb-mcp/Dockerfile` `[NEW]`
  - `vector-kb-mcp/main.py` `[NEW]`
  - `vector-kb-mcp/core/config.py` `[NEW]`
* **Code Specification:**
  ```python
  # vector-kb-mcp/main.py
  import json
  import asyncio
  import redis.asyncio as redis
  from retriever.chroma_retriever import ChromaRetriever
  from services.kb_service import KnowledgeBaseService

  async def mcp_worker_loop():
      r = redis.from_url(REDIS_URL, decode_responses=True)
      retriever = ChromaRetriever(...)
      kb_service = KnowledgeBaseService(...)

      TOOL_HANDLERS = {
          "query_knowledge_base": lambda args: retriever.search(**args),
          "list_knowledge_bases": lambda args: kb_service.list_kbs(**args),
          "get_knowledge_base": lambda args: kb_service.get_kb(**args),
          "create_knowledge_base": lambda args: kb_service.create_kb(**args),
          "update_knowledge_base": lambda args: kb_service.update_kb(**args),
          "delete_knowledge_base": lambda args: kb_service.delete_kb(**args),
          "list_documents": lambda args: kb_service.list_documents(**args),
          "get_document": lambda args: kb_service.get_document(**args),
          "get_processing_tasks": lambda args: kb_service.get_tasks(**args),
      }

      while True:
          item = await r.blpop("mcp:vector:requests", timeout=0)
          if not item:
              continue
          _, raw_payload = item
          msg = json.loads(raw_payload)
          correlation_id = msg["correlation_id"]
          response_queue = msg["response_queue"]
          tool_name = msg.get("tool_name", "query_knowledge_base")
          args = msg.get("arguments", {})

          handler = TOOL_HANDLERS.get(tool_name)
          if handler:
              result = await handler(args)
              payload = {"status": "ok", "data": result}
          else:
              payload = {"status": "error", "error": f"Unknown tool: {tool_name}"}

          await r.rpush(response_queue, json.dumps(payload))
          await r.expire(response_queue, 60)
  ```
* **User Acceptance Criteria (UAC):**
  - Worker starts up cleanly, registers with Redis, and handles both vector queries and document/KB management requests in $< 5\text{ms}$ queue latency.
* **Technical Acceptance Criteria (TAC):**
  - Dockerfile uses lightweight `python:3.11-slim`.
  - Handles SIGTERM/SIGINT gracefully without dropping in-flight requests.

---

#### `TASK-TEST-104`: Unit & Integration Test Suite for `vector-kb-mcp`
* **Target Path:** `vector-kb-mcp/tests/`
* **Vibe-Coding Estimate:** `1.5 hours`
* **Detailed Description:**  
  Implement a complete test suite for `vector-kb-mcp` validating text extractors, PDF parsers, chunk token boundaries, ChromaRetriever query execution, and the Redis request-reply worker loop using live test containers (`redis`, `chromadb`) or `fakeredis`.
* **Key Touchpoints:**
  - `vector-kb-mcp/tests/test_parser.py` `[NEW]`
  - `vector-kb-mcp/tests/test_chunker.py` `[NEW]`
  - `vector-kb-mcp/tests/test_retriever.py` `[NEW]`
  - `vector-kb-mcp/tests/test_redis_worker.py` `[NEW]`
* **User Acceptance Criteria (UAC):**
  - All tests execute and pass via `pytest` inside the running `vector-kb-mcp` container.
* **Technical Acceptance Criteria (TAC):**
  - Test suite achieves $\ge 85\%$ line coverage across `parser/`, `chunker/`, and `retriever/`.

---

### Phase 2: Unified Database, Schema Isolation & Metadata Hardening

#### `TASK-DB-201`: Port Vector-KB SQLAlchemy Models into `vector-kb-mcp/models/`
* **Target Path:** `vector-kb-mcp/models/`
* **Vibe-Coding Estimate:** `1.5 hours`
* **Detailed Description:**  
  Port `KnowledgeBase`, `Document`, and `DocumentChunk` models from the legacy repository into `vector-kb-mcp/models/`. Use SQLAlchemy 2.0 declarative models matching PostgreSQL 17 datatypes (UUID, JSONB, TIMESTAMP with timezone).
* **Key Touchpoints:**
  - `vector-kb-mcp/models/__init__.py` `[NEW]`
  - `vector-kb-mcp/models/knowledge_base.py` `[NEW]`
  - `vector-kb-mcp/models/document.py` `[NEW]`
  - `vector-kb-mcp/models/document_chunk.py` `[NEW]`
* **User Acceptance Criteria (UAC):**
  - Relational metadata for knowledge bases, uploaded documents, and chunks are tracked accurately in PostgreSQL 17.
* **Technical Acceptance Criteria (TAC):**
  - ForeignKey relationships link `documents.kb_id -> knowledge_bases.id` and `document_chunks.document_id -> documents.id`.

---

#### `TASK-DB-202`: Enrich `KnowledgeBase` & `Document` Models with Metadata & 1536-dim Embedding Guard
* **Target Path:** `vector-kb-mcp/models/`
* **Vibe-Coding Estimate:** `1.5 hours`
* **Detailed Description:**  
  Add public-sector and governance metadata fields to `documents` (`doc_version`, `issuing_authority`, `effective_date`, `doc_type`, `jurisdiction`). Add `embedding_model` (default: `text-embedding-3-small`) and `embedding_dim` (default: 1536) to `knowledge_bases` with validation guards that reject query/ingest attempts if dimension mismatch occurs.
* **Key Touchpoints:**
  - `vector-kb-mcp/models/knowledge_base.py` `[MODIFY]`
  - `vector-kb-mcp/models/document.py` `[MODIFY]`
  - `vector-kb-mcp/models/document_chunk.py` `[MODIFY]`
* **User Acceptance Criteria (UAC):**
  - Document citations include issuing authority, effective date, and edition (e.g. *"National Water Standard 2024, Ministry of Water, Section 4"*).
* **Technical Acceptance Criteria (TAC):**
  - Database schema includes indices on `(kb_id, status)` and `(document_id, chunk_index)`.

---

#### `TASK-DB-203`: Setup Service-Owned Alembic Migrations (`alembic_version_vkb`)
* **Target Path:** `vector-kb-mcp/alembic/`
* **Vibe-Coding Estimate:** `1.5 hours`
* **Detailed Description:**  
  Configure a dedicated, service-owned Alembic environment inside `vector-kb-mcp/`. Configure `env.py` and `alembic.ini` with `version_table = "alembic_version_vkb"`. Generate the initial migration script creating `vkb_knowledge_bases`, `vkb_documents`, and `vkb_document_chunks` (including all enriched metadata columns).
* **Key Touchpoints:**
  - `vector-kb-mcp/alembic.ini` `[NEW]`
  - `vector-kb-mcp/alembic/env.py` `[NEW]`
  - `vector-kb-mcp/alembic/versions/001_initial_vkb_schema.py` `[NEW]`
* **User Acceptance Criteria (UAC):**
  - Running `alembic upgrade head` creates all vector KB tables without interfering with core tables (`users`, `prompts`, `chats`).
* **Technical Acceptance Criteria (TAC):**
  - `version_table` is explicitly isolated to prevent migration state collisions in PostgreSQL 17.

---

#### `TASK-DB-204`: PostgreSQL Adapter (`asyncpg`) & Automated Legacy Data Migration CLI
* **Target Path:** `backend/app/scripts/` & `backend/app/core/`
* **Vibe-Coding Estimate:** `2.0 hours`
* **Detailed Description:**  
  Update `backend/app/core/config.py` and `backend/app/db/session.py` to connect to PostgreSQL 17 using `asyncpg`. Build an automated CLI ETL script (`migrate_legacy_to_consolidated_postgres.py`) to extract all users, prompts, chats, and vector KB records from legacy MySQL and PostgreSQL instances into the new database.
* **Key Touchpoints:**
  - `backend/app/core/config.py` `[MODIFY]`
  - `backend/app/db/session.py` `[MODIFY]`
  - `backend/app/scripts/migrate_legacy_to_consolidated_postgres.py` `[NEW]`
* **Code Specification:**
  ```python
  # CLI execution command
  python -m app.scripts.migrate_legacy_to_consolidated_postgres \
    --mysql-url "mysql+pymysql://user:pass@mysql:3306/akvo_rag" \
    --legacy-pg-url "postgresql://user:pass@legacy_vkb:5432/vector_kb" \
    --target-pg-url "postgresql+asyncpg://postgres:postgres@postgres:5432/akvo_rag"
  ```
* **User Acceptance Criteria (UAC):**
  - All existing prompt versions, admin users, apps, and knowledge bases migrate into PostgreSQL 17 with 0 data loss.
* **Technical Acceptance Criteria (TAC):**
  - Idempotent execution (safe to run multiple times with UPSERT logic).

---

### Phase 3: Queue-Backed MCP Dispatcher, Scoping Removal & FastMCP Purge

#### `TASK-MCP-301`: Implement `mcp_config.json` Declarative Schema & Static Parser
* **Target Path:** `backend/app/core/` & `backend/mcp_config.json`
* **Vibe-Coding Estimate:** `1.0 hour`
* **Detailed Description:**  
  Define the declarative static MCP registry schema in `backend/mcp_config.json`. Configure vector tool definitions (`query_knowledge_base`, `list_knowledge_bases`, `get_knowledge_base`, `create_knowledge_base`, `update_knowledge_base`, `delete_knowledge_base`, `list_documents`, `get_document`, `get_processing_tasks`). Implement a type-safe parser (`backend/app/core/mcp_config.py`) that loads server definitions, tool schemas, request/reply queue names, and timeout values at FastAPI startup.
* **Key Touchpoints:**
  - `backend/mcp_config.json` `[NEW]`
  - `backend/app/core/mcp_config.py` `[NEW]`
* **User Acceptance Criteria (UAC):**
  - Adding a new tool to `mcp_config.json` immediately exposes the tool to the backend without code modifications.
* **Technical Acceptance Criteria (TAC):**
  - Pydantic v2 validation enforces presence of `mcp_name`, `request_queue`, `response_prefix`, and `timeout_ms`.

---

#### `TASK-MCP-302`: Build `MCPQueueDispatcher` (Redis Request-Reply with Correlation ID)
* **Target Path:** `backend/app/services/`
* **Vibe-Coding Estimate:** `3.0 hours`
* **Detailed Description:**  
  Implement the high-performance async Redis Request-Reply client (`MCPQueueDispatcher`). It generates a unique UUID `correlation_id` per tool call, pushes the payload to `mcp:{name}:requests`, and awaits the response on `mcp:{name}:responses:{correlation_id}` using `BLPOP` with sub-10ms overhead.
* **Key Touchpoints:**
  - `backend/app/services/mcp_queue_dispatcher.py` `[NEW]`
* **Code Specification:**
  ```python
  # backend/app/services/mcp_queue_dispatcher.py
  class MCPQueueDispatcher:
      async def call_tool(self, mcp_name: str, tool_name: str, arguments: Dict[str, Any], timeout_seconds: float = 5.0) -> Dict[str, Any]:
          ...
  ```
* **User Acceptance Criteria (UAC):**
  - Core RAG engine invokes remote MCP tools with $< 5\text{ms}$ queue latency and clean error propagation on timeout.
* **Technical Acceptance Criteria (TAC):**
  - Fully asynchronous with `redis.asyncio`. Connection pooling configured for high concurrency.

---

#### `TASK-MCP-303`: Integrate `MCPQueueDispatcher` into RAG Graph & Host REST Endpoints (`apps.py`, `knowledge_base.py`)
* **Target Path:** `backend/app/` & `backend/mcp_clients/`
* **Vibe-Coding Estimate:** `2.0 hours`
* **Detailed Description:**  
  Refactor both the LangGraph workflow (`query_answering_workflow.py`) and FastAPI routers (`backend/app/api/api_v1/knowledge_base.py` and `backend/app/api/api_v1/apps.py`) to execute retrieval and KB/document management via `MCPQueueDispatcher.call_tool("vector", ...)`. Guarantee 100% backwards compatibility for all endpoints in Section 7.3 used by **AgriConnect** and **CoM Tenant** (`/api/v1/chat`, `/api/v1/knowledge-bases`, `/api/v1/knowledge-bases/{id}/documents`, etc.). Purge legacy FastMCP HTTP transport files and discovery managers.
* **Key Touchpoints:**
  - `backend/app/api/api_v1/knowledge_base.py` `[MODIFY]` (replaces `KnowledgeBaseMCPEndpointService` with `MCPQueueDispatcher`)
  - `backend/app/api/api_v1/apps.py` `[MODIFY]` (replaces `KnowledgeBaseMCPEndpointService` with `MCPQueueDispatcher`)
  - `backend/app/services/query_answering_workflow.py` `[MODIFY]`
  - `backend/mcp_clients/kb_mcp_endpoint_service.py` `[DELETE]`
  - `backend/mcp_clients/fastmcp_client_service.py` `[DELETE]`
  - `backend/mcp_clients/mcp_discovery_manager.py` `[DELETE]`
  - `backend/mcp_clients/mcp_servers_config.py` `[DELETE]`
* **User Acceptance Criteria (UAC):**
  - All public endpoints called by AgriConnect and CoM continue to return identical JSON structures with zero breaking changes or regressions.
* **Technical Acceptance Criteria (TAC):**
  - Deletion of ~900 lines of legacy HTTP reconnect/retry/discovery code in `backend/mcp_clients/`.

---

#### `TASK-MCP-304`: Remove `ScopingAgent` Redundant LLM Call & Route Directly to Vector Queue
* **Target Path:** `backend/app/services/`
* **Vibe-Coding Estimate:** `1.5 hours`
* **Detailed Description:**  
  Remove the `scoping_node` from the primary LangGraph execution graph. Route execution directly from `contextualize` $\rightarrow$ `vector_queue_rpc` $\rightarrow$ `generate_answer`, saving 1.5s–3.0s of latency and 1 LLM API call per turn.
* **Key Touchpoints:**
  - `backend/app/services/query_answering_workflow.py` `[MODIFY]`
  - `backend/app/services/scoping_agent.py` `[MODIFY / DEPRECATE]`
* **User Acceptance Criteria (UAC):**
  - End-to-end question answering latency drops by 1.5s–3.0s on the default knowledge query path.
* **Technical Acceptance Criteria (TAC):**
  - LangGraph node graph passes tests with direct edge `contextualize -> retrieve`.

---

#### `TASK-MCP-305`: Dynamic Prompt Resolver (`PromptService`) with PostgreSQL 17 Overlays
* **Target Path:** `backend/app/services/`
* **Vibe-Coding Estimate:** `1.5 hours`
* **Detailed Description:**  
  Refactor `PromptService` to dynamically query PostgreSQL 17 (`prompt_definitions` and `prompt_versions`), applying application/tenant prompt overlays (e.g. `AgriConnect` or `WASH` system instructions) with fallback to hardcoded default constants.
* **Key Touchpoints:**
  - `backend/app/services/prompt_service.py` `[MODIFY]`
  - `backend/app/seeder/seed_prompts.py` `[MODIFY]`
* **User Acceptance Criteria (UAC):**
  - Editing prompts in the Admin UI immediately takes effect on the next conversation turn without container restart.
* **Technical Acceptance Criteria (TAC):**
  - In-memory LRU cache (TTL = 60s) with explicit cache invalidation endpoint on prompt update.

---

#### `TASK-TEST-306`: Backend Unit & Integration Test Suite (Dispatcher, RAG Graph, Host Endpoints, Session)
* **Target Path:** `backend/tests/`
* **Vibe-Coding Estimate:** `2.0 hours`
* **Detailed Description:**  
  Implement unit and integration tests verifying `MCPQueueDispatcher` Redis RPC request-reply, timeout handling, `mcp_config.json` validation, PostgreSQL 17 session handling, LangGraph workflow execution, and **100% backwards-compatibility of Section 7.3 host endpoints** (`/api/v1/chat`, `/api/v1/knowledge-bases`, `/api/v1/knowledge-bases/{id}/documents`, `/api/v1/knowledge-bases/{id}/documents/upload`).
* **Key Touchpoints:**
  - `backend/tests/services/test_mcp_queue_dispatcher.py` `[NEW]`
  - `backend/tests/core/test_mcp_config.py` `[NEW]`
  - `backend/tests/api/test_host_api_backwards_compatibility.py` `[NEW]`
  - `backend/tests/services/test_query_answering_workflow.py` `[MODIFY]`
  - `backend/tests/services/test_prompt_service.py` `[MODIFY]`
* **User Acceptance Criteria (UAC):**
  - All backend unit and integration tests (including host API contract assertions) run and pass cleanly via `pytest tests/ -v`.
* **Technical Acceptance Criteria (TAC):**
  - Mock Redis and mock OpenAI clients ensure tests run deterministically offline in $< 10\text{s}$.

---

### Phase 4: Document Ingestion, MinIO Storage & Celery Deletion

#### `TASK-ING-401`: Integrate MinIO S3 Client in FastAPI & Purge Legacy Celery/RabbitMQ Code
* **Target Path:** `backend/app/services/` & `backend/app/tasks/`
* **Vibe-Coding Estimate:** `1.5 hours`
* **Detailed Description:**  
  Integrate MinIO S3 client for saving uploaded PDF files into bucket `documents/`. Update the `upload_kb_documents` endpoint in `backend/app/api/api_v1/knowledge_base.py` to stream multipart files to MinIO, create `PROCESSING` document records in PostgreSQL 17, and enqueue processing tasks directly to Redis queue `document_ingestion`. Delete legacy `celery_app.py`, RabbitMQ configurations, and `backend/app/tasks/`.
* **Key Touchpoints:**
  - `backend/app/services/minio_service.py` `[NEW]`
  - `backend/app/api/api_v1/knowledge_base.py` `[MODIFY]`
  - `backend/app/celery_app.py` `[DELETE]`
  - `backend/app/tasks/upload_task.py` `[DELETE]`
  - `backend/app/tasks/chat_task.py` `[DELETE]`
* **User Acceptance Criteria (UAC):**
  - Host document upload (`POST /api/v1/knowledge-bases/{id}/documents/upload`) streams raw PDF to MinIO, creates `vkb_documents` record, and enqueues task to Redis.
* **Technical Acceptance Criteria (TAC):**
  - Celery and RabbitMQ completely eliminated from `backend/requirements.txt` and codebase.

---

#### `TASK-ING-402`: Build Native Async Redis Ingestion Consumer in `vector-kb-mcp`
* **Target Path:** `vector-kb-mcp/`
* **Vibe-Coding Estimate:** `2.0 hours`
* **Detailed Description:**  
  Implement the background document ingestion consumer inside `vector-kb-mcp/`. Consumes from Redis `document_ingestion`, downloads raw file from MinIO, parses text/OCR, splits tokens, computes OpenAI embeddings, upserts vectors into ChromaDB `kb_{id}`, and updates document status to `INDEXED` in PostgreSQL 17.
* **Key Touchpoints:**
  - `vector-kb-mcp/ingestion/worker.py` `[NEW]`
  - `vector-kb-mcp/ingestion/processor.py` `[NEW]`
* **User Acceptance Criteria (UAC):**
  - Uploaded documents process asynchronously in the background and become immediately searchable in $< 15\text{s}$.
* **Technical Acceptance Criteria (TAC):**
  - Catches parsing errors and safely updates document status to `FAILED` with detailed error logs.

---

### Phase 5: Quality Gates, Golden Set Evaluation & Developer Onboarding

#### `TASK-OPS-501`: End-to-End Golden Set Accuracy & Legacy Test Gate (Faithfulness $\ge 0.85$)
* **Target Path:** `backend/RAG_evaluation/`
* **Vibe-Coding Estimate:** `2.5 hours`
* **Detailed Description:**  
  Run the automated headless evaluation harness (`backend/RAG_evaluation/run_e2e_tests_headless_container.sh`) against the golden evaluation dataset on the consolidated PostgreSQL 17 and ChromaDB stack. Assert quality thresholds across RAG metrics.
* **Key Touchpoints:**
  - `backend/RAG_evaluation/headless_evaluation.py` `[MODIFY]`
  - `backend/RAG_evaluation/run_e2e_tests_headless_container.sh` `[MODIFY]`
* **User Acceptance Criteria (UAC):**
  - RAGAS evaluation passes with:
    - **Faithfulness:** $\ge 0.85$
    - **Answer Relevancy:** $\ge 0.85$
    - **Groundedness:** $\ge 0.90$
* **Technical Acceptance Criteria (TAC):**
  - All unit tests pass cleanly: `pytest tests/unit -v` with 0 failures and 0 regressions.

---

#### `TASK-DOC-502`: Comprehensive Developer Onboarding & Architecture Documentation Alignment
* **Target Path:** `docs/` & `README.md`
* **Vibe-Coding Estimate:** `1.5 hours`
* **Detailed Description:**  
  Update all developer documentation, architecture guides, and onboarding manuals to reflect the unified 7-container monorepo architecture, Redis queue-based MCP communication, `mcp_config.json` extensibility, service-owned Alembic schema isolation (`alembic_version` / `alembic_version_vkb`), and troubleshooting playbooks.
* **Key Touchpoints:**
  - `README.md` `[MODIFY]` (Updated 7-container startup instructions & architecture diagram)
  - `docs/dev-guide.md` `[MODIFY]` (Local setup, watch mode, running migrations, seed prompts)
  - `docs/architecture_map.md` `[MODIFY]` (Container topology, Redis queue RPC contracts, MinIO bucket layout)
  - `docs/admin-guide.md` `[MODIFY]` (Knowledge base management, prompt editing, API key provisioning)
  - `docs/troubleshooting.md` `[MODIFY]` (Redis queue debugging, timeout tuning, ChromaDB healthchecks)
* **User Acceptance Criteria (UAC):**
  - A new developer can clone the repository, spin up the entire platform via `docker compose up -d --build`, run the test suite, and understand how to attach a new MCP tool within 15 minutes.
* **Technical Acceptance Criteria (TAC):**
  - Documentation complies with `.agent/rules/docs-standard.md` (root-relative paths only, no hardcoded machine paths, zero credentials/API keys).

---

## 10. Verification & Quality Gates

1. **Legacy & Unit Test Gate:**
   - Execute backend unit tests: `docker exec akvo-rag-backend-1 python -m pytest tests/unit -v`.
   - Execute vector KB unit tests: `docker exec akvo-rag-vector-kb-mcp-1 python -m pytest tests/ -v`.
   - All tests must pass cleanly against PostgreSQL 17 with 0 errors.
2. **Queue Request-Reply Latency Assertion:**
   - Benchmark `MCPQueueDispatcher.call_tool("vector", ...)`: Must return in $< 5\text{ms}$ queue overhead (excluding Chroma/OpenAI compute).
3. **Multi-MCP Extensibility Gate:**
   - Add mock tool to `mcp_config.json` $\rightarrow$ verify backend dynamically discovers and routes tool calls to the mock queue without code alterations.
4. **Golden Set RAGAS Evaluation:**
   - Run headless evaluation harness (`backend/RAG_evaluation/headless_evaluation.py`) asserting:
     - Faithfulness $\ge 0.85$
     - Answer Relevancy $\ge 0.85$
     - Groundedness $\ge 0.90$

