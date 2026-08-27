"""Agent CRUD + tool catalog."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, get_owned_agent
from app.models import Agent, User
from app.schemas import AgentCreate, AgentOut, AgentUpdate, ToolInfo
from app.tools import TOOL_REGISTRY, get_tool_names

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/tools", response_model=list[ToolInfo])
def list_tools():
    return [
        ToolInfo(name=name, description=spec["description"], parameters=spec["parameters"])
        for name, spec in sorted(TOOL_REGISTRY.items())
    ]


@router.post("", response_model=AgentOut, status_code=status.HTTP_201_CREATED)
def create_agent(
    payload: AgentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    valid_tools = set(get_tool_names())
    unknown = set(payload.enabled_tools) - valid_tools
    if unknown:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Unknown tools: {sorted(unknown)}")
    agent = Agent(user_id=current_user.id, **payload.model_dump())
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return AgentOut.model_validate(agent)


@router.get("", response_model=list[AgentOut])
def list_agents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    agents = db.query(Agent).filter(Agent.user_id == current_user.id).order_by(Agent.created_at.desc()).all()
    return [AgentOut.model_validate(a) for a in agents]


@router.get("/{agent_id}", response_model=AgentOut)
def get_agent(agent_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AgentOut.model_validate(get_owned_agent(db, agent_id, current_user))


@router.patch("/{agent_id}", response_model=AgentOut)
def update_agent(
    agent_id: str,
    payload: AgentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = get_owned_agent(db, agent_id, current_user)
    updates = payload.model_dump(exclude_unset=True)
    if "enabled_tools" in updates:
        valid_tools = set(get_tool_names())
        unknown = set(updates["enabled_tools"]) - valid_tools
        if unknown:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Unknown tools: {sorted(unknown)}")
    for key, value in updates.items():
        setattr(agent, key, value)
    db.commit()
    db.refresh(agent)
    return AgentOut.model_validate(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(agent_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    agent = get_owned_agent(db, agent_id, current_user)
    db.delete(agent)
    db.commit()
    return None
