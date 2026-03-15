# Job Application OS — Local & Production Runbook

**Date:** March 15, 2026
**Backend:** Python FastAPI

---

## 1. Local Environment Configuration

Create a `.env` file at the repo root by copying `.env.example`:

```bash
cp .env.example .env
```

Then fill in the values below.

### REQUIRED — App will not start without these

```bash
# ═══ Database (Supabase PostgreSQL) ═══
SUPABASE_DB_URL=postgresql+asyncpg://<user>:<password>@<host>:6543/<dbname>
#   ↑ Get from: Supabase Dashboard → Settings → Database → Connection String
#   ↑ IMPORTANT: Use port 6543 (PgBouncer), NOT 5432 (direct)
#   ↑ Replace "postgresql://" with "postgresql+asyncpg://" (SQLAlchemy async driver)

SUPABASE_URL=https://<your-project-ref>.supabase.co
#   ↑ Get from: Supabase Dashboard → Settings → API → URL

SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...
#   ↑ Get from: Supabase Dashboard → Settings → API → service_role (secret)
#   ↑ WARNING: This is a SECRET key with full database access. Never commit it.

SUPABASE_JWT_SECRET=<your-jwt-secret>
#   ↑ Get from: Supabase Dashboard → Settings → API → JWT Secret
#   ↑ The backend uses this to verify JWTs issued by Supabase Auth

# ═══ Redis ═══
REDIS_URL=redis://localhost:6379/0
#   ↑ If running via Docker Compose, use: redis://redis:6379/0

# ═══ Encryption ═══
MASTER_ENCRYPTION_KEY=<64-character-hex-string>
#   ↑ Generate with: python -c "import secrets; print(secrets.token_hex(32))"
#   ↑ This encrypts all user BYOK API keys (AES-256-GCM). Store it securely.
#   ↑ If you lose this key, all stored API keys become unrecoverable.
```

### OPTIONAL — App will run without these but features will be limited

```bash
# ═══ File Storage (Cloudflare R2) ═══
R2_ACCOUNT_ID=                          # Cloudflare Dashboard → R2 → Account ID
R2_ACCESS_KEY_ID=                       # Cloudflare Dashboard → R2 → API Tokens
R2_SECRET_ACCESS_KEY=                   # Cloudflare Dashboard → R2 → API Tokens
R2_BUCKET_NAME=jobapp-files
R2_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com

# ═══ Monitoring ═══
SENTRY_DSN=                             # Sentry Dashboard → Settings → Client Keys
#   ↑ Leave empty in local dev — errors will log to console instead

# ═══ Application ═══
ENVIRONMENT=development                 # development | staging | production
CORS_ORIGINS=http://localhost:3000      # Your frontend URL (comma-separated for multiple)
API_VERSION=v1
LOG_LEVEL=DEBUG                         # DEBUG in dev, INFO in production
RATE_LIMIT_PER_MINUTE=100               # Per-user rate limit
```

---

## 2. Local Execution — Step by Step

### Option A: Docker Compose (Recommended — runs everything)

```bash
# 1. Build and start all services
docker compose up --build -d

# 2. Verify services are running
docker compose ps
#   You should see: fastapi, redis, celery-worker, celery-beat
#   (caddy and playwright need config files — skip for local dev)

# 3. Check FastAPI health
curl http://localhost:8000/api/v1/health

# 4. Open Swagger docs
open http://localhost:8000/docs

# 5. Apply database migrations
docker compose exec fastapi alembic upgrade head

# 6. Seed the dev database (2 users, 100 jobs, mock data)
docker compose exec fastapi python -m scripts.seed

# 7. View logs
docker compose logs -f fastapi

# 8. Stop everything
docker compose down
```

### Option B: Local Python (without Docker)

