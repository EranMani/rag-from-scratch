from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

REGISTRY = CollectorRegistry()


# Request metrics
REQUEST_COUNT = Counter(
    "rag_requests_total",
    "Total Rag query requests",
    ["endpoint", "status"],
    registry=REGISTRY
)

REQUEST_LATENCY = Histogram(
    "rag_request_latency_seconds",
    "RAG query end-to-end latency",
    ["endpoint"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=REGISTRY,
)

# Cache metrics
CACHE_HITS = Counter(
    "rag_cache_hits_total",
    "Cache hits by layer",
    ["layer"],          # "query" | "embedding" | "llm"
    registry=REGISTRY,
)

CACHE_MISSES = Counter(
    "rag_cache_misses_total",
    "Cache misses by layer",
    ["layer"],
    registry=REGISTRY,
)

# Retrieval metrics
CHUNKS_RETRIEVED = Histogram(
    "rag_chunks_retrieved",
    "Number of chunks retrieved per query",
    buckets=[1, 2, 3, 5, 8, 10],
    registry=REGISTRY,
)

# Circuit breaker state
CIRCUIT_BREAKER_STATE = Gauge(
    "rag_circuit_breaker_state",
    "Circuit breaker state: 0=CLOSED 1=OPEN 2=HALF_OPEN",
    ["service"],        # "chroma" | "openai" | "redis"
    registry=REGISTRY,
)

# LLM provider
LLM_CALLS = Counter(
    "rag_llm_calls_total",
    "LLM API calls",
    ["provider", "status"],
    registry=REGISTRY,
)