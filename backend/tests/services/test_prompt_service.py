from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.constants.prompt_constant import (
    DEFAULT_CONTEXTUALIZE_PROMPT,
    DEFAULT_QA_FLEXIBLE_PROMPT,
    DEFAULT_QA_STRICT_PROMPT,
)
from app.models.base import Base
from app.models.prompt import PromptDefinition, PromptNameEnum, PromptVersion
from app.seeder.seed_prompts import seed_prompts
from app.services.prompt_service import PromptService


@pytest.fixture
def sync_db_session():
    """In-memory SQLite synchronous session fixture."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.mark.asyncio
async def test_get_active_prompt_tier1_app_overlay_async():
    """Tier 1: App custom prompt override takes top priority in async."""
    mock_session = AsyncMock()
    service = PromptService(db=mock_session)
    custom_overlay = (
        "You are an expert agronomist advising smallholder farmers."
    )

    result = await service.get_active_prompt_content_async(
        PromptNameEnum.qa_flexible_prompt, app_custom_prompt=custom_overlay
    )
    assert result == custom_overlay
    mock_session.execute.assert_not_called()


def test_get_active_prompt_tier1_app_overlay_sync(sync_db_session):
    """Tier 1: App custom prompt override takes top priority in sync mode."""
    service = PromptService(db=sync_db_session)
    custom_overlay = "You are a municipal water and sanitation officer."

    result = service.get_active_prompt_content(
        PromptNameEnum.qa_strict_prompt, app_custom_prompt=custom_overlay
    )
    assert result == custom_overlay


@pytest.mark.asyncio
async def test_get_active_prompt_tier2_db_version_async():
    """Tier 2: Active version in database resolved in async mode."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = (
        "Active PostgreSQL 17 Prompt Content"
    )
    mock_session.execute.return_value = mock_result

    service = PromptService(db=mock_session)
    result = await service.get_active_prompt_content_async(
        PromptNameEnum.qa_flexible_prompt
    )
    assert result == "Active PostgreSQL 17 Prompt Content"
    assert mock_session.execute.called


def test_get_active_prompt_tier2_db_version_sync(sync_db_session):
    """Tier 2: Active version in database resolved in sync mode."""
    prompt_def = PromptDefinition(name=PromptNameEnum.qa_strict_prompt.value)
    sync_db_session.add(prompt_def)
    sync_db_session.flush()

    v1 = PromptVersion(
        prompt_definition_id=prompt_def.id,
        content="Sync Active Prompt Content",
        version_number=1,
        is_active=True,
    )
    sync_db_session.add(v1)
    sync_db_session.commit()

    service = PromptService(db=sync_db_session)
    result = service.get_active_prompt_content(PromptNameEnum.qa_strict_prompt)
    assert result == "Sync Active Prompt Content"


