# Feature Specification: Developer Onboarding & Documentation Alignment

> **Feature ID:** `019_doc_503_developer_onboarding_and_architecture_alignment_spec`  
> **Task Ref:** `TASK-DOC-503`  
> **Target Branch:** `epic/rag-monorepo-mcp`  
> **Status:** `PROPOSED (Party Mode Approved)`  
> **Estimated Effort:** `1.5 hrs (Vibe-Coding) / 1.0 day (Traditional)`  
> **Author:** Antigravity Architect / Lead Technical Writer & DevEx Specialist  
> **Upstream Reference:** [docs/lld/container_based_rag_platform_lld.md](file:///Users/galihpratama/Sites/akvo-rag/docs/lld/container_based_rag_platform_lld.md) (Sections 7, 8, 9)

---

## 1. Overview & 5W1H Requirements Discovery

### 1.1 Problem Statement
The transformation of Akvo-RAG into a container-based monorepo introduces a new operational model: 7 core containers, Redis RPC request-reply queues, declarative `mcp_config.json`, service-owned Alembic schema isolation (`alembic_version` vs `alembic_version_vkb`), and MinIO S3 document storage.

Outdated documentation referencing MySQL 8.0, RabbitMQ, Celery, or FastMCP HTTP reconnect loops creates friction, misleads new developers, and increases onboarding time.

`TASK-DOC-503` updates all project documentation, quickstart manuals, architecture maps, and troubleshooting playbooks to align with the production architecture.

### 1.2 5W1H Discovery Lens

| Dimension | Specification |
|---|---|
| **Who** | New developers joining the team, open-source contributors, DevOps engineers, and system administrators. |
| **What** | Update `README.md`, `docs/dev-guide.md`, `docs/architecture_map.md`, `docs/admin-guide.md`, and `docs/troubleshooting.md` to reflect the 7-container topology and Redis queue IPC. |
| **Where** | `README.md`, `docs/dev-guide.md`, `docs/architecture_map.md`, `docs/admin-guide.md`, `docs/troubleshooting.md`. |
| **When** | **Phase 5, Step 3** — the final step of the migration epic. |
| **Why** | Guarantees that any new engineer can spin up the full platform in $< 15\text{ minutes}$, understand how to add an MCP tool, and execute migrations safely. |
| **How** | Markdown updates following `.agent/rules/docs-standard.md`, root-relative links, zero credentials, and verified CLI snippets. |

---

## 2. BMAD Party Mode Deliberation Synthesis 🎭

### 2.1 Four-Way Agent Council Consensus

* **🏗️ Winston (System Architect):**  
  Update `docs/architecture_map.md` with the definitive container diagram, port mappings (Frontend `:3000`, Backend `:8000`, ChromaDB `:8001` host $\rightarrow$ `:8000` container, MinIO `:9000` / `:9001`, Redis `:6379`, Postgres `:5432`), and Redis queue message contracts.

* **💻 Amelia (Senior Developer):**  
  Document both production and local development workflows clearly in `docs/dev-guide.md`:
  - Standard Production Boot: `docker compose up -d --build`
  - Hot-Reloading Development Boot: `docker compose -f docker-compose.dev.yml up -d --build`
  - Running Isolated Migrations: `docker exec backend alembic upgrade head` vs `docker exec vector-kb-mcp alembic upgrade head`.

* **🧪 Murat (Test Architect):**  
  Include deterministic verification commands in the guide so developers can immediately confirm healthy deployment:
  - Backend tests: `docker exec akvo-rag-backend-1 python -m pytest tests/unit -v`
  - Vector KB tests: `docker exec akvo-rag-vector-kb-mcp-1 pytest tests/ -v`
  - Evaluation suite: `./rag-evaluate`

* **🛡️ Rachel (Adversarial Security Red Team):**  
  Documentation Security Audit:
  1. Enforce that `.env.example` contains zero default production secrets.
  2. Document API key generation and tenant isolation mechanisms in `docs/admin-guide.md`.
  3. Include a security disclosure and vulnerability reporting section in `README.md`.

---

## 3. Documentation Touchpoint Specifications

### 3.1 `README.md`
- **7-Container Monorepo Overview**: Clear diagram and architecture highlights.
- **Quickstart Guide**:
  ```bash
  # 1. Clone & prepare environment
  cp .env.example .env
  
  # 2. Spin up local development environment (with hot reload)
  docker compose -f docker-compose.dev.yml up -d --build
  
  # 3. Seed prompt templates
  docker compose exec backend python -m app.seeder.seed_prompts
  
  # 4. Access Web UI at http://localhost:3000
  ```
- **Testing Commands & Evaluation Dashboard**.

---

### 3.2 `docs/dev-guide.md`
- **Hot-Reloading & Live Volume Mounts**: How local file changes sync into containers.
- **Alembic Schema Isolation**:
  - Core Backend: `backend/alembic.ini` using `alembic_version`.
  - Vector Microservice: `vector-kb-mcp/alembic.ini` using `alembic_version_vkb`.
- **How to Add a New MCP Tool**: Step-by-step guide on adding an entry to `backend/mcp_config.json` and attaching an async handler in `vector-kb-mcp/main.py`.

---

### 3.3 `docs/architecture_map.md`
- Complete container dependency graph.
- Redis RPC queue naming standard (`mcp:vector:requests`, `mcp:vector:responses:{id}`, `document_ingestion`).
- S3 MinIO bucket structure (`documents/kb_{id}/{doc_id}_{filename}`).

---

### 3.4 `docs/admin-guide.md` & `docs/troubleshooting.md`
- **Admin Guide**: Creating Knowledge Bases, managing App API keys, adjusting Prompt overlays.
- **Troubleshooting Playbook**:
  - Redis connection drops / timeout troubleshooting.
  - ChromaDB volume permission fixes.
  - MinIO connection verification.

---

## 4. Verification & Quality Gates

1. **Docs Standard Compliance (`.agent/rules/docs-standard.md`):**
   - Zero hardcoded local machine paths (e.g. `/Users/...`).
   - Root-relative or GitHub markdown links used throughout.
   - Zero exposed API keys, passwords, or tokens.
2. **Fresh Clone Dry-Run:**
   - Execute all README quickstart commands in sequence on a clean test environment to verify 100% accuracy.

---

## 5. Subtask Estimation & Breakdown

| Subtask ID | Description | Target Files | Vibe Est. | Trad. Est. | Confidence |
|---|---|---|:---:|:---:|:---:|
| `SUB-503.1` | Update `README.md` with 7-container topology & quickstart | `README.md` `[MODIFY]` | 0.4 hr | 0.3 day | High (99%) |
| `SUB-503.2` | Update `docs/dev-guide.md` & `docs/architecture_map.md` | `docs/dev-guide.md`, `docs/architecture_map.md` `[MODIFY]` | 0.5 hr | 0.3 day | High (99%) |
| `SUB-503.3` | Update `docs/admin-guide.md` & `docs/troubleshooting.md` | `docs/admin-guide.md`, `docs/troubleshooting.md` `[MODIFY]` | 0.4 hr | 0.3 day | High (99%) |
| `SUB-503.4` | Docs compliance audit & link verification | `docs/` `[VERIFY]` | 0.2 hr | 0.1 day | High (99%) |
| **TOTAL** | | | **1.5 hrs** | **1.0 day** | **High** |

---

## 6. Definition of Done (DoD)

- [ ] `README.md` and all 5 living documents in `docs/` reflect the 7-container architecture.
- [ ] Documentation complies with `.agent/rules/docs-standard.md` (root-relative links, zero secrets).
- [ ] A new engineer can follow the quickstart guide and start chatting in $< 15\text{ minutes}$.
