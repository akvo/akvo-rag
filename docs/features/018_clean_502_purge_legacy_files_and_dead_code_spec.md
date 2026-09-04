# Feature Specification: Purge Legacy Files, Dead Code & Unused Dependencies

> **Feature ID:** `018_clean_502_purge_legacy_files_and_dead_code_spec`  
> **Task Ref:** `TASK-CLEAN-502`  
> **Target Branch:** `epic/rag-monorepo-mcp`  
> **Status:** `PROPOSED (Party Mode Approved)`  
> **Estimated Effort:** `1.0 hr (Vibe-Coding) / 0.5 day (Traditional)`  
> **Author:** Antigravity Architect / Code Quality & Platform Hygiene Specialist  
> **Upstream Reference:** [docs/lld/container_based_rag_platform_lld.md](file:///Users/galihpratama/Sites/akvo-rag/docs/lld/container_based_rag_platform_lld.md) (Sections 8, 9)

---

## 1. Overview & 5W1H Requirements Discovery

### 1.1 Problem Statement
Following the completion of Option C across Phases 1 through 4, several legacy modules, deprecated discovery files, old Celery tasks, and unused Python dependencies remain in the repository. If left uncleaned, these dead artifacts confuse new developers, bloat container image build times, and introduce potential security vulnerabilities.

`TASK-CLEAN-502` permanently purges all obsolete legacy files, cleans `requirements.txt`, and executes an automated linter audit to guarantee zero broken imports or dead symbols across the entire monorepo.

### 1.2 5W1H Discovery Lens

| Dimension | Specification |
|---|---|
| **Who** | All backend developers, CI/CD pipeline, and future codebase maintainers. |
| **What** | Delete legacy FastMCP files, old Celery/RabbitMQ tasks, deprecated ScopingAgent, remove unused pip packages, and run linter validation. |
| **Where** | `backend/mcp_clients/`, `backend/app/tasks/`, `backend/app/services/`, `backend/requirements.txt`, monorepo root. |
| **When** | **Phase 5, Step 2** — after golden evaluation passes and before finalizing developer onboarding documentation. |
| **Why** | Minimizes Docker image sizes by ~250MB, eliminates security debt from unmaintained packages, and enforces clean codebase hygiene. |
| **How** | Atomic file deletions (`git rm`), dependency manifest cleanup, and repository-wide `ruff check .` / `flake8` execution. |

---

## 2. BMAD Party Mode Deliberation Synthesis 🎭

### 2.1 Four-Way Agent Council Consensus

* **🏗️ Winston (System Architect):**  
  Verification before deletion: Ensure zero active routers, workflows, or seeder scripts retain dangling imports from `mcp_discovery_manager`, `scoping_agent`, or `celery_app`. All MCP routing must be 100% verified through `MCPQueueDispatcher`.

* **💻 Amelia (Senior Developer):**  
  Clean requirements trimming: Pin dependencies cleanly in `backend/requirements.txt` and `vector-kb-mcp/requirements.txt`. Rebuild Docker images with `--no-cache` to ensure clean builds without leftover layers.

* **🧪 Murat (Test Architect):**  
  Run full regression test suite (`pytest tests/ -v`) immediately before and after file deletion to confirm that no test fixtures accidentally depended on legacy task or discovery files.

* **🛡️ Rachel (Adversarial Security Red Team):**  
  Scan for leftover secret or credential references in backup files (`.bak`, `.agriconnect_bak`) before deleting them. Run `pip audit` / Dependabot checks to ensure zero known high/critical CVEs remain in the final slim requirements.

---

## 3. Inventory of Files & Dependencies to Purge

### 3.1 Files to Delete (`[DELETE]`)

| File Path | Component | Reason for Deletion |
|---|---|---|
| `backend/mcp_discovery.json` | Core Gateway | Superseded by declarative `backend/mcp_config.json` |
| `backend/mcp_discovery.json.bak` | Core Gateway | Obsolete backup file |
| `backend/mcp_discovery.json.agriconnect_bak` | Core Gateway | Obsolete backup file |
| `backend/mcp_clients/fastmcp_client_service.py` | FastMCP Transport | Superseded by Redis Request-Reply IPC |
| `backend/mcp_clients/mcp_discovery_manager.py` | Dynamic Discovery | Superseded by `MCPConfigParser` |
| `backend/mcp_clients/mcp_servers_config.py` | Legacy Config | Superseded by `MCPConfigParser` |
| `backend/mcp_clients/rest_mcp_client_service.py` | Legacy REST MCP | Superseded by `MCPQueueDispatcher` |
| `backend/app/services/scoping_agent.py` | LangGraph | Redundant LLM scoping call purged in `TASK-MCP-304` |
| `backend/app/celery_app.py` | Background Tasks | Replaced by Redis native queues |
| `backend/app/tasks/upload_task.py` | Background Tasks | Replaced by MinIO S3 + Redis Ingestion Worker |
| `backend/app/tasks/chat_task.py` | Background Tasks | Replaced by direct LangGraph streaming |
| `backend/app/tasks/test_task.py` | Background Tasks | Deprecated Celery test task |
| `backend/app/tasks/__init__.py` | Background Tasks | Deprecated tasks package |
| `backend/entrypoint-celery.sh` | Container Entrypoint | Celery worker container removed from compose |

---

### 3.2 Dependencies to Remove from `backend/requirements.txt`

```diff
- mysql-connector-python>=8.0.33
- fastmcp==2.11.1
- celery==5.5.3
- pika
- kombu
- pymysql
- mysqlclient
```

---

## 4. Verification & Quality Gates

### 4.1 Linter & Import Audit Command
```bash
# Verify zero unresolved imports or dead symbols
docker exec akvo-rag-backend-1 python -m ruff check /app
docker exec akvo-rag-backend-1 python -m flake8 /app --max-line-length=100
```

### 4.2 Test Regression Gate
```bash
# Verify entire test suite passes post-cleanup
docker exec akvo-rag-backend-1 python -m pytest tests/ -v
docker exec akvo-rag-vector-kb-mcp-1 python -m pytest tests/ -v
```

---

## 5. Subtask Estimation & Breakdown

| Subtask ID | Description | Target Files | Vibe Est. | Trad. Est. | Confidence |
|---|---|---|:---:|:---:|:---:|
| `SUB-502.1` | Delete legacy discovery, FastMCP, and backup JSON files | `backend/mcp_clients/`, root `[DELETE]` | 0.2 hr | 0.1 day | High (99%) |
| `SUB-502.2` | Delete Celery app, task modules, and entrypoint scripts | `backend/app/tasks/`, `backend/entrypoint-celery.sh` `[DELETE]` | 0.2 hr | 0.1 day | High (99%) |
| `SUB-502.3` | Clean `backend/requirements.txt` and rebuild Docker containers | `backend/requirements.txt` `[MODIFY]` | 0.3 hr | 0.2 day | High (99%) |
| `SUB-502.4` | Run linter pass & regression test suites to verify zero broken imports | Monorepo root `[VERIFY]` | 0.3 hr | 0.1 day | High (99%) |
| **TOTAL** | | | **1.0 hr** | **0.5 day** | **High** |

---

## 6. Definition of Done (DoD)

- [ ] All 14 listed legacy files and backups are permanently deleted from git.
- [ ] Celery, RabbitMQ, MySQL, and FastMCP packages are removed from `requirements.txt`.
- [ ] `ruff check .` / `flake8` passes with zero unresolved import errors.
- [ ] All unit and integration test suites pass with 100% success rate.
