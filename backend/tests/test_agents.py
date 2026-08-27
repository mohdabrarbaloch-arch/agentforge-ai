"""Agent CRUD tests."""
from tests.conftest import auth_headers, make_agent, register_user


def test_create_agent(client):
    token = register_user(client, email="ag@b.com")
    r = client.post(
        "/api/agents",
        json={"name": "Helper", "system_prompt": "Be helpful.", "enabled_tools": ["get_time"]},
        headers=auth_headers(token),
    )
    assert r.status_code == 201
    assert r.json()["name"] == "Helper"
    assert r.json()["enabled_tools"] == ["get_time"]


def test_list_agents_isolated_per_user(client):
    t1 = register_user(client, email="u1@b.com")
    t2 = register_user(client, email="u2@b.com")
    make_agent(client, t1)
    r1 = client.get("/api/agents", headers=auth_headers(t1))
    r2 = client.get("/api/agents", headers=auth_headers(t2))
    assert len(r1.json()) == 1
    assert len(r2.json()) == 0


def test_unknown_tool_rejected(client):
    token = register_user(client, email="ut@b.com")
    r = client.post(
        "/api/agents",
        json={"name": "Bad", "system_prompt": "x", "enabled_tools": ["not_a_tool"]},
        headers=auth_headers(token),
    )
    assert r.status_code == 422


def test_update_agent(client):
    token = register_user(client, email="ua@b.com")
    agent = make_agent(client, token)
    r = client.patch(f"/api/agents/{agent['id']}", json={"temperature": 0.2}, headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["temperature"] == 0.2


def test_delete_agent(client):
    token = register_user(client, email="da@b.com")
    agent = make_agent(client, token)
    r = client.delete(f"/api/agents/{agent['id']}", headers=auth_headers(token))
    assert r.status_code == 204
    r = client.get(f"/api/agents/{agent['id']}", headers=auth_headers(token))
    assert r.status_code == 404


def test_foreign_agent_404(client):
    t1 = register_user(client, email="f1@b.com")
    t2 = register_user(client, email="f2@b.com")
    agent = make_agent(client, t1)
    r = client.get(f"/api/agents/{agent['id']}", headers=auth_headers(t2))
    assert r.status_code == 404


def test_tools_catalog(client):
    r = client.get("/api/agents/tools")
    assert r.status_code == 200
    names = [t["name"] for t in r.json()]
    assert "web_search" in names
    assert "generate_image" in names
