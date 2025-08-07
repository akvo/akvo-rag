import json
import base64
from typing import List
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from app.core.config import settings
from app.models.knowledge import KnowledgeBase, Document
from app.services.vector_store import VectorStoreFactory
from app.services.embedding.embedding_factory import EmbeddingsFactory
from app.services.llm.llm_factory import LLMFactory
from app.services.prompt_service import PromptService
from app.services.system_settings_service import SystemSettingsService


async def query_kbs_simple(query: str, knowledge_base_ids: List[int]):
    db: Session = SessionLocal()
    try:
        prompt_service = PromptService(db=db)
        settings_service = SystemSettingsService(db=db)

        knowledge_bases = (
            db.query(KnowledgeBase)
            .filter(KnowledgeBase.id.in_(knowledge_base_ids))
            .all()
        )
        if not knowledge_bases:
            return {
                "context": None,
                "answer": "No active knowledge base found for given IDs.",
            }

        embeddings = EmbeddingsFactory.create()

        kb = knowledge_bases[-1]
        documents = (
            db.query(Document)
            .filter(Document.knowledge_base_id == kb.id)
            .all()
        )
        if not documents:
            return {
                "context": None,
                "answer": f"Knowledge base {kb.id} is empty.",
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

        # Init LLM
        llm = LLMFactory.create()

        qa_system_prompt = prompt_service.get_full_qa_strict_prompt()
        qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", qa_system_prompt),
                ("human", "{input}"),
            ]
        )

        # Format document context
        document_prompt = PromptTemplate.from_template(
            "\n\n- {page_content}\n\n"
        )

        question_answer_chain = create_stuff_documents_chain(
            llm,
            qa_prompt,
            document_variable_name="context",
            document_prompt=document_prompt,
        )
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)

        result = await rag_chain.ainvoke({"input": query})

        # Encode context
        retrieved_docs = result.get("context", [])
        serializable_context = [
            {"page_content": doc.page_content, "metadata": doc.metadata}
            for doc in retrieved_docs
        ]
        base64_context = base64.b64encode(
            json.dumps({"context": serializable_context}).encode()
        ).decode()

        return {"context": base64_context, "answer": result.get("answer", "")}

    except Exception as e:
        return {"context": None, "answer": f"Error: {str(e)}"}
    finally:
        db.close()
