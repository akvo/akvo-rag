from dataclasses import dataclass
from typing import List
from unittest.mock import AsyncMock, MagicMock
import fakeredis.aioredis
import pytest
import pytest_asyncio
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from models import Base


@pytest.fixture
def db_session():
    """
    Create an isolated in-memory SQLite database session for unit testing.
    Shared across all test modules.
    """
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Enable SQLite foreign key constraint enforcement
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False
    )
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@dataclass
class MockEmbeddingData:
    embedding: List[float]


@dataclass
class MockEmbeddingResponse:
    data: List[MockEmbeddingData]


@pytest.fixture
def mock_openai_client():
    client = MagicMock()
    client.embeddings = MagicMock()
    mock_vector = [0.05] * 1536
    client.embeddings.create = AsyncMock(
        return_value=MockEmbeddingResponse(
            data=[MockEmbeddingData(embedding=mock_vector)]
        )
    )
    return client


@pytest.fixture
def mock_chroma_client():
    client = MagicMock()

    def get_mock_collection(name: str):
        mock_col = MagicMock()
        mock_col.name = name
        if name == "kb_1":
            mock_col.query.return_value = {
                "ids": [["chunk-1", "chunk-2"]],
                "documents": [
                    [
                        "First document content in KB 1",
                        "Second document content in KB 1",
                    ]
                ],
                "metadatas": [
                    [
                        {
                            "kb_id": 1,
                            "document_id": "doc-1",
                            "file_name": "guide.pdf",
                        },
                        {
                            "kb_id": 1,
                            "document_id": "doc-1",
                            "file_name": "guide.pdf",
                        },
                    ]
                ],
                "distances": [[0.10, 0.35]],
            }
        elif name == "kb_2":
            mock_col.query.return_value = {
                "ids": [["chunk-3"]],
                "documents": [["Third document content in KB 2"]],
                "metadatas": [
                    [
                        {
                            "kb_id": 2,
                            "document_id": "doc-2",
                            "file_name": "manual.docx",
                        }
                    ]
                ],
                "distances": [[0.20]],
            }
        elif name == "kb_empty":
            mock_col.query.return_value = {
                "ids": [[]],
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]],
            }
        else:
            raise ValueError(f"Collection {name} does not exist")
        return mock_col

    client.get_collection.side_effect = get_mock_collection
    return client


@pytest_asyncio.fixture
async def fake_redis():
    server = fakeredis.FakeServer()
    r = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    yield r
    await r.flushall()
    await r.aclose()


@pytest_asyncio.fixture(autouse=True)
async def reset_db_engine():
    yield
    from db.session import close_db_engine

    try:
        await close_db_engine()
    except Exception:
        pass
