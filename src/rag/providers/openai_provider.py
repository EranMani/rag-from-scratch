from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from rag.providers.base import LLMProvider
from app.core.config import settings


class OpenAIProvider(LLMProvider):
    def get_llm(self) -> BaseChatModel:
        return ChatOpenAI(
            model=settings.openai_model,
            openai_api_key=settings.openai_api_key,
            temperature=0.1, # low temperature = more factual answers
            streaming=True
        )

    def provider_name(self) -> str:
        return "openai"
