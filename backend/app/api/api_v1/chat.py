from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from app.db.session import get_db
from app.models.user import User
from app.models.chat import Chat
from app.schemas.chat import ChatResponse
from app.api.api_v1.auth import get_current_user

router = APIRouter()


@router.get("/{chat_id}", response_model=ChatResponse)
def get_chat(
    *,
    db: Session = Depends(get_db),
    chat_id: int,
    current_user: User = Depends(get_current_user)
) -> Any:
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.user_id == current_user.id)
        .first()
    )
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


# TODO :: DELETE BELOW
# @router.post("/{chat_id}/messages")
# async def create_message(
#     *,
#     db: Session = Depends(get_db),
#     chat_id: int,
#     messages: dict,
#     current_user: User = Depends(get_current_user)
# ) -> StreamingResponse:
#     chat = (
#         db.query(Chat)
#         .options(joinedload(Chat.knowledge_bases))
#         .filter(Chat.id == chat_id, Chat.user_id == current_user.id)
#         .first()
#     )
#     if not chat:
#         raise HTTPException(status_code=404, detail="Chat not found")

#     # Get the last user message
#     last_message = messages["messages"][-1]
#     if last_message["role"] != "user":
#         raise HTTPException(
#             status_code=400, detail="Last message must be from user"
#         )

#     # Get knowledge base IDs
#     knowledge_base_ids = [kb.id for kb in chat.knowledge_bases]

#     async def response_stream():
#         # async for chunk in generate_response(
#         #     query=last_message["content"],
#         #     messages=messages,
#         #     knowledge_base_ids=knowledge_base_ids,
#         #     chat_id=chat_id,
#         #     db=db,
#         # ):
#         #     yield chunk
#         return "OK"

#     return StreamingResponse(
#         response_stream(),
#         media_type="text/event-stream",
#         headers={"x-vercel-ai-data-stream": "v1"},
#     )
# EOL DELETE


@router.delete("/{chat_id}")
def delete_chat(
    *,
    db: Session = Depends(get_db),
    chat_id: int,
    current_user: User = Depends(get_current_user)
) -> Any:
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.user_id == current_user.id)
        .first()
    )
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    db.delete(chat)
    db.commit()
    return {"status": "success"}
