# Imports
from pydantic_settings import BaseSettings, SettingsConfigDict
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


@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
 