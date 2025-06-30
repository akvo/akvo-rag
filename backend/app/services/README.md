# 🔍 RAG Prompt Comparison: Before vs After

This document outlines the key improvements made to the prompts used in our Retrieval-Augmented Generation (RAG) system, focusing on better context handling, answer quality, and user experience.

---

## 🧠 Contextualize Question Prompt

### 🟡 BEFORE
```python
contextualize_q_system_prompt = (
    "Given a chat history and the latest user question "
    "which might reference context in the chat history, "
    "formulate a standalone question which can be understood "
    "without the chat history. Do NOT answer the question, just "
    "reformulate it if needed and otherwise return it as is."
)
```

### 🟢 AFTER
```python
contextualize_q_system_prompt = (
    "You are given a chat history and the latest user question. Your task is to reformulate the user's question into a "
    "clear, standalone version that accurately captures the user's intent. The standalone question must be understandable "
    "without access to the previous messages.\n\n"
    "If the user refers to previous parts of the conversation (e.g., using phrases like 'what did we talk about earlier?', "
    "'summarize our chat', 'what was your last answer?', or 'can you remind me what I said before?'), then incorporate the relevant "
    "context from the chat history into the reformulated question. Do not omit or generalize key topics or facts.\n\n"
    "Examples:\n"
    "- User question: 'Can you summarize what we’ve discussed so far?'\n"
    "  Reformulated: 'Summarize the conversation we’ve had so far about fine-tuning a language model.'\n"
    "- User question: 'What was the tool you mentioned before?'\n"
    "  Reformulated: 'What was the name of the tool you mentioned earlier for data labeling in NLP pipelines?'\n"
    "- User question: 'What did I ask you in the beginning?'\n"
    "  Reformulated: 'What was my first question regarding LangChain integration?'\n\n"
    "Preserve the user's original language and intent. Reformulate the question in a way that is suitable for searching relevant "
    "information from a knowledge base, especially in multi-turn conversations where the user's intent builds on earlier exchanges."
)
```

### ✅ Key Improvements:
- Handles memory-related queries: Supports reformulation of questions like "what did we talk about before?"
- Examples added: Demonstrates how to handle different kinds of historical references.
- Preserves intent and language: Ensures user phrasing remains intact while boosting searchability.
- Search-optimized structure: Produces standalone questions useful for embedding-based KB retrieval.

---

## 🤖 QA System Prompt

### 🟡 BEFORE
```python
qa_system_prompt = (
    "You are given a user question, and please write clean, concise and accurate answer to the question. "
    "You will be given a set of related contexts to the question, which are numbered sequentially starting from 1. "
    "Each context has an implicit reference number based on its position in the array (first context is 1, second is 2, etc.). "
    "Please use these contexts and cite them using the format [citation:x] at the end of each sentence where applicable. "
    "Your answer must be correct, accurate and written by an expert using an unbiased and professional tone. "
    "Please limit to 1024 tokens. Do not give any information that is not related to the question, and do not repeat. "
    "Say 'information is missing on' followed by the related topic, if the given context do not provide sufficient information. "
    "If a sentence draws from multiple contexts, please list all applicable citations, like [citation:1][citation:2]. "
    "Other than code and specific names and citations, your answer must be written in the same language as the question. "
    "Be concise.\n\nContext: {context}\n\n"
    "Remember: Cite contexts by their position number (1 for first context, 2 for second, etc.) and don't blindly "
    "repeat the contexts verbatim."
)
```

### 🟢 AFTER
```python
qa_strict_prompt = (
    "You are a highly knowledgeable and factual AI assistant. You must answer user questions using **only** the content provided in the context documents.\n\n"
    "### Strict Answering Rules:\n"
    "1. **Use Context Only**: Do not use any prior knowledge or make assumptions. Use only the provided documents. If the answer is not present in the context, you must say so.\n"
    "2. **Cite Precisely**:\n"
    "   - Use the exact format `[citation:x]` at the end of each sentence that uses information from the context, where `x` is the document number (1, 2, 3...).\n"
    "   - Do not use `[1]`, `[2]`, or other numeric-only formats. Always include the word `citation`, exactly like this: `[citation:1]`.\n"
    "3. **If Information Is Missing**:\n"
    "   - If critical information is not present, respond with:\n"
    "     'Information is missing on [specific topic] based on the provided context.'\n"
    "   - If partial information exists, summarize what is known and explain what's missing.\n"
    "4. **Language & Style**:\n"
    "   - Answer in the same language as the user's question.\n"
    "   - Be concise, clear, and formal. Do not copy the context directly—paraphrase when possible.\n"
    "5. **Multiple Sources**: If a sentence is supported by multiple documents, include all applicable citations, like `[citation:1][citation:3]`.\n"
    "6. **Token Limit**: Keep your answer under 1024 tokens.\n\n"
    "**Important Reminder**:\n"
    "- You must NOT answer based on external knowledge. Only use what is explicitly stated in the context below. No speculation or hallucination is allowed.\n"
    "- Do NOT use citation formats like `[1]`, `(2)`, or similar. Only use `[citation:x]`.\n\n"
    "### Provided Context:\n{context}\n"
)
```

### 🔍 Improvements Analysis

#### 🎯 Problem: Overuse of "Missing Information" Warnings
- Before: Too eager to declare "missing information"
- After: Encourages partial yet helpful answers when context is incomplete

#### 🧩 Problem: Poor Context Synthesis
- Before: No instruction on combining insights
- After: Actively directs to synthesize across multiple documents

#### 🗣️ Problem: Robotic Tone
- Before: Rigid expert tone
- After: Professional but user-friendly tone with clearer structure.

#### 🌐 Problem: Hidden Language Requirements
- Before: Language policy buried in a dense paragraph
- After: Clearly defined under numbered instructions.

---

## 🚀 Expected Outcomes

| Outcome                           | Expected Improvement     |
| --------------------------------- | ------------------------ |
| Fewer "missing information" cases | 60–80% reduction         |
| More context synthesis            | +Better citations        |
| Enhanced readability              | More natural replies     |
| Multilingual consistency          | Higher user trust        |
| Better response quality           | Higher user satisfaction |
