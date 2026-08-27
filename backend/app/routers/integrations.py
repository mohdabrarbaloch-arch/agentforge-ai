"""Third-party integrations: connect stubs, status, webhooks, API keys."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import ApiKey, Integration, User
from app.schemas import ApiKeyCreate, ApiKeyCreated, ApiKeyOut, IntegrationConnect, IntegrationOut
from app.security import generate_api_key

router = APIRouter(prefix="/integrations", tags=["integrations"])

SERVICES = {"gmail", "slack", "notion", "github", "stripe"}


def _get_owned_integration(db: Session, integration_id: str, user: User) -> Integration:
    integration = db.query(Integration).filter(Integration.id == integration_id, Integration.user_id == user.id).first()
    if integration is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")
    return integration


@router.get("", response_model=list[IntegrationOut])
def list_integrations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Integration).filter(Integration.user_id == current_user.id).order_by(Integration.created_at).all()
    return [IntegrationOut.model_validate(r) for r in rows]


@router.post("/connect", response_model=IntegrationOut, status_code=status.HTTP_201_CREATED)
def connect_integration(
    payload: IntegrationConnect,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = payload.service.lower()
    if service not in SERVICES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Unsupported service '{service}'")
    existing = (
        db.query(Integration)
        .filter(Integration.user_id == current_user.id, Integration.service == service)
        .first()
    )
    if existing:
        existing.status = "connected"
        if payload.config:
            existing.config = payload.config
        db.commit()
        db.refresh(existing)
        return IntegrationOut.model_validate(existing)
    row = Integration(user_id=current_user.id, service=service, status="connected", config=payload.config)
    db.add(row)
    db.commit()
    db.refresh(row)
    return IntegrationOut.model_validate(row)


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_integration(
    integration_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = _get_owned_integration(db, integration_id, current_user)
    row.status = "disconnected"
    db.commit()
    return None


@router.post("/api-keys", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
def create_api_key(payload: ApiKeyCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    raw, prefix, key_hash = generate_api_key()
    api_key = ApiKey(user_id=current_user.id, name=payload.name.strip(), prefix=prefix, key_hash=key_hash)
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    out = ApiKeyCreated.model_validate(api_key)
    out.key = raw
    return out


@router.get("/api-keys", response_model=list[ApiKeyOut])
def list_api_keys(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    keys = db.query(ApiKey).filter(ApiKey.user_id == current_user.id).order_by(ApiKey.created_at.desc()).all()
    return [ApiKeyOut.model_validate(k) for k in keys]


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(key_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    key = db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.user_id == current_user.id).first()
    if key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    db.delete(key)
    db.commit()
    return None


@router.post("/webhook/{service}", status_code=status.HTTP_202_ACCEPTED)
async def receive_webhook(service: str, request: Request):
    """Accept inbound webhooks from connected services (fire-and-forget)."""
    if service.lower() not in SERVICES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Unsupported service '{service}'")
    body = await request.json()
    return {"received": True, "service": service, "event": body.get("type", "unknown")}
