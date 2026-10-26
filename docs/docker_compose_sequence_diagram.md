# Docker Compose Architecture & Interaction Diagrams (Option C)

This document provides the complete **Mermaid Architecture Flowcharts** and **Sequence Diagrams** detailing the Docker Compose setup, container boundaries, networks, volumes, and runtime interactions for **both deployment topologies**:
1. **Setup 1: Standalone `akvo-rag` + `vector-kb`** (`docker-compose.dev.yml` / `docker-compose.yml`)
2. **Setup 2: Embedded `xxxconnect` (AgriConnect / WASHConnect)** (`xxxconnect/docker-compose.yml`)

You can copy the code snippets below directly into the [Mermaid Live Editor](https://dedenbangkit.github.io/mermaid-live-editor/) to view and export high-resolution PNG/SVG diagrams.

---

## 1. Setup 1: Standalone `akvo-rag` + `vector-kb`

> **Target Audience:** Developers, Admins, and Prompt Engineers managing prompts, testing RAG queries in the playground, and managing knowledge bases.

### 1.1 Docker Compose Architecture & Container Interaction Flowchart

```mermaid
flowchart TB
    subgraph Clients["Clients & Users"]
        Browser["Web Browser (Admin / Dev)<br/>http://localhost:3000"]
        RESTClient["API Client / Third-Party<br/>http://localhost:8000"]
    end

    subgraph ComposeNetwork["akvo-rag Docker Compose Network (docker-compose.dev.yml)"]
        direction TB
        
        subgraph AppTier["Application Tier"]
            direction TB
            Frontend["frontend (Next.js 14)<br/>• Port: 3000:3000<br/>• Prompt Management UI & Chat Playground"]
            
            subgraph BackendContainer["backend (FastAPI) - Port: 8000:8000"]
                API["FastAPI REST & SSE Router<br/>(Auth, Prompts, KB Admin)"]
                
                subgraph InProcessLibs1["In-Process Python Libraries"]
                    RAGCore1["akvo-rag-core<br/>(LangGraph Engine & PromptResolver)"]
                    VKBCore1["vector-kb-core<br/>(ChromaRetriever & Direct Search)"]
                end
                
                API --> RAGCore1
                RAGCore1 --> VKBCore1
            end
        end

        subgraph WorkerTier["Background Workers"]
            IngWorker1["ingestion-worker (Celery Worker)<br/>• Package: vector-kb-mcp-server<br/>• PDF Parsing, Chunking & Embeddings"]
        end

        subgraph Datastores["Datastores & Storage (Docker Volumes)"]
            PG1[("postgres (PostgreSQL 17)<br/>• Port: 5432:5432<br/>• Vol: postgres_data<br/>• Users, Prompts, Documents, Chunks")]
            Chroma1[("chromadb (Chroma Vector DB)<br/>• Port: 8000:8000<br/>• Vol: chroma_data<br/>• Collections: kb_1, kb_2...")]
            MinIO1[("minio (Object Storage)<br/>• Ports: 9000 (API), 9001 (Console)<br/>• Vol: minio_data<br/>• Bucket: documents/")]
            Redis1[("redis (Task Broker & Cache)<br/>• Port: 6379:6379<br/>• Vol: redis_data<br/>• Queue: document_ingestion")]
        end
    end

    subgraph External["External Cloud APIs"]
        OpenAI1["OpenAI API (api.openai.com:443)<br/>• text-embedding-3-small<br/>• gpt-4o-mini / gpt-4o"]
    end

    %% Client Connections
    Browser -->|HTTP 3000| Frontend
    Browser -->|SSE / REST 8000| API
    RESTClient -->|POST /api/chat 8000| API
    Frontend -->|Internal REST / SSE| API

    %% Backend In-Process & Storage Connections
    API -->|SQLAlchemy asyncpg: 5432| PG1
    API -->|S3 Upload PDF: 9000| MinIO1
    API -->|Enqueue Task: 6379| Redis1
    VKBCore1 -->|HTTP Client: 8000| Chroma1
    RAGCore1 -->|HTTPS: 443| OpenAI1
    VKBCore1 -->|HTTPS: 443| OpenAI1

    %% Ingestion Worker Connections
    IngWorker1 -->|Consume Task: 6379| Redis1
    IngWorker1 -->|Download PDF: 9000| MinIO1
    IngWorker1 -->|Batch Embeddings: 443| OpenAI1
    IngWorker1 -->|Upsert Vectors: 8000| Chroma1
    IngWorker1 -->|Save Chunks & Status: 5432| PG1
```

### 1.2 Mode 1 Sequence Diagram: Standalone Interaction

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

### 1.3 Mode 1 Container Specification Table

| Container Name | Image / Source | Port Mapping | Volume / Storage | Primary Function |
|---|---|---|---|---|
| **`frontend`** | `akvo-rag/frontend` (Next.js 14) | `3000:3000` | Bind mount for dev | Admin UI, Prompt Versioning, Chat Playground |
| **`backend`** | `akvo-rag/backend` (FastAPI) | `8000:8000` | Bind mount for dev | REST API, In-process `akvo-rag-core` & `vector-kb-core` |
| **`ingestion-worker`**| `vector-kb` Celery worker | Internal | Code mount | Background PDF parsing, chunking, and embedding |
| **`postgres`** | `postgres:17-alpine` | `5432:5432` | `postgres_data:/var/lib/postgresql/data` | Relational database (users, prompts, document records) |
| **`chromadb`** | `chromadb/chroma:latest` | `8000:8000` | `chroma_data:/chroma/chroma` | Persistent vector collections (`kb_{id}`) |
| **`minio`** | `minio/minio:latest` | `9000:9000`, `9001:9001` | `minio_data:/data` | S3 object storage for uploaded PDF files |
| **`redis`** | `redis:7-alpine` | `6379:6379` | `redis_data:/data` | Task broker for document ingestion queue |

---

## 2. Setup 2: Embedded `xxxconnect` (AgriConnect / WASHConnect)

> **Target Audience:** Production partner deployments serving farmers and citizens over WhatsApp with sub-second response times and zero internal network hops.

### 2.1 Docker Compose Architecture & Container Interaction Flowchart

```mermaid
flowchart TB
    subgraph ExternalActors["External Users & Services"]
        Farmer["Farmer / Citizen<br/>(WhatsApp App on Mobile)"]
        WhatsAppCloud["Meta WhatsApp Cloud API<br/>(graph.facebook.com:443)"]
        OpenAI2["OpenAI API (api.openai.com:443)<br/>• text-embedding-3-small<br/>• gpt-4o-mini"]
    end

    subgraph PartnerNamespace["xxxconnect Single Docker Compose Namespace (docker-compose.yml)"]
        direction TB

        subgraph AppContainer["app (Host FastAPI Backend) - Port: 8000:8000"]
            Router["WhatsApp Webhook Router & CRM<br/>(POST /whatsapp/webhook)"]
            
            subgraph InProcessLibs2["In-Process Core Libraries (Imported Packages)"]
                AIService["EmbeddedAIService Adapter"]
                RAGCore2["akvo-rag-core<br/>(LangGraph Engine & PromptResolver)"]
                VKBCore2["vector-kb-core<br/>(ChromaRetriever & Direct Search)"]
            end
            
            Router --> AIService
            AIService --> RAGCore2
            RAGCore2 --> VKBCore2
        end

        subgraph WorkerContainers["Background Celery Workers"]
            AppWorker["app-worker (Host Celery Worker)<br/>• Queue: outbound_messages<br/>• WhatsApp Message Dispatcher with Retries"]
            IngWorker2["ingestion-worker (vector-kb Worker)<br/>• Queue: document_ingestion<br/>• Sector PDF Parser & Vector Indexer"]
        end

        subgraph PartnerDatastores["Datastores & Storage (Docker Volumes)"]
            PG2[("postgres (PostgreSQL 17)<br/>• Port: 5432:5432<br/>• Vol: partner_pg_data<br/>• Farmer Profiles, Chat Sessions, KB Metadata")]
            Chroma2[("chromadb (Chroma Vector DB)<br/>• Port: 8000:8000<br/>• Vol: partner_chroma_data<br/>• Collections: kb_1 (Avocado), kb_2 (WASH)...")]
            MinIO2[("minio (Object Storage)<br/>• Port: 9000:9000<br/>• Vol: partner_minio_data<br/>• Bucket: documents/")]
            Redis2[("redis (Task Broker & Cache)<br/>• Port: 6379:6379<br/>• Vol: partner_redis_data<br/>• Queues: outbound_messages, document_ingestion")]
        end
    end

    %% WhatsApp Inbound Flow
    Farmer -->|1. WhatsApp Message| WhatsAppCloud
    WhatsAppCloud -->|2. Webhook Event POST :8000| Router
    Router -->|3. Read Profile & KBs: 5432| PG2
    
    %% In-Process Execution
    VKBCore2 -->|4. Get Query Vector: 443| OpenAI2
    VKBCore2 -->|5. Parallel Vector Query: 8000| Chroma2
    RAGCore2 -->|6. Grounded Answer Gen: 443| OpenAI2
    
    %% Outbound WhatsApp Dispatch Flow
    Router -->|7. Enqueue Outbound Task: 6379| Redis2
    Router -->|8. Immediate 200 OK Ack| WhatsAppCloud
    AppWorker -->|9. Consume Outbound Task: 6379| Redis2
    AppWorker -->|10. POST Message: 443| WhatsAppCloud
    WhatsAppCloud -->|11. Deliver Answer Message| Farmer

    %% Ingestion Flow
    Router -->|Upload PDF: 9000| MinIO2
    Router -->|Enqueue Ingest: 6379| Redis2
    IngWorker2 -->|Consume Ingest: 6379| Redis2
    IngWorker2 -->|Fetch PDF: 9000| MinIO2
    IngWorker2 -->|Embeddings: 443| OpenAI2
    IngWorker2 -->|Upsert Vectors: 8000| Chroma2
    IngWorker2 -->|Update Status: 5432| PG2
```

### 2.2 Mode 2 Sequence Diagram: Embedded WhatsApp Flow

```mermaid
sequenceDiagram
    autonumber
    actor Farmer as Farmer / WhatsApp User
    actor Admin as Sector Admin / Agronomist
    
    box rgb(240, 248, 255) Host App Container (xxxconnect: AgriConnect / WASHConnect)
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

### 2.3 Mode 2 Container Specification Table

| Container Name | Image / Source | Port Mapping | Volume / Storage | Primary Function |
|---|---|---|---|---|
| **`app`** | `xxxconnect/backend` (FastAPI) | `8000:8000` | Code bind mount | WhatsApp webhook receiver with embedded `akvo-rag-core` and `vector-kb-core` |
| **`app-worker`** | `xxxconnect` Celery worker | Internal | Code bind mount | Outbound WhatsApp message dispatcher with automatic retries |
| **`ingestion-worker`**| `vector-kb` Celery worker | Internal | Code bind mount | Sector document parser & vector embedder |
| **`postgres`** | `postgres:17-alpine` | `5432:5432` | `partner_pg_data:/var/lib/postgresql/data` | Partner CRM data, farmer profiles, prompt overlays, KB metadata |
| **`chromadb`** | `chromadb/chroma:latest` | `8000:8000` | `partner_chroma_data:/chroma/chroma` | Sector vector collections (`kb_1`, `kb_2`...) |
| **`minio`** | `minio/minio:latest` | `9000:9000` | `partner_minio_data:/data` | Object storage for partner PDFs |
| **`redis`** | `redis:7-alpine` | `6379:6379` | `partner_redis_data:/data` | Celery task broker for outbound WhatsApp & document ingestion |

---

## 3. Direct Architectural Comparison

| Dimension | Mode 1: Standalone `akvo-rag` + `vector-kb` | Mode 2: Embedded `xxxconnect` |
|---|---|---|
| **Primary Entrypoint** | Next.js Web UI (`http://localhost:3000`) | Meta WhatsApp Cloud API Webhook (`POST :8000`) |
| **In-Process RAG Libraries** | `akvo-rag-core` + `vector-kb-core` inside `backend` container | `akvo-rag-core` + `vector-kb-core` inside `app` container |
| **Response Mechanism** | Server-Sent Events (SSE) streaming tokens to UI | Asynchronous Celery worker dispatching to WhatsApp |
| **Ingestion Worker** | `ingestion-worker` (from `vector-kb`) | `ingestion-worker` (from `vector-kb`) |
| **Database Engine** | Single PostgreSQL 17 (Prompt & Document tables) | Single PostgreSQL 17 (Host CRM + Document tables) |
| **Vector Engine** | Single ChromaDB (Sub-100ms direct lookup) | Single ChromaDB (Sub-100ms direct lookup) |
| **Number of Workloads** | **3 workloads** (`frontend`, `backend`, `ingestion-worker`) | **3 workloads** (`app`, `app-worker`, `ingestion-worker`) |
