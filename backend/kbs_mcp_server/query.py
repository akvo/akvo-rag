import json
import base64
from typing import List
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.core.config import settings
from app.models.knowledge import KnowledgeBase, Document
from app.services.vector_store import VectorStoreFactory
from app.services.embedding.embedding_factory import EmbeddingsFactory
from app.services.system_settings_service import SystemSettingsService


async def query_kbs(query: str, knowledge_base_ids: List[int]):
    db: Session = SessionLocal()
    try:
        settings_service = SystemSettingsService(db=db)

        knowledge_bases = (
            db.query(KnowledgeBase)
            .filter(KnowledgeBase.id.in_(knowledge_base_ids))
            .all()
        )
        if not knowledge_bases:
            return {
                "context": None,
                "note": "No active knowledge base found for given IDs.",
            }

        embeddings = EmbeddingsFactory.create()

        # Ambil KB terakhir
        kb = knowledge_bases[-1]
        documents = (
            db.query(Document)
            .filter(Document.knowledge_base_id == kb.id)
            .all()
        )
        if not documents:
            return {
                "context": None,
                "note": f"Knowledge base {kb.id} is empty.",
            }

        # Vector store
        vector_store = VectorStoreFactory.create(
            store_type=settings.VECTOR_STORE_TYPE,
            collection_name=f"kb_{kb.id}",
            embedding_function=embeddings,
        )
        retriever = vector_store.as_retriever(
            search_kwargs={"k": settings_service.get_top_k()}
        )

        # Hanya ambil dokumen relevan
        retrieved_docs = await retriever.aget_relevant_documents(query)

        # Encode context biar aman lewat network
        serializable_context = [
            {"page_content": doc.page_content, "metadata": doc.metadata}
            for doc in retrieved_docs
        ]
        base64_context = base64.b64encode(
            json.dumps({"context": serializable_context}).encode()
        ).decode()

        return {"context": base64_context}

    except Exception as e:
        return {"context": None, "note": f"Error: {str(e)}"}
    finally:
        db.close()
