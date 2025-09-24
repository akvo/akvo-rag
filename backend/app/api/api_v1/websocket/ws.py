from fastapi import APIRouter
from app.api.api_v1.websocket import ws_chat


ws_router = APIRouter()

ws_router.include_router(ws_chat.router, prefix="/ws", tags=["websocket"])
