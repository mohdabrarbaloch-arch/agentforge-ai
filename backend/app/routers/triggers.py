"""Scheduled automations (cron triggers) + WebSocket live status."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Trigger, User
from app.scheduler import schedule_trigger, unschedule_trigger
from app.schemas import TriggerCreate, TriggerOut, TriggerToggle
from app.ws import manager

router = APIRouter(prefix="/triggers", tags=["triggers"])


def _get_owned_trigger(db: Session, trigger_id: str, user: User) -> Trigger:
    trigger = db.query(Trigger).filter(Trigger.id == trigger_id, Trigger.user_id == user.id).first()
    if trigger is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found")
    return trigger


@router.post("", response_model=TriggerOut, status_code=status.HTTP_201_CREATED)
def create_trigger(
    payload: TriggerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.deps import get_owned_agent

    if payload.agent_id:
        get_owned_agent(db, payload.agent_id, current_user)
    trigger = Trigger(
        user_id=current_user.id,
        agent_id=payload.agent_id,
        name=payload.name.strip(),
        cron_expression=payload.cron_expression,
        prompt=payload.prompt,
        timezone=payload.timezone,
    )
    db.add(trigger)
    db.commit()
    db.refresh(trigger)
    schedule_trigger(db, trigger)
    return TriggerOut.model_validate(trigger)


@router.get("", response_model=list[TriggerOut])
def list_triggers(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    triggers = db.query(Trigger).filter(Trigger.user_id == current_user.id).order_by(Trigger.created_at.desc()).all()
    return [TriggerOut.model_validate(t) for t in triggers]


@router.patch("/{trigger_id}", response_model=TriggerOut)
def toggle_trigger(
    trigger_id: str,
    payload: TriggerToggle,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trigger = _get_owned_trigger(db, trigger_id, current_user)
    trigger.enabled = payload.enabled
    db.commit()
    if payload.enabled:
        schedule_trigger(db, trigger)
    else:
        unschedule_trigger(trigger.id)
    db.refresh(trigger)
    return TriggerOut.model_validate(trigger)


@router.delete("/{trigger_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trigger(trigger_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    trigger = _get_owned_trigger(db, trigger_id, current_user)
    unschedule_trigger(trigger.id)
    db.delete(trigger)
    db.commit()
    return None


@router.websocket("/ws")
async def websocket_status(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
