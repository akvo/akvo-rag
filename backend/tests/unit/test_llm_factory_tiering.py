import pytest
from unittest.mock import patch, MagicMock
from app.services.llm.llm_factory import LLMFactory, ModelTier
from app.core.config import settings


@pytest.mark.unit
class TestLLMFactoryTiering:
    """Unit tests for LLMFactory model tiering and backwards compatibility."""

    @patch("app.services.llm.llm_factory.ChatOpenAI")
    def test_default_openai_model_tier_is_synthesis(self, mock_chat_openai):
        """LLMFactory.create() should default to synthesis tier (gpt-4o)."""
        mock_instance = MagicMock()
        mock_chat_openai.return_value = mock_instance

        llm = LLMFactory.create(provider="openai")

        mock_chat_openai.assert_called_once_with(
            temperature=0,
            streaming=True,
            model=settings.OPENAI_MODEL_SYNTHESIS,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_API_BASE,
        )
        assert llm == mock_instance

    @patch("app.services.llm.llm_factory.ChatOpenAI")
    def test_openai_fast_tier_resolution(self, mock_chat_openai):
        """
        LLMFactory.create(model_tier='fast') should select OPENAI_MODEL_FAST.
        """
        mock_instance = MagicMock()
        mock_chat_openai.return_value = mock_instance

        llm = LLMFactory.create(
            provider="openai",
            model_tier="fast",
            streaming=False,
            temperature=0.2,
        )

        mock_chat_openai.assert_called_once_with(
            temperature=0.2,
            streaming=False,
            model=settings.OPENAI_MODEL_FAST,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_API_BASE,
        )
        assert llm == mock_instance

    @patch("app.services.llm.llm_factory.ChatOpenAI")
    def test_openai_model_tier_enum_support(self, mock_chat_openai):
        """
        LLMFactory.create(model_tier=ModelTier.FAST) should accept ModelTier.
        """
        mock_instance = MagicMock()
        mock_chat_openai.return_value = mock_instance

        llm = LLMFactory.create(
            provider="openai",
            model_tier=ModelTier.FAST,
        )

        mock_chat_openai.assert_called_once_with(
            temperature=0,
            streaming=True,
            model=settings.OPENAI_MODEL_FAST,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_API_BASE,
        )
        assert llm == mock_instance

    @patch("app.services.llm.llm_factory.ChatOpenAI")
    def test_custom_model_name_override(self, mock_chat_openai):
        """Explicit model_name should take precedence over model_tier."""
        mock_instance = MagicMock()
        mock_chat_openai.return_value = mock_instance

        llm = LLMFactory.create(
            provider="openai",
            model_tier="fast",
            model_name="ft:gpt-4o-mini-custom-2026",
        )

        mock_chat_openai.assert_called_once_with(
            temperature=0,
            streaming=True,
            model="ft:gpt-4o-mini-custom-2026",
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_API_BASE,
        )
        assert llm == mock_instance

    @patch("app.services.llm.llm_factory.ChatDeepSeek")
    def test_deepseek_tier_resolution(self, mock_chat_deepseek):
        """LLMFactory should resolve fast and synthesis tiers for DeepSeek."""
        mock_instance = MagicMock()
        mock_chat_deepseek.return_value = mock_instance

        # Fast tier
        LLMFactory.create(provider="deepseek", model_tier="fast")
        mock_chat_deepseek.assert_called_with(
            temperature=0,
            streaming=True,
            model=settings.DEEPSEEK_MODEL_FAST,
            api_key=settings.DEEPSEEK_API_KEY,
            api_base=settings.DEEPSEEK_API_BASE,
        )

        # Synthesis tier
        LLMFactory.create(provider="deepseek", model_tier="synthesis")
        mock_chat_deepseek.assert_called_with(
            temperature=0,
            streaming=True,
            model=settings.DEEPSEEK_MODEL_SYNTHESIS,
            api_key=settings.DEEPSEEK_API_KEY,
            api_base=settings.DEEPSEEK_API_BASE,
        )

    @patch("app.services.llm.llm_factory.OllamaLLM")
    def test_ollama_tier_resolution(self, mock_ollama):
        """LLMFactory should resolve fast and synthesis tiers for Ollama."""
        mock_instance = MagicMock()
        mock_ollama.return_value = mock_instance

        # Fast tier
        LLMFactory.create(provider="ollama", model_tier=ModelTier.FAST)
        mock_ollama.assert_called_with(
            model=settings.OLLAMA_MODEL_FAST,
            base_url=settings.OLLAMA_API_BASE,
            temperature=0,
            streaming=True,
        )

        # Synthesis tier
        LLMFactory.create(provider="ollama", model_tier=ModelTier.SYNTHESIS)
        mock_ollama.assert_called_with(
            model=settings.OLLAMA_MODEL_SYNTHESIS,
            base_url=settings.OLLAMA_API_BASE,
            temperature=0,
            streaming=True,
        )

    def test_unsupported_provider_raises_value_error(self):
        """LLMFactory should raise ValueError for unsupported providers."""
        with pytest.raises(
            ValueError, match="Unsupported LLM provider: unknown_provider"
        ):
            LLMFactory.create(provider="unknown_provider")
