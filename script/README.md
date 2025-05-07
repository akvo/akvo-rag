# 📚 Table of Contents

- [📚 Table of Contents](#-table-of-contents)
- [🤖 UNEP Knowledge Base import script](#-unep-knowledge-base-import-script)
  - [🔐 Environment Variables](#-environment-variables)
  - [🚀 Running the Script](#-running-the-script)
  - [📁 Directory Structure](#-directory-structure)

---

# 🤖 UNEP Knowledge Base import script

This script automates the process of collecting, saving, and uploading PDF documents from [GlobalPlasticsHub](https://globalplasticshub.org) into a RAG (Retrieval-Augmented Generation) system.

This Python script supports three main operation modes:

1. **CSV Only** – Save PDF URLs to a CSV file.
2. **CSV + Download** – Save URLs and download the corresponding PDFs.
3. **Full Process** – Save URLs, download PDFs, and upload/process them in RAG.

## 🔐 Environment Variables

Before running the script, set RAG credentials in your shell or environment:

``` bash
export RAG_USERNAME="rag_admin"
export RAG_PASSWORD="RAGadmin1"
```

## 🚀 Running the Script

To execute the script:

```bash
./dev.sh exec script python -m kb_init_unep
```

You will be prompted to:
- Choose the operation mode:
  1: Save PDF URLs to CSV only.
  2: Save to CSV and download PDFs.
  3: Full process (CSV + download + upload to RAG).

- Enter the number of documents to import.
- Provide a description for the RAG knowledge base.

## 📁 Directory Structure
```bash
./downloads/unep/unep_files.csv – Stores PDF URLs and offsets.
./downloads/unep/ – Folder where downloaded PDF files are saved.
```