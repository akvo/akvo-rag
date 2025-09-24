from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.db.session import get_db
from app.core.security import get_api_key_user
from mcp_clients.kb_mcp_endpoint_service import KnowledgeBaseMCPEndpointService


router = APIRouter()


# TODO :: Need to refactor this route to use MCP related implementation
@router.get("/{knowledge_base_id}/query")
async def query_knowledge_base(
    *,
    db: Session = Depends(get_db),
    knowledge_base_id: int,
    query: str,
    top_k: int = 3,
    current_user: models.User = Depends(get_api_key_user),
) -> Any:
    """
    Query a specific knowledge base using API key authentication
    """
    kb = None
    try:
        kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
        kb = await kb_mcp_endpoint_service.get_kb(kb_id=knowledge_base_id)
    except Exception:
        pass

    if not kb:
        raise HTTPException(
            status_code=404,
            detail=f"Knowledge base {knowledge_base_id} not found",
        )

    try:
        # embeddings = EmbeddingsFactory.create()

        # vector_store = VectorStoreFactory.create(
        #     store_type=settings.VECTOR_STORE_TYPE,
        #     collection_name=f"kb_{knowledge_base_id}",
        #     embedding_function=embeddings,
        # )

        # results = vector_store.similarity_search_with_score(query, k=top_k)

        # response = []
        # for doc, score in results:
        #     response.append(
        #         {
        #             "content": doc.page_content,
        #             "metadata": doc.metadata,
        #             "score": float(score),
        #         }
        #     )

        # return {"results": response}
        raise HTTPException(
            status_code=400, detail="Feature not supported yet"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
