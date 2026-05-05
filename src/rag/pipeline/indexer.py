from pathlib import Path
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_chroma import Chroma
from langchain_core.documents import Document
import chromadb
from app.core.config import settings
from app.core.logging_config import logger
from rag.embeddings import get_embeddings
from rag.pipeline.chunker import chunk_documents, ChunkConfig


def load_knoweldge_base(path: str = "data/knowledge_base") -> list[Document]:
    """Load all .md files from the knowledge base folder."""
    # Walks a folder and loads all files matching the glob pattern
    loader = DirectoryLoader(
        path,
        glob="**/*.md", # ** - any subdirectory at any depth, *.md - any markdown file
        loader_cls=TextLoader, # reads each file as raw text, warps it in a document with file path as metadata
        loader_kwargs={"encoding": "utf-8"}
    )

    docs = loader.load()
    logger.info("Knowledge base loaded", extra={"doc_count": len(docs)})
    return docs


def get_vectorstore() -> Chroma:
    """Return the chroma vecorstore client"""
    # Connect to ChromaDB running in Docker as an independent HTTP server
    client = chromadb.HttpClient(
        host=settings.chroma_host,
        port=settings.chroma_port,
    )

    return Chroma(
        client=client,
        collection_name=settings.chroma_collection, # chroma organizes vectors into collections
        embedding_function=get_embeddings(),
    )


def ingest_documents(docs: list[Document], config: ChunkConfig = ChunkConfig()) -> int:
    """
    Chunk -> embed -> store pipeline
    Returns the number of chunks stored
    """

    # Split documents into small pieces
    chunks = chunk_documents(docs, config)
    # Connect to ChromaDB
    vectorstore = get_vectorstore()
    # Embed each chunk and store
    vectorstore.add_documents(chunks)

    logger.info(
        "Ingestion complete",
        extra={"chunks_stored": len(chunks)}
    )

    return len(chunks)
