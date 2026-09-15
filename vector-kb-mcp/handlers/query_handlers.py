import dataclasses
from typing import Any, Dict, Optional

from retriever.chroma_retriever import ChromaRetriever


async def handle_query_kb(
    args: Dict[str, Any], retriever: Optional[ChromaRetriever] = None
) -> Dict[str, Any]:
    """Query knowledge base using ChromaRetriever vector search."""
    if not retriever:
        raise RuntimeError("ChromaRetriever is not initialized")

    query = args.get("query", "")
    kb_ids = args.get("kb_ids", [])
    top_k = args.get("top_k", 4)
    score_threshold = args.get("score_threshold")

    chunks = await retriever.search(
        query=query,
        kb_ids=kb_ids,
        top_k=top_k,
        score_threshold=score_threshold,
    )

    formatted_chunks = [
        (
            dataclasses.asdict(c)
            if dataclasses.is_dataclass(c)
            else c.__dict__
        )
        for c in chunks
    ]
    return {"chunks": formatted_chunks}
