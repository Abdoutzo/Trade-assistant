from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from trade_assistant import config
from trade_assistant.api import _FAILED, app


@pytest.fixture
def client():
    _FAILED.clear()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def with_password(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "correct horse")
    config.get_settings.cache_clear()


def test_health_is_public(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["database"] is True


def test_dev_mode_without_password_is_open(client):
    assert client.get("/api/auth/me").json() == {"authenticated": True, "login_enabled": False}
    assert client.get("/api/profile").status_code == 200


def test_private_routes_need_login(with_password, client):
    assert client.get("/api/profile").status_code == 401
    assert client.get("/api/llm/status").status_code == 401


def test_login_logout_cycle(with_password, client):
    assert client.post("/api/auth/login", json={"password": "wrong"}).status_code == 401
    r = client.post("/api/auth/login", json={"password": "correct horse"})
    assert r.status_code == 200
    assert "httponly" in r.headers["set-cookie"].lower()
    assert client.get("/api/profile").json()["satellite_share"] == 0.3
    client.post("/api/auth/logout")
    assert client.get("/api/profile").status_code == 401


def test_forged_cookie_is_rejected(with_password, client):
    client.cookies.set("ta_session", "owner.forged.signature")
    assert client.get("/api/profile").status_code == 401


def test_login_is_rate_limited(with_password, client):
    for _ in range(5):
        client.post("/api/auth/login", json={"password": "guess"})
    r = client.post("/api/auth/login", json={"password": "correct horse"})
    assert r.status_code == 429


def test_prod_refuses_insecure_config(monkeypatch):
    monkeypatch.setenv("ENV", "prod")
    config.get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="APP_PASSWORD"):
        config.get_settings().check()
    monkeypatch.setenv("APP_PASSWORD", "x")
    config.get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        config.get_settings().check()


def test_llm_test_without_keys_returns_503(client):
    r = client.post("/api/llm/test", json={"role": "fast"})
    assert r.status_code == 503


def test_llm_test_rejects_unknown_role(client):
    assert client.post("/api/llm/test", json={"role": "magic"}).status_code == 422


def test_profile_defaults_then_edited_from_the_site(client):
    p = client.get("/api/profile").json()
    assert (p["initial_amount_eur"], p["monthly_amount_eur"], p["core_share"], p["account_type"]) == (
        500, 100, 0.7, "PEA")
    new = {"account_type": "PEA", "initial_amount_eur": 1000, "monthly_amount_eur": 150, "core_share": 0.8,
           "horizon_years": 20}
    r = client.put("/api/profile", json=new)
    assert r.status_code == 200 and r.json()["satellite_share"] == 0.2
    assert client.get("/api/profile").json()["monthly_amount_eur"] == 150  # stored, not just echoed


@pytest.mark.parametrize("field, value", [("core_share", 1.5), ("monthly_amount_eur", -10),
                                          ("account_type", "Livret A"), ("horizon_years", 0)])
def test_profile_rejects_invalid_values(client, field, value):
    body = {"account_type": "PEA", "initial_amount_eur": 500, "monthly_amount_eur": 100, "core_share": 0.7,
            "horizon_years": 15, field: value}
    assert client.put("/api/profile", json=body).status_code == 422


def test_profile_needs_login(with_password, client):
    assert client.put("/api/profile", json={}).status_code == 401
