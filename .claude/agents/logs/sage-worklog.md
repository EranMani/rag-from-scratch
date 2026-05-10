# Sage — Worklog
# Project: RAG from Scratch
# Stack: Python / FastAPI / LangGraph / NiceGUI / SQLite / ChromaDB / AWS EC2

---

## Current State
Last reviewed: Commit 21 `production-compose` (Pass 2 — Viktor fix verification)
Open findings unresolved: MEDIUM: hardcoded NiceGUI storage secret : Rex (from Commit 10, still open)
CRITICAL findings this project: 0 — none
Attack surface map (current):
- POST /api/chat — public SSE endpoint; user input flows to LangGraph → LLM; session_id user-controlled memory key
- POST /api/ingest — authenticated (get_current_user); path traversal mitigations verified intact
- POST /api/auth/login, /api/auth/register — credential intake
- GET /api/auth/me — authenticated
- GET /metrics — unauthenticated Prometheus endpoint (pre-existing; not reviewed this session)
- NiceGUI UI layer — calls /api/chat via internal httpx client; stores JWT in app.storage.user
- MemorySaver — in-process, not persisted; keyed by user-supplied session_id with no ownership binding
- OpenAI API key — env-only via pydantic-settings; no hardcoding found
- JWT secret — env-only with 32-char minimum validator; no hardcoding found
- Redis query cache — keyed by SHA-256(question + null-byte + user_level); per-level isolation verified
- mastery_level DB value — coercion guard with warning log on unexpected values; allowlist validated
- Host network exposure: app:8000 (intended public), grafana:3000 (portfolio), all others bridge-internal only
- Redis (bridge-internal): no auth; full cache read/write to any compromised container
- Chroma (bridge-internal): no auth; full vector store access to any compromised container
- Elasticsearch (bridge-internal): xpack.security disabled by Team Lead decision; team-documented
- Logstash monitoring API :9600 (bridge-internal): unauthenticated, exposes pipeline/plugin/OS metadata
- ./data bind mount into app container: SQLite user DB on host filesystem; no volume isolation

---

## Session Index

| # | Commit | Status | Key Decision |
|---|--------|--------|--------------|
| 01 | 10 `langgraph-graph-assembly` | Done | No hard blocks; one MEDIUM finding on hardcoded NiceGUI storage secret |
| 02 | 21 `production-compose` | Done (Pass 1) | NON-BLOCKING; two LOW + two INFO findings; no Hard Block triggers |
| 03 | 21 `production-compose` | Done (Pass 2) | NON-BLOCKING confirmed; all three Viktor-fix changes verified; ALLOW_ANONYMOUS_CHAT typo fix improves enforcement of false default |

---

## Session 01 — Commit 10: `langgraph-graph-assembly`

**Date:** 2026-05-10
**Status:** Done

### Task Brief

Ad-hoc security review of the SSE streaming refactor. Six areas flagged for
scrutiny: prompt injection / input sanitization, session_id as memory key,
MemorySaver isolation in multi-worker deployments, SSE headers, httpx error
handling in ui.py, and OpenAI API key provenance.

### Findings

**Finding 1 — MEDIUM — Hardcoded NiceGUI storage secret**
File: src/app/ui.py:370
`ui.run_with(fastapi_app, mount_path="/", storage_secret="rag-secret-key")`
Literal string used as the NiceGUI session-storage encryption key. Any attacker
who reads the source (public portfolio = public repo) can forge or decrypt
NiceGUI storage cookies, potentially stealing access tokens stored in
app.storage.user. Mitigation: move to settings.nicegui_storage_secret sourced
from env.

**Finding 2 — LOW — Unbounded session_id memory accumulation (session_id IDOR)**
File: src/app/api/routes/chat.py:138 / src/agents/graph.py:31
MemorySaver holds all thread checkpoints for the process lifetime. An attacker
(anonymous, if allow_anonymous_chat=True) can supply arbitrary session_id values,
either enumerating other users' conversation history (if session IDs are guessable)
or growing the in-process checkpoint store without bound. No max-sessions cap or
ownership binding exists. Mitigation: bind thread_id to authenticated user_id
(e.g., thread_id = f"{user_id}:{session_id}"), reject anonymous callers from
supplying a session_id, and add a per-process session cap.

**Finding 3 — INFO — Prompt injection surface acknowledged, no server-side mitigation**
req.question flows unsanitized into HumanMessage → LLM. For a portfolio RAG app
scoped to educational content, this is expected and acceptable. Noted for
completeness; no action required.

**Finding 4 — INFO — MemorySaver not isolated across workers**
Pre-existing architectural characteristic acknowledged in the commit brief.
Not a security defect in single-worker EC2 deployment.

**Verified clean:**
- /api/ingest auth gate intact (get_current_user, non-optional)
- OpenAI API key: env-only, empty-string default, no hardcoding
- JWT secret: env-only, 32-char minimum enforced at startup
- httpx internal client has 30s timeout, no redirect concerns (localhost only)
- SSE Content-Type set correctly via StreamingResponse media_type
- No shell=True, no eval/exec, no pickle, no raw SQL, no verify=False

### Decisions Made

**1. session_id IDOR rated LOW not HIGH**
The attack requires knowledge of another user's session_id, which is a UUID4
generated client-side and never disclosed in responses. Enumeration is
computationally infeasible. Rated LOW (defense-in-depth) rather than HIGH.
The memory growth concern is real but bounded by the EC2 instance's restart cycle.

