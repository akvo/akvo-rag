# Research Findings: Technical Deep Dive (Advanced Extraction & Chunking)

- **Date**: 2026-03-09
- **Topic**: Data Engineering for RAG
- **Sources**: [RAG Zero to Hero Guide](https://github.com/KalyanKS-NLP/rag-zero-to-hero-guide)

## 📊 1. Data Extraction (The "Garbage In, Garbage Out" Fix)

### **Why we need it?**
Most RAG failures (~40%) start at the extraction phase. Simple PDF scraping often breaks tables, loses headers, and merges footnotes into body text, creating "hallucination bait" for the AI.

### **How it works (Advanced Tools):**
- **Docling (IBM)**: A layout-aware parser. It doesn't just read text; it understands blocks, headers, and tables, converting them into clean Markdown.
- **PyMuPDF4LLM**: Optimized for converting PDFs to Markdown specifically for RAG, preserving the hierarchical structure.
- **LlamaParse**: Specialized for complex multi-column layouts and images within documents.

### **Impact on our system**:
Improved extraction ensures that when the AI searches for a "Table of Specs," it receives a structured table rather than a random string of numbers.

---

## 🧩 2. Advanced Chunking (The "Context Preservation" Fix)

### **Why we need it?**
Standard fixed-size chunking (e.g., split every 500 characters) is blind to content. It often cuts a critical sentence in half, making the chunk meaningless for retrieval.

### **How it works (New Techniques):**
- **Semantic Chunking**: Uses embeddings to find where a "thought" ends. It splits the document at natural thematic breaks.
- **Late Chunking**: This is a revolutionary optimization. we embed the entire document at once (capturing global context) before splitting. Each resulting chunk "remembers" its relationship to the whole document.
- **Agentic Chunking**: Uses a small, fast LLM to decide where the logically "best" break points are.

### **Impact on our system**:
Higher retrieval precision. The search engine finds "complete thoughts" rather than "sentence fragments."

---

## 📚 3. Critical Research Papers (The "RAG Blueprint")

We should align our development with these two seminal 2024 papers:
1. **"Seven Failure Points When Engineering a RAG System"**: Provides a checklist of where systems fail (e.g., "The retrieved context does not contain the answer").
2. **"Searching for Best Practices in RAG"**: A systematic study that proves **Reranking** and **Hybrid Search** provide the highest ROI for accuracy.

## 🛠️ Proposed Integration
In **Sprint 2/3**, we should evaluate replacing our standard `PyCard` extraction logic with **Docling** and testing **Semantic Chunking** on our larger knowledge bases.
