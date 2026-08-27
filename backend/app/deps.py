"""Shared FastAPI dependencies: current user via JWT or API key."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ApiKey, User
from app.security import decode_token, hash_api_key

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = credentials.credentials

    # API key auth: agf_...
    if token.startswith("agf_"):
        key_hash = hash_api_key(token)
        api_key = db.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()
        if api_key is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        api_key.last_used_at = datetime.now(timezone.utc)
        db.commit()
        user = db.query(User).filter(User.id == api_key.user_id).first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user

    # JWT auth
    user_id = decode_token(token)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_owned_agent(db: Session, agent_id: str, user: User) -> Agent:
    """Fetch an agent that belongs to the user; foreign agents resolve to 404."""
    from app.models import Agent

    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == user.id).first()
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent
