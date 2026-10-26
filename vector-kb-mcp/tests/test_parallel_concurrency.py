from unittest.mock import AsyncMock, MagicMock, patch
import openai
import pytest

from main import parse_args
from retriever.chroma_retriever import ChromaRetriever, configure_sqlite_wal
from ingestion.processor import IngestionProcessor


def test_parse_args_default():
    with patch("sys.argv", ["main.py"]):
        with patch.dict("os.environ", {}, clear=True):
            args = parse_args()
            assert args.mode == "all"


def test_parse_args_cli_flag():
    with patch("sys.argv", ["main.py", "--mode=query"]):
        args = parse_args()
        assert args.mode == "query"

    with patch("sys.argv", ["main.py", "--mode=ingest"]):
        args = parse_args()
        assert args.mode == "ingest"


def test_parse_args_env_var():
    with patch("sys.argv", ["main.py"]):
        with patch.dict("os.environ", {"WORKER_MODE": "query"}):
            args = parse_args()
            assert args.mode == "query"


def test_configure_sqlite_wal_nonexistent(tmp_path):
    # Should safely return False when file not found
    result = configure_sqlite_wal(str(tmp_path / "nonexistent.sqlite3"))
    assert result is False


def test_configure_sqlite_wal_success(tmp_path):
    import sqlite3

    db_path = tmp_path / "chroma.sqlite3"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE test (id INT);")
    conn.commit()
    conn.close()

    result = configure_sqlite_wal(str(db_path))
    assert result is True

    # Verify journal mode was set to WAL
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode;")
    mode = cursor.fetchone()[0]
    conn.close()
    assert mode.lower() == "wal"


@pytest.mark.asyncio
async def test_chroma_retriever_retry_on_rate_limit(mock_chroma_client):
    """Verify that tenacity retries upon encountering OpenAI RateLimitError."""
    mock_openai = AsyncMock()
    mock_response = MagicMock()
    mock_data = MagicMock()
    mock_data.embedding = [0.1] * 1536
    mock_response.data = [mock_data]

    # First attempt raises RateLimitError, second succeeds
    mock_openai.embeddings.create.side_effect = [
        openai.RateLimitError(
            message="Rate limit reached",
            response=MagicMock(status_code=429, headers={}),
            body={},
        ),
        mock_response,
    ]

    retriever = ChromaRetriever(
        chroma_client=mock_chroma_client,
        openai_client=mock_openai,
        embedding_model="text-embedding-3-small",
    )

    vector = await retriever._embed_query("test query")
    assert len(vector) == 1536
    assert mock_openai.embeddings.create.call_count == 2


@pytest.mark.asyncio
async def test_chroma_retriever_embed_texts_retry(mock_chroma_client):
    """Verify embed_texts recovers from temporary APIConnectionError."""
    mock_openai = AsyncMock()
    mock_response = MagicMock()
    mock_data = MagicMock()
    mock_data.embedding = [0.2] * 1536
    mock_response.data = [mock_data]

    mock_openai.embeddings.create.side_effect = [
        openai.APIConnectionError(request=MagicMock()),
        mock_response,
    ]

    retriever = ChromaRetriever(
        chroma_client=mock_chroma_client,
        openai_client=mock_openai,
        embedding_model="text-embedding-3-small",
    )

    embs = await retriever.embed_texts(["sample text"])
    assert len(embs) == 1
    assert len(embs[0]) == 1536
    assert mock_openai.embeddings.create.call_count == 2


@pytest.mark.asyncio
async def test_ingestion_processor_rejects_oversized_file():
    """Verify that files exceeding 25MB are rejected by IngestionProcessor."""
    mock_storage = MagicMock()
    # Mock downloading 26MB
    mock_storage.download_file_bytes.return_value = b"A" * (26 * 1024 * 1024)

    mock_db = AsyncMock()
    mock_doc = MagicMock()
    mock_doc.id = 1
    mock_doc.knowledge_base_id = 1
    mock_doc.file_name = "huge.pdf"
    mock_doc.file_path = "kb_1/huge.pdf"

    mock_task = MagicMock()
    mock_task.id = 1
    mock_task.task_id = "task-1"

    exec_res = MagicMock()
    exec_res.scalar_one_or_none.return_value = mock_doc
    mock_db.execute.return_value = exec_res

    processor = IngestionProcessor(
        storage_service=mock_storage,
        batch_size=50,
    )

    with patch.object(
        processor, "_resolve_document", new_callable=AsyncMock
    ) as mock_res_doc, patch.object(
        processor, "_resolve_task", new_callable=AsyncMock
    ) as mock_res_task:
        mock_res_doc.return_value = mock_doc
        mock_res_task.return_value = mock_task

        res = await processor.process_document(
            {
                "kb_id": 1,
                "file_path": "kb_1/huge.pdf",
                "filename": "huge.pdf",
            },
            db=mock_db,
        )

        assert res["status"] == "failed"
        assert "25MB" in res["error"]
