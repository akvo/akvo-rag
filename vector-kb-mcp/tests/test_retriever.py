import pytest
from retriever.chroma_retriever import ChromaRetriever


@pytest.mark.asyncio
async def test_chroma_retriever_search_single_kb(
    mock_chroma_client, mock_openai_client
):
    retriever = ChromaRetriever(
        chroma_client=mock_chroma_client,
        openai_client=mock_openai_client,
        embedding_model="text-embedding-3-small",
    )

    results = await retriever.search(
        query="water treatment guide", kb_ids=[1], top_k=4
    )

    assert len(results) == 2
    mock_openai_client.embeddings.create.assert_called_once_with(
        input=["water treatment guide"], model="text-embedding-3-small"
    )

    # First result has distance 0.10 -> score 0.90
    assert results[0].chunk_id == "chunk-1"
    assert results[0].score == 0.90
    assert results[0].kb_id == 1
    assert results[0].document_id == "doc-1"
    assert "First document content" in results[0].content

    # Second result has distance 0.35 -> score 0.65
    assert results[1].chunk_id == "chunk-2"
    assert results[1].score == 0.65


@pytest.mark.asyncio
async def test_chroma_retriever_multi_kb_ranking(
    mock_chroma_client, mock_openai_client
):
    retriever = ChromaRetriever(
        chroma_client=mock_chroma_client, openai_client=mock_openai_client
    )

    # Collection kb_1 yields scores [0.90, 0.65]
    # Collection kb_2 yields score [0.80] (dist 0.20)
    # Merged and ranked: 0.90 (kb_1), 0.80 (kb_2), 0.65 (kb_1)
    results = await retriever.search(
        query="sanitation project", kb_ids=[1, 2], top_k=10
    )

    assert len(results) == 3
    assert results[0].score == 0.90
    assert results[0].kb_id == 1
    assert results[1].score == 0.80
    assert results[1].kb_id == 2
    assert results[2].score == 0.65
    assert results[2].kb_id == 1


@pytest.mark.asyncio
async def test_chroma_retriever_score_threshold(
    mock_chroma_client, mock_openai_client
):
    retriever = ChromaRetriever(
        chroma_client=mock_chroma_client, openai_client=mock_openai_client
    )

    # Filter with score_threshold = 0.75
    results = await retriever.search(
        query="water hygiene", kb_ids=[1, 2], top_k=10, score_threshold=0.75
    )

    # 0.90 (kb_1) and 0.80 (kb_2) should pass; 0.65 (kb_1) dropped
    assert len(results) == 2
    assert all(r.score >= 0.75 for r in results)


@pytest.mark.asyncio
async def test_chroma_retriever_top_k_limit(
    mock_chroma_client, mock_openai_client
):
    retriever = ChromaRetriever(
        chroma_client=mock_chroma_client, openai_client=mock_openai_client
    )

    results = await retriever.search(
        query="monitoring report", kb_ids=[1, 2], top_k=1
    )
    assert len(results) == 1
    assert results[0].score == 0.90


@pytest.mark.asyncio
async def test_chroma_retriever_empty_and_nonexistent_kb(
    mock_chroma_client, mock_openai_client
):
    retriever = ChromaRetriever(
        chroma_client=mock_chroma_client, openai_client=mock_openai_client
    )

    # kb_999 does not exist, kb_empty returns no documents, kb_1 returns 2 docs
    results = await retriever.search(
        query="infrastructure",
        kb_ids=[999, 1],
        top_k=5,
    )

    assert len(results) == 2
    assert results[0].kb_id == 1


@pytest.mark.asyncio
async def test_chroma_retriever_empty_collection(
    mock_chroma_client, mock_openai_client
):
    retriever = ChromaRetriever(
        chroma_client=mock_chroma_client, openai_client=mock_openai_client
    )

    results = await retriever.search(
        query="something",
        kb_ids=["empty"],  # triggers kb_empty which returns empty lists
        top_k=5,
    )

    assert results == []


@pytest.mark.asyncio
async def test_chroma_retriever_empty_input(
    mock_chroma_client, mock_openai_client
):
    retriever = ChromaRetriever(
        chroma_client=mock_chroma_client, openai_client=mock_openai_client
    )

    assert await retriever.search(query="", kb_ids=[1, 2]) == []
    assert await retriever.search(query="   ", kb_ids=[1, 2]) == []
    assert await retriever.search(query="valid query", kb_ids=[]) == []

