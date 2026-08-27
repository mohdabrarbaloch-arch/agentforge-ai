"""1-on-1 chat: threads, messages, and agent turns."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, get_owned_agent
from app.engine import run_agent
from app.models import Message, Thread, User
from app.schemas import ChatRequest, ChatResponse, MessageOut, ThreadCreate, ThreadOut

router = APIRouter(prefix="/chat", tags=["chat"])


def _get_owned_thread(db: Session, thread_id: str, user: User) -> Thread:
    thread = db.query(Thread).filter(Thread.id == thread_id, Thread.user_id == user.id).first()
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    return thread


@router.post("/threads", response_model=ThreadOut, status_code=status.HTTP_201_CREATED)
def create_thread(payload: ThreadCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_owned_agent(db, payload.agent_id, current_user)
    thread = Thread(user_id=current_user.id, agent_id=payload.agent_id, title=payload.title or "New conversation")
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return ThreadOut.model_validate(thread)


@router.get("/threads", response_model=list[ThreadOut])
def list_threads(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    threads = db.query(Thread).filter(Thread.user_id == current_user.id).order_by(Thread.created_at.desc()).all()
    return [ThreadOut.model_validate(t) for t in threads]


@router.get("/threads/{thread_id}/messages", response_model=list[MessageOut])
def list_messages(thread_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _get_owned_thread(db, thread_id, current_user)
    messages = db.query(Message).filter(Message.thread_id == thread_id).order_by(Message.created_at).all()
    return [MessageOut.model_validate(m) for m in messages]


@router.post("/threads/{thread_id}/messages", response_model=ChatResponse)
def send_message(
    thread_id: str,
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    thread = _get_owned_thread(db, thread_id, current_user)
    agent = get_owned_agent(db, thread.agent_id, current_user)

    db.add(Message(thread_id=thread.id, role="user", content=payload.message))
    db.commit()

    result = run_agent(agent, payload.message, thread, db)

    db.add(Message(thread_id=thread.id, role="assistant", content=result["reply"]))
    if result.get("tool_uses"):
        for tool_name in result["tool_uses"]:
            db.add(Message(thread_id=thread.id, role="tool", content=f"Called tool: {tool_name}", tool_name=tool_name))
    if thread.title == "New conversation":
        thread.title = payload.message[:48]
    db.commit()

    return ChatResponse(
        thread_id=thread.id,
        reply=result["reply"],
        artifact_urls=result.get("artifact_urls", []),
        tool_uses=result.get("tool_uses", []),
    )


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_thread(thread_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    thread = _get_owned_thread(db, thread_id, current_user)
    db.delete(thread)
    db.commit()
    return None
