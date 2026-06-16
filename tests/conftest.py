"""Test bootstrap defaults.

The app intentionally requires strong runtime secrets, but tests should collect
from a fresh clone without a local .env file. Set safe dummy values before test
modules import app.core.config.
"""

from __future__ import annotations

import os


os.environ.setdefault("JWT_SECRET", "test-jwt-secret-000000000000000000000000")
os.environ.setdefault("NICEGUI_STORAGE_SECRET", "test-nicegui-secret-0000000000000000000")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("EMBEDDING_PROVIDER", "local")
os.environ.setdefault("CHROMA_HOST", "localhost")
os.environ.setdefault("CHROMA_PORT", "8001")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("SQLITE_DB_PATH", ":memory:")
