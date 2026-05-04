from dataclasses import dataclass
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from src.app.core.logging_config import logger


@dataclass
class ChunkConfig:
    chunk_size: int = 500
    chunk_overlap: int = 100
    strategy: str = "recursive" # fixed | recursive | sentence


def chunk_documents(docs: list[Document], config: ChunkConfig) -> list[Document]:
    """
    Split a list of Langchain documents into smaller chunks

    NOTE: Without chunking, a 500 page document is embedded as a single vector,
          losing all precision.
          Chunking creates focused, searchable pieces.
    """

    logger.info(
        "Chunking documents",
        extra={
            "doc_count": len(docs),
            "strategy": config.strategy,
            "chunk_size": config.chunk_size,
            "chunk_overlap": config.chunk_overlap
        }
    )

    if config.strategy == "fixed":
        # Split every N characters - fast but can break mid-sentence
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=[], # no preferred separators, pure size
        )

    elif config.strategy == "sentence":
        # Split only on sentence/paragraph boundries
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=["\n\n", "\n", ". "]
        )

    elif config.strategy == "recursive":
        # Try paragraph -> sentence -> word -> character splits in order
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    else:
        raise ValueError(f"Unkown chunking strategy: {config.strategy}")

    chunks = splitter.split_documents(docs)

    logger.info(
        "Chunking complete!",
        extra={
            "chunks_created": len(chunks),
            "avg_chunk_size": sum(len(c.page_content) for c in chunks) //
                max(len(chunks), 1),
        }
    )

    return chunks
