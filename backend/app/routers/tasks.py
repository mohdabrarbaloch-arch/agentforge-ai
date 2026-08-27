"""Task cards: create agent tasks, list them, view status & artifact URLs."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, get_owned_agent
from app.models import Task, User
from app.queue import create_task, execute_task_in_background
from app.schemas import TaskCreate, TaskOut

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _get_owned_task(db: Session, task_id: str, user: User) -> Task:
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.post("", response_model=TaskOut, status_code=status.HTTP_202_ACCEPTED)
def create_run(
    payload: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_agent(db, payload.agent_id, current_user)
    task = create_task(db, current_user.id, payload.agent_id, payload.prompt, input_data=payload.input_data)
    execute_task_in_background(task.id, None)
    db.refresh(task)
    return TaskOut.model_validate(task)


@router.get("", response_model=list[TaskOut])
def list_tasks(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tasks = (
        db.query(Task)
        .filter(Task.user_id == current_user.id)
        .order_by(Task.created_at.desc())
        .limit(100)
        .all()
    )
    return [TaskOut.model_validate(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return TaskOut.model_validate(_get_owned_task(db, task_id, current_user))
