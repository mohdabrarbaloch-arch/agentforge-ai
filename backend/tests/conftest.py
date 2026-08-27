"""Shared pytest fixtures — an isolated app + temp SQLite DB per test."""

import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_agentforge.db"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["SCHEDULER_ENABLED"] = "false"

sys.path.insert(0, os.path.dirname(__file__))  # make `app` importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _db_setup():
    init_db()
    yield


@pytest.fixture(autouse=True)
def _clean_db():
    yield
    db = SessionLocal()
    try:
        for table in ["messages", "threads", "tasks", "triggers", "integrations", "api_keys", "agents", "users"]:
            db.execute(f"DELETE FROM {table}")
        db.commit()
    finally:
        db.close()


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def register_user(client, email="test@example.com", password="passw0rd1", name="Test User"):
    r = client.post("/api/auth/register", json={"email": email, "password": password, "name": name})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def make_agent(client, token, tools=None):
    payload = {
        "name": "Research Bot",
        "description": "Test agent",
        "system_prompt": "You are a helpful research assistant.",
        "enabled_tools": tools or ["web_search", "get_time"],
    }
    r = client.post("/api/agents", json=payload, headers=auth_headers(token))
    assert r.status_code == 201, r.text
    return r.json()
