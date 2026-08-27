"""Task queue — persisted task lifecycle: queued → running → succeeded | failed."""
from __future__ import annotations

import contextlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import Task

_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="task-worker")
_status_listeners: list[Any] = []  # websocket connection managers hook in here


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_task(
    db: Session,
    user_id: str,
    agent_id: str | None,
    prompt: str,
    task_type: str = "run",
    thread_id: str | None = None,
    input_data: dict | None = None,
) -> Task:
    task = Task(
        user_id=user_id,
        agent_id=agent_id,
        thread_id=thread_id,
        task_type=task_type,
        status="queued",
        prompt=prompt,
        input_data=input_data,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_status(
    db: Session,
    task_id: str,
    status: str,
    error: str | None = None,
    result: str | None = None,
    artifact_urls: list[str] | None = None,
) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise ValueError(f"Task {task_id} not found")
    task.status = status
    if status == "running" and task.started_at is None:
        task.started_at = _now()
    if status in ("succeeded", "failed", "cancelled"):
        task.finished_at = _now()
    if error is not None:
        task.error = error
    if result is not None:
        task.result = result
    if artifact_urls is not None:
        task.artifact_urls = artifact_urls
    db.commit()
    db.refresh(task)
    for listener in _status_listeners:
        with contextlib.suppress(Exception):
            listener(task.id, status)
    return task


def subscribe(listener: Any) -> None:
    """Register a callable (task_id, status) -> None for live updates."""
    _status_listeners.append(listener)


def execute_task_in_background(task_id: str, db_factory: Any) -> None:
    _pool.submit(_run_task, task_id, db_factory)


def _run_task(task_id: str, db_factory: Any) -> None:
    from app.database import SessionLocal
    from app.engine import run_agent
    from app.models import Agent, Thread

    db: Session = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task is None:
            return
        update_status(db, task_id, "running")

        agent = db.query(Agent).filter(Agent.id == task.agent_id).first() if task.agent_id else None
        thread = None
        if task.thread_id:
            thread = db.query(Thread).filter(Thread.id == task.thread_id).first()

        if agent is None:
            update_status(db, task_id, "failed", error="Agent not found")
            return

        if thread is None:
            thread = Thread(user_id=task.user_id, agent_id=agent.id, title=task.prompt[:60])
            db.add(thread)
            db.commit()
            db.refresh(thread)
            task.thread_id = thread.id
            db.commit()

        result = run_agent(agent, task.prompt, thread, db)
        if result.get("error"):
            update_status(
                db, task_id, "failed",
                error=result["error"],
                result=result.get("reply"),
                artifact_urls=result.get("artifact_urls", []),
            )
            return

        update_status(
            db, task_id, "succeeded",
            result=result["reply"],
            artifact_urls=result.get("artifact_urls", []),
        )
    except Exception as exc:  # noqa: BLE001
        with contextlib.suppress(Exception):
            update_status(db, task_id, "failed", error=str(exc))
    finally:
        db.close()
