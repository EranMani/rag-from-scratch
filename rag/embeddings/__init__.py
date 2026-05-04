from app.core.config import settings
from rag.embeddings.local_embedder import get_local_emgeddings
from rag.embeddings.openai_embedder import get_openai_embeddings


def get_embeddings():
    """Return the correct embedder based on EMBEDDING_PROVIDER"""
    if settings.embedding_provider == "openai":
        return get_openai_embeddings()
    return get_local_emgeddings()
