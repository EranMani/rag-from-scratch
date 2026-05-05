from langchain_core.documents import Document
from app.core.logging_config import logger
from app.core.metrics import CHUNKS_RETRIEVED
from rag.pipeline.indexer import get_vectorstore
from rag.resilience.circuit_breaker import chroma_cb
from rag.resilience.degradation import BM25FallbackRetriever

# BM25 fallback is loaded at startup — holds docs in memory
_bm25_fallback: BM25FallbackRetriever | None = None


def set_bm25_fallback(docs: list[Document]) -> None:
    """Called at startup with the full document set."""
    global _bm25_fallback
    _bm25_fallback = BM25FallbackRetriever(docs)


def retrieve(query: str, k: int = 4) -> list[Document]:
    """
    Retrieve relevant chunks for a query
    Primary: ChromaDB semantic search
    Fallback: BM25 keyword search (when Chroma circuit breaker is OPEN)
    BM25 must be ready before ChromaDB ever fails!
    """
    if chroma_cb.is_available():
        try:
            # Get the ChromaDB store
            store = get_vectorstore()
            # Find similarity between query and docs
            docs = store.similarity_search(query, k=k)
            # Mark this operation a success
            chroma_cb.record_success()
            CHUNKS_RETRIEVED.observe(len(docs))
            logger.info(
                "Semantic retrieval",
                extra={"query": query[:80], "chunks": len(docs)}
            )
            return docs
        except Exception as e:
            # Mark this operation a failure
            chroma_cb.record_failure()
            logger.error(
                "ChromaDB retrieval failed — activating fallback",
                extra={"error": str(e)}
            )

    # Use fallback method to fetch similar docs to query
    if _bm25_fallback:
        return _bm25_fallback.get_relevant_documents(query, k=k)

    logger.error("No retriever available — BM25 fallback not loaded")
    return []
