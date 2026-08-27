# ⚡ AgentForge AI

**Build agents. Chat with them. Automate your busywork.**

AgentForge is a production-ready AI agent platform — think of it as your own little teamily.ai. Create AI agents with a personality and a toolbelt, chat with them one-on-one, hand them tasks (research, emails, images, websites, code), and put them on a cron schedule so they work while you sleep. Every run becomes a task card with a thread id, a status, and permanent artifact URLs.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-blue)
![Tests](https://img.shields.io/badge/tests-50%20passing-brightgreen)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat&logo=docker&logoColor=white)

---

## ✨ What it does

| Capability | How it works |
|---|---|
| 🤖 **Create agents** | Name, system prompt, model (GPT-4o / Claude), temperature, per-agent toolbelt |
| 💬 **Chat 1-on-1** | Threaded conversations; the agent calls its tools mid-conversation |
| 🧰 **Tool registry** | web_search, generate_image, generate_website, send_email, send_slack, create_notion_page, github_action, code_exec (sandboxed), get_time, list_integrations |
| 📋 **Task cards** | Background runs with status queued → running → succeeded/failed, thread_id + artifact URLs |
| ⏰ **Scheduled automations** | Cron expressions + timezone; APScheduler fires the agent and logs a task |
| 🔌 **Integrations** | Gmail, Slack, Notion, GitHub, Stripe; API keys for programmatic access |
| 🔐 **Auth** | JWT (24h) + bcrypt (12 rounds) + rate-limited login/register + per-user isolation |
| ⚡ **Live updates** | WebSocket pushes task status to the browser in real time |

## 🖼️ Screenshots

| Dashboard | Chat |
|---|---|
| ![Dashboard](screenshots/dashboard.jpg) | ![Chat](screenshots/chat.jpg) |

| Agents | Tasks |
|---|---|
| ![Agents](screenshots/agents.jpg) | ![Tasks](screenshots/tasks.jpg) |

| Automations | Integrations |
|---|---|
| ![Triggers](screenshots/triggers.jpg) | ![Integrations](screenshots/integrations.jpg) |

## 🚀 Quick start (local, zero config)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open http://localhost:8000 — register and start chatting. **No API keys? No problem**: a built-in demo responder keeps the whole platform functional.

## 🐳 Docker (PostgreSQL + Redis + nginx)

```bash
cp backend/.env.example .env
docker compose up --build
```

- Frontend (nginx): http://localhost:8080
- Backend API: http://localhost:8000 · Swagger at `/docs`

## 🧪 Tests & lint

```bash
cd backend
pytest
ruff check app tests
ruff format --check app tests
```

## 📚 Docs

- [ARCHITECTURE.md](ARCHITECTURE.md) · [Setup](docs/SETUP.md) · [Usage](docs/USAGE.md) · [API reference](docs/API.md)

## 📄 License

[MIT](LICENSE) © mohdabrarbaloch-arch
