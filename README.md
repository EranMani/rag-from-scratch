# RAG From Scratch

Production-oriented RAG demo with a LangGraph agent, Chroma retrieval, realtime
knowledge-profile updates, local/cloud model fallback, and Dockerized service
infrastructure.

## Quickstart

Install dependencies with `uv`:

```bash
uv sync
```

Copy the environment template and set the values you need:

```bash
cp .env.example .env
```

Run the standalone terminal demo:

```bash
uv run rag-demo
```

If `OPENAI_API_KEY` is configured, the demo uses OpenAI embeddings and OpenAI
generation. If the key is missing or invalid, it routes to Ollama generation and
local Hugging Face embeddings.

To force the local fallback path:

```bash
DEMO_FORCE_OLLAMA=true uv run rag-demo
```

For Ollama fallback, start Ollama and pull the configured model:

```bash
ollama pull gemma3:4b
```

## Infrastructure

The repo has two runtime shapes:

- **Standalone demo:** runs from the local Python process, creates a local Chroma
  index under `data/demo_chroma_db/`, and chooses OpenAI or Ollama at startup.
- **Docker app stack:** runs FastAPI plus the supporting services needed for the
  full application.

### Docker Services

`docker-compose.yml` defines the local service stack:

| Service | Purpose |
|---|---|
| `app` | FastAPI/NiceGUI application, LangGraph agent, API routes, startup ingestion |
| `chroma` | Persistent vector database for semantic retrieval |
| `redis` | Cache backend for query, embedding, and LLM response layers |
| `ollama` | Local LLM runtime used as the cloud fallback/local path |
| `prometheus` | Optional metrics scraper, enabled with the `monitoring` profile |
| `grafana` | Optional dashboards, enabled with the `monitoring` profile |
| `elasticsearch` | Optional log storage for the monitoring stack |
| `logstash` | Optional log ingestion pipeline |
| `kibana` | Optional log exploration UI |

Run the core app stack:

```bash
docker compose up --build
```

Run with monitoring services:

```bash
docker compose --profile monitoring up --build
```

The local compose file exposes:

- API/UI: `http://localhost:8000`
- Chroma: `http://localhost:8001`
- Redis: `localhost:6379`
- Ollama: `http://localhost:11434`
- Prometheus: `http://localhost:9090` when monitoring is enabled
- Grafana: `http://localhost:3000` when monitoring is enabled
- Kibana: `http://localhost:5601` when monitoring is enabled

`docker-compose.prod.yml` tightens exposure for production-like deployment:
Chroma, Redis, Prometheus, Elasticsearch, Logstash, Kibana, and Ollama are
internal-only with `expose`, while the app and Grafana are externally published.

### Startup Flow

On FastAPI startup, [src/app/main.py](src/app/main.py) performs the operational
boot sequence:

1. Initialize SQLite auth/profile tables.
2. Seed the admin user.
3. Load markdown knowledge-base documents.
4. Build the in-memory BM25 fallback retriever.
5. Check Chroma and ingest documents if the collection is empty.
6. Compile the LangGraph graph with a `MemorySaver` checkpointer.
7. Start background dependency health probes.

That startup path means the application can still answer with degraded retrieval
when Chroma is unavailable, because BM25 is loaded before requests are served.

### Redis

Redis is used as the application cache layer. The environment controls cache
lifetimes:

- `CACHE_TTL_QUERY`: exact query/answer cache
- `CACHE_TTL_EMBEDDING`: text-to-vector cache
- `CACHE_TTL_LLM`: prompt-to-response cache

The compose stack runs Redis with append-only persistence:

```text
redis-server --appendonly yes
```

### Circuit Breakers

The app has circuit breakers for Chroma, OpenAI, and Redis in
[src/rag/resilience/circuit_breaker.py](src/rag/resilience/circuit_breaker.py).
Each breaker has three states:

- `CLOSED`: service is healthy; requests flow normally
- `OPEN`: repeated failures crossed the threshold; avoid the failing service
- `HALF_OPEN`: recovery window elapsed; allow a probe request

The configured thresholds are:

- `CB_FAILURE_THRESHOLD`: failures before opening
- `CB_RECOVERY_TIMEOUT`: seconds before a half-open recovery probe

Where fallbacks apply:

- **Retrieval:** Chroma failure routes retrieval to the BM25 fallback retriever.
- **Generation:** OpenAI failure can route generation to Ollama when the breaker
  is open. The standalone demo also catches OpenAI auth failures and immediately
  reroutes to Ollama.
- **Health:** `/api/health/circuit-breakers` exposes breaker state.

### Local vs Cloud

The project intentionally supports both cloud and local operation:

| Layer | Cloud/default path | Local/fallback path |
|---|---|---|
| Chat generation | OpenAI chat model | Ollama, default `gemma3:4b` |
| Embeddings | OpenAI `text-embedding-3-small` | Hugging Face `all-MiniLM-L6-v2` |
| Vector store | Chroma service in Docker | Local demo Chroma index |
| Cache | Redis service | Redis service in Docker |
| App state | LangGraph `MemorySaver` per app lifetime | Same |

OpenAI embeddings and local Hugging Face embeddings use different vector
dimensions, so the standalone demo stores separate Chroma indexes per backend:

```text
data/demo_chroma_db/openai/
data/demo_chroma_db/ollama/
```

### Health And Observability

Operational endpoints:

- `GET /api/health`: liveness
- `GET /api/health/ready`: live Redis and Chroma readiness probe
- `GET /api/health/services`: cached dependency snapshot from the background probe
- `GET /api/health/circuit-breakers`: Chroma/OpenAI/Redis breaker states
- `GET /metrics`: Prometheus metrics

Prometheus metrics include:

- request counts and latency
- cache hits and misses
- chunks retrieved per query
- LLM call counts by provider/status
- circuit breaker state gauges

## Project Structure

```text
src/
  agents/              LangGraph state, graph assembly, and nodes
  rag/                 retrieval, indexing, embeddings, providers, resilience
  app/                 FastAPI routes, UI, auth, profile, health, metrics
  rag_from_scratch/    standalone demo entry point
data/
  sample_docs/         small public docs used by the demo
  knowledge_base/      app knowledge base loaded at startup
monitoring/            Prometheus, Grafana, Logstash configuration
```
