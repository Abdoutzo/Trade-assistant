from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from trade_assistant import db
from trade_assistant.agent import facts
from trade_assistant.data import http, store
from trade_assistant.portfolio import service, tradeplans

from . import fake_sources as fake

ETF = {"isin": "ETF", "name": "ETF monde", "role": "core"}
ITX = {"isin": "ITX", "name": "Inditex", "role": "satellite"}
RMS = {"isin": "RMS", "name": "Hermès", "role": "satellite"}
PRICES = {"ETF": 6.3, "ITX": 57.18, "RMS": 1261.0}


def orders(etf=80, itx=10, rms=10):
    return [{**ETF, "amount": etf}, {**ITX, "amount": itx}, {**RMS, "amount": rms}]


def by_isin(plans):
    return {p["isin"]: (p["amount"], p["frequency"]) for p in plans}


def test_whole_shares_turn_small_amounts_into_a_quarterly_plan():
    plans, notes = tradeplans.practical(orders(), PRICES, whole_shares=True)
    # Hermès is out of reach: its 10 € join Inditex, whose 20 €/month buy one share each quarter.
    assert by_isin(plans) == {"ETF": (80, "monthly"), "ITX": (60, "quarterly")}
    assert any("Hermès" in n and "Inditex" in n for n in notes)
    assert any("trimestriel de 60 €" in n for n in notes)
    assert sum(p["monthly"] for p in plans) == 100


def test_with_fractions_every_line_stays_monthly():
    plans, notes = tradeplans.practical(orders(), PRICES, whole_shares=False)
    assert by_isin(plans) == {"ETF": (80, "monthly"), "ITX": (10, "monthly"), "RMS": (10, "monthly")}
    assert notes == []


def test_unaffordable_stocks_give_their_money_to_the_etf():
    plans, _ = tradeplans.practical([{**ETF, "amount": 90}, {**RMS, "amount": 10}], PRICES, whole_shares=True)
    assert by_isin(plans) == {"ETF": (100, "monthly")}


def test_cheap_share_stays_monthly():
    plans, _ = tradeplans.practical(orders(itx=60, rms=0, etf=40), PRICES, whole_shares=True)
    assert by_isin(plans) == {"ETF": (40, "monthly"), "ITX": (60, "monthly")}


def test_actions_compare_with_the_running_plans():
    proposed, _ = tradeplans.practical(orders(), PRICES, whole_shares=True)
    running = [{"isin": "ETF", "name": "ETF monde", "amount": 440, "frequency": "monthly",
                "frequency_label": "chaque mois"},
               {"isin": "ITX", "name": "Inditex", "amount": 60, "frequency": "quarterly",
                "frequency_label": "tous les 3 mois"},
               {"isin": "OLD", "name": "Ancienne", "amount": 10, "frequency": "monthly",
                "frequency_label": "chaque mois"}]
    todo = {a["isin"]: a for a in tradeplans.actions(proposed, running)}
    assert todo["ETF"]["kind"] == "update" and "440 € chaque mois → 80 € chaque mois" in todo["ETF"]["text"]
    assert todo["ITX"]["kind"] == "keep" and todo["OLD"]["kind"] == "delete"
    steps = tradeplans.checklist(list(todo.values()), None, running)
    assert any("Modifie le plan ETF monde" in s for s in steps)

    same = [{**r, "amount": 80} if r["isin"] == "ETF" else r for r in running if r["isin"] != "OLD"]
    steps = tradeplans.checklist(tradeplans.actions(proposed, same), None, same)
    assert steps[0].startswith("Rien à changer")


# --- With the database ---------------------------------------------------------------------------

@pytest.fixture
def session(monkeypatch):
    http.set_client(fake.fake_client())
    monkeypatch.setattr(http.time, "sleep", lambda s: None)
    db.init_db()
    with Session(db.get_engine()) as s:
        for isin in (fake.ETF_ISIN, fake.ISIN):
            store.refresh_prices(s, store.add_instrument(s, isin))
        yield s
    http.set_client(None)


def test_api_and_agent_facts(session):
    from trade_assistant.api import app

    with TestClient(app) as client:
        assert client.get("/api/portfolio/trade-plans").json() == []
        body = [{"isin": fake.ETF_ISIN, "amount": 80, "frequency": "monthly"},
                {"isin": fake.ISIN, "amount": 345, "frequency": "quarterly"}]
        saved = client.put("/api/portfolio/trade-plans", json=body).json()
        assert [(p["amount"], p["frequency_label"]) for p in saved] == [(345, "tous les 3 mois"),
                                                                       (80, "chaque mois")]
        assert saved[0]["monthly"] == 115
        assert client.put("/api/portfolio/trade-plans", json=body[:1] * 2).status_code == 422
        bad = [{"isin": "XX0000000000", "amount": 10, "frequency": "monthly"}]
        assert client.put("/api/portfolio/trade-plans", json=bad).status_code == 404
        plan = client.get("/api/portfolio/plan").json()
        assert plan["trade_plans"] and plan["actions"] and plan["checklist"]

    service.add_transaction(session, __import__("datetime").date(2026, 10, 22), fake.ISIN, "buy", 1, 173)
    ctx = facts.build(session)
    text = "\n".join(ctx.facts.values())
    assert "actions entières uniquement" in text
    assert "Plans en cours sur Trade Republic" in text and "tous les 3 mois" in text
    assert "2026-10 : achat 1 x" in text
    assert "prix d'une action 173,00 €" in text


def test_command_line_plans(session, capsys):
    from trade_assistant.portfolio import __main__ as cli

    assert cli.main(["plans", f"{fake.ETF_ISIN}:80:monthly, {fake.ISIN}:345:quarterly"]) == 0
    out = capsys.readouterr().out
    assert "345 € tous les 3 mois" in out and "80 € chaque mois" in out
    assert cli.main(["plans", f"{fake.ETF_ISIN}:80:yearly"]) == 1
    assert cli.main(["plans"]) == 0 and "80 € chaque mois" in capsys.readouterr().out
