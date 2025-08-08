import json
import base64
from typing import List, AsyncGenerator

from sqlalchemy.orm import Session
from langchain_core.documents import Document
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
)
from langchain.chains.combine_documents import create_stuff_documents_chain

from app.services.llm.llm_factory import LLMFactory
from app.services.prompt_service import PromptService
from app.models.chat import Message


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
    chat_id: int,
    tool_contexts: List[str],
    chat_history: List[dict] = [],
    strict_mode: bool = True,
) -> AsyncGenerator[str, None]:
    """
    Generate response using provided Base64-encoded context from MCP tool.
    """
    try:
        # Service
        prompt_service = PromptService(db=db)
        llm = LLMFactory.create()

        # Create user message
        user_message = Message(content=query, role="user", chat_id=chat_id)
        db.add(user_message)
        db.commit()

        # Create bot message placeholder
        bot_message = Message(content="", role="assistant", chat_id=chat_id)
        db.add(bot_message)
        db.commit()

        # Step 1: Decode the Base64 contexts
        all_context_docs = []
        for b64 in tool_contexts:
            try:
                decoded = decode_mcp_context(base64_context=b64)
                all_context_docs.extend(decoded)
            except Exception as e:
                print(f"Error decoding context: {e}")

        if not all_context_docs:
            yield '0:"No context found from tools."\n'
            bot_message.content = "No context found from tools"
            db.commit()
            return

        # Step 2: QA Prompt (strict/flexible)
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

        # Step 3: Run QA directly (no retriever — docs already provided)
        full_response = ""
        async for chunk in qa_chain.astream(
            {
                "input": query,  # already contextualized
                "context": all_context_docs,
                "chat_history": chat_history,
            }
        ):
            part = chunk
            if isinstance(part, str):
                full_response += part
                escaped = part.replace('"', '\\"').replace("\n", "\\n")
                yield f'0:"{escaped}"\n'

        # Update bot message content
        bot_message.content = full_response
        db.commit()

    except Exception as e:
        yield f'3:"Error: {str(e)}"\n'

        # Update bot message with error
        if "bot_message" in locals():
            bot_message.content = f'3:"Error: {str(e)}"\n'
            db.commit()
