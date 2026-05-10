# Commit 21 Spec — `production-compose`
> **Project:** rag-from-scratch · **Assignee:** Adam · **Load only for the active commit.**

---

### Commit 21 — `production-compose`

**Commit message:** `chore: production docker-compose with monitoring, hardened config, log rotation`

**Body:**
Creates `docker-compose.prod.yml` as a standalone file (not a compose override).
Key differences from dev compose:

- `./src:/app/src` bind mount **removed** — prod runs the baked image
- All internal service ports (`chroma`, `redis`, `ollama`, `elasticsearch`) use
  `expose:` only — not mapped to host
- `restart: always` on all services (survives EC2 reboots)
- Logging driver on every service: `json-file` with `max-size: 10m`, `max-file: 5`
- Memory limits: `ollama` capped at `5G` (t3.xlarge has 16 GB), `elasticsearch` JVM
  heap reduced to `-Xms256m -Xmx512m`
- Grafana: `GF_SECURITY_ADMIN_PASSWORD` read from env, not hardcoded
- Elasticsearch: `xpack.security.enabled=false` flagged with a TODO comment for the
  monitoring hardening commit — Team Lead decision to leave as-is for portfolio demo
- Monitoring services (Prometheus, Grafana, ELK) **remain in prod compose** — portfolio
  decision: the system should show it can evaluate itself in production

Also:
- `docker-compose.yml` (dev): adds `profiles: [monitoring]` to ELK + Prometheus +
  Grafana services so local dev can run `docker compose up` without the monitoring stack
  and opt in with `--profile monitoring`
- `.env.prod.example` created — all env vars required in production with no defaults
  for secrets (JWT_SECRET, OPENAI_API_KEY, GRAFANA_ADMIN_PASSWORD documented as required)

**Assignee:** Adam (`adam.stockagent@gmail.com`)

**Files touched:**
- `docker-compose.prod.yml` (new)
- `.env.prod.example` (new)
- `docker-compose.yml` (add profiles: [monitoring] to monitoring services)

**Depends on:** 17 (all application features complete before production config is written)

**Testing — done when:**
- [ ] `docker compose -f docker-compose.prod.yml config` validates without errors
- [ ] No `./src:/app/src` bind mount present in prod compose
- [ ] All monitoring service ports are internal-only (`expose:`, not `ports:`)
- [ ] `.env.prod.example` contains every env var referenced in config.py with no secret defaults
- [ ] Dev compose `docker compose up` starts without ELK/Prometheus (monitoring profile opt-in)
