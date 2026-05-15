"""
Health routes — the system's pulse before the agent talks to the user.

Endpoints:
    GET /health                   — liveness (is the FastAPI process up?)
    GET /health/ready             — readiness: live Redis + Chroma probe, 503 if either down
    GET /health/circuit-breakers  — visibility into LLM/Chroma/Redis circuit breaker state
    GET /health/services          — cached snapshot updated by background probe every N seconds
"""

import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.routes.health_probe import probe_redis, probe_chroma
from rag.resilience.circuit_breaker import chroma_cb, openai_cb, redis_cb


router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(request: Request):
    """Live probe — runs on every call. Returns 503 if Redis or Chroma is down."""
    client = request.app.state.probe_http_client
    redis_ok = await probe_redis()
    chroma_ok = await probe_chroma(client)

    checks = {
        "redis": "ok" if redis_ok else "unavailable",
        "chroma": "ok" if chroma_ok else "unavailable",
    }
    all_ok = all(v == "ok" for v in checks.values())
    return JSONResponse(content={"status": checks}, status_code=200 if all_ok else 503)


@router.get("/health/circuit-breakers")
async def circuit_breakers():
    return {
        "circuit_breakers": [
            chroma_cb.status(),
            openai_cb.status(),
            redis_cb.status(),
        ]
    }


@router.get("/health/services")
async def services_health(request: Request):
    """Returns the cached health snapshot. No live probes on this path.

    Background task in lifespan refreshes the snapshot every
    settings.health_probe_interval_seconds seconds.
    """
    snapshot = dict(request.app.state.health_snapshot)
    checked_at = snapshot.get("checked_at", 0)
    if time.time() - checked_at > 2 * settings.health_probe_interval_seconds:
        snapshot["stale"] = True
    return snapshot
