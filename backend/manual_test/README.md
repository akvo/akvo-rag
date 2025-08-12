# How to Run the Manual MCP Flow Test

This guide explains how to prepare and run the `manual_test/test_mcp_flow.py` script to manually test the MCP flow with the Image RAG MCP server.

---

## Prerequisites

You need the following running before the test:

- **Image RAG MCP server** (with indexed images)
- **Akvo RAG backend** (to run the test script)
- **Chroma DB** (shared by both MCP servers)
- A **valid Chat ID** from Akvo RAG UI

---

## Step 1 — Prepare Image Dataset

1. Inside the `image-rag-mcp` folder, create a `dataset` directory.
2. Place your image folders inside `dataset` using the following structure:

```bash
image-rag-mcp/dataset
└── pest_disease
    ├── cashew anthracnose
    │   ├── anthracnose10_.jpg
    │   ├── anthracnose2_.jpg
    │   └── ... more images
    ├── cashew gumosis
    │   ├── gumosis10_.jpg
    │   ├── gumosis2_.jpg
    │   └── ... more images
    ├── cashew healthy
    │   ├── healthy8_.jpg
    │   ├── healthy9_.jpg
    │   └── ... more images
    └── cashew leaf miner
        ├── leaf miner8_.jpg
        ├── leaf miner9_.jpg
        └── ... more images
```

## Step 2 — Run Image Indexing

From inside the **`image-rag-mcp` container**, run:

```bash
python -m script.indexing
```

Wait until the indexing process is complete before continuing.

## Step 3 — Get a Chat ID
1. Open the Akvo RAG UI.
2. Create a new chat (you can select any random KB).
3. Copy the generated Chat ID.

## Step 4 — Update the Test Script
1. Open manual_test/test_mcp_flow.py.
2. Locate the variable where the Chat ID is stored.
3. Replace it with the Chat ID from Step 3.

## Step 5 — Run the MCP Flow Test
From inside the backend container, run:
```bash
python -m manual_test.test_mcp_flow
```

## ✅ Expected Outcome
If everything is set up correctly, the script will:
- Send the test query through the MCP flow
- Call the relevant MCP server tool
- Return the processed result
- You can check the result from the Chat window (Akvo RAG UI) that pointed to the Chat ID from step 3.