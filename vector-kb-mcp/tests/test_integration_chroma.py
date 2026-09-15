import os
from unittest.mock import AsyncMock, MagicMock
import chromadb
import pytest

from retriever.chroma_retriever import ChromaRetriever
from tests.conftest import MockEmbeddingData, MockEmbeddingResponse


@pytest.mark.asyncio
async def test_chroma_real_container_integration():
    """
    Test direct integration with the live ChromaDB container
    in the Docker network.
    """
    chroma_host = os.getenv("CHROMA_HOST", "chromadb")
    chroma_port = int(os.getenv("CHROMA_PORT", "8000"))

    try:
        client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
        # Heartbeat check
        heartbeat = client.heartbeat()
        assert heartbeat > 0
    except Exception as e:
        pytest.skip(
            f"ChromaDB container unreachable at {chroma_host}:{chroma_port}: {e}"  # noqa
        )

    test_collection_name = "kb_9999"
    try:
        # Create or recreate test collection
        collection = client.get_or_create_collection(
            name=test_collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        # Insert test chunks with 1536-dimensional embeddings
        test_vector_1 = [0.1] * 1536
        test_vector_2 = [0.8] * 1536

        collection.add(
            ids=["chunk-real-1", "chunk-real-2"],
            embeddings=[test_vector_1, test_vector_2],
            documents=[
                "Water sanitation and hygiene standards in rural communities.",
                "Financial audit guidelines and budget management protocols.",
            ],
            metadatas=[
                {
                    "kb_id": 9999,
                    "document_id": "doc-real-1",
                    "file_name": "wash_standards.pdf",
                },
                {
                    "kb_id": 9999,
                    "document_id": "doc-real-2",
                    "file_name": "audit_guide.docx",
                },
            ],
        )

        # Mock OpenAI query embedding returning a vector close to test_vector_1
        mock_openai = MagicMock()
        mock_openai.embeddings.create = AsyncMock(
            return_value=MockEmbeddingResponse(
                data=[MockEmbeddingData(embedding=test_vector_1)]
            )
        )

        retriever = ChromaRetriever(
            chroma_client=client,
            openai_client=mock_openai,
        )

        # Search against kb_ids=[9999]
        results = await retriever.search(
            query="sanitation standards",
            kb_ids=[9999],
            top_k=2,
            score_threshold=0.5,
        )

        assert len(results) >= 1
        assert results[0].kb_id == 9999
        assert results[0].document_id == "doc-real-1"
        assert "Water sanitation" in results[0].content
        assert (
            results[0].score >= 0.9
        )  # Near identical vectors -> similarity ~ 1.0

    finally:
        try:
            client.delete_collection(name=test_collection_name)
        except Exception:
            pass
