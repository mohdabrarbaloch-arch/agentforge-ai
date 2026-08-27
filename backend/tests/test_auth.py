"""Auth endpoint tests."""
from tests.conftest import auth_headers, register_user


def test_register_success(client):
    r = client.post("/api/auth/register", json={"email": "a@b.com", "password": "secret123", "name": "Alice"})
    assert r.status_code == 201
    data = r.json()
    assert "access_token" in data
    assert data["user"]["email"] == "a@b.com"


def test_register_duplicate_email(client):
    register_user(client, email="dup@b.com")
    r = client.post("/api/auth/register", json={"email": "dup@b.com", "password": "secret123", "name": "Dup"})
    assert r.status_code == 409


def test_register_weak_password_rejected(client):
    r = client.post("/api/auth/register", json={"email": "w@b.com", "password": "short", "name": "Weak"})
    assert r.status_code == 422


def test_login_success(client):
    register_user(client, email="login@b.com", password="secret123")
    r = client.post("/api/auth/login", json={"email": "login@b.com", "password": "secret123"})
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "login@b.com"


def test_login_wrong_password(client):
    register_user(client, email="bad@b.com", password="secret123")
    r = client.post("/api/auth/login", json={"email": "bad@b.com", "password": "nope1234"})
    assert r.status_code == 401


def test_me_requires_auth(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_with_token(client):
    token = register_user(client, email="me@b.com")
    r = client.get("/api/auth/me", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["email"] == "me@b.com"
