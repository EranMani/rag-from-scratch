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

---

## Ad-hoc Fix — ChromaDB health check — 2026-05-11

**Approach:** The symptom was `dependency failed to start: container rag-chroma is unhealthy`. Two hypotheses going in: wrong API path (v1 vs v2) or missing curl. `docker inspect` health log answered immediately — every check returned `/bin/sh: 1: curl: not found` with exit 1. The container is a native Go/Rust binary (`chroma` ELF, no Python interpreter, no curl, no wget, no netcat). The server itself was healthy: `docker logs` showed it binding on 8000 and accepting connections. Ruled out fixing the image (upstream, not ours to patch) and installing curl at runtime (wrong layer — health check runs in the existing container, not a new one). Bash `/dev/tcp` built-in was the only available HTTP mechanism; confirmed it works with a manual exec producing HTTP/1.0 200 from `/api/v2/heartbeat`. Also confirmed `/api/v1/heartbeat` — the previous path — also returns 200 on chromadb 1.5.8 (backward-compatible alias exists), so the endpoint path was not the failure mode. Both failures were the `curl` binary. Replaced health check in both `docker-compose.yml` and `docker-compose.prod.yml` with the `/dev/tcp` bash built-in pattern. Container transitioned from `unhealthy` to `healthy` on the first check after restart (failing streak: 0).

**Failure mode:** `curl: not found` — the chromadb/chroma:latest image ships a native binary with no HTTP client tools.

**Changes made:**
- `docker-compose.yml` line 61 — health check: `curl` replaced with bash `/dev/tcp` against `/api/v2/heartbeat`
- `docker-compose.prod.yml` line 69 — same replacement

**Verification:**
- `docker inspect rag-chroma` health log: ExitCode 0, FailingStreak 0, Status `healthy` on first probe after restart

---

## 📋 Replan Notice — 2026-05-17

The commit plan has been updated. Here is what changed for you:

**What was removed:** nothing

**What was added:** Commits 26–29 — four visual UI redesign commits (Aria's responsibility).
- Commit 26 `ui-foundation` — Inter font, palette tokens, auth page glass morphism
- Commit 27 `ui-header` — brand mark, refined typography
- Commit 28 `ui-chat` — gradient bubbles, AI accent, knowledge check prominence
- Commit 29 `ui-sidebar-admin` — mastery badge, score pills, stat card accents

All four touch only `src/app/ui.py` with a hard scope rule (no streaming, no auth logic).

**What changed in your sequence:**
- Old Commit 26 `nginx-config` → **Commit 30**
- Old Commit 27 `aws-ec2-deployment` → **Commit 31**

**Your next commit is now: Commit 30 `nginx-config`**
Specs updated: `commit-specs/commit-30.md` and `commit-specs/commit-31.md`.
Dependency updated: Commit 30 now depends on Commit 29 (last UI commit).

---

## 📋 Replan Notice — 2026-05-19

The commit plan has been updated again. Here is what changed for you:

**What changed:** Three new Aria UI commits (30, 31, 32) were inserted before your nginx commit. Your commits have shifted by 3 positions again:
- `nginx-config` → **Commit 33** (was 30)
- `aws-ec2-deployment` → **Commit 34** (was 31)

**Dependency updated:**
- Commit 33 `nginx-config` now depends on Commit 32 (last UI commit)
- Commit 34 `aws-ec2-deployment` now depends on Commit 33

**Specs updated:** `commit-specs/commit-33.md` and `commit-specs/commit-34.md`

**Your next commit is now: Commit 33 `nginx-config`** (after Aria completes Commits 30, 31, 32)

---

## Replan Notice — 2026-05-19

The commit plan has been updated. Here is what changed for you:

**What was removed:** nothing

**What changed in your sequence:**
- Old Commit 33 `nginx-config` → now **Commit 39** (renumbered; content unchanged)
- Old Commit 34 `aws-ec2-deployment` → now **Commit 40** (renumbered; content unchanged)
- 6 new progression commits (33–38) were inserted before your work

**Your next commit is now: Commit 39 `nginx-config`** (after Commit 38 progression-ui is complete)
Specs: rename commit-specs/commit-39.md and commit-specs/commit-40.md — already renamed — content is unchanged.

## 📋 Replan Notice — 2026-05-20

The commit plan has been updated. Here is what changed for you:

**What was removed:** nothing — your work is entirely unchanged in scope.
**What was reordered:** 7 learning flow commits inserted before your deployment work.
- nginx-config moves from Commit 39 → **Commit 46** (spec: `commit-specs/commit-46.md` — content identical, only number changed)
- aws-ec2-deployment moves from Commit 40 → **Commit 47** (spec: `commit-specs/commit-47.md` — dependency updated to Commit 46)

**What changed in your sequence:** you now follow after 7 new learning flow commits complete.

**Your next commit is now: Commit 46 `nginx-config`** (after Commit 45 `rag-specialist-content` is complete)
