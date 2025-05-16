import logging

from fastapi import WebSocket, WebSocketDisconnect, Depends, APIRouter
from starlette.websockets import WebSocketState
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from pydantic import BaseModel, Field, ValidationError
from typing import Literal, List

from app.db.session import get_db

from app.models.knowledge import KnowledgeBase
from app.models.user import User
from app.models.chat import Chat

from app.api.api_v1.auth import get_current_user
from app.api.api_v1.extended.util.util_user import get_super_user_ids
from app.services.chat_service import generate_response

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1)


class ChatMessages(BaseModel):
    messages: List[ChatMessage]


@router.websocket("/chat")
async def websocket_chat(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    logger.info("WebSocket connection accepted")

    try:
        # Step 1: Tunggu pesan autentikasi
        init_data = await websocket.receive_json()

        if init_data.get("type") != "auth":
            await websocket.send_json({
                "type": "error",
                "message": "Expected type 'auth' as first message"
            })
            await websocket.close(code=4000)
            return

        token = init_data.get("token")
        kb_id = init_data.get("kb_id")

        if not token or not kb_id:
            await websocket.send_json({
                "type": "error",
                "message": "Missing token or knowledge base ID"
            })
            await websocket.close(code=4001)
            return

        try:
            user: User = get_current_user(token=token, db=db)
        except Exception as e:
            await websocket.send_json({"type": "error", "message": str(e)})
            await websocket.close(code=4002)
            return

        # Validasi KB
        super_user_ids = get_super_user_ids(db=db)
        kb = (
            db.query(KnowledgeBase)
            .filter(
                KnowledgeBase.id == kb_id,
                or_(
                    KnowledgeBase.user_id == user.id,
                    KnowledgeBase.user_id.in_(super_user_ids)
                )
            )
            .first()
        )

        if not kb:
            await websocket.send_json({
                "type": "error",
                "message": "Knowledge base not found or unauthorized"
            })
            await websocket.close(code=4003)
            return

        logger.info(
            f"User {user.id} connected to WebSocket using kb_id={kb_id}"
        )
        await websocket.send_json({
            "type": "info",
            "message": "Authentication successful"
        })

        # Step 2: Tunggu pesan dari client
        while True:
            client_data = await websocket.receive_json()
            msg_type = client_data.get("type")

            if msg_type == "chat":
                chat_id = client_data.get("chat_id")
                messages = client_data.get("messages")

                if not chat_id or not messages:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Missing chat_id or messages"
                    })
                    continue

                chat = (
                    db.query(Chat)
                    .options(joinedload(Chat.knowledge_bases))
                    .filter(Chat.id == chat_id, Chat.user_id == user.id)
                    .first()
                )
                if not chat:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Chat not found or unauthorized"
                    })
                    continue

                if not isinstance(messages, list) or not messages:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid messages format"
                    })
                    continue

                try:
                    validated_messages = ChatMessages(messages=messages)
                except ValidationError as ve:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Validation error",
                        "details": ve.errors()
                    })
                    continue

                messages = [msg.dict() for msg in validated_messages.messages]
                last_message = messages[-1]
                if last_message["role"] != "user":
                    await websocket.send_json({
                        "type": "error",
                        "message": "Last message must be from user"
                    })
                    continue

                knowledge_base_ids = [kb.id for kb in chat.knowledge_bases]

                # Kirim response bertahap
                await websocket.send_json({
                    "type": "start",
                    "message": "Generating response..."
                })

                assistant_response = ""

                async for chunk in generate_response(
                    query=last_message["content"],
                    messages={"messages": messages},
                    knowledge_base_ids=knowledge_base_ids,
                    chat_id=chat_id,
                    db=db
                ):
                    if websocket.client_state != WebSocketState.CONNECTED:
                        logger.warning("WebSocket closed during stream")
                        break

                    assistant_response += chunk
                    await websocket.send_json({
                        "type": "response_chunk",
                        "content": chunk
                    })

                await websocket.send_json({
                    "type": "end",
                    "message": "Done"
                })

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}"
                })

    except WebSocketDisconnect:
        logger.warning("Client disconnected")
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})
        await websocket.close(code=1011)
