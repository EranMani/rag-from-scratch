import asyncio
import time

import httpx

from app.core.config import settings
from rag.cache.redis_cache import cache
from rag.resilience.circuit_breaker import openai_cb


async def probe_redis() -> bool:
    try:
        await asyncio.to_thread(cache._get_client().ping)
        return True
    except Exception:
        return False


async def probe_chroma(client: httpx.AsyncClient) -> bool:
    try:
        r = await client.get(
            f"http://{settings.chroma_host}:{settings.chroma_port}/api/v2/heartbeat",
            timeout=settings.health_probe_timeout_seconds,
        )
        r.raise_for_status()
        return True
    except Exception:
        return False


async def build_snapshot(client: httpx.AsyncClient) -> dict:
    redis_ok = await probe_redis()
    chroma_ok = await probe_chroma(client)

    llm_state = openai_cb.state.name
    llm_healthy = llm_state in ("CLOSED", "HALF_OPEN")

    services = {
        "api": "healthy",
        "redis": "healthy" if redis_ok else "unavailable",
        "vectorstore": "healthy" if chroma_ok else "degraded",
        "llm": "healthy" if llm_healthy else "degraded",
    }
    services["rag_pipeline"] = (
        "healthy"
        if services["vectorstore"] == "healthy" and services["llm"] == "healthy"
        else "degraded"
    )

    overall = "healthy" if all(v == "healthy" for v in services.values()) else "degraded"
    return {"status": overall, "services": services, "checked_at": time.time()}
