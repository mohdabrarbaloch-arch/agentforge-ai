# Setup Guide

## Prerequisites

- Python 3.11+
- (Optional) Docker + Docker Compose
- (Optional) API keys: OpenAI (`OPENAI_API_KEY`) and/or Anthropic (`ANTHROPIC_API_KEY`), Tavily (`TAVILY_API_KEY`)

## Option A — local (recommended for development)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env — at minimum change SECRET_KEY; add API keys for full features

uvicorn app.main:app --reload    # http://localhost:8000
```

## Option B — Docker (production parity)

```bash
cp backend/.env.example .env     # root .env is read by docker-compose
docker compose up --build
```

- Frontend (nginx): http://localhost:8080
- Backend API: http://localhost:8000 · Swagger UI: http://localhost:8000/docs
- Postgres 16 + Redis 7 are provisioned automatically.

## Verification

```bash
curl http://localhost:8000/api/health
# {"status":"ok","app":"AgentForge AI","version":"1.0.0"}

cd backend && pytest     # 50 tests
```

## Configuration quick reference

| Env var | Default | Notes |
|---|---|---|
| `SECRET_KEY` | `change-me-in-production` | **Must change.** `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | `sqlite:///./agentforge.db` | Postgres: `postgresql+psycopg2://user:pass@host:5432/db` |
| `OPENAI_API_KEY` | empty | Enables GPT-4o tool-calling |
| `ANTHROPIC_API_KEY` | empty | Alternative provider |
| `TAVILY_API_KEY` | empty | Live web search |
| `SCHEDULER_ENABLED` | `true` | Cron automations |
| `RATE_LIMIT_ENABLED` | `true` | Set `false` only in tests |
| `CORS_ORIGINS` | `*` | Comma-separated for production |
