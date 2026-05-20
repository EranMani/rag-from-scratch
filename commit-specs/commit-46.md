# Commit 46 Spec — `nginx-config`
> **Project:** rag-from-scratch · **Assignee:** Adam · **Load only for the active commit.**
> **Note:** This was formerly Commit 30, renumbered to 33 (replan 2026-05-19), then to 39 (replan 2026-05-19), then to 46 (replan 2026-05-20 — 7 learning flow commits inserted before deployment).

---

### Commit 46 — `nginx-config`

**Commit message:** `feat: nginx reverse proxy with WebSocket support, HTTPS, and monitoring routes`

**Body:**
Adds nginx as a service in `docker-compose.prod.yml` and writes `nginx/nginx.conf`.

Required config (non-negotiable):
- HTTP → HTTPS redirect (301), except `/.well-known/acme-challenge/` for Certbot renewal
- SSL termination with Let's Encrypt certs at `/etc/letsencrypt/live/{domain}/`
- `proxy_read_timeout 86400` — **critical**: NiceGUI WebSocket silently disconnects
  at the default 60s timeout without this
- `proxy_buffering off` — required for NiceGUI SSE fallback and any streaming responses
- WebSocket upgrade headers: `Upgrade`, `Connection: upgrade`
- `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto` headers

Security:
- `location /metrics { deny all; return 403; }` — Prometheus scrape endpoint must
  not be publicly accessible
- Monitoring dashboards proxied at internal paths with HTTP basic auth:
  `/grafana/` → Grafana, `/kibana/` → Kibana, `/prometheus/` → Prometheus
- Security headers: `X-Frame-Options DENY`, `X-Content-Type-Options nosniff`,
  `Strict-Transport-Security max-age=31536000`

**Assignee:** Adam (`adam.stockagent@gmail.com`)

**Files touched:**
- `nginx/nginx.conf` (new)
- `docker-compose.prod.yml` (add nginx service with cert volumes)

**Depends on:** 32 (all application features complete)

**Testing — done when:**
- [ ] `nginx -t` (config test) passes inside the nginx container
- [ ] `curl -I http://domain` returns 301 redirect to https
- [ ] NiceGUI chat page remains connected for > 60 seconds without disconnect
- [ ] `GET /metrics` returns 403 from outside the Docker network
- [ ] WebSocket connection established (check browser DevTools Network tab)
