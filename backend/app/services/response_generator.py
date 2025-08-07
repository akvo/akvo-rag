import json
import base64
from typing import List, AsyncGenerator

from sqlalchemy.orm import Session
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
)
from langchain.chains import create_history_aware_retriever

from app.services.llm.llm_factory import LLMFactory
from app.services.prompt_service import PromptService


def decode_mcp_context(base64_context: str) -> List[Document]:
    """
    Decode Base64-encoded MCP context into a list of LangChain Documents.
    """
    decoded = base64.b64decode(base64_context).decode()
    context_dict = json.loads(decoded)
    return [
        Document(
            page_content=item["page_content"],
            metadata=item.get("metadata", {}),
        )
        for item in context_dict.get("context", [])
    ]


async def generate_response_from_context(
    query: str,
    db: Session,
    tool_contexts: List[str],
    chat_history: List[dict] = [],
    messages: List[dict] = [],
    strict_mode: bool = True,
) -> AsyncGenerator[str, None]:
    """
    Generate response using provided Base64-encoded context from MCP tool.
    """
    try:
        # Service
        prompt_service = PromptService(db=db)
        llm = LLMFactory.create()

        # Step 1: Decode the Base64 context
        all_context_docs = []
        for b64 in tool_contexts:
            try:
                decoded = decode_mcp_context(base64_context=b64)
                all_context_docs.extend(decoded)
            except Exception as e:
                print(f"Error decoding context: {e}")

        if not all_context_docs:
            yield '0:"No context found from tools."\n'
            return

        # --- Step 2: Convert chat history to LangChain message format
        lc_chat_history = []
        for msg in chat_history:
            content = msg.get("content", "")
            if "__LLM_RESPONSE__" in content:
                content = content.split("__LLM_RESPONSE__")[-1]
            if msg["role"] == "user":
                lc_chat_history.append(HumanMessage(content=content))
            elif msg["role"] == "assistant":
                lc_chat_history.append(AIMessage(content=content))

        # --- Step 3: Contextualize Query (History-aware)
        contextualize_prompt_str = (
            prompt_service.get_full_contextualize_prompt()
        )
        contextualize_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", contextualize_prompt_str),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )

        contextualize_chain = create_history_aware_retriever(
            llm=llm,
            retriever=None,  # We'll skip retriever use and adapt only prompt
            contextualize_prompt=contextualize_prompt,
        )

        # "Fake" retriever chain input with documents already available
        contextualized_input = await contextualize_chain.ainvoke(
            {
                "input": query,
                "chat_history": lc_chat_history,
            }
        )

        contextualized_query = contextualized_input.get("next_input", query)

        # --- Step 4: QA Prompt
        qa_prompt_str = (
            prompt_service.get_full_qa_strict_prompt()
            if strict_mode
            else prompt_service.get_full_qa_flexible_prompt()
        )

        qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", qa_prompt_str),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )

        document_prompt = PromptTemplate.from_template(
            "\n\n- {page_content}\n\n"
        )

        qa_chain = create_stuff_documents_chain(
            llm=llm,
            prompt=qa_prompt,
            document_prompt=document_prompt,
            document_variable_name="context",
        )

        # --- Step 5: Run QA with docs from MCP
        full_response = ""
        async for chunk in qa_chain.astream(
            {
                "input": contextualized_query,
                "context": all_context_docs,
                "chat_history": lc_chat_history,
            }
        ):
            if "answer" in chunk:
                part = chunk["answer"]
                full_response += part
                escaped = part.replace('"', '\\"').replace("\n", "\\n")
                print(escaped)
                yield f'0:"{escaped}"\n'

    except Exception as e:
        yield f'3:"Error: {str(e)}"\n'
