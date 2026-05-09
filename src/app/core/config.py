# Imports
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # LLM Provider
    llm_provider: str = "openai" # openai | ollama
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "gemma3:4b"

    # Embedding
    embedding_provider: str = "local" # openai | local

    # ChromaDB
    chroma_host: str = "chroma"
    chroma_port: int = 8001
    chroma_collection: str = "rag_knowledge_base"

    # Redis
    redis_url: str = "redis://redis:6379/0"
    cache_ttl_query: int = 3600
    cache_ttl_embedding: int = 86400
    cache_ttl_llm: int = 1800

    # Circuit breaker
    cb_failure_threshold: int = 5
    cb_recovery_timeout: int = 30

    # Prometheus
    prometheus_port: int = 9090

    # Auth — no default: startup fails with a clear error if JWT_SECRET is not set.
    # Minimum 32 characters enforced by require_strong_secret below.
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    sqlite_db_path: str = "data/app_users.db"
    allow_anonymous_chat: bool = False

    @field_validator("jwt_secret")
    @classmethod
    def require_strong_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError(
                f"JWT_SECRET must be at least 32 characters — "
                f"got {len(v)}. Set a strong secret in your .env file."
            )
        return v


@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
 