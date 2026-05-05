from langchain_community.chat_models import ChatOllama
from langchain_core.language_models import BaseChatModel
from rag.providers.base import LLMProvider
from app.core.config import settings


class OllamaProvider(LLMProvider):
    def get_llm(self) -> BaseChatModel:
        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.1
        )

    def provider_name(self) -> str:
        return "ollama"
