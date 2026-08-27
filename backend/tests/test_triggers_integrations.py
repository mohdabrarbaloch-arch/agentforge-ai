"""Trigger + integration + API key tests."""
from tests.conftest import auth_headers, make_agent, register_user


def test_create_trigger(client):
    token = register_user(client, email="tr@b.com")
    r = client.post(
        "/api/triggers",
        json={"name": "Morning brief", "cron_expression": "0 9 * * *", "prompt": "daily summary"},
        headers=auth_headers(token),
    )
    assert r.status_code == 201
    assert r.json()["cron_expression"] == "0 9 * * *"


def test_invalid_cron_rejected(client):
    token = register_user(client, email="cr@b.com")
    r = client.post(
        "/api/triggers",
        json={"name": "Bad cron", "cron_expression": "not-a-cron", "prompt": "x"},
        headers=auth_headers(token),
    )
    assert r.status_code == 422


def test_toggle_trigger(client):
    token = register_user(client, email="tg@b.com")
    trig = client.post(
        "/api/triggers",
        json={"name": "Toggle me", "cron_expression": "30 8 * * *", "prompt": "x"},
        headers=auth_headers(token),
    ).json()
    r = client.patch(f"/api/triggers/{trig['id']}", json={"enabled": False}, headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["enabled"] is False


def test_foreign_trigger_404(client):
    t1 = register_user(client, email="gt1@b.com")
    t2 = register_user(client, email="gt2@b.com")
    trig = client.post(
        "/api/triggers",
        json={"name": "Mine", "cron_expression": "0 7 * * *", "prompt": "x"},
        headers=auth_headers(t1),
    ).json()
    r = client.delete(f"/api/triggers/{trig['id']}", headers=auth_headers(t2))
    assert r.status_code == 404


def test_connect_integration(client):
    token = register_user(client, email="ci@b.com")
    r = client.post(
        "/api/integrations/connect",
        json={"service": "gmail"},
        headers=auth_headers(token),
    )
    assert r.status_code == 201
    assert r.json()["status"] == "connected"


def test_unsupported_integration_rejected(client):
    token = register_user(client, email="ui@b.com")
    r = client.post(
        "/api/integrations/connect",
        json={"service": "snapchat"},
        headers=auth_headers(token),
    )
    assert r.status_code == 422


def test_create_api_key(client):
    token = register_user(client, email="ak@b.com")
    r = client.post("/api/integrations/api-keys", json={"name": "cli"}, headers=auth_headers(token))
    assert r.status_code == 201
    data = r.json()
    assert data["key"].startswith("agf_")


def test_api_key_authenticates(client):
    token = register_user(client, email="ka@b.com")
    key = client.post("/api/integrations/api-keys", json={"name": "cli"}, headers=auth_headers(token)).json()["key"]
    r = client.get("/api/auth/me", headers=auth_headers(key))
    assert r.status_code == 200
    assert r.json()["email"] == "ka@b.com"


def test_revoke_api_key(client):
    token = register_user(client, email="rv@b.com")
    key = client.post("/api/integrations/api-keys", json={"name": "cli"}, headers=auth_headers(token)).json()
    r = client.delete(f"/api/integrations/api-keys/{key['id']}", headers=auth_headers(token))
    assert r.status_code == 204
    r = client.get("/api/auth/me", headers=auth_headers(key["key"]))
    assert r.status_code == 401


def test_dashboard_stats(client):
    token = register_user(client, email="ds@b.com")
    r = client.get("/api/dashboard/me", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["agent_count"] == 0
