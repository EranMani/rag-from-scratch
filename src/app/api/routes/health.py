from fastapi import APIRouter
from rag.resilience.circuit_breaker import chroma_cb, openai_cb, redis_cb


router = APIRouter(prefix="/api", tags=["health"])



@router.get("/health")
async def healt():
    return {"status": "ok"}


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
