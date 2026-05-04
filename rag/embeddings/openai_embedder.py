from langchain_openai import OpenAIEmbeddings
from functools import lru_cache
from app.core.config import settings


@lru_cache(maxsize=1)
def get_openai_embeddings() -> OpenAIEmbeddings:
    """
    text-embedding-3-small: 1536 dimensions
    Captures richer semantic nuance than local models
    """
    return OpenAIEmbeddings(
        model=settings.openai_embedding_model,
        openai_api_key=settings.openai_api_key,
    )
