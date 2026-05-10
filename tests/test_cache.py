"""
Tests for Commit 18 — redis_cache key isolation by user_level.

Coverage targets:
  - Cache keys for the same question but different user_level values must differ
    (guards against the naive string-concatenation collision).
  - set_query / get_query round-trip: a value stored under 'novice' is NOT
    retrievable under 'expert' (cross-level isolation via mock Redis client).

Design notes:
- _make_key is a pure function — tested directly without Redis.
- RAGRedisCache round-trip test uses a MagicMock as the Redis client so no
  real Redis process is required.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from rag.cache.redis_cache import _make_key, RAGRedisCache


# ---------------------------------------------------------------------------
# Pure-function tests — no Redis required
# ---------------------------------------------------------------------------

class TestMakeKeyCacheIsolation:
    """_make_key must produce distinct digests for different user_level values."""

    def test_same_question_different_level_yields_different_keys(self) -> None:
        """Same question + different user_level -> different cache keys."""
        key_novice = _make_key("query", f"What is RAG?\x00novice")
        key_expert = _make_key("query", f"What is RAG?\x00expert")
        assert key_novice != key_expert

    def test_all_five_levels_produce_distinct_keys(self) -> None:
        """Every valid mastery level produces a unique cache key for the same question."""
        levels = ["novice", "beginner", "intermediate", "advanced", "expert"]
        question = "Explain chunking."
        keys = [_make_key("query", f"{question}\x00{level}") for level in levels]
        assert len(set(keys)) == len(levels), (
            f"Expected {len(levels)} distinct keys, got {len(set(keys))}: {keys}"
        )

    def test_ambiguous_inputs_do_not_collide(self) -> None:
        """Null-byte separator prevents ('foobar', 'expert') from colliding
        with ('foo', 'barexpert') — the classic naive-concatenation collision."""
        key_a = _make_key("query", f"foobar\x00expert")
        key_b = _make_key("query", f"foo\x00barexpert")
        assert key_a != key_b, (
            "Null-byte separation must make ('foobar', 'expert') and "
            "('foo', 'barexpert') produce different hashes"
        )


# ---------------------------------------------------------------------------
# Round-trip tests — mock Redis client
# ---------------------------------------------------------------------------

class TestRAGRedisCacheLevelIsolation:
    """set_query / get_query must store and retrieve per user_level independently."""

    def _make_cache_with_mock_client(self) -> tuple[RAGRedisCache, dict]:
        """Return a RAGRedisCache backed by an in-memory dict via MagicMock."""
        store: dict = {}

        mock_client = MagicMock()
        mock_client.get.side_effect = lambda key: store.get(key)
        mock_client.setex.side_effect = lambda key, ttl, value: store.update({key: value})

        cache = RAGRedisCache()
        cache._client = mock_client  # bypass redis.from_url
        return cache, store

    def test_set_novice_not_retrievable_as_expert(self) -> None:
        """Value stored under 'novice' must not be returned for 'expert' query."""
        cache, _ = self._make_cache_with_mock_client()
        cache.set_query("What is RAG?", "novice answer", "novice")
        result = cache.get_query("What is RAG?", "expert")
        assert result is None, (
            "Cross-level cache hit: 'expert' retrieved a value stored under 'novice'"
        )

    def test_set_and_get_same_level_round_trips(self) -> None:
        """Value stored under a level is retrievable under the same level."""
        cache, _ = self._make_cache_with_mock_client()
        cache.set_query("What is RAG?", "expert answer", "expert")
        result = cache.get_query("What is RAG?", "expert")
        assert result == "expert answer"

    def test_two_levels_stored_independently(self) -> None:
        """Novice and expert answers for the same question are stored separately."""
        cache, _ = self._make_cache_with_mock_client()
        cache.set_query("What is RAG?", "novice answer", "novice")
        cache.set_query("What is RAG?", "expert answer", "expert")

        assert cache.get_query("What is RAG?", "novice") == "novice answer"
        assert cache.get_query("What is RAG?", "expert") == "expert answer"
