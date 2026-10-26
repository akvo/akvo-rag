from enum import Enum
from typing import Optional, Union
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langchain_ollama import OllamaLLM
from app.core.config import settings


class ModelTier(str, Enum):
    FAST = "fast"
    SYNTHESIS = "synthesis"


class LLMFactory:
    @staticmethod
    def create(
        provider: Optional[str] = None,
        temperature: float = 0,
        streaming: bool = True,
        model_tier: Union[str, ModelTier] = ModelTier.SYNTHESIS,
        model_name: Optional[str] = None,
    ) -> BaseChatModel:
        """
        Create an LLM instance based on the provider and model tier.
        Defaults to 'synthesis' tier for 100% backwards compatibility.
        """
        # If no provider specified, use the one from settings
        provider = provider or settings.CHAT_PROVIDER
        tier_val = (
            model_tier.value
            if isinstance(model_tier, ModelTier)
            else str(model_tier).lower()
        )

        if provider.lower() == "openai":
            selected_model = model_name or (
                settings.OPENAI_MODEL_FAST
                if tier_val == ModelTier.FAST.value
                else settings.OPENAI_MODEL_SYNTHESIS
            )
            return ChatOpenAI(
                temperature=temperature,
                streaming=streaming,
                model=selected_model,
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_API_BASE,
            )
        elif provider.lower() == "deepseek":
            selected_model = model_name or (
                settings.DEEPSEEK_MODEL_FAST
                if tier_val == ModelTier.FAST.value
                else settings.DEEPSEEK_MODEL_SYNTHESIS
            )
            return ChatDeepSeek(
                temperature=temperature,
                streaming=streaming,
                model=selected_model,
                api_key=settings.DEEPSEEK_API_KEY,
                api_base=settings.DEEPSEEK_API_BASE,
            )
        elif provider.lower() == "ollama":
            # Initialize Ollama model
            selected_model = model_name or (
                settings.OLLAMA_MODEL_FAST
                if tier_val == ModelTier.FAST.value
                else settings.OLLAMA_MODEL_SYNTHESIS
            )
            return OllamaLLM(
                model=selected_model,
                base_url=settings.OLLAMA_API_BASE,
                temperature=temperature,
                streaming=streaming,
            )
        # Add more providers here as needed
        # elif provider.lower() == "anthropic":
        #     return ChatAnthropic(...)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
