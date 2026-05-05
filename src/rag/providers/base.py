from abc import ABC, abstractmethod
from langchain_core.language_models import BaseChatModel


class LLMProvider(ABC):
    """Abstract base - all providers must implement get_llm()."""

    @abstractmethod
    def get_llm(self) -> BaseChatModel:
        ...

    @abstractmethod
    def provider_name(self) -> str:
        ...
