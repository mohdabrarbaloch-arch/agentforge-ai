# API Reference

Base URL: `http://localhost:8000/api` · Interactive docs at `/docs`.

Auth: `Authorization: Bearer <JWT or agf_ API key>` on all protected routes.

## Auth

| Method | Path | Body | Description |
|---|---|---|---|
| POST | `/auth/register` | `{email, password, name}` | Create account → `{access_token, user}` |
| POST | `/auth/login` | `{email, password}` | Log in → `{access_token, user}` |
| GET | `/auth/me` | — | Current user |

Errors: `401` bad credentials · `409` duplicate email · `422` validation · `429` rate limited.

## Agents

| Method | Path | Description |
|---|---|---|
| GET | `/agents/tools` | Tool catalog with descriptions + JSON schemas |
| POST | `/agents` | Create agent `{name, description?, system_prompt, model?, temperature?, enabled_tools?}` |
| GET | `/agents` | List my agents |
| GET | `/agents/{id}` | Get one (404 if not yours) |
| PATCH | `/agents/{id}` | Partial update (any field) |
| DELETE | `/agents/{id}` | Delete + cascade |

## Chat

| Method | Path | Description |
|---|---|---|
| POST | `/chat/threads` | `{agent_id, title?}` → thread |
| GET | `/chat/threads` | My threads |
| GET | `/chat/threads/{id}/messages` | Full message history |
| POST | `/chat/threads/{id}/messages` | `{message}` → `{thread_id, reply, artifact_urls, tool_uses}` |
| DELETE | `/chat/threads/{id}` | Delete thread |

## Tasks

| Method | Path | Description |
|---|---|---|
| POST | `/tasks` | `{agent_id, prompt, input_data?}` → 202 + task card |
| GET | `/tasks` | My 100 most recent tasks |
| GET | `/tasks/{id}` | Task status, result, error, artifact_urls, thread_id |

Status flow: `queued → running → succeeded | failed`.

## Triggers

| Method | Path | Description |
|---|---|---|
| POST | `/triggers` | `{name, cron_expression, prompt, agent_id?, timezone?}` |
| GET | `/triggers` | My automations |
| PATCH | `/triggers/{id}` | `{enabled}` — pause/resume |
| DELETE | `/triggers/{id}` | Delete |
| WS | `/triggers/ws` | WebSocket — live `{type:"task_status", task_id, status}` pushes |

Cron format: 5 fields `min hour dom month dow` (validated).

## Integrations

| Method | Path | Description |
|---|---|---|
| GET | `/integrations` | Connected services |
| POST | `/integrations/connect` | `{service, config?}` — gmail/slack/notion/github/stripe |
| DELETE | `/integrations/{id}` | Disconnect |
| POST | `/integrations/api-keys` | `{name}` → key shown once (`agf_…`) |
| GET | `/integrations/api-keys` | List keys |
| DELETE | `/integrations/api-keys/{id}` | Revoke |
| POST | `/integrations/webhook/{service}` | Receive webhook payloads |

## System

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/dashboard/me` | `{agent_count, task_count, thread_count, trigger_count, recent_tasks}` |
