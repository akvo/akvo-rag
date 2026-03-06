import json
import base64
import logging
from sqlalchemy.orm import Session
from typing import List, Optional

from app.models import Message
from app.services.prompt_service import PromptService
from app.services.system_settings_service import SystemSettingsService

from app.services.query_answering_workflow import (
    classify_intent_node,
    small_talk_node,
    contextualize_node,
    scoping_node,
    run_mcp_tool_node,
    post_processing_node,
    error_handler_node,
)

from app.services.llm.llm_factory import LLMFactory
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
)
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger(__name__)


async def stream_mcp_response(
    query: str,
    messages: dict,
    chat_id: int,
    db: Session,
    max_history_length: int = 10,
    generate_last_n_messages: bool = False,
    knowledge_base_ids: Optional[List[int]] = [],
):
    """
    Best-practice streaming:
        - Run MCP for scoping/retrieval (context)
        - Stream context prefix first (base64 + __LLM_RESPONSE__)
        - Stream tokens directly from qa_chain.astream
        - Persist user + assistant at the end
        - Use Vercel protocol lines: 0:"...", d:{...}, 3:{...}
    """
    if not knowledge_base_ids:
        raise ValueError("No knowledge_base_ids provided for this chat.")

    prompt_service = PromptService(db=db)
    settings_service = SystemSettingsService(db=db)
    top_k = settings_service.get_top_k()
    bot_message = None

    try:
        # 1) Persist user and placeholder assistant early
        user_message = Message(content=query, role="user", chat_id=chat_id)
        db.add(user_message)
        db.commit()

        bot_message = Message(content="", role="assistant", chat_id=chat_id)
        db.add(bot_message)
        db.commit()

        # 2) Prepare chat history for contextualization
        if len(messages.get("messages", [])) <= 1 or generate_last_n_messages:
            # Fetch from DB: get last (N+2) messages to account for the
            # current pair then exclude the current pair for
            # contextualization.
            chat_history_query = (
                db.query(Message)
                .filter(Message.chat_id == chat_id)
                .order_by(Message.created_at.desc())
                .limit(max_history_length + 2)
                .all()
            )
            chat_history_query.reverse()
            chat_history = [
                {"role": m.role, "content": m.content}
                for m in chat_history_query
            ]
            # Exclude current user message and placeholder bot message
            if len(chat_history) >= 2:
                chat_history = chat_history[:-2]
        else:
            chat_history = messages.get("messages", [])[-max_history_length:]
            # Ensure the current query is NOT in history
            if chat_history and chat_history[-1]["content"] == query:
                chat_history = chat_history[:-1]

        # 3) Sanitize chat history by removing internal context prefixes.
        from app.services.utils.history_utils import strip_context_prefixes

        chat_history = strip_context_prefixes(chat_history)

        # 4) Prepare initial state for MCP nodes
        contextualize_prompt = prompt_service.get_full_contextualize_prompt()
        qa_prompt = prompt_service.get_full_qa_strict_prompt()

        state = {
            "query": query,
            "chat_history": chat_history,
            "contextualize_prompt_str": contextualize_prompt,
            "qa_prompt_str": qa_prompt,
            "scope": {
                "knowledge_base_ids": knowledge_base_ids,
                "top_k": top_k,
            },
        }

        # 4) Classify intent
        state = await classify_intent_node(state)
        intent = state.get("intent", "knowledge_query")
        logger.info(f"[stream_mcp_response] Detected intent: {intent}")

        # If it's a memory query, use a more permissive prompt
        if intent == "memory_query":
            state["qa_prompt_str"] = (
                "You are a helpful assistant. Use the provided Chat History "
                "to answer the user's question about your conversation. "
                "Be friendly, concise, and helpful.\n\n"
                "Context: {context}"
            )

        # 5) Handle small talk directly
        if intent == "small_talk":
            state = await small_talk_node(state)
            reply = state.get("answer", "Hello! How can I help you today?")
            bot_message.content = reply
            db.commit()

            yield f'0:"{reply}"\n'
            yield 'd:{"finishReason":"stop"}\n'
            return

        # =============== normal MCP process ============================
        # 6) Contextualize query
        state = await contextualize_node(state)

        # 7) Route based on intent
        if intent != "memory_query":
            # Knowledge queries need scoping and retrieval
            state = await scoping_node(state)
            state = await run_mcp_tool_node(state)

            # Check if MCP tool failed - use error handler
            if state.get("error"):
                logger.warning(
                    "[stream_mcp_response] MCP tool failed, using error "
                    f"handler. Error: {state['error']}"
                )
                state = await error_handler_node(state)
                reply = state.get(
                    "answer",
                    "I'm having trouble with that right now. "
                    "Please try again in a moment.",
                )

                bot_message.content = reply
                db.commit()

                # Stream the error handler's response
                escaped = reply.replace('"', '\\"').replace("\n", "\\n")
                yield f'0:"{escaped}"\n'
                yield 'd:{"finishReason":"stop"}\n'
                return

            # Continue with normal flow if no error
            state = await post_processing_node(state)
        else:
            # Memory queries skip retrieval and go straight to generation
            logger.info(
                "[stream_mcp_response] Memory query detected, skipping "
                "retrieval."
            )
            state["context"] = []

        # 8) If context exists, stream it first (base64 + separator)
        context_prefix = ""
        if (
            state.get("context")
            and isinstance(state["context"], list)
            and state["context"]
        ):
            serializable_context = [
                {
                    "page_content": doc.page_content.replace('"', '\\"'),
                    "metadata": doc.metadata,
                }
                for doc in state["context"]
            ]
            escaped_context = json.dumps({"context": serializable_context})
            base64_context = base64.b64encode(
                escaped_context.encode()
            ).decode()
            separator = "__LLM_RESPONSE__"
            context_prefix = base64_context + separator
            # Vercel protocol: send context marker first
            yield f'0:"{context_prefix}"\n'

        # 9) Build the QA chain and stream tokens directly from the LLM chain
        llm = LLMFactory.create()

        qa_prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", state["qa_prompt_str"]),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        document_prompt = PromptTemplate.from_template(
            "\n\n- {page_content}\n\n"
        )

        qa_chain = create_stuff_documents_chain(
            llm=llm,
            prompt=qa_prompt_template,
            document_prompt=document_prompt,
            document_variable_name="context",
        )

        # Prepare chat_history for the chain (HumanMessage/AIMessage)
        chain_chat_history = []
        for m in chat_history:
            if m["role"] == "user":
                chain_chat_history.append(HumanMessage(content=m["content"]))
            elif m["role"] == "assistant":
                chain_chat_history.append(AIMessage(content=m["content"]))

        # Input to generation: prefer contextual_query if available
        generation_input = state.get("contextual_query", query)

        full_response = ""

        # Stream tokens as they arrive from the QA chain
        async for chunk in qa_chain.astream(
            {
                "input": generation_input,
                "context": state.get("context", []),
                "chat_history": chain_chat_history,
            }
        ):
            # handle both string tokens and the old dict style if present
            if isinstance(chunk, str):
                token = chunk
            elif isinstance(chunk, dict) and "answer" in chunk:
                token = chunk["answer"]
            else:
                # ignore unexpected chunk types
                continue

            full_response += token
            escaped = token.replace('"', '\\"').replace("\n", "\\n")
            yield f'0:"{escaped}"\n'

        # 10) Persist final assistant message
        # (context prefix + accumulated tokens)
        bot_message.content = context_prefix + full_response
        db.commit()

        # 11) Send final metadata / finish signal
        usage = '{"promptTokens":0,"completionTokens":0}'
        yield f'd:{{"finishReason":"stop","usage":{usage}}}\n'

    except Exception as e:
        # log full traceback
        logger.exception("stream_mcp_response failed: %s", e)

        error_message = f"Error generating response: {str(e)}"
        # Use json.dumps to safely escape the error string
        yield f'3:{json.dumps({"error": error_message})}\n'

        try:
            if bot_message is not None:
                bot_message.content = error_message
                db.commit()
            else:
                # fallback: persist a new error assistant message
                bot_message = Message(
                    content=error_message, role="assistant", chat_id=chat_id
                )
                db.add(bot_message)
                db.commit()
        except Exception:
            # swallow secondary errors
            pass

    finally:
        # ensure DB connection cleaned up
        try:
            db.close()
        except Exception:
            pass
