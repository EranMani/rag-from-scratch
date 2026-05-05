from rank_bm25 import BM25Okapi
from langchain_core.documents import Document
from app.core.logging_config import logger


class BM25FallbackRetriever:
    """
    BM25 keyword retriever - used when chroma db is unavailable

    A graceful degradation fallback - instead of returning an error,
    fall back to classic keyword matching (BM25)
    System keeps running, even when semantic understanding is lost
    """

    def __init__(self, docs: list[Document]) -> None:
        corpus = [doc.page_content.lower().split() for doc in docs]
        self.bm25 = BM25Okapi(corpus)
        self.docs = docs
        logger.warning(
            "BM25 fallback retriever activated — ChromaDB is unavailable"
        )

    def get_relevant_documents(self, query: str, k: int = 4) -> list[Document]:
        """
        Compare user query to all given documents, provide matching scores, filter indices
        according to highest scores (using reverse=true) and get relevant documents
        according to top indices
        """
        # Break down the sentence into words, like actual tokens
        tokens = query.lower().split()
        # Compare the tokens to documents and provide scores
        scores = self.bm25.get_scores(tokens)
        # Sort indices by score descending, keep only top k
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        # Use top indices to fetch the actual documents in ranked order
        results = [self.docs[i] for i in top_indices]

        logger.info(
            "BM25 fallback retrieval",
            extra={"query": query[:80], "docs_returned": len(results)}
        )
        
        return results
