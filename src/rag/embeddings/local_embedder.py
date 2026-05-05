from langchain_huggingface import HuggingFaceEmbeddings
from functools import lru_cache

@lru_cache(maxsize=1)
def get_local_embeddings() -> HuggingFaceEmbeddings:
    """
    all-minilm-l6-v2: 384 dimensions, run locally, no api cos
    downloaded once and cached on first call
    """
    return HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True} # required for cosine similarity
    )
