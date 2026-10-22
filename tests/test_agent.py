from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from trade_assistant import db, llm
from trade_assistant.agent import checks, facts, pipeline, roles
from trade_assistant.data import http, store
from trade_assistant.models import MonthlyPlan
from trade_assistant.portfolio import service as portfolio

from . import fake_sources as fake

CORE = fake.ETF_ISIN


@pytest.fixture
def session(monkeypatch):
    http.set_client(fake.fake_client())
    monkeypatch.setattr(http.time, "sleep", lambda s: None)
    db.init_db()
    with Session(db.get_engine()) as s:
        store.add_instrument(s, CORE)
        stock = store.add_instrument(s, fake.ISIN)
        store.refresh_prices(s, stock)
        portfolio.set_choice(s, fake.ISIN, "pinned")  # selected whatever its score
        yield s
    http.set_client(None)


def answers(monkeypatch, analyst=None, critic=None, manager=None):
    """A fake model answering each role; None = the role's default valid answer."""
    calls = []

    def ask(role, prompt, system=None):
        calls.append(system)
        isins = list(dict.fromkeys(re.findall(r"ISIN ([A-Z]{2}[A-Z0-9]{9}\d)", prompt)))
        if system == roles.ANALYST:
            companies = [{"isin": i, "thesis": "Entreprise de qualité.", "risks": "Prix élevé.",
                          "stance": "renforcer", "confidence": 2, "facts": ["F1", "F999"]} for i in isins]
            text = analyst if analyst is not None else json.dumps(
                {"companies": companies, "overview": "Correct.", "facts": []})
        elif system == roles.CRITIC:
            text = critic if critic is not None else json.dumps({"objections": [
                {"isin": None, "text": "Portefeuille encore petit.", "severity": 1, "facts": ["F3"]}]})
        else:
            plan = json.loads(prompt.split("Plan calculé par les règles :\n")[1])
            text = manager if manager is not None else json.dumps({
                "orders": [{"isin": o["isin"], "amount": o["amount"], "reason": "Conforme.", "facts": ["F1"]}
                           for o in plan],
                "summary": "On suit le plan.", "changes": "Aucun changement", "change_my_mind": "Une alerte.",
                "lesson": {"title": "Le DCA", "text": "Investir chaque mois lisse le prix."}})
        if callable(text):
            text = text(len([c for c in calls if c == system]))
        return llm.Answer(text, "fake", "m")

    monkeypatch.setattr(llm, "ask", ask)
    return calls


# --- Checks --------------------------------------------------------------------------------------

def test_numbers_ignore_fact_ids_and_read_french_formats():
    assert checks.numbers("PER 31,3 [F12] et 4 000 € (F3), 13 %") == [31.3, 4000.0, 13.0]


def test_unverified_figures():
    ctx = facts.Context(facts={"F1": "PER 31,3, pire baisse -77,0 %, valeur 528 €."},
                        profile={"monthly": 100, "min_order_eur": 10})
    text = "PER 31, baisse de 77 %, 528 € et 100 € par mois, 3 actions, en 2026"
    assert checks.unverified(text, ctx) == []
    assert checks.unverified("PER 77,7 et 4 000 € de rachats", ctx) == [77.7, 4000.0]


def _ctx(positions=None):
    ctx = facts.Context(profile={"monthly": 100, "core_isin": "CORE", "core_share": 0.7, "min_order_eur": 10,
                                 "max_position_share": 0.10},
                        portfolio={"total_value": 1000, "positions": positions or []})
    ctx.companies = {"A": facts.Company("A", "A", None, "target", 70),
                     "B": facts.Company("B", "B", None, "target", 65)}
    return ctx


@pytest.mark.parametrize("orders, error", [
    ([{"isin": "CORE", "amount": 70}, {"isin": "A", "amount": 30}], None),
    ([{"isin": "CORE", "amount": 80}, {"isin": "A", "amount": 20}], None),  # more prudence: allowed
    ([{"isin": "CORE", "amount": 60}, {"isin": "A", "amount": 40}], "au lieu d'au moins 70"),
    ([{"isin": "CORE", "amount": 70}, {"isin": "A", "amount": 25}], "au lieu de 100"),
    ([{"isin": "CORE", "amount": 70}, {"isin": "X", "amount": 30}], "liste autorisée"),
    ([{"isin": "CORE", "amount": 70}, {"isin": "A", "amount": 25}, {"isin": "B", "amount": 5}], "minimum"),
    ([{"isin": "CORE", "amount": 70}, {"isin": "A", "amount": 15.5}, {"isin": "B", "amount": 14.5}],
     "entier"),
    ([{"isin": "A", "amount": 100}], "absent"),
])
def test_order_rules(orders, error):
    result = checks.check_orders(orders, _ctx())
    assert result.ok == (error is None)
    if error:
        assert any(error in e for e in result.errors), result.errors


