"""Scheduled triggers — APScheduler cron jobs that enqueue agent tasks."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.models import Trigger

logger = logging.getLogger("agentforge.scheduler")

_scheduler: BackgroundScheduler | None = None


def _job_wrapper(trigger_id: str) -> None:
    from app.database import SessionLocal
    from app.models import Agent, Trigger
    from app.queue import _run_task, create_task

    db: Session = SessionLocal()
    try:
        trigger = db.query(Trigger).filter(Trigger.id == trigger_id).first()
        if trigger is None or not trigger.enabled:
            return
        agent = db.query(Agent).filter(Agent.id == trigger.agent_id).first() if trigger.agent_id else None
        if agent is None:
            logger.warning("Trigger %s has no valid agent; skipping", trigger_id)
            return
        task = create_task(db, trigger.user_id, agent.id, trigger.prompt, task_type="scheduled")
        trigger.last_run_at = datetime.now(timezone.utc)
        db.commit()
        _run_task(task.id, None)
        logger.info("Trigger %s fired → task %s", trigger_id, task.id)
    except Exception as exc:  # noqa: BLE001
        logger.error("Trigger %s failed: %s", trigger_id, exc)
    finally:
        db.close()


def schedule_trigger(db: Session, trigger: Trigger) -> None:
    if _scheduler is None:
        return
    job_id = f"trigger-{trigger.id}"
    try:
        _scheduler.add_job(
            _job_wrapper,
            CronTrigger.from_crontab(trigger.cron_expression, timezone=trigger.timezone),
            args=[trigger.id],
            id=job_id,
            replace_existing=True,
        )
        trigger.next_run_at = _scheduler.get_job(job_id).next_run_time
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.error("Could not schedule trigger %s: %s", trigger.id, exc)


def unschedule_trigger(trigger_id: str) -> None:
    if _scheduler is None:
        return
    job_id = f"trigger-{trigger_id}"
    try:
        if _scheduler.get_job(job_id):
            _scheduler.remove_job(job_id)
    except Exception:  # noqa: BLE001
        pass


def start_scheduler(db: Session) -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.start()
    for trigger in db.query(Trigger).filter(Trigger.enabled.is_(True)).all():
        schedule_trigger(db, trigger)


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
