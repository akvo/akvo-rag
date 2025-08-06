import json
import base64
from typing import Optional, AsyncGenerator

from langchain.chains import (
    create_history_aware_retriever,
    create_retrieval_chain,
)
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
)
from langchain_core.messages import HumanMessage, AIMessage

from app.core.config import settings
from app.services.vector_store import VectorStoreFactory
from app.services.embedding.embedding_factory import EmbeddingsFactory
from app.services.llm.llm_factory import LLMFactory
from app.services.prompt_service import PromptService
from app.services.system_settings_service import SystemSettingsService


async def query_kbs_tool(
    manager, query: str, messages: list, db, strict_mode: Optional[bool] = True
) -> AsyncGenerator[str, None]:
    # 1. Ambil daftar KB dari MCP server
    kb_list = await manager.read_resource(
        server_name="knowledge_bases_mcp", uri="resource://knowledge_bases"
    )

    if not kb_list:
        yield f'0:"I don\'t have any knowledge base to help answer your question."\n'
        return

    knowledge_base_ids = [kb["id"] for kb in kb_list]

    # 2. Inisialisasi service
    prompt_service = PromptService(db=db)
    settings_service = SystemSettingsService(db=db)
    embeddings = EmbeddingsFactory.create()

    # 3. Siapkan vector store
    vector_stores = []
    for kb in kb_list:
        vector_store = VectorStoreFactory.create(
            store_type=settings.VECTOR_STORE_TYPE,
            collection_name=f"kb_{kb['id']}",
            embedding_function=embeddings,
        )
        if vector_store._store._collection.count() > 0:
            vector_stores.append(vector_store)

    if not vector_stores:
        yield f'0:"No active knowledge bases found."\n'
        return

    # 4. Ambil top_k dari setting
    top_k = settings_service.get_top_k()
    retriever = vector_stores[0].as_retriever(search_kwargs={"k": top_k})

    # 5. Inisialisasi LLM
    llm = LLMFactory.create()

    # 6. Contextualize question prompt
    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", prompt_service.get_full_contextualize_prompt()),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_q_prompt
    )

    # 7. QA prompt
    qa_system_prompt = (
        prompt_service.get_full_qa_strict_prompt()
        if strict_mode
        else prompt_service.get_full_qa_flexible_prompt()
    )
    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", qa_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )

    document_prompt = PromptTemplate.from_template("\n\n- {page_content}\n\n")
    question_answer_chain = create_stuff_documents_chain(
        llm,
        qa_prompt,
        document_variable_name="context",
        document_prompt=document_prompt,
    )

    # 8. Retrieval chain
    rag_chain = create_retrieval_chain(
        history_aware_retriever, question_answer_chain
    )

    # 9. Bentuk chat history
    chat_history = []
    for message in messages:
        if message["role"] == "user":
            chat_history.append(HumanMessage(content=message["content"]))
        elif message["role"] == "assistant":
            if "__LLM_RESPONSE__" in message["content"]:
                message["content"] = message["content"].split(
                    "__LLM_RESPONSE__"
                )[-1]
            chat_history.append(AIMessage(content=message["content"]))

    # 10. Jalankan RAG dan stream hasil
    async for chunk in rag_chain.astream(
        {"input": query, "chat_history": chat_history}
    ):
        if "context" in chunk:
            retrieved_docs = chunk["context"]
            serializable_context = [
                {
                    "page_content": context.page_content.replace('"', '\\"'),
                    "metadata": context.metadata,
                }
                for context in retrieved_docs
            ]

            escaped_context = json.dumps({"context": serializable_context})
            base64_context = base64.b64encode(
                escaped_context.encode()
            ).decode()
            yield f'0:"{base64_context}__LLM_RESPONSE__"\n'

        if "answer" in chunk:
            answer_chunk = chunk["answer"]
            escaped_chunk = answer_chunk.replace('"', '\\"').replace(
                "\n", "\\n"
            )
            yield f'0:"{escaped_chunk}"\n'
