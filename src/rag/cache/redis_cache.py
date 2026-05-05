import hashlib
import json
import redis
from typing import Any, Optional
from app.core.config import settings
from app.core.logging_config import logger
from app.core.metrics import CACHE_HITS, CACHE_MISSES


def _make_key(layer: str, content: str) -> str:
    """SHA-256 hash of the content, prefixed by cache layer."""
    digest = hashlib.sha256(content.encode()).hexdigest()
    return f"rag:{layer}:{digest}"


class RAGRedisCache:
    """
    Three cache layers:
    - query: exact question -> final answer (TTL: 1h)
    - embedding: text → embedding vector (TTL: 24h)
    - llm: prompt hash → LLM response (TTL: 30min)
    """

    def __init__(self):
        self._client: Optional[redis.Redis] = None

    def _get_client(self) -> redis.Redis:
        """Get redis client. Create new if not exists"""
        if self._client is None:
            self._client = redis.from_url(settings.redis_url, decode_responses=True)
        return self._client

    def _safe_get(self, key: str) -> Optional[str]:
        """Swallow Redis errors - cache is optional"""
        try:
            return self._get_client().get(key)
        except Exception as e:
            logger.warning("Redis GET failed", extra={"key": key, "error": str(e)})

    def _safe_set(self, key: str, value: str, ttl: int) -> None:
        """Set the key and value using ttl in atomic way"""
        try:
            self._get_client().setex(key, ttl, value)
        except Exception as e:
            logger.warning("Redis SET failed", extra={"key": key, "error": str(e)})

    # -- Query cache ---------------
    def get_query(self, question: str) -> Optional[str]:
        key = _make_key("query", question)
        value = self._safe_get(key)
        if value:
            CACHE_HITS.labels(layer="query").inc()
            logger.info("Query cache hit", extra={"question": question[:80]})
        else:
            CACHE_MISSES.labels(layer="query").inc()
        return value

    def set_query(self, question: str, answer: str) -> None:
        key = _make_key("query", question)
        self._safe_set(key, answer, settings.cache_ttl_query)

    # -- Embedding cache -----------
    def get_embedding(self, text: str) -> Optional[list[float]]:
        key = _make_key("embedding", text)
        raw = self._safe_get(key)
        if raw:
            CACHE_HITS.labels(layer="embedding").inc()
            return json.loads(raw)
        CACHE_MISSES.labels(layer="embedding").inc()
        return None

    def set_embedding(self, text: str, vector: list[float]) -> None:
        key = _make_key("embedding", text)
        self._safe_set(key, json.dumps(vector), settings.cache_ttl_embedding)

    # -- llm response cache ----------
    def get_llm_response(self, prompt: str) -> Optional[str]:
        key = _make_key("llm", prompt)
        value = self._safe_get(key)
        if value:
            CACHE_HITS.labels(layer="llm").inc()
            logger.info("LLM response cache hit")
        else:
            CACHE_MISSES.labels(layer="llm").inc()
        return value

    def set_llm_response(self, prompt: str, response: str) -> None:
        key = _make_key("llm", prompt)
        self._safe_set(key, response, settings.cache_ttl_llm)

cache = RAGRedisCache()
