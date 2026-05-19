# Brainstorming: Reprioritization Analysis (Phase 1 vs Phase 3)

- **Date**: 2026-03-09
- **Agents**: Mary (Analyst) 📊, John (PM) 📋, Winston (Architect) 🏗️

## ⚖️ The Dilemma
We have two paths forward:
1.  **Path A (Original)**: Focus on **Speed & UI Transparency** (Parallel Search, Reranking, Caching, Status Streaming).
2.  **Path B (Reprioritized)**: Focus on **Foundational Accuracy** (Docling Extraction, Semantic Chunking, Late Chunking).

---

## 🔍 ROI Comparison

| Feature | Effort | Impact on UX | Impact on Accuracy |
| :--- | :--- | :--- | :--- |
| **Status Streaming** | Low | ⭐⭐⭐⭐⭐ (Feel) | None |
| **Parallel Search** | Med | ⭐⭐⭐⭐ (Speed) | None |
| **Docling Extraction** | Med | None | ⭐⭐⭐⭐⭐ (Quality) |
| **Semantic Chunking** | High | None | ⭐⭐⭐⭐ (Quality) |
| **FlashRank Rerank** | Low | None | ⭐⭐⭐⭐ (Quality) |

---

## �️ Technical Effort & Location (Winston's Audit)

### **1. Advanced Extraction (Docling / PyMuPDF4LLM)**
- **Repo**: `vector-knowledge-base-mcp-server`
- **Location**: `main/app/services/document_processor.py` (L360-370)
- **Effort**: Medium. Need to add `docling` to `requirements.txt` and refactor the `if ext == ".pdf"` logic to use the new parser.

### **2. Semantic Chunking**
- **Repo**: `vector-knowledge-base-mcp-server`
- **Location**: `main/app/services/document_processor.py` (L375-380)
- **Effort**: Medium. Replace `RecursiveCharacterTextSplitter` with `SemanticChunker` (requires an embedding model to compute breaks).

### **3. Parallel Retrieval (Keep in Sprint 2)**
- **Repo**: `vector-knowledge-base-mcp-server`
- **Location**: `main/app/api/mcp.py` (Drafting asyncio logic)
- **Effort**: Low/Medium. This is already planned and provides the "Speed" win.

## � Final Recommendation: "The Hybrid Foundation"
We should merge Phase 1 and Phase 3 into a single **"Accuracy & Performance"** Sprint:
1.  **DATA**: Implement **Docling** (Extraction) & **Semantic Chunking**. (Foundation)
2.  **RETRIEVAL**: Implement **Parallel Search** & **FlashRank Reranking**. (Accuracy + Speed)
3.  **UI**: Keep **Status Streaming** as a "Stretch Goal" (it's nice but aesthetic).
4.  **DEFER**: **Semantic Cache** (let's get accuracy perfect before we start caching answers).
