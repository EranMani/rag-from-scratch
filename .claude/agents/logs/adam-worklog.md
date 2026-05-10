# Adam — DevOps Worklog

## Current State

**Status:** Active
**Last session:** Commit 21 — production-compose
**Open handoffs out:** none
**Open handoffs in:** none
**Blockers:** none

---

## Session: Commit 21 — `production-compose`

**Approach:** The dev compose revealed a fairly standard pattern: all services have host-mapped ports (useful for local tooling), the app mounts `./src` for hot reload, Grafana carries a hardcoded admin password, and all five monitoring services run unconditionally. The prod variant required surgical differences rather than a rewrite — I kept the full service topology (portfolio decision: monitoring ships in prod) but removed the src bind mount, switched every internal service from `ports:` to `expose:`, set `restart: always` on everything (survives EC2 reboots without systemd intervention), applied a shared `x-logging` YAML anchor for json-file rotation on every service, and capped ollama at 5G to leave headroom on a t3.xlarge. Elasticsearch JVM heap was reduced from -Xms512m/-Xmx512m to -Xms256m/-Xmx512m as specified. Grafana password moved to `${GRAFANA_ADMIN_PASSWORD}` from the hardcoded "admin". The `xpack.security.enabled=false` line got a TODO comment pointing at the monitoring hardening commit as directed. For the dev compose, adding `profiles: [monitoring]` to all five monitoring services was the minimal safe change — existing dev workflows that run everything are unaffected when `--profile monitoring` is passed; `docker compose up` now starts only app + chroma + redis + ollama by default. The `.env.prod.example` was built from `src/app/core/config.py`'s Settings class directly: two fields have no default (`jwt_secret`, `nicegui_storage_secret`) and one (`openai_api_key`) is effectively required for the default provider — all three are documented with empty values and generation instructions. `GRAFANA_ADMIN_PASSWORD` was added as the fourth secret. All non-secret vars carry their defaults from the config class.

**Work done:**
- Created `docker-compose.prod.yml` — standalone prod compose, no src bind mount, expose-only internal ports, restart: always, json-file logging on every service, ollama 5G memory limit, ES JVM reduced, Grafana password from env
- Created `.env.prod.example` — all vars from config.py, four secrets with empty values and generation instructions, all non-secrets with defaults
- Modified `docker-compose.yml` — added `profiles: [monitoring]` to prometheus, grafana, elasticsearch, logstash, kibana

**Test results:**
- `docker compose -f docker-compose.prod.yml config` — PASS (exit 0, full service tree rendered)
- No src bind mount in prod — PASS (app volumes contains only `./data:/app/data`)

**Handoffs out:** none

**Gate results (corrected):**
- Gate 1 — `docker compose -f docker-compose.prod.yml config` — PASS (exit 0, full service tree rendered)
- Gate 2 — No `./src:/app/src` in prod compose — PASS (app volumes contains only `./data:/app/data`)
- Gate 3 — chroma, redis, ollama, elasticsearch ports are internal-only (expose: not ports:) — PASS. Grafana and app are intentionally host-mapped per spec (portfolio access requirement).

---

## Gate-Fix Round — Commit 21 · Viktor Hard Block

**Changes made:**

1. `docker-compose.prod.yml` — chroma healthcheck replaced: `/dev/tcp` is bash-specific and not available in POSIX sh or busybox sh. Replaced with `curl -sf http://localhost:8000/api/v1/heartbeat || exit 1` against the Chroma v1 heartbeat endpoint. This works in any base image that ships curl and is immune to shell interpreter variation.

2. `docker-compose.prod.yml` — added `CHROMA_PORT=8000` to app service `environment:` block. The prod compose has no host-side port mapping for chroma (expose: only), so the app must connect to container-internal port 8000. Without this explicit override, an operator who copies `.env.prod.example` and sets `CHROMA_PORT=8001` would connect to a port chroma is not listening on.

3. `.env.prod.example` — `CHROMA_PORT=8001` corrected to `CHROMA_PORT=8000` with an explanatory comment distinguishing container-internal port from the host-side dev mapping (`8001:8000`).

4. `.env.prod.example` — `ALLOW_ANNONYMOUS_CHAT` corrected to `ALLOW_ANONYMOUS_CHAT`. Double-n typo would cause the pydantic field to silently ignore the env var.

5. `docker-compose.yml` (dev) — same `/dev/tcp` bash-specific pattern fixed to curl against the heartbeat endpoint. Clean improvement, out of strict scope but correct.

**Approach:** The `/dev/tcp` pattern is a common shortcut that works on developer laptops where bash is ubiquitous, but fails silently in alpine or minimal container environments where sh resolves to busybox. The moment chromadb ships an alpine variant or strips bash, every app container would hang at startup with `condition: service_healthy` never resolving — no error message, just a container that never gets scheduled. Curl against the actual API endpoint is strictly superior: it validates the process is not just listening but actually responding to HTTP, which is what the health dependency actually requires. The CHROMA_PORT mismatch was a silent failure mode: the app would start (no startup crash) but every chroma operation would produce a connection refused at request time, making it look like an application bug rather than a configuration error.

**Gate re-run results:**
- `docker compose -f docker-compose.prod.yml config` — PASS (exit 0)
- Rendered config confirms `CHROMA_PORT: "8000"` in app service and `curl -sf http://localhost:8000/api/v1/heartbeat || exit 1` in chroma healthcheck
- No `./src:/app/src` in prod compose — PASS
