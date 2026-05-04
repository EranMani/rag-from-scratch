from dataclasses import dataclass
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from app.core.logging_config import logger
from enum import StrEnum


class ChunkStrategy(StrEnum):
    FIXED = "fixed"
    SENTENCE = "sentence"
    RECURSIVE = "recursive"


@dataclass
class ChunkConfig:
    chunk_size: int = 500
    chunk_overlap: int = 100
    strategy: ChunkStrategy = ChunkStrategy.RECURSIVE

SEPARATORS: dict[ChunkStrategy, list[str]] = {
    ChunkStrategy.FIXED: [],
    ChunkStrategy.SENTENCE: ["\n\n", "\n", ". "],
    ChunkStrategy.RECURSIVE: ["\n\n", "\n", ". ", " ", ""],
}


def chunk_documents(docs: list[Document], config: ChunkConfig = ChunkConfig()) -> list[Document]:
    """
    Split a list of Langchain documents into smaller chunks
    Return a list of chunks (Document objects)

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

    # Create the splitter engine
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        separators=SEPARATORS[config.strategy]
    )

    # Build chunks from the given documents
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
