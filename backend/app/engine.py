"""Agent engine — the LLM orchestration layer.

Given an agent + a user message, the engine builds message history, asks the
LLM (OpenAI or Anthropic) with the agent's enabled tool schemas, executes any
tool calls, and loops until the model stops requesting tools (max 6 iterations).
Falls back to a deterministic demo responder when no API key is configured.
"""
from __future__ import annotations

import json
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Agent, Message, Thread
from app.tools import run_tool, tool_schemas

settings = get_settings()

MAX_TOOL_ITERATIONS = 6
_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="agent-engine")


def _demo_reply(agent: Agent, user_text: str, tool_names: list[str]) -> tuple[str, list[str], list[str]]:
    lowered = user_text.lower()
    artifacts: list[str] = []
    uses: list[str] = []

    if "search" in lowered or "news" in lowered or "research" in lowered:
        uses.append("web_search")
        reply = (
            f"Here's what I found for you — running a web search on '{user_text[:80]}'. "
            "The results are summarized above. In demo mode I couldn't reach a live LLM, "
            "but the search pipeline is wired up — set OPENAI_API_KEY and TAVILY_API_KEY "
            "to get full answers."
        )
    elif "image" in lowered or "logo" in lowered or "poster" in lowered or "design" in lowered:
        uses.append("generate_image")
        demo = f"https://static.teamily.ai/files/agentforge-demo-{agent.id[:8]}/image.png"
        artifacts.append(demo)
        reply = (
            f"Done — I generated an image based on: '{user_text[:100]}'. "
            "You'll find it attached as a permanent artifact URL. (Demo mode: no OPENAI_API_KEY, "
            "so this is a placeholder link — connect a key for real generations.)"
        )
    elif "website" in lowered or "landing" in lowered or "page" in lowered:
        uses.append("generate_website")
        reply = (
            f"Website request received: '{user_text[:100]}'. "
            "I've scaffolded a landing page for you. Demo mode — connect OPENAI_API_KEY "
            "for a live LLM to write real copy."
        )
    elif "email" in lowered:
        uses.append("send_email")
        reply = (
            "Got it — I can draft and send that email. Give me the recipient, subject and body "
            "and I'll queue it through the Gmail integration (connect it in Integrations first)."
        )
    elif "code" in lowered or "function" in lowered or "python" in lowered:
        uses.append("code_exec")
        reply = "I can help with code — paste what you'd like me to run or review and I'll take it from there."
    elif "time" in lowered or "date" in lowered:
        uses.append("get_time")
        reply = "I can check the current time and date for you — want the UTC time, or your local time?"
    else:
        reply = (
            f"I'm {agent.name}, ready to help. I can search the web, generate images and websites, "
            "send emails, post to Slack, create Notion pages, run GitHub actions, and execute code. "
            "This reply came from the demo responder (no OPENAI_API_KEY set) — add a key to .env "
            "for full LLM-powered answers."
        )
    return reply, artifacts, uses


def _build_messages(agent: Agent, thread: Thread, user_text: str, db: Session) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [{"role": "system", "content": agent.system_prompt}]
    for msg in db.query(Message).filter(Message.thread_id == thread.id).order_by(Message.created_at).all():
        role = "assistant" if msg.role in ("assistant", "tool") else "user"
        messages.append({"role": role, "content": msg.content})
    messages.append({"role": "user", "content": user_text})
    return messages[-20:]  # keep context window sane


def _run_openai(agent: Agent, messages: list[dict[str, str]], tool_names: list[str]) -> dict[str, Any]:
    import openai

    client = openai.OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=agent.model,
        messages=messages,  # type: ignore[arg-type]
        tools=tool_schemas(tool_names) or None,
        temperature=agent.temperature,
    )
    message = response.choices[0].message
    return {
        "content": message.content or "",
        "tool_calls": [
            {"id": tc.id, "name": tc.function.name, "arguments": tc.function.arguments}
            for tc in (message.tool_calls or [])
        ],
    }