def test_order_rules_respect_the_cap():
    ctx = _ctx(positions=[{"isin": "A", "value": 150}])  # 150 >= 10 % of 1 100
    result = checks.check_orders([{"isin": "CORE", "amount": 70}, {"isin": "A", "amount": 30}], ctx)
    assert not result.ok and "plafond" in result.errors[0]


# --- Pipeline ------------------------------------------------------------------------------------

def test_agent_plan_when_everything_works(session, monkeypatch):
    answers(monkeypatch)
    data = pipeline.run(session)
    assert data["source"] == "agent" and data["fallback_reason"] is None
    assert sum(o["amount"] for o in data["orders"]) == 100
    assert data["orders"][0]["isin"] == CORE
    company = data["analyst"]["companies"][0]
    assert company["isin"] == fake.ISIN and company["facts"] == ["F1"]  # F999 does not exist: removed
    assert data["lesson"]["title"] == "Le DCA" and data["checklist"][0].startswith("Ouvre Trade Republic")
    assert all(s["ok"] for s in data["steps"]) and len(data["steps"]) == 3


def test_without_any_model_the_calculated_plan_is_used(session):
    data = pipeline.run(session)  # no API key in tests
    assert data["source"] == "rules" and "analyste" in data["fallback_reason"]
    assert data["orders"] and data["steps"][0]["ok"] is False


def test_a_plan_breaking_the_rules_is_replaced(session, monkeypatch):
    bad = json.dumps({"orders": [{"isin": CORE, "amount": 20, "reason": "x"},
                                 {"isin": fake.ISIN, "amount": 80, "reason": "Tout sur une action !"}],
                      "summary": "Audacieux."})
    answers(monkeypatch, manager=bad)
    data = pipeline.run(session)
    assert data["source"] == "rules" and "ne respectait pas tes règles" in data["fallback_reason"]
    assert data["analyst"] is not None and data["critic"]  # their work is still shown
    assert next(o for o in data["orders"] if o["isin"] == CORE)["amount"] >= 70


def test_malformed_answer_gets_a_second_chance(session, monkeypatch):
    valid = None

    def analyst(attempt):
        return "Je pense que..." if attempt == 1 else valid

    calls = answers(monkeypatch, analyst=analyst)
    valid = json.dumps({"companies": [], "overview": "Rien à signaler."})
    data = pipeline.run(session)
    assert calls.count(roles.ANALYST) == 2 and data["analyst"]["overview"] == "Rien à signaler."


def test_failed_critic_does_not_stop_the_plan(session, monkeypatch):
    answers(monkeypatch, critic="pas du JSON")
    data = pipeline.run(session)
    assert data["source"] == "agent" and data["critic"] == []
    assert [s["ok"] for s in data["steps"]] == [True, False, True]


def test_invented_figures_are_flagged(session, monkeypatch):
    def manager_with_invention(attempt):
        reason = "Le marché va monter de 23,7 %."
        return json.dumps({"orders": [{"isin": CORE, "amount": 100, "reason": reason}],
                           "summary": "Prudence."})

    answers(monkeypatch, manager=manager_with_invention)
    data = pipeline.run(session)
    assert data["orders"][0]["unverified"] == [23.7]


def test_approving_replaces_the_previous_approval(session, monkeypatch):
    answers(monkeypatch)
    first = pipeline.save(session, pipeline.run(session))
    second = pipeline.save(session, pipeline.run(session))
    pipeline.decide(session, first.id, "approved")
    pipeline.decide(session, second.id, "approved", "Vu.")
    statuses = {p.id: p.status for p in session.query(MonthlyPlan)}
    assert statuses == {first.id: "replaced", second.id: "approved"}
    assert pipeline.history(session)[0]["id"] == second.id


def test_api(session, monkeypatch):
    answers(monkeypatch)
    from trade_assistant.api import app

    with TestClient(app) as client:
        assert client.get("/api/plans/latest").json() is None
        client.post("/api/plans/generate")  # background task runs right after the response
        job = client.get("/api/plans/job").json()
        assert job["running"] is False and job["error"] is None and job["plan_id"]
        latest = client.get("/api/plans/latest").json()
        assert latest["status"] == "draft" and latest["source"] == "agent"
        r = client.post(f"/api/plans/{latest['id']}/decision", json={"status": "approved", "note": "ok"})
        assert r.json()["status"] == "approved"
        assert client.post("/api/plans/999/decision", json={"status": "approved"}).status_code == 404
        assert client.post(f"/api/plans/{latest['id']}/decision", json={"status": "maybe"}).status_code == 422


def test_command_line_run_and_show(session, monkeypatch, capsys):
    from trade_assistant.agent import __main__ as cli

    answers(monkeypatch)
    monkeypatch.setattr(cli, "_fresh_news", lambda s: None)
    assert cli.main(["run"]) == 0  # prints after the session is closed: no detached object
    assert "Plan n°1" in capsys.readouterr().out
    assert cli.main(["show"]) == 0
    assert "Statut : draft" in capsys.readouterr().out
