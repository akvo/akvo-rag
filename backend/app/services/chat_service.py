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

        # Use first vector store for now
        retriever = vector_stores[0].as_retriever()
        # After creating retriever
        # retriever = vector_stores[0].as_retriever(
        #     search_type="similarity_score_threshold",
        #     search_kwargs={"score_threshold": 0.7, "k": 5},
        # )

        # Initialize the language model
        llm = LLMFactory.create()

        # Create contextualize question prompt
        contextualize_q_system_prompt = (
            "You are given a chat history and the user's latest question. Your task is to rewrite the user's input as a clear, "
            "standalone question that fully captures their intent. The reformulated question must be understandable on its own, "
            "without requiring access to earlier parts of the conversation.\n\n"
            "If the user refers to earlier messages or prior context (e.g., 'what did we talk about?', 'summarize our chat', "
            "'what was your last response?', or 'can you remind me what I said before?'), incorporate the relevant details from the "
            "chat history into the rewritten question. Be precise—do not omit specific topics, facts, or tools mentioned earlier.\n\n"
            "Your reformulated question should:\n"
            "1. Retain the user's original language and tone.\n"
            "2. Be specific and context-aware.\n"
            "3. Be suitable for use in retrieval or question-answering over a knowledge base.\n\n"
            "Examples:\n"
            "- User: 'Can you summarize what we’ve discussed so far?'\n"
            "  Reformulated: 'Summarize our conversation so far about fine-tuning a language model.'\n"
            "- User: 'What was the tool you mentioned before?'\n"
            "  Reformulated: 'What was the name of the tool you mentioned earlier for data labeling in NLP pipelines?'\n"
            "- User: 'What did I ask you in the beginning?'\n"
            "  Reformulated: 'What was my first question regarding LangChain integration?'\n\n"
            "Focus on maintaining the intent while making the question precise and independently interpretable."
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
        qa_flexible_prompt = (
            "You are given a user question, and please write clean, concise and accurate answer to the question. "
            "You will be given a set of related contexts to the question, which are numbered sequentially starting from 1. "
            "Each context has an implicit reference number based on its position in the array (first context is 1, second is 2, etc.). "
            "Please use these contexts and cite them using the format [citation:x] at the end of each sentence where applicable. "
            "Your answer must be correct, accurate and written by an expert using an unbiased and professional tone. "
            "Please limit to 1024 tokens. Do not give any information that is not related to the question, and do not repeat. "
            "Say 'information is missing on' followed by the related topic, if the given context do not provide sufficient information. "
            "If a sentence draws from multiple contexts, please list all applicable citations, like [citation:1][citation:2]. "
            "Other than code and specific names and citations, your answer must be written in the same language as the question. "
            "Be concise.\n\nContext: {context}\n\n"
            "Remember: Cite contexts by their position number (1 for first context, 2 for second, etc.) and don't blindly "
            "repeat the contexts verbatim."
        )
        qa_strict_prompt = (
            "You are a highly knowledgeable and factual AI assistant. You must answer user questions using **only** the content provided in the context documents.\n\n"
            "### Strict Answering Rules:\n"
            "1. **Use Context Only**:\n"
            "   - Do not use any prior knowledge or make assumptions.\n"
            "   - Use only the documents provided in this prompt.\n"
            "   - **Do NOT use information or citations from previous chat turns or history.**\n"
            "   - If the answer is not present in the context, you must say so.\n"
            "2. **Cite Precisely**:\n"
            "   - Use the exact format `[citation:x]` at the end of each sentence that uses information from the context, where `x` is the document number (1, 2, 3...).\n"
            "   - These numbers are based on the order of the context provided below — the first document is `[citation:1]`, the second is `[citation:2]`, and so on.\n"
            "   - Do NOT use `[1]`, `(2)`, page numbers, or metadata for citations. Only use `[citation:x]` based on order.\n"
            "3. **If Information Is Missing**:\n"
            "   - If critical information is not present, respond with:\n"
            "     'Information is missing on [specific topic] based on the provided context.'\n"
            "   - If partial information exists, summarize what is known and explain what's missing.\n"
            "4. **Language & Style**:\n"
            "   - Answer in the same language as the user's question.\n"
            "   - Be concise, clear, and formal. Do not copy the context directly—paraphrase when possible.\n"
            "5. **Multiple Sources**:\n"
            "   - If a sentence is supported by multiple documents, include all applicable citations, like `[citation:1][citation:3]`.\n"
            "6. **Token Limit**:\n"
            "   - Keep your answer under 1024 tokens.\n\n"
            "**Important Reminder**:\n"
            "- You must NOT answer based on external knowledge, prior chat context, or assumptions.\n"
            "- Only use what is explicitly stated in the current provided context. No speculation or hallucination is allowed.\n"
            "- Do NOT use citation formats like `[1]`, `(2)`, or similar. Only use `[citation:x]`.\n"
            "- Remember: Cite based on the order in which documents appear in the context — NOT based on page number, filename, or metadata.\n"
            "- Do not repeat the context verbatim — always paraphrase.\n\n"
            "### Provided Context:\n{context}\n"
        )

        if strict_mode:
            qa_system_prompt = qa_strict_prompt
        else:
            qa_system_prompt = (
                qa_flexible_prompt  # your original or a looser version
            )

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
