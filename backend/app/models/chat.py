from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class ChatKnowledgeBase(Base):
    __tablename__ = "chat_knowledge_bases"

    chat_id = Column(Integer, ForeignKey("chats.id"), primary_key=True)
    # External MCP Knowledge Base ID
    knowledge_base_id = Column(Integer, primary_key=True)


class Chat(Base, TimestampMixin):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    messages = relationship(
        "Message", back_populates="chat", cascade="all, delete-orphan"
    )
    user = relationship("User", back_populates="chats")

    # KBs are external MCP IDs
    knowledge_bases = relationship(
        "ChatKnowledgeBase", cascade="all, delete-orphan", lazy="joined"
    )

    @property
    def knowledge_base_ids(self) -> list[int]:
        return [kb.knowledge_base_id for kb in self.knowledge_bases]


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(LONGTEXT, nullable=False)
    role = Column(String(50), nullable=False)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)

    # Relationships
    chat = relationship("Chat", back_populates="messages")
