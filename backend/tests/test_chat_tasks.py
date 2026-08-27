"""Chat + task lifecycle tests."""
import time

from tests.conftest import auth_headers, make_agent, register_user


def test_create_thread(client):
    token = register_user(client, email="ct@b.com")
    agent = make_agent(client, token)
    r = client.post(
        "/api/chat/threads",
        json={"agent_id": agent["id"], "title": "My chat"},
        headers=auth_headers(token),
    )
    assert r.status_code == 201
    assert r.json()["title"] == "My chat"


def test_send_message_gets_reply(client):
    token = register_user(client, email="sm@b.com")
    agent = make_agent(client, token)
    thread = client.post("/api/chat/threads", json={"agent_id": agent["id"]}, headers=auth_headers(token)).json()
    r = client.post(
        f"/api/chat/threads/{thread['id']}/messages",
        json={"message": "search for ai news"},
        headers=auth_headers(token),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["thread_id"] == thread["id"]
    assert data["reply"]


def test_message_history_persisted(client):
    token = register_user(client, email="mh@b.com")
    agent = make_agent(client, token)
    thread = client.post("/api/chat/threads", json={"agent_id": agent["id"]}, headers=auth_headers(token)).json()
    client.post(
        f"/api/chat/threads/{thread['id']}/messages",
        json={"message": "hello there"},
        headers=auth_headers(token),
    )
    r = client.get(f"/api/chat/threads/{thread['id']}/messages", headers=auth_headers(token))
    roles = [m["role"] for m in r.json()]
    assert "user" in roles
    assert "assistant" in roles


def test_foreign_thread_404(client):
    t1 = register_user(client, email="ft1@b.com")
    t2 = register_user(client, email="ft2@b.com")
    agent = make_agent(client, t1)
    thread = client.post("/api/chat/threads", json={"agent_id": agent["id"]}, headers=auth_headers(t1)).json()
    r = client.get(f"/api/chat/threads/{thread['id']}/messages", headers=auth_headers(t2))
    assert r.status_code == 404


def test_create_task_returns_card(client):
    token = register_user(client, email="tc@b.com")
    agent = make_agent(client, token)
    r = client.post(
        "/api/tasks",
        json={"agent_id": agent["id"], "prompt": "Write me a summary of the news"},
        headers=auth_headers(token),
    )
    assert r.status_code == 202
    data = r.json()
    assert data["status"] in ("queued", "running", "succeeded")
    assert data["task_type"] == "run"


def test_task_eventually_succeeds(client):
    token = register_user(client, email="ts@b.com")
    agent = make_agent(client, token)
    task = client.post(
        "/api/tasks",
        json={"agent_id": agent["id"], "prompt": "search the web for tech news"},
        headers=auth_headers(token),
    ).json()
    for _ in range(30):
        status = client.get(f"/api/tasks/{task['id']}", headers=auth_headers(token)).json()["status"]
        if status in ("succeeded", "failed"):
            break
        time.sleep(0.2)
    final = client.get(f"/api/tasks/{task['id']}", headers=auth_headers(token)).json()
    assert final["status"] == "succeeded"
    assert final["result"]


def test_task_foreign_404(client):
    t1 = register_user(client, email="tt1@b.com")
    t2 = register_user(client, email="tt2@b.com")
    agent = make_agent(client, t1)
    task = client.post(
        "/api/tasks",
        json={"agent_id": agent["id"], "prompt": "do something"},
        headers=auth_headers(t1),
    ).json()
    r = client.get(f"/api/tasks/{task['id']}", headers=auth_headers(t2))
    assert r.status_code == 404
