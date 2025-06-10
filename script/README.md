# 📚 Table of Contents

- [📚 Table of Contents](#-table-of-contents)
- [🤖 UNEP Knowledge Base import script](#-unep-knowledge-base-import-script)
  - [🔐 Environment Variables](#-environment-variables)
  - [🚀 Running the Script](#-running-the-script)
  - [📁 Directory Structure](#-directory-structure)
- [🤖 Create or Update User script](#-create-or-update-user-script)
  - [🚀 Usage](#-usage)
  - [⚙️ Script flow:](#️-script-flow)
    - [Example](#example)

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

---

# 🤖 Create or Update User script

This script helps create or update user quickly in the system, ensuring user records are set up correctly for authentication and access control. It can also assign superuser status for administrative privileges.

## 🚀 Usage

The `add_user.py` script allows you to create or update a user account in the system’s user database (or service).

```bash
./dev.sh exec script python -m add_user
```

## ⚙️ Script flow:
  1. Prompt for Email
      The script will ask for the user's email address.
  2. Prompt for Superuser Status
      You’ll be asked whether the user should be a superuser (y for yes, n for no).
  3. User Creation/Update
      - The script will either create a new user or update an existing user with the given email.
      - The username and password will both be set to the email address as a default (consider changing the password later for security).

### Example

```bash
=== Create or Update User ===
Email: john_doe@example.com
Is Super User? (y/n): y
```

This creates or updates the user `john_doe@example.com` and marks them as a superuser.