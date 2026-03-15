# Job Application OS — Backend API

AI-powered job search command center backend. Automates the entire job application lifecycle: discovery, scoring, content generation, submission, outreach, and analytics — all orchestrated through a FastAPI backend with Celery task workers, Redis caching, and Playwright browser automation. The system supports 285+ features across 31 modules, exposed through 17 API route groups.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.12 |
| Framework | FastAPI |
| ORM | SQLAlchemy (async) |
| Database | PostgreSQL (Supabase) |
| Migrations | Alembic |
| Task Queue | Celery + Redis |
| Auth | Supabase JWT verification |
| Encryption | AES-256-GCM + HKDF (BYOK) |
| Browser Automation | Playwright (Chromium) |
| Logging | Loguru (structured JSON) |
| Testing | pytest + pytest-asyncio |
| Linting | ruff + mypy (strict) |
| Monitoring | Sentry |
| Containerization | Docker + Docker Compose |
| Reverse Proxy | Caddy (auto-HTTPS) |

---

## Prerequisites

- **Python 3.12+**
- **Docker and Docker Compose** (recommended)
- **Supabase account** (for PostgreSQL + Auth)
- **Redis** (included in Docker Compose)

---

## Quick Start

```bash
# 1. Clone the repo
git clone <repo-url>
cd job-os-backend

# 2. Copy environment template and fill in values
cp .env.example .env
# Edit .env with your Supabase credentials, encryption key, etc.

# 3. Start all services
docker compose up --build -d

# 4. Apply database migrations
docker compose exec fastapi alembic upgrade head

# 5. Seed the database with sample data
docker compose exec fastapi python -m scripts.seed

# 6. Open Swagger UI
open http://localhost:8000/docs
```

---

## Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `SUPABASE_DB_URL` | Yes | PostgreSQL connection string (use port 6543 for PgBouncer) | `postgresql+asyncpg://user:pass@host:6543/dbname` |
| `SUPABASE_URL` | Yes | Supabase project URL | `https://xxx.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Supabase service role secret key | `eyJhbGci...` |
| `SUPABASE_JWT_SECRET` | Yes | JWT secret for token verification | `your-jwt-secret` |
| `REDIS_URL` | Yes | Redis connection string | `redis://localhost:6379/0` |
| `MASTER_ENCRYPTION_KEY` | Yes | 256-bit hex key for BYOK encryption | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `R2_ACCOUNT_ID` | No | Cloudflare R2 account ID | `your-account-id` |
| `R2_ACCESS_KEY_ID` | No | R2 API access key | `your-access-key` |
| `R2_SECRET_ACCESS_KEY` | No | R2 API secret key | `your-secret-key` |
| `R2_BUCKET_NAME` | No | R2 bucket name | `jobapp-files` |
| `R2_ENDPOINT_URL` | No | R2 S3-compatible endpoint | `https://<id>.r2.cloudflarestorage.com` |
| `SENTRY_DSN` | No | Sentry error tracking DSN | `https://key@sentry.io/project` |
| `ENVIRONMENT` | No | Runtime environment | `development` / `staging` / `production` |
| `CORS_ORIGINS` | No | Allowed CORS origins (comma-separated) | `http://localhost:3000` |
| `API_VERSION` | No | API version prefix | `v1` |
| `LOG_LEVEL` | No | Logging verbosity | `DEBUG` / `INFO` |
| `RATE_LIMIT_PER_MINUTE` | No | Per-user rate limit | `100` |

---

## Local Development (without Docker)

```bash
# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies (includes dev tools)
pip install -r requirements-dev.txt

# Apply database migrations
alembic upgrade head

# Seed the database
python -m scripts.seed

# Start the API server (with hot reload)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# In a separate terminal — start Celery worker
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4

# In another terminal — start Celery beat (scheduler)
celery -A app.tasks.celery_app beat --loglevel=info
```

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=app --cov-report=term-missing

# Linting
ruff check .

# Type checking
mypy .
```

Coverage threshold: 45% (Sprint 0), target 80% by V2.

---

## API Architecture

All endpoints are under `/api/v1/`. Interactive documentation available at `/docs` (Swagger) and `/redoc` (ReDoc).

### Route Groups (17)

| Group | Prefix | Endpoints | Description |
|-------|--------|-----------|-------------|
| Health | `/health` | 1 | Postgres + Redis health check |
| Auth | `/auth` | 5 | Signup, login, logout, refresh, me |
| Profiles | `/profiles` | 8 | Profile CRUD, clone, activate, completeness |
| Jobs | `/jobs` | 11 | List, search, manual add, score, discover |
| Content | `/content` | 4 | Resume, cover letter, answers generation |
| Applications | `/applications` | 6 | Track, submit, status management |
| Review | `/review` | 6 | Approve, reject, regenerate, bulk-approve |
| Outreach | `/outreach` | 6 | Contact + message management |
| Email | `/email` | 3 | Gmail integration settings + scanning |
| Interviews | `/interviews` | 5 | Interview CRUD + prep |
| Analytics | `/analytics` | 7 | Funnel, sources, rejections, AI cost, export |
| Market | `/market` | 3 | Salary data, trends, insights |
| AI | `/ai` | 7 | BYOK key management, model config, usage |
| Files | `/files` | 5 | R2 presigned upload/download, document CRUD |
| Copilot | `/copilot` | 4 | AI chat (SSE), conversations, actions |
| Notifications | `/notifications` | 4 | List, mark read, unread count |
| Admin | `/admin` | 7 | User management, system health, feature flags |

### Error Envelope

All errors follow a consistent format:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Job not found",
    "details": [{"field": "job_id", "message": "No job with this ID exists"}]
  }
}
```

### Pagination

Cursor-based pagination for list endpoints:

```json
{
  "data": [...],
  "next_cursor": "eyJpZCI6...",
  "has_more": true
}
```

---

## Project Structure

```
app/                          # Main application
├── api/
│   ├── deps.py               # Shared dependencies (auth, db)
│   └── v1/                   # 17 route files
│       ├── router.py          # Central router registration
│       ├── auth.py            # Authentication endpoints
│       ├── health.py          # Health check
│       ├── profiles.py        # Profile management
│       ├── jobs.py            # Job management
│       ├── content.py         # Content generation
│       ├── applications.py    # Application tracking
│       ├── review.py          # Review queue
│       ├── outreach.py        # Outreach contacts/messages
│       ├── email.py           # Email intelligence
│       ├── interviews.py      # Interview management
│       ├── analytics.py       # Analytics & reporting
│       ├── market.py          # Market intelligence
│       ├── ai.py              # AI provider management
│       ├── files.py           # File upload/download
│       ├── copilot.py         # AI copilot chat
│       ├── notifications.py   # Notification management
│       └── admin.py           # Admin endpoints
├── core/                     # Middleware, security, exceptions
│   ├── exceptions.py          # 14 error codes + envelope format
│   ├── security.py            # JWT verification + BYOK encryption
│   ├── rate_limiter.py        # Redis-based per-user rate limiting
│   ├── middleware.py          # Request logging (request_id, duration)
│   ├── circuit_breaker.py     # Redis-based circuit breaker
│   └── logging.py             # Loguru structured logging setup
├── db/                       # Database layer
│   ├── base.py                # SQLAlchemy Base + mixins (UUID, Timestamp, SoftDelete)
│   ├── session.py             # Async engine + session factory
│   └── redis.py               # Redis connection pool
├── models/                   # 20 SQLAlchemy ORM models
├── schemas/                  # 16 Pydantic schema files
├── services/                 # 17 service files (business logic)
├── tasks/                    # 10 Celery task files
│   ├── celery_app.py          # Celery configuration
│   ├── scheduled_tasks.py     # Beat schedule
│   ├── discovery_tasks.py     # Job board scraping
│   ├── scoring_tasks.py       # AI-powered scoring
│   ├── content_tasks.py       # Resume/cover letter generation
│   ├── application_tasks.py   # ATS auto-submission
│   ├── outreach_tasks.py      # Contact discovery + messaging
│   ├── email_tasks.py         # Gmail scanning
│   ├── analytics_tasks.py     # Report generation
│   └── market_tasks.py        # Market intelligence
├── config.py                 # Pydantic settings (reads .env)
├── main.py                   # FastAPI app factory
└── dependencies.py           # Additional DI helpers
tests/                        # Test suite
├── unit/                     # Unit tests (circuit breaker, encryption, errors, rate limiter)
├── integration/              # Integration tests (auth API, health API)
└── tasks/                    # Task tests
alembic/                      # Database migrations
scripts/                      # Utility scripts (seed, teardown, backup)
docs/                         # Technical documentation
```

---

## Deployment

**Architecture:** AWS EC2 + Docker Compose + Caddy (auto-HTTPS)

```
Internet → Caddy (443) → FastAPI (8000)
                        → Celery Worker
                        → Celery Beat
                        → Redis
                        → Playwright
```

| Environment | Instance | Specs | Cost |
|-------------|----------|-------|------|
| Production | t3.xlarge | 4 vCPU, 16GB RAM | ~$120/mo |
| Staging | t3.medium | 2 vCPU, 4GB RAM | ~$30/mo |

See [docs/Runbook.md](docs/Runbook.md) for full deployment instructions.

---

## Documentation

| Document | Description |
|----------|-------------|
| [Technical Documentation](docs/JobApplicationOS_Technical_Documentation_v1.0.md) | Full technical spec — architecture, database, security, observability |
| [Sprint Roadmap (Part 2)](docs/Master_Implementation_Plan_Part2.md) | Agentic sprint plan with task breakdowns |
| [Infrastructure Blueprints (Part 3)](docs/Master_Implementation_Plan_Part3.md) | MCP, agent rules, git protocol, env management |
| [UI/UX Blueprint](docs/UI_UX_Design_Blueprint.md) | Frontend design system and component specs |
| [Runbook](docs/Runbook.md) | Local setup, Docker usage, production deployment |
| [Backend Audit](Backend_Audit.md) | Audit report from latest restructure |
