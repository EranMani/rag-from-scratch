"""
Health routes — the system's pulse before the agent talks to the user.

An adaptive agent like AgentCanvas depends on many moving parts (LLM, Vector DB,
SQLite, Redis). This module lets you build toward Self-Healing behavior:

    If Chroma or Redis is down, readiness returns 503 instead of letting the agent
    return empty answers or cryptic AI errors to the user.

In one sentence: health.py verifies that all RAG organs are working together before
the agent starts a conversation.

Endpoints:
    GET /health              — liveness (is the FastAPI process up?)
    GET /health/ready        — readiness (can we serve RAG traffic right now?)
    GET /health/circuit-breakers — visibility into LLM/Chroma/Redis failure state
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from rag.resilience.circuit_breaker import chroma_cb, openai_cb, redis_cb
from rag.cache.redis_cache import cache
from rag.pipeline.indexer import get_vectorstore


router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health():
    """Liveness probe — is the FastAPI process running and able to handle HTTP?

    Load balancers and Kubernetes use this to decide whether to restart the pod.
    Does NOT check dependencies; use /health/ready for that.
    """
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness():
    """Readiness probe — are dependencies available to serve real RAG traffic?

    Returns 200 only when Redis and Chroma are reachable; 503 otherwise so traffic
    can be routed away before users hit a broken agent pipeline.
    """
    checks = {}

    # Redis — query/LLM response cache; failure means degraded performance or cache bypass
    try:
        cache._get_client().ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unavailable"

    # Chroma — vector store for retrieval; failure means the agent cannot ground answers
    try:
        get_vectorstore()
        checks["chroma"] = "ok"
    except Exception:
        checks["chroma"] = "unavailable"

    all_ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        content={"status": checks},
        status_code=200 if all_ok else 503,
    )


@router.get("/health/circuit-breakers")
async def circuit_breakers():
    """Expose circuit breaker state for OpenAI, Chroma, and Redis.

    Useful in ops/debugging: when a breaker is OPEN, the system has stopped calling
    that dependency and may be on a fallback path (e.g. Ollama instead of OpenAI).
    """
    return {
        "circuit_breakers": [
            chroma_cb.status(),
            openai_cb.status(),
            redis_cb.status(),
        ]
    }
