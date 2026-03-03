# User Guide: Akvo RAG

Welcome to the Akvo RAG User Guide. This document provides instructions on how to effectively use and manage your RAG system.

## 1. Getting Started
(Brief overview of logging in and starting a chat)

## 2. Knowledge Base Management
(How to upload documents and manage KBs)

## 3. Advanced Features

### 3.1 Self-Healing & Context Management
Akvo RAG includes advanced "self-healing" capabilities to ensure stable conversations even with large document sets:

- **Automatic Context Stripping**: The system automatically identifies and removes internal retrieval metadata from your chat history before sending it to the AI. This prevents "Context Overflow" errors (`400 BadRequest`) and ensures that you can have long, multi-turn conversations without hitting token limits.
- **Robust Workflow Nodes**: The backend query engine is designed to be "error-aware." If a specific step (like retrieving from a database or contextualizing a query) fails due to a transient API issue, the system will gracefully skip subsequent steps and provide a helpful fallback response instead of crashing.
- **Targeted Citations**: Even though internal data is stripped for the AI's "memory," your citations in the UI remain intact and accurate.

### 3.2 Query Modes (ASQ vs USQ)
- **ASQ (Agent-Scoped Query)**: Let the AI decide which KB to use.
- **USQ (User-Scoped Query)**: You pick the KB explicitly.

## 4. Troubleshooting
(Common issues and how to resolve them)

- **"I'm having trouble with that right now"**: This is a graceful fallback. Usually, a retry of the message will solve it if the underlying API was momentarily unreachable.
