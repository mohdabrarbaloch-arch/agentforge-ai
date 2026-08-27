# AgentForge — Architecture

## 1. System diagram

```
Browser (dark SPA)
   │  REST + WebSocket
   ▼
FastAPI app
   ├── /api/auth        JWT + bcrypt, rate-limited
   ├── /api/agents      CRUD + tool catalog
   ├── /api/chat        threads + messages + agent turns
   ├── /api/tasks       queue + task cards
   ├── /api/triggers    cron automations + WS
   └── /api/integrations  services + API keys + webhooks
   │
   ├── Agent Engine     LLM loop (OpenAI/Anthropic) + tool calling (max 6 iterations)
   ├── Tool Registry    plugin-style tools, each returning text + artifact URLs
   ├── Task Queue       in-process thread pool (Celery-ready)
   └── APScheduler      cron jobs → Task rows + agent runs
   │
   ▼
SQLite (dev) / PostgreSQL 16 (docker) + Redis (optional)
```

Full docs in the repo.
