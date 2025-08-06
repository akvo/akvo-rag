from fastmcp import FastMCP
from app.db.session import SessionLocal
from app.models.knowledge import KnowledgeBase, Document
from app.services.vector_store import VectorStoreFactory
from app.services.embedding.embedding_factory import EmbeddingsFactory
from app.core.config import settings


mcp = FastMCP(name="Kowledge Bases MCP Server")


@mcp.custom_route("/health", methods=["GET"])
def health_check():
    return {"status": "ok"}


@mcp.resource("resource://knowledge_bases")
def list_all_knowledge_bases():
    """
    List all knowledge bases.
    """
    db = SessionLocal()
    try:
        embeddings = EmbeddingsFactory.create()

        kbs = (
            db.query(KnowledgeBase)
            .join(Document, Document.knowledge_base_id == KnowledgeBase.id)
            .group_by(KnowledgeBase.id)
            .all()
        )

        available_kbs = []
        for kb in kbs:
            vector_store = VectorStoreFactory.create(
                store_type=settings.VECTOR_STORE_TYPE,
                collection_name=f"kb_{kb.id}",
                embedding_function=embeddings,
            )
            chunk_count = vector_store._store._collection.count()
            if chunk_count > 0:
                available_kbs.append(
                    {
                        "id": kb.id,
                        "name": kb.name,
                        "description": kb.description,
                        "document_count": len(kb.documents),
                        "chunk_count": chunk_count,
                    }
                )

        return available_kbs
    finally:
        db.close()
        return []


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8700,
        log_level="debug",
    )
