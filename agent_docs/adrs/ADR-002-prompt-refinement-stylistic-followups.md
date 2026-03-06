# ADR-002: Prompt Refinement for Stylistic Follow-ups

## Status
Proposed

## Context
When users ask stylistic follow-up questions (e.g., "explain in simple terms"), the current RAG system often performs a fresh vector search using the simplified request. This leads to "Retrieval Drift," where the search finds irrelevant documents that contain implementation-related keywords like "simple" or "easy" rather than the core subject matter.

## Decision
We will enhance the **Contextualization Prompt** to explicitly handle meta-requests (style, depth, simpler language) by:
1.  **Anchor Phrases**: Ensuring the contextualized question always contains the core "subject" from previous turns as an anchor.
2.  **Meta-Tags**: If a stylistic change is requested, the contextualizer will append a meta-instruction (e.g., `[STYLE: SIMPLE]`) or include specific keywords that the QA prompt is trained to recognize.
3.  **Search Neutrality**: The reformulated query for vector search should prefer subject-matter keywords over stylistic ones to maintain retrieval consistency.

## Technical Implementation
- Update `backend/app/services/prompt_service.py` with a more robust `static_context_rule`.
- Add a new "Stylistic Refinement" section to the `contextualize_q_system_prompt`.
- Update `backend/app/constants/prompt_constant.py` to support these changes.

## Consequences
- **Positive**: More accurate follow-up responses; reduced retrieval drift.
- **Negative**: Slight increase in prompt tokens for contextualization.
- **Risk**: Over-contextualization might lead to overly broad search queries if not carefully tuned.