def _run_anthropic(agent: Agent, messages: list[dict[str, str]], tool_names: list[str]) -> dict[str, Any]:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    system = messages[0]["content"] if messages and messages[0]["role"] == "system" else agent.system_prompt
    conv = [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "system"]
    conv = [
        {"role": "user" if m["role"] == "assistant" else m["role"], "content": m["content"]}
        for m in conv
    ]
    tools = [
        {
            "name": t["function"]["name"],
            "description": t["function"]["description"],
            "input_schema": t["function"]["parameters"],
        }
        for t in tool_schemas(tool_names)
    ]
    response = client.messages.create(
        model=agent.model,
        max_tokens=1024,
        system=system,
        messages=conv,  # type: ignore[arg-type]
        tools=tools or None,
        temperature=agent.temperature,
    )
    tool_calls = []
    content_parts = []
    for block in response.content:
        if block.type == "text":
            content_parts.append(block.text)
        elif block.type == "tool_use":
            tool_calls.append({"id": block.id, "name": block.name, "arguments": json.dumps(block.input)})
    return {"content": "\n".join(content_parts), "tool_calls": tool_calls}


def run_agent(
    agent: Agent,
    user_text: str,
    thread: Thread,
    db: Session,
    tools_override: list[str] | None = None,
) -> dict[str, Any]:
    """Execute one agent turn. Returns {reply, artifact_urls, tool_uses, iterations}."""
    tool_names = tools_override or (agent.enabled_tools or [])
    messages = _build_messages(agent, thread, user_text, db)
    artifact_urls: list[str] = []
    tool_uses: list[str] = []

    if not settings.openai_api_key and not settings.anthropic_api_key:
        reply, artifacts, uses = _demo_reply(agent, user_text, tool_names)
        return {"reply": reply, "artifact_urls": artifacts, "tool_uses": uses, "iterations": 0, "demo": True}

    iterations = 0
    try:
        while iterations < MAX_TOOL_ITERATIONS:
            iterations += 1
            if settings.anthropic_api_key and not settings.openai_api_key:
                step = _run_anthropic(agent, messages, tool_names)
            else:
                step = _run_openai(agent, messages, tool_names)

            messages.append({"role": "assistant", "content": step["content"] or ""})

            if not step["tool_calls"]:
                return {
                    "reply": step["content"],
                    "artifact_urls": artifact_urls,
                    "tool_uses": tool_uses,
                    "iterations": iterations,
                }

            for tc in step["tool_calls"]:
                tool_uses.append(tc["name"])
                try:
                    args = json.loads(tc["arguments"] or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = run_tool(tc["name"], agent.user_id, db, args)
                artifact_urls.extend(result.artifact_urls)
                messages.append(
                    {"role": "tool", "tool_call_id": tc["id"], "name": tc["name"], "content": result.text}
                )

        return {
            "reply": "Reached the tool-call limit for this turn. " + (step.get("content") or ""),
            "artifact_urls": artifact_urls,
            "tool_uses": tool_uses,
            "iterations": iterations,
            "truncated": True,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "reply": f"Agent run failed: {exc}",
            "artifact_urls": artifact_urls,
            "tool_uses": tool_uses,
            "iterations": iterations,
            "error": str(exc),
        }


def run_agent_async(
    agent: Agent,
    user_text: str,
    thread: Thread,
    db_factory: Any,
    tools_override: list[str] | None = None,
) -> Future[dict[str, Any]]:
    """Run an agent turn in a background thread. Returns the Future."""

    def _work() -> dict[str, Any]:
        from app.database import SessionLocal

        session: Session = SessionLocal()
        try:
            fresh_agent = session.query(Agent).filter(Agent.id == agent.id).first()
            fresh_thread = session.query(Thread).filter(Thread.id == thread.id).first()
            if fresh_agent is None or fresh_thread is None:
                return {"reply": "Agent or thread no longer exists.", "artifact_urls": [], "tool_uses": []}
            return run_agent(fresh_agent, user_text, fresh_thread, session, tools_override)
        finally:
            session.close()

    return _executor.submit(_work)
