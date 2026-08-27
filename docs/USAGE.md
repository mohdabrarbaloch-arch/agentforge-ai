# Usage Guide

## 1. Create an account

`POST /api/auth/register` — email, name, password (8+ chars, at least one letter and one digit). You immediately receive a JWT. Or just use the sign-up form in the UI.

## 2. Create an agent

In the **Agents** page: name, description, system prompt, model, temperature, and a toolbelt (click to toggle). Recommended starter prompt:

```
You are a research assistant. Always use web_search to verify facts
before answering, and cite the sources you found.
```

Tools you can enable: `web_search`, `generate_image`, `generate_website`, `send_email`, `send_slack`, `create_notion_page`, `github_action`, `code_exec`, `get_time`, `list_integrations`.

## 3. Chat with your agent

**Chat** page → pick an agent → **+ New** → type away. Try:

- `search the web for today's AI news and summarize the top 3 stories`
- `generate an image of a mountain sunset for my travel blog`
- `what time is it in UTC?`

The agent will call tools mid-conversation; the reply shows which tools were used and any artifact URLs.

## 4. Queue a task (background)

**Tasks** page → **+ New task** → pick agent + prompt → **Queue task**. The card appears with status `queued`, then flips to `running` and finally `succeeded`/`failed` — live via WebSocket. Each card shows the `thread_id`, task id, result preview, and artifact links.

## 5. Schedule an automation

**Triggers** page → **+ New trigger**. Example: name `Morning news`, cron `0 9 * * *`, agent `Research Assistant`, prompt `Summarize the top tech news stories for today and save a brief.`, timezone `Asia/Karachi`. Every fire creates a task card. Pause/resume/delete anytime.

Common crons:
- `0 9 * * *` — daily 09:00
- `0 */6 * * *` — every 6 hours
- `0 8 * * 1` — Mondays 08:00

## 6. Connect integrations & API keys

**Integrations** page: connect Gmail/Slack/Notion/GitHub/Stripe (simulated actions until real OAuth is configured). Generate an API key (`agf_…`) to call the API from scripts:

```bash
curl -H "Authorization: Bearer agf_YOUR_KEY" http://localhost:8000/api/auth/me
```

## 7. Demo mode

Without `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`, agents use a built-in responder that still exercises the full pipeline (threads, tasks, tools list, artifact URLs) and tells you honestly when it's running in demo mode. Add keys to `.env` and restart for real LLM answers.
