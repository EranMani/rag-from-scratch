import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response
from langgraph.checkpoint.memory import MemorySaver
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app.core.config import settings
from app.core.logging_config import logger
from app.core.metrics import REGISTRY, REQUEST_COUNT, REQUEST_LATENCY
from app.api.routes import chat, documents, health, auth, profile, admin
from app.auth.db import init_user_db
from app.profile.db import init_profile_db, migrate_topic_slugs
from rag.pipeline.indexer import load_knowledge_base, get_vectorstore, ingest_documents
from rag.pipeline.retriever import set_bm25_fallback
from agents.graph import build_graph



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    logger.info("Starting Educational RAG System")

    # Create users table and user_profiles table in sqlite3
    init_user_db()
    init_profile_db()
    migrate_topic_slugs()

    # Load knowledge base and setup BM25 fallback on startup
    docs = load_knowledge_base()
    set_bm25_fallback(docs)

    # Ingest documents into ChromaDB if collection is empty
    try:
        store = get_vectorstore()
        if store._collection.count() == 0:
            logger.info("Empty collection — ingesting knowledge base")
            ingest_documents(docs)
    except Exception as e:
        logger.warning("Could not check ChromaDB on startup", extra={"error": str(e)})

    # LangGraph — build graph with MemorySaver checkpointer.
    # MemorySaver is instantiated here (not at module level) so that it is
    # scoped to a single application lifetime and garbage-collected on shutdown.
    checkpointer = MemorySaver()
    app.state.rag_graph = build_graph(checkpointer)

    app.state.internal_http_client = httpx.AsyncClient(
        base_url=f"http://127.0.0.1:{settings.app_port}",
        timeout=httpx.Timeout(30.0),
    )

    logger.info("RAG system ready")
    try:
        yield
    finally:
        await app.state.internal_http_client.aclose()
        logger.info("Shutting down RAG system")


app = FastAPI(
    title="Educational RAG system",
    description="Production-grade RAG demo - portfolio project",
    version="1.0.0",
    lifespan=lifespan
)


# Middleware: request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    latency = round((time.perf_counter() - start) * 1000)
    logger.info(
        "HTTP request",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "latency_ms": latency,
        }
    )
    return response


# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    data = generate_latest(REGISTRY)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


# Routes
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(admin.router)


# Mount NICEGUI
from app.ui import setup_ui
setup_ui(app)