```bash
# Prerequisites: Python 3.12+, PostgreSQL (or Supabase), Redis running locally

# 1. Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows

# 2. Install dependencies
pip install -r requirements-dev.txt

# 3. Apply database migrations
alembic upgrade head

# 4. Seed the database
python -m scripts.seed

# 5. Start the API server (with hot reload)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 6. In a separate terminal — start Celery worker
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4

# 7. In another terminal — start Celery beat (scheduler)
celery -A app.tasks.celery_app beat --loglevel=info

# 8. Run tests
pytest tests/ -v --tb=short

# 9. Run tests with coverage
pytest tests/ --cov=app --cov-report=term-missing

# 10. Run linters
ruff check .
mypy .
```

### Verification Checklist

- [ ] `curl http://localhost:8000/api/v1/health` → returns `{"status": "healthy", ...}`
- [ ] `curl http://localhost:8000/docs` → Swagger UI loads with all 17 route groups
- [ ] `curl http://localhost:8000/redoc` → ReDoc loads
- [ ] `pytest tests/ -v` → 30+ tests pass (unit + integration)
- [ ] Seed script completes: "2 users, 3 profiles, 20 skills, 100 jobs"

---

## 3. Deployment Strategy

### Architecture Decision: AWS EC2 + Docker Compose (per Technical Documentation Section 7)

This is NOT a serverless app. It has long-running Celery workers, Redis state,
WebSocket-like real-time needs, and Playwright browser automation. Serverless
platforms (Vercel, Lambda) are wrong for this workload.

### Recommended Topology

```
Internet → Caddy (auto-HTTPS) → FastAPI (port 8000)
                                → Celery Worker (background jobs)
                                → Celery Beat (scheduled tasks)
                                → Redis (broker + cache)
                                → Playwright (browser automation)

Frontend (Vercel) → API calls → Caddy → FastAPI

Supabase (managed PostgreSQL + Auth + Realtime)
Cloudflare R2 (file storage via presigned URLs)
```

### EC2 Instance Sizing

| Environment | Instance   | Specs              | Cost       |
|-------------|------------|--------------------|------------|
| Production  | t3.xlarge  | 4 vCPU, 16GB RAM   | ~$120/month |
| Staging     | t3.medium  | 2 vCPU, 4GB RAM    | ~$30/month  |

### Deployment Steps (Production)

```bash
# 1. SSH into EC2
ssh -i key.pem ubuntu@<ec2-ip>

# 2. Pull latest images from ECR (or git pull + docker compose build)
docker compose pull

# 3. Apply migrations
docker compose exec fastapi alembic upgrade head

# 4. Rolling restart (zero-downtime)
docker compose up -d --no-deps fastapi
docker compose up -d --no-deps celery-worker
docker compose up -d --no-deps celery-beat

# 5. Verify
curl https://api.yourdomain.com/api/v1/health
```

### Environment Variables in Production

Set ALL variables from `.env.example` with PRODUCTION values:

- `ENVIRONMENT=production`
- `CORS_ORIGINS=https://yourdomain.com` (exact frontend domain, no wildcards)
- `LOG_LEVEL=INFO`
- `SENTRY_DSN=<your-production-DSN>`
- `SUPABASE_DB_URL=<production Supabase connection string>`
- `REDIS_URL=redis://redis:6379/0` (Docker internal network)

### CI/CD (GitHub Actions)

Trigger: Push to main → Build Docker image → Push to ECR → SSH deploy to EC2

Workflow files: defined in infra repo (per Technical Documentation Section 7.3)

### DNS

- `api.yourdomain.com` → A record → EC2 public IP
- Caddy handles HTTPS automatically via Let's Encrypt

### Infrastructure Files

| File | Location | Purpose |
|------|----------|---------|
| `Caddyfile` | repo root | Caddy reverse proxy config |
| `Dockerfile.playwright` | repo root | Playwright container build |
| GitHub Actions workflows | infra repo | CI/CD pipeline |
| Terraform configs | infra repo | AWS infrastructure as code |

Per the 3-repo strategy (Technical Documentation Section 7.7: frontend, backend, infra),
CI/CD workflows and Terraform configs live in the separate `infra` repository.
