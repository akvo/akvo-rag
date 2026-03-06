# Feature Document: RAG Follow-up Alignment Improvement

## Problem Statement
The RAG system currently fails to maintain context relevance for stylistic follow-up questions (e.g., "Can you explain in easy way?"). When such a request is made, the system reformulates the question and performs a fresh vector search. This often retrieves chunks that discuss practical implementations or pilots (where "simple" or "easy" terminology might appear) rather than the original subject matter, causing the LLM to deviate into off-topic answers.

### Example Failure
- **U**: What is living income?
- **AI**: (Correct technical definition)
- **U**: Can you explain in easy way?
- **AI**: (Lists countries with basic income pilots) -> **FAILURE: Off-topic and ignores the "easy explanation" request.**

## Proposed Solution
We need to enhance the **Dynamic Prompt Service** and specifically the **Contextualization Prompt** to better handle meta-requests (depth, style, simpler language).

### Goals
1. Ensure the contextualized question preserves the core subject matter.
2. Signal to the QA prompt that a stylistic change (e.g., "simple language") is requested.
3. Improve retrieval robustness for follow-up queries.

## User Impact
Users will experience a more natural, conversational flow where follow-up questions about depth or style don't break the system's focus.

## Risks & Mitigations
- **Context Overload**: Including too much history might confuse the LLM. Mitigation: Strict reformulation rules.
- **Retrieval Drift**: Small changes in phrasing can lead to completely different vector search results. Mitigation: Consider reuse of previous context for meta-requests.
