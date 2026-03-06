# Feature Document: Context Re-ranking Service

**Agent**: John (Product Manager)
**Status**: Ideation / Draft

## 1. Problem Statement
Vector databases (like Chroma or Pinecone) use "Semantic Search" to find similar chunks, but they are not always precise. Often, the top-k results (e.g., top 10) contain "noise"—chunks that are mathematically similar but contextually irrelevant to the specific user question.

Currently, we send these raw chunks directly to the LLM. This leads to:
- **Accuracy Loss**: The LLM might hallucinate based on "noisy" or less relevant chunks.
- **Token Waste**: We pay for tokens that don't help answer the question.
- **Context Window Pressure**: If we retrieve 20 chunks, we hit the LLM's context limit faster without necessarily improving the answer.

## 2. Proposed Solution: Two-Stage Retrieval
Implement a **Re-ranker** step between retrieval and generation.
1. **Stage 1 (Retrieval)**: Ask the Vector DB for a broad set of candidates (e.g., top 25).
2. **Stage 2 (Re-ranking)**: Pass 25 chunks + query to a high-precision `Cross-Encoder` model (e.g., BGE-Reranker or Cohere).
3. **Filtering**: Only the top 5 re-ranked chunks are sent to the LLM for the final answer.

## 3. Analysis for Management

### Pros
- **Superior Accuracy**: Re-rankers are much better at understanding the *relationship* between a user's question and a document chunk than standard vector distance.
- **Reduced Hallucinations**: By filtering out the "noise," the LLM is less likely to get confused by tangentially related info.
- **Token Efficiency**: Instead of sending 10-15 raw chunks to capture the right answer, we only send 3-5 high-quality re-ranked chunks.
- **Context Optimization**: Allows us to use a smaller context window, making responses faster and cheaper.

### Cons
- **Additional Latency**: Adds a small processing step (typically 100-300ms) after retrieval but before the LLM starts streaming.
- **Compute Cost**: Requires either a local GPU-bound service (BGE) or an external API call (Cohere/FlashRank).
- **Service Dependency**: Introducing a new component in the `query_answering_workflow`.

### Alternatives
| Alternative | Description | Comparison |
| :--- | :--- | :--- |
| **Pure Vector Search** | Just retrieve top 5 and pray. | **Less Accurate**: High risk of missing the best snippet if it's ranked 6th or 7th by the vector DB. |
| **LLM Filtering** | Use GPT-3.5 to filter the chunks. | **Expensive & Slow**: Calling an LLM twice for one question is much more expensive than a re-ranker. |
| **Hybrid Search** | Combine keyword (BM25) + vector search. | **Halfway Measure**: Helps with specific terms but doesn't solve the "noise" problem as effectively as a re-ranker. |

## 4. Industry Context & Best Practices
How others solve this:
- **Cohere Rerank**: The gold standard API for this. It allows you to send a query and a list of documents and returns them sorted by relevance. It's used by major enterprises to fix "retrieval bloat."
- **LlamaIndex/LangChain**: These frameworks implement "Node Postprocessors" that act as a filter after the initial vector search.
- **BGE-Reranker**: A top-performing open-source model (from BAAI) that can be run locally. It’s a "Cross-Encoder," which means it looks at the query and document *together* to find deep semantic relationships that standard search misses.
- **Best Practice: "Recall-Heavy Retrieval"**: Best practices suggest retrieving 50-100 documents initially (optimizing for high recall) and then using the Re-ranker to pick the top 5 (optimizing for high precision).

## 5. Goals & Requirements
- **[MUST]** Integrate a Re-ranking node in the `query_answering_workflow`.
- **[MUST]** Support for both local (BGE/FlashRank) and remote (Cohere) re-rankers.
- **[MUST]** Configurable "Top-K" for both initial retrieval and final re-ranked subset.
- **[SHOULD]** Measurement markers to track the accuracy boost (e.g., using RAGAS scores).

## 6. User Impact
- **End Users**: Answers will feel much more "on point" and intelligent.
- **Developers**: Better control over which parts of the documentation are being prioritized.

## 6. Risks & Mitigations
- **Risk**: Latency increase.
- **Mitigation**: Use a fast cross-encoder (like BGE-M3 small) or perform re-ranking in parallel with other pre-processing tasks.
