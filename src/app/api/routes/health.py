from fastapi import APIRouter
from fastapi.responses import JSONResponse
from rag.resilience.circuit_breaker import chroma_cb, openai_cb, redis_cb
from rag.cache.redis_cache import cache
from rag.pipeline.indexer import get_vectorstore


router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness():
    """Readiness probe - checks if dependencies are available to serve traffic"""
    checks = {}

    try:
        cache._get_client().ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unavailable"

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
    """Show the current state of all circuit breakers"""
    return {
        "circuit_breakers": [
            chroma_cb.status(),
            openai_cb.status(),
            redis_cb.status(),
        ]
    }
