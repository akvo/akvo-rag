import json
import base64
import uuid

from typing import List, AsyncGenerator, Optional
from sqlalchemy.orm import Session
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
from app.models.chat import Message
from app.models.knowledge import KnowledgeBase, Document
from langchain.globals import set_verbose, set_debug
from app.services.vector_store import VectorStoreFactory
from app.services.embedding.embedding_factory import EmbeddingsFactory
from app.services.llm.llm_factory import LLMFactory
from app.services.prompt_service import PromptService
from app.services.system_settings_service import SystemSettingsService

set_verbose(True)
set_debug(True)


async def generate_response(
    query: str,
    messages: dict,
    knowledge_base_ids: List[int],
    chat_id: int,
    db: Session,
    max_history_length: Optional[int] = 10,
    generate_last_n_messages: Optional[bool] = False,
    strict_mode: Optional[bool] = True,
) -> AsyncGenerator[str, None]:
    try:
        """
        Since the RAG frontend sent all chat history on FE
        into generate_response, we need to reduce the length of the messages
        otherwise, the model will throw an error

        ### handle error
        This model's maximum context length is 8192 tokens.
        However, your messages resulted in 38669 tokens.
        Please reduce the length of the messages
        ### eol handle error
        """

        prompt_service = PromptService(db=db)
        settings_service = SystemSettingsService(db=db)

        if not generate_last_n_messages and not messages.get("id", None):
            messages_id = uuid.uuid4()
            messages["id"] = messages_id

        # Get the only last 10 messages
        if not generate_last_n_messages and messages.get("messages", None):
            messages_tmp = messages["messages"]
            messages["messages"] = messages_tmp[-max_history_length:]

        # Generate last n message in backend
        if generate_last_n_messages:
            new_messages_id = uuid.uuid4()
            messages = {"id": new_messages_id, "messages": []}
            # limit last n messages
            all_history_messages = (
                db.query(Message)
                .filter(Message.chat_id == chat_id)
                .order_by(Message.created_at.desc())
                .limit(max_history_length)
                .all()
            )
            for message in all_history_messages:
                messages["messages"].append(
                    {
                        "role": message.role,
                        "content": message.content,
                    }
                )
            if not all_history_messages:
                messages["messages"].append({"role": "user", "content": query})
                print(messages, "generate n last message")
        # EOL generate last n message in backend

        # Create user message
        user_message = Message(content=query, role="user", chat_id=chat_id)
        db.add(user_message)
        db.commit()

        # Create bot message placeholder
        bot_message = Message(content="", role="assistant", chat_id=chat_id)
        db.add(bot_message)
        db.commit()

        # Get knowledge bases and their documents
        knowledge_bases = (
            db.query(KnowledgeBase)
            .filter(KnowledgeBase.id.in_(knowledge_base_ids))
            .all()
        )

        # Initialize embeddings
        embeddings = EmbeddingsFactory.create()

        # Create a vector store for each knowledge base
        vector_stores = []
        for kb in knowledge_bases:
            documents = (
                db.query(Document)
                .filter(Document.knowledge_base_id == kb.id)
                .all()
            )
            if documents:
                # Use the factory to create the appropriate vector store
                vector_store = VectorStoreFactory.create(
                    # 'chroma' or other supported types
                    store_type=settings.VECTOR_STORE_TYPE,
                    collection_name=f"kb_{kb.id}",
                    embedding_function=embeddings,
                )
                print(
                    f"Collection {f'kb_{kb.id}'} count:",
                    vector_store._store._collection.count(),
                )
                vector_stores.append(vector_store)

        if not vector_stores:
            error_msg = (
                "I don't have any knowledge base to help answer your question."
            )
            yield f'0:"{error_msg}"\n'
            yield 'd:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n'
            bot_message.content = error_msg
            db.commit()
            return

        # Get global top_k setting and use it for vector retrieval
        top_k = settings_service.get_top_k()
        retriever = vector_stores[0].as_retriever(search_kwargs={"k": top_k})

        # Initialize the language model
        llm = LLMFactory.create()

        # Create contextualize question prompt
        contextualize_q_system_prompt = (
            prompt_service.get_full_contextualize_prompt()
        )

        contextualize_q_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", contextualize_q_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )

        # Create history aware retriever
        history_aware_retriever = create_history_aware_retriever(
            llm, retriever, contextualize_q_prompt
        )

        # Create QA prompt
        if strict_mode:
            qa_system_prompt = prompt_service.get_full_qa_strict_prompt()
        else:
            qa_system_prompt = prompt_service.get_full_qa_flexible_prompt()

        qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", qa_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )

        # 修改 create_stuff_documents_chain 来自定义 context 格式
        document_prompt = PromptTemplate.from_template(
            "\n\n- {page_content}\n\n"
        )

        # Create QA chain
        question_answer_chain = create_stuff_documents_chain(
            llm,
            qa_prompt,
            document_variable_name="context",
            document_prompt=document_prompt,
        )

        # Create retrieval chain
        rag_chain = create_retrieval_chain(
            history_aware_retriever,
            question_answer_chain,
        )

        # Generate response
        chat_history = []
        for message in messages["messages"]:
            if message["role"] == "user":
                chat_history.append(HumanMessage(content=message["content"]))
            elif message["role"] == "assistant":
                # if include __LLM_RESPONSE__, only use the last part
                if "__LLM_RESPONSE__" in message["content"]:
                    message["content"] = message["content"].split(
                        "__LLM_RESPONSE__"
                    )[-1]
                chat_history.append(AIMessage(content=message["content"]))

        full_response = ""
        async for chunk in rag_chain.astream(
            {"input": query, "chat_history": chat_history}
        ):
            if "context" in chunk:
                retrieved_docs = chunk["context"]
                serializable_context = []
                for context in retrieved_docs:
                    serializable_doc = {
                        "page_content": context.page_content.replace(
                            '"', '\\"'
                        ),
                        "metadata": context.metadata,
                    }
                    serializable_context.append(serializable_doc)

                # 先替换引号，再序列化
                escaped_context = json.dumps({"context": serializable_context})

                # 转成 base64
                base64_context = base64.b64encode(
                    escaped_context.encode()
                ).decode()

                # 连接符号
                separator = "__LLM_RESPONSE__"

                yield f'0:"{base64_context}{separator}"\n'
                full_response += base64_context + separator

            if "answer" in chunk:
                answer_chunk = chunk["answer"]
                full_response += answer_chunk
                # Escape quotes and use json.dumps to properly handle special characters
                escaped_chunk = answer_chunk.replace('"', '\\"').replace(
                    "\n", "\\n"
                )
                yield f'0:"{escaped_chunk}"\n'

        # Update bot message content
        bot_message.content = full_response
        db.commit()

    except Exception as e:
        error_message = f"Error generating response: {str(e)}"
        print(error_message)
        yield "3:{text}\n".format(text=error_message)

        # Update bot message with error
        if "bot_message" in locals():
            bot_message.content = error_message
            db.commit()
    finally:
        db.close()