**2. Prompt injection rated INFO**
This is a portfolio RAG system, not a privileged action system. The LLM has no
tool access that would amplify injection impact. No server-side mitigation required
at this stage.

---

## Session 02 — Commit 21: `production-compose`

**Date:** 2026-05-10
**Status:** Done

### Task Brief

Security review of new production Docker Compose file (`docker-compose.prod.yml`)
and `.env.prod.example`. Five focus areas: secrets in files/env defaults, host
port exposure, Elasticsearch xpack disabled (known team decision), Grafana on
host port 3000 (portfolio requirement), and general trust boundary issues in the
compose topology.

### Hard Block Check

No Hard Block triggers present:
- No raw SQL string interpolation
- No hardcoded credentials (all secret fields are empty in example file)
- No verify=False
- No shell=True with user input
- No pickle deserialization
- No auth-that-fails-open
- No secrets in log statements
- No == comparison on passwords

### Findings

**Finding 1 — LOW — Redis: no authentication within the bridge network**
File: docker-compose.prod.yml (redis service)
The Redis container runs without a password (`redis-server --appendonly yes`, no
`--requirepass` flag). Within the `rag-network` bridge, any compromised container
can connect to `redis:6379` with full unauthenticated access — read, write, and
FLUSHALL on the entire cache. For a public portfolio demo this is acceptable; for
any real deployment it is not.
Mitigation: add `--requirepass ${REDIS_PASSWORD}` to the redis command, add
`REDIS_PASSWORD=` to `.env.prod.example`, and update `REDIS_URL` in the app
service to `redis://:${REDIS_PASSWORD}@redis:6379/0`.

**Finding 2 — LOW — Logstash monitoring API unauthenticated (bridge-internal)**
File: docker-compose.prod.yml (logstash service)
Logstash exposes port 9600 (Monitoring API) within the bridge network with no
authentication. An attacker who has compromised any container on `rag-network`
can query `http://logstash:9600` to enumerate installed plugins, pipeline
configurations, and OS-level statistics — useful lateral reconnaissance. There
is also no pipeline config volume mounted, meaning Logstash starts with defaults
and its behavior is undefined.
Mitigation: if Logstash is not yet wired up, comment it out or add a
`profiles: [logging]` gate. If it is active, mount a pipeline config volume and
set `xpack.monitoring.enabled=false` or pin monitoring to localhost-only via
`http.host: 0.0.0.0` to `http.host: 127.0.0.1` in logstash.yml (bridge-internal
so impact is limited, but defense-in-depth applies).

**Finding 3 — INFO — Grafana on host port 3000: admin password is the only access control**
File: docker-compose.prod.yml (grafana service)
Grafana is externally reachable at host:3000. `GF_USERS_ALLOW_SIGN_UP=false` is
correctly set. However, the admin account's only protection is the
`GRAFANA_ADMIN_PASSWORD` env var. There is no IP allowlisting, no reverse proxy
with TLS, and no rate-limiting on the Grafana login form configured in compose.
For a portfolio demo this is acceptable given the Team Lead decision. Noted so
the operator knows to set a strong `GRAFANA_ADMIN_PASSWORD` and consider fronting
Grafana with a reverse proxy if the demo is long-lived.
No action required.

**Finding 4 — INFO — Elasticsearch xpack.security disabled (team decision)**
File: docker-compose.prod.yml (elasticsearch service)
`xpack.security.enabled=false` disables all Elasticsearch authentication, TLS,
and audit logging. Elasticsearch is bridge-internal only (expose, not ports), so
the attack path requires first compromising another container. The inline TODO
comment documents the team's intent. Flagged for completeness per instructions.
No action required for portfolio demo context.

**Verified clean:**
- .env.prod.example: all four secret fields empty (no defaults that could be shipped)
- docker-compose.prod.yml: no literal secrets in any environment block
- All non-app, non-grafana services use expose: not ports: — host attack surface
  is limited to :8000 and :3000 as intended
- ANONYMIZED_TELEMETRY=FALSE on Chroma: prevents deployment fingerprinting via telemetry
- GF_USERS_ALLOW_SIGN_UP=false on Grafana: self-registration disabled
- Log rotation configured on all services (max-size: 10m, max-file: 5)
- Ollama memory limit set (5G): prevents OOM exploitation via model loading

### Decisions Made

**1. Redis no-auth rated LOW not MEDIUM**
The attack path requires prior container compromise within the bridge network.
Redis is not reachable from the host. Lateral movement within a Docker bridge
network is a meaningful threat on a shared host, less so on a dedicated EC2
instance. Rated LOW for a single-host portfolio deployment.

**2. Logstash monitoring API rated LOW not MEDIUM**
Same reasoning as Redis: bridge-internal only. Reconnaissance value to an attacker
is real but limited in a single-host context. The absence of a pipeline config
mount is the more operationally concerning issue.

**3. Grafana and Elasticsearch rated INFO**
Both are explicit Team Lead decisions with inline documentation. Noted per
instructions; no action required.

### Verdict

NON-BLOCKING. Two LOW findings with mitigations. Two INFO findings (team decisions).
No Hard Block triggers. The infra topology is sound: secrets handling is correct,
host exposure is minimal and intentional, and the internal service mesh follows
least-exposure principles. The LOWs are appropriate for a portfolio demo deployment
and are documented here for any future hardening pass.

