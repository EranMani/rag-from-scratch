# Module 6: Production and Performance

## Caching Strategy
Every LLM call and vector search is expensive. Three cache layers reduce costs:

1. **Query Cache** (Redis, TTL: 1 hour): Stores complete question → answer pairs. If the same question is asked again, serve instantly from cache.
2. **Embedding Cache** (Redis, TTL: 24 hours): Stores text → vector. Computing embeddings has cost; cache them for repeated text.
3. **LLM Response Cache** (Redis, TTL: 30 min): Stores prompt hash → response. Most valuable — LLM calls are the slowest step.

Cache key = SHA-256 hash of the input. Hit rate is a key dashboard metric.

## Circuit Breaker Pattern
Prevents a failing service from cascading failures across the system.

Three states:
- **CLOSED**: Normal operation. Requests flow through.
- **OPEN**: Too many failures detected. Requests are rejected immediately (fail-fast). No calls to the broken service.
- **HALF-OPEN**: After a timeout, one probe request is allowed. If it succeeds → back to CLOSED. If it fails → back to OPEN.

Services protected in this system: ChromaDB, OpenAI API, Redis.

## Graceful Degradation
When a service fails, the system degrades gracefully rather than returning an error:
- ChromaDB unavailable → fall back to BM25 keyword search
- OpenAI unavailable → fall back to Ollama (local Gemma 4)
- Redis unavailable → bypass cache, serve normally (with warning log)

## Key Metrics to Monitor
- **Response latency** (p50, p95): How fast is the system?
- **Cache hit rate**: Are repeated queries being cached?
- **Retrieval quality**: Are the right chunks being retrieved?
- **Circuit breaker state**: Is any upstream service degraded?
- **LLM provider**: Which provider is currently serving requests?

## Observability Stack
- **Prometheus**: Scrapes `/metrics` endpoint every 15 seconds
- **Grafana**: Visualizes Prometheus metrics on dashboards
- **Logstash**: Collects JSON logs from stdout (Docker log driver)
- **Elasticsearch**: Stores and indexes logs for full-text search
- **Kibana**: Visualizes logs — filter by level, trace_id, latency
