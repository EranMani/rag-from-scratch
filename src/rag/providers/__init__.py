from app.core.config import settings
from rag.providers.openai_provider import OpenAIProvider
from rag.providers.ollama_provider import OllamaProvider
from rag.providers.base import LLMProvider
from rag.resilience.circuit_breaker import openai_cb


def get_provider() -> LLMProvider:
    """
    Returns the active LLM provider.
    If OPENAI circuit breaker is OPEN - fallback to ollama automatically
    Graceful degradation for the LLM layer
    """
    if settings.llm_provider == "openai" and openai_cb.is_available():
        return OpenAIProvider()
    return OllamaProvider()
