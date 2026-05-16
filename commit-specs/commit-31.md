# Commit 31 Spec — `aws-ec2-deployment`
> **Project:** rag-from-scratch · **Assignee:** Adam · **Load only for the active commit.**

---

### Commit 31 — `aws-ec2-deployment`

**Commit message:** `feat: EC2 deployment scripts — systemd, SSL, swapfile, backup`

**Body:**
All scripts and config needed for a clean first deploy on a fresh EC2 instance.

`scripts/deploy.sh`:
- Install Docker + Docker Compose plugin (not v1)
- Clone repository to `/opt/rag-from-scratch`
- `.env.prod` validation guard: `grep JWT_SECRET .env.prod || (echo "FATAL: JWT_SECRET missing" && exit 1)`
- `docker compose -f docker-compose.prod.yml build`
- `docker compose -f docker-compose.prod.yml up -d`
- Ollama model pre-pull: `docker exec rag-ollama ollama pull gemma3:4b`
- Run Certbot initial cert acquisition

`systemd/rag-app.service`:
- `After=docker.service`, `Requires=docker.service`
- `ExecStart` runs `docker compose -f docker-compose.prod.yml up -d`
- `ExecStop` runs `docker compose -f docker-compose.prod.yml down`
- Ensures stack restarts after EC2 reboot

`scripts/setup-swap.sh`:
- Creates 4 GB swapfile at `/swapfile`
- Cheap insurance against OOM kills during Ollama model loading spikes

`scripts/backup.sh`:
- Tarballs `data/app_users.db` (SQLite) and `chroma_data` Docker volume to S3
- Intended to run via daily cron: `0 3 * * * /opt/rag-from-scratch/scripts/backup.sh`
- S3 bucket and IAM role documented in script header

`scripts/health-check.sh`:
- Hits `https://{domain}/api/health`
- Returns 0 on success, 1 on failure

Target EC2 instance: **t3.xlarge** (4 vCPU, 16 GB RAM) with 32 GB gp3 EBS volume.
Rationale: Ollama (gemma3:4b) needs ~3.5 GB RAM, ELK stack needs ~2 GB, app + ChromaDB
+ Redis need ~1 GB. t3.large (8 GB) is insufficient with monitoring running.

**Assignee:** Adam (`adam.stockagent@gmail.com`)

**Files touched:**
- `scripts/deploy.sh` (new)
- `scripts/health-check.sh` (new)
- `scripts/backup.sh` (new)
- `scripts/setup-swap.sh` (new)
- `systemd/rag-app.service` (new)

**Depends on:** 30

**Testing — done when:**
- [ ] `scripts/deploy.sh` runs on a fresh Ubuntu EC2 instance without errors
- [ ] `systemctl status rag-app` shows active after reboot
- [ ] `scripts/health-check.sh` returns 0 on a running stack
- [ ] Ollama responds with `gemma3:4b` after deploy (not on-demand pull)
- [ ] `.env.prod` missing → deploy.sh exits with FATAL message, not silently continues
