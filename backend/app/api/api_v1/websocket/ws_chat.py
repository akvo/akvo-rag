import logging
import asyncio

from datetime import datetime
from typing import Optional, Literal, List
from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from starlette.websockets import WebSocketState
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_
from pydantic import BaseModel, Field, ValidationError

from app.db.session import SessionLocal
from app.models.knowledge import KnowledgeBase
from app.models.user import User
from app.models.chat import Chat
from app.api.api_v1.auth import get_current_user
from app.api.api_v1.extended.util.util_user import get_super_user_ids
from app.services.chat_service import generate_response

logger = logging.getLogger(__name__)
router = APIRouter()

PING_INTERVAL = 10  # seconds


# -------------------------------------
# Pydantic Schemas
# -------------------------------------
class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1)


class ChatPayload(BaseModel):
    messages: List[ChatMessage]


# -------------------------------------
# Utility: Safe WebSocket JSON Sender
# -------------------------------------
async def safe_send_json(websocket: WebSocket, data: dict):
    try:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json(data)
    except Exception as e:
        logger.warning(f"[safe_send_json] Failed: {e}")


# -------------------------------------
# Auth + Validation
# -------------------------------------
async def authenticate_and_get_user(
    websocket: WebSocket, db: Session
) -> tuple[User, KnowledgeBase]:
    init_data = await websocket.receive_json()

    if init_data.get("type") != "auth":
        await safe_send_json(
            websocket,
            {
                "type": "error",
                "message": "Expected 'auth' type as the first message",
            },
        )
        await websocket.close(code=4000)
        raise WebSocketDisconnect()

    token = init_data.get("token")
    kb_id = init_data.get("kb_id")

    if not token or not kb_id:
        await safe_send_json(
            websocket,
            {"type": "error", "message": "Missing token or knowledge base ID"},
        )
        await websocket.close(code=4001)
        raise WebSocketDisconnect()

    try:
        user = get_current_user(token=token, db=db)
    except Exception as e:
        await safe_send_json(websocket, {"type": "error", "message": str(e)})
        await websocket.close(code=4002)
        raise WebSocketDisconnect()

    super_user_ids = get_super_user_ids(db=db)
    kb = (
        db.query(KnowledgeBase)
        .filter(
            KnowledgeBase.id == kb_id,
            or_(
                KnowledgeBase.user_id == user.id,
                KnowledgeBase.user_id.in_(super_user_ids),
            ),
        )
        .first()
    )
    if not kb:
        await safe_send_json(
            websocket,
            {
                "type": "error",
                "message": "Knowledge base not found or unauthorized",
            },
        )
        await websocket.close(code=4003)
        raise WebSocketDisconnect()

    logger.info(f"Authenticated user {user.id} for kb_id={kb_id}")
    return user, kb


# -------------------------------------
# Create/Retrieve Chat
# -------------------------------------
def get_or_create_chat(db: Session, user: User, kb: KnowledgeBase) -> Chat:
    chat = (
        db.query(Chat)
        .options(selectinload(Chat.knowledge_bases))
        .filter(Chat.user_id == user.id)
        .filter(Chat.knowledge_bases.any(KnowledgeBase.id == kb.id))
        .first()
    )
    if not chat:
        chat = Chat(user_id=user.id, title="New Chat")
        chat.knowledge_bases.append(kb)
        db.add(chat)
        db.commit()
        db.refresh(chat)
    return chat


# -------------------------------------
# Validate Incoming Chat Payload
# -------------------------------------
async def validate_chat_payload(
    websocket: WebSocket, data: dict
) -> Optional[ChatPayload]:
    try:
        return ChatPayload(**data)
    except ValidationError as ve:
        await safe_send_json(
            websocket,
            {
                "type": "error",
                "message": "Validation error",
                "details": ve.errors(),
            },
        )
        return None


# -------------------------------------
# WebSocket Endpoint
# -------------------------------------
@router.websocket("/chat")
async def websocket_chat(websocket: WebSocket):
    db = SessionLocal()
    await websocket.accept()
    logger.info("WebSocket connection accepted")

    async def send_ping():
        while True:
            try:
                await asyncio.sleep(PING_INTERVAL)
                if websocket.client_state != WebSocketState.CONNECTED:
                    break
                await safe_send_json(websocket, {"type": "ping"})
            except Exception as e:
                logger.warning(f"Ping failed: {e}")
                break

    ping_task = None
    chat_created = False
    chat_id = None
    knowledge_base_ids = []

    try:
        user, kb = await authenticate_and_get_user(websocket, db)

        ping_task = asyncio.create_task(send_ping())

        while True:
            client_data = await websocket.receive_json()
            msg_type = client_data.get("type")

            if msg_type != "chat":
                await safe_send_json(
                    websocket,
                    {
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}",
                    },
                )
                continue

            payload = await validate_chat_payload(websocket, client_data)
            if payload is None:
                continue

            messages = [msg.dict() for msg in payload.messages]
            last_message = messages[-1]

            if last_message["role"] != "user":
                await safe_send_json(
                    websocket,
                    {
                        "type": "error",
                        "message": "The last message must be from the user",
                    },
                )
                continue

            # Only create chat once per session
            if not chat_created:
                logger.info(
                    f"Creating new chat for user {user.id} and kb {kb.id}"
                )
                timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
                chat_title = f"Chat started at {timestamp}"

                chat = Chat(user_id=user.id, title=chat_title)
                chat.knowledge_bases.append(kb)
                db.add(chat)
                db.commit()
                db.refresh(chat)

                chat_id = chat.id
                knowledge_base_ids = [kb.id for kb in chat.knowledge_bases]
                chat_created = True

            await safe_send_json(
                websocket,
                {"type": "start", "message": "Generating response..."},
            )
            assistant_response = ""

            async for chunk in generate_response(
                query=last_message["content"],
                messages={"messages": messages},
                knowledge_base_ids=knowledge_base_ids,
                chat_id=chat_id,
                db=db,
            ):
                if websocket.client_state != WebSocketState.CONNECTED:
                    logger.warning(
                        "WebSocket closed during response streaming"
                    )
                    break

                assistant_response += chunk
                await safe_send_json(
                    websocket, {"type": "response_chunk", "content": chunk}
                )

            await safe_send_json(
                websocket,
                {"type": "end", "message": "Response generation completed"},
            )

    except WebSocketDisconnect:
        logger.warning("Client disconnected")
    except Exception as e:
        logger.error(f"Unhandled error: {e}", exc_info=True)
        try:
            await safe_send_json(
                websocket, {"type": "error", "message": str(e)}
            )
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        if ping_task:
            try:
                ping_task.cancel()
                await ping_task
            except asyncio.CancelledError:
                pass
        db.close()