@pytest.mark.asyncio
async def test_get_active_prompt_tier3_fallback_on_missing_async():
    """Tier 3: Fallback to constant when DB has no active record (async)."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    service = PromptService(db=mock_session)
    result = await service.get_active_prompt_content_async(
        PromptNameEnum.contextualize_q_system_prompt
    )
    assert result == DEFAULT_CONTEXTUALIZE_PROMPT.strip()


def test_get_active_prompt_tier3_fallback_on_missing_sync(sync_db_session):
    """Tier 3: Gracefully fallback to hardcoded constant in sync mode."""
    service = PromptService(db=sync_db_session)
    result = service.get_active_prompt_content(
        PromptNameEnum.qa_flexible_prompt
    )
    assert result == DEFAULT_QA_FLEXIBLE_PROMPT.strip()


@pytest.mark.asyncio
async def test_get_active_prompt_tier3_fallback_on_db_exception():
    """Tier 3: Fallback gracefully when sync DB query throws error."""
    mock_session = MagicMock()
    mock_session.query.side_effect = OperationalError(
        "Connection lost", params=None, orig=Exception()
    )

    service = PromptService(db=mock_session)
    result = service.get_active_prompt_content(PromptNameEnum.qa_strict_prompt)
    assert result == DEFAULT_QA_STRICT_PROMPT.strip()


@pytest.mark.asyncio
async def test_get_active_prompt_tier3_fallback_on_async_db_exception():
    """Tier 3: Fallback gracefully when async DB execute throws error."""
    mock_session = AsyncMock()
    mock_session.execute.side_effect = OperationalError(
        "Connection refused", params=None, orig=Exception()
    )

    service = PromptService(db=mock_session)
    result = await service.get_active_prompt_content_async(
        PromptNameEnum.qa_strict_prompt
    )
    assert result == DEFAULT_QA_STRICT_PROMPT.strip()


def test_get_full_contextualize_prompt_sync(sync_db_session):
    """Verify contextualize prompt formatting with static context rules."""
    service = PromptService(db=sync_db_session)
    full_prompt = service.get_full_contextualize_prompt(
        app_custom_prompt="Custom Contextualizer Intent"
    )
    assert "Custom Contextualizer Intent" in full_prompt
    assert "Static Rule for Context-Aware Inputs" in full_prompt


@pytest.mark.asyncio
async def test_get_full_contextualize_prompt_async():
    """Verify contextualize prompt formatting in async mode."""
    mock_session = AsyncMock()
    service = PromptService(db=mock_session)
    full_prompt = await service.get_full_contextualize_prompt_async(
        app_custom_prompt="Async Contextualizer Intent"
    )
    assert "Async Contextualizer Intent" in full_prompt
    assert "Static Rule for Context-Aware Inputs" in full_prompt


def test_get_full_qa_flexible_prompt_sync(sync_db_session):
    """Verify flexible QA prompt formatting with context placeholder."""
    service = PromptService(db=sync_db_session)
    full_prompt = service.get_full_qa_flexible_prompt(
        app_custom_prompt="Custom Flexible Overlay"
    )
    assert full_prompt.startswith("Custom Flexible Overlay")
    assert "Context: {context}" in full_prompt
    assert "[citation:x]" in full_prompt


@pytest.mark.asyncio
async def test_get_full_qa_flexible_prompt_async():
    """Verify flexible QA prompt formatting in async mode."""
    mock_session = AsyncMock()
    service = PromptService(db=mock_session)
    full_prompt = await service.get_full_qa_flexible_prompt_async(
        app_custom_prompt="Async Flexible Overlay"
    )
    assert full_prompt.startswith("Async Flexible Overlay")
    assert "Context: {context}" in full_prompt
    assert "[citation:x]" in full_prompt


def test_get_full_qa_strict_prompt_sync(sync_db_session):
    """Verify strict QA prompt formatting with strict answering rules."""
    service = PromptService(db=sync_db_session)
    full_prompt = service.get_full_qa_strict_prompt(
        app_custom_prompt="Custom Strict Overlay"
    )
    assert full_prompt.startswith("Custom Strict Overlay")
    assert "### Provided Context:\n{context}" in full_prompt
    assert "Citation (MANDATORY)" in full_prompt


@pytest.mark.asyncio
async def test_get_full_qa_strict_prompt_async():
    """Verify strict QA prompt formatting in async mode."""
    mock_session = AsyncMock()
    service = PromptService(db=mock_session)
    full_prompt = await service.get_full_qa_strict_prompt_async(
        app_custom_prompt="Async Strict Overlay"
    )
    assert full_prompt.startswith("Async Strict Overlay")
    assert "### Provided Context:\n{context}" in full_prompt
    assert "Citation (MANDATORY)" in full_prompt


def test_seed_prompts_idempotency(sync_db_session, monkeypatch):
    """Verify seed_prompts creates definitions and runs idempotently."""
    monkeypatch.setattr(
        "app.seeder.seed_prompts.SessionLocal", lambda: sync_db_session
    )

    # Run 1: Should seed new definitions
    seed_prompts()
    defs = sync_db_session.query(PromptDefinition).all()
    assert len(defs) == 3

    versions = (
        sync_db_session.query(PromptVersion).filter_by(is_active=True).all()
    )
    assert len(versions) == 3

    # Run 2: Re-running should be a clean no-op
    seed_prompts()
    defs_after = sync_db_session.query(PromptDefinition).all()
    assert len(defs_after) == 3
    versions_after = (
        sync_db_session.query(PromptVersion).filter_by(is_active=True).all()
    )
    assert len(versions_after) == 3
