"""Main FastAPI application for AgentForge."""
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal, get_db, init_db
from app.deps import get_current_user
from app.models import Agent, Task, Thread, Trigger
from app.queue import subscribe
from app.routers import agents, auth, chat, integrations, tasks, triggers
from app.scheduler import shutdown_scheduler, start_scheduler
from app.schemas import DashboardStats, TaskOut
from app.ws import ws_status_listener

settings = get_settings()
limiter = Limiter(key_func=get_remote_address)
_WEB_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        if settings.scheduler_enabled:
            start_scheduler(db)
    finally:
        db.close()
    subscribe(ws_status_listener)
    yield
    shutdown_scheduler()


app = FastAPI(
    title="AgentForge AI",
    description="Build, chat with, and automate AI agents — a production-ready AI agent platform.",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": "Too many requests — slow down a little."})


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(agents.router, prefix=settings.api_prefix)
app.include_router(chat.router, prefix=settings.api_prefix)
app.include_router(tasks.router, prefix=settings.api_prefix)
app.include_router(triggers.router, prefix=settings.api_prefix)
app.include_router(integrations.router, prefix=settings.api_prefix)


@app.get("/api/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "version": "1.0.0"}


@app.get("/api/dashboard/me", tags=["system"])
def dashboard_me(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardStats:
    agent_count = db.query(Agent).filter(Agent.user_id == current_user.id).count()
    task_count = db.query(Task).filter(Task.user_id == current_user.id).count()
    thread_count = db.query(Thread).filter(Thread.user_id == current_user.id).count()
    trigger_count = db.query(Trigger).filter(Trigger.user_id == current_user.id).count()
    recent = (
        db.query(Task)
        .filter(Task.user_id == current_user.id)
        .order_by(Task.created_at.desc())
        .limit(5)
        .all()
    )
    return DashboardStats(
        agent_count=agent_count,
        task_count=task_count,
        thread_count=thread_count,
        trigger_count=trigger_count,
        recent_tasks=[TaskOut.model_validate(t) for t in recent],
    )


_static_dir = os.path.join(_WEB_ROOT, "static")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(os.path.join(_WEB_ROOT, "index.html"))


@app.get("/{path:path}")
def spa_fallback(path: str) -> FileResponse:
    """Serve the SPA for client-side routes; 404 for missing assets."""
    candidate = os.path.join(_WEB_ROOT, path)
    if path and os.path.isfile(candidate):
        return FileResponse(candidate)
    return FileResponse(os.path.join(_WEB_ROOT, "index.html"))
