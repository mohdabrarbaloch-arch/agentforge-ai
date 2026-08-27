"""Pydantic schemas — request/response shapes for the API."""
import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

CRON_PATTERN = re.compile(r"^(\S+\s+){4}\S+$")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=120)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("password must contain at least one letter and one digit")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: str
    email: EmailStr
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    system_prompt: str = Field(min_length=1, max_length=8000)
    model: str = Field(default="gpt-4o-mini", max_length=64)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    enabled_tools: list[str] = Field(default_factory=list)


class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    enabled_tools: list[str] | None = None


class AgentOut(BaseModel):
    id: str
    name: str
    description: str
    system_prompt: str
    model: str
    temperature: float
    enabled_tools: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ThreadCreate(BaseModel):
    agent_id: str
    title: str | None = None


class ThreadOut(BaseModel):
    id: str
    agent_id: str
    title: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: str
    thread_id: str
    role: str
    content: str
    tool_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20000)


class ChatResponse(BaseModel):
    thread_id: str
    reply: str
    artifact_urls: list[str] = []
    tool_uses: list[str] = []


class TaskCreate(BaseModel):
    agent_id: str
    prompt: str = Field(min_length=1, max_length=20000)
    input_data: dict[str, Any] | None = None


class TaskOut(BaseModel):
    id: str
    agent_id: str | None
    thread_id: str | None
    task_type: str
    status: str
    prompt: str
    result: str | None
    error: str | None
    artifact_urls: list[str]
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class TriggerCreate(BaseModel):
    agent_id: str | None = None
    name: str = Field(min_length=1, max_length=160)
    cron_expression: str = Field(min_length=9, max_length=64)
    prompt: str = Field(min_length=1, max_length=20000)
    timezone: str = Field(default="Asia/Karachi", max_length=64)

    @field_validator("cron_expression")
    @classmethod
    def valid_cron(cls, v: str) -> str:
        if not CRON_PATTERN.match(v):
            raise ValueError("cron must have 5 fields (min hour dom month dow) e.g. '0 9 * * *'")
        return v


class TriggerOut(BaseModel):
    id: str
    agent_id: str | None
    name: str
    cron_expression: str
    prompt: str
    timezone: str
    enabled: bool
    last_run_at: datetime | None
    next_run_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TriggerToggle(BaseModel):
    enabled: bool


class IntegrationConnect(BaseModel):
    service: str = Field(min_length=2, max_length=40)
    config: dict[str, Any] | None = None


class IntegrationOut(BaseModel):
    id: str
    service: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ApiKeyOut(BaseModel):
    id: str
    name: str
    prefix: str
    created_at: datetime
    last_used_at: datetime | None

    model_config = {"from_attributes": True}


class ApiKeyCreated(ApiKeyOut):
    key: str  # shown exactly once


class ToolInfo(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class DashboardStats(BaseModel):
    agent_count: int
    task_count: int
    thread_count: int
    trigger_count: int
    recent_tasks: list[TaskOut]
