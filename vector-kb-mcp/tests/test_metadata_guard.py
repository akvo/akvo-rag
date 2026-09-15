from datetime import date
from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy.orm import Session

from models import KnowledgeBase, Document
from core.exceptions import VectorMCPException, EmbeddingDimensionMismatchError
from core.guards import validate_embedding_dimension
from retriever.chroma_retriever import ChromaRetriever
from tests.conftest import MockEmbeddingData, MockEmbeddingResponse


# ---------------------------------------------------------------------------
# 1. KnowledgeBase Embedding Configuration Tests (SUB-202.1)
# ---------------------------------------------------------------------------


def test_knowledge_base_embedding_defaults(db_session: Session):
    """Verify default embedding model and dimension on KnowledgeBase."""
    kb = KnowledgeBase(name="default_embedding_kb")
    db_session.add(kb)
    db_session.commit()
    db_session.refresh(kb)

    assert kb.embedding_model == "text-embedding-3-small"
    assert kb.embedding_dim == 1536


def test_knowledge_base_custom_embedding_model_and_dim(db_session: Session):
    """Verify custom embedding model and dimension on KnowledgeBase."""
    kb = KnowledgeBase(
        name="custom_embedding_kb",
        embedding_model="text-embedding-3-large",
        embedding_dim=3072,
    )
    db_session.add(kb)
    db_session.commit()
    db_session.refresh(kb)

    assert kb.embedding_model == "text-embedding-3-large"
    assert kb.embedding_dim == 3072


# ---------------------------------------------------------------------------
# 2. Document Governance Metadata Tests (SUB-202.2)
# ---------------------------------------------------------------------------


def test_document_governance_metadata_persistence(db_session: Session):
    """Verify persistence and retrieval of enriched governance metadata."""
    kb = KnowledgeBase(name="gov_kb")
    db_session.add(kb)
    db_session.commit()

    eff_date = date(2024, 1, 15)
    custom_meta = {
        "program": "WASH-2024",
        "author": "Dr. Jane Doe",
        "keywords": ["water", "sanitation", "borehole"],
    }

    doc = Document(
        knowledge_base_id=kb.id,
        file_name="water_standard_2024.pdf",
        file_path="uploads/water_standard_2024.pdf",
        file_size=2048576,
        content_type="application/pdf",
        file_hash="g" * 64,
        doc_version="2024.1",
        issuing_authority="Ministry of Water & Sanitation",
        effective_date=eff_date,
        doc_type="STANDARD",
        jurisdiction="National",
        metadata_=custom_meta,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    assert doc.id is not None
    assert doc.doc_version == "2024.1"
    assert doc.issuing_authority == "Ministry of Water & Sanitation"
    assert doc.effective_date == eff_date
    assert doc.doc_type == "STANDARD"
    assert doc.jurisdiction == "National"
    assert doc.metadata_ == custom_meta
    assert doc.metadata_["program"] == "WASH-2024"


def test_document_legacy_compatibility_null_metadata(db_session: Session):
    """Verify that nullable governance columns preserve legacy format."""
    kb = KnowledgeBase(name="legacy_kb")
    db_session.add(kb)
    db_session.commit()

    doc = Document(
        knowledge_base_id=kb.id,
        file_name="legacy_document.pdf",
        file_path="uploads/legacy_document.pdf",
        file_size=5000,
        content_type="application/pdf",
        file_hash="l" * 64,
        # Governance columns omitted -> should all be None
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    assert doc.doc_version is None
    assert doc.issuing_authority is None
    assert doc.effective_date is None
    assert doc.doc_type is None
    assert doc.jurisdiction is None
    assert doc.metadata_ is None


# ---------------------------------------------------------------------------
# 3. Exceptions & Dimension Guard Tests (SUB-202.3)
# ---------------------------------------------------------------------------


def test_embedding_dimension_mismatch_error_properties():
    """Verify EmbeddingDimensionMismatchError message and attributes."""
    err = EmbeddingDimensionMismatchError(
        kb_id=42,
        expected_dim=1536,
        actual_dim=768,
        model="text-embedding-3-small",
    )
    assert isinstance(err, VectorMCPException)
    assert err.kb_id == 42
    assert err.expected_dim == 1536
    assert err.actual_dim == 768
    assert err.model == "text-embedding-3-small"
    assert "Embedding dimension mismatch for KB #42" in str(err)
    assert "Expected 1536-dim, received 768-dim." in str(err)


def test_validate_embedding_dimension_positive():
    """Verify that a vector with matching dimensions passes validation."""
    valid_vector = [0.1] * 1536
    result = validate_embedding_dimension(
        embedding=valid_vector,
        expected_dim=1536,
        kb_id=1,
        model="text-embedding-3-small",
    )
    assert result == valid_vector


def test_validate_embedding_dimension_negative():
    """Verify mismatched vector lengths raise mismatch error."""
    invalid_vector = [0.1] * 768
    with pytest.raises(EmbeddingDimensionMismatchError) as exc_info:
        validate_embedding_dimension(
            embedding=invalid_vector,
            expected_dim=1536,
            kb_id=10,
            model="text-embedding-3-small",
        )

    err = exc_info.value
    assert err.kb_id == 10
    assert err.expected_dim == 1536
    assert err.actual_dim == 768


@pytest.mark.asyncio
async def test_chroma_retriever_dimension_guard_positive(mock_chroma_client):
    """Verify ChromaRetriever executes when embedding dimension is 1536."""
    mock_openai = MagicMock()
    mock_openai.embeddings = MagicMock()
    mock_openai.embeddings.create = AsyncMock(
        return_value=MockEmbeddingResponse(
            data=[MockEmbeddingData(embedding=[0.05] * 1536)]
        )
    )

    retriever = ChromaRetriever(
        chroma_client=mock_chroma_client,
        openai_client=mock_openai,
        embedding_model="text-embedding-3-small",
        expected_dim=1536,
    )

    results = await retriever.search(query="water quality", kb_ids=[1])
    assert len(results) > 0


@pytest.mark.asyncio
async def test_chroma_retriever_dimension_guard_mismatch(mock_chroma_client):
    """Verify ChromaRetriever raises mismatch error on dimension mismatch."""
    mock_openai = MagicMock()
    mock_openai.embeddings = MagicMock()
    mock_openai.embeddings.create = AsyncMock(
        return_value=MockEmbeddingResponse(
            data=[MockEmbeddingData(embedding=[0.05] * 768)]
        )
    )

    retriever = ChromaRetriever(
        chroma_client=mock_chroma_client,
        openai_client=mock_openai,
        embedding_model="text-embedding-3-small",
        expected_dim=1536,
    )

    with pytest.raises(EmbeddingDimensionMismatchError) as exc_info:
        await retriever.search(query="water quality", kb_ids=[1])

    assert exc_info.value.expected_dim == 1536
    assert exc_info.value.actual_dim == 768
