from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from trade_assistant import db, journal
from trade_assistant.data import http, store
from trade_assistant.models import MonthlyPlan, Price
from trade_assistant.portfolio import service

from . import fake_sources as fake

TODAY = date(2027, 2, 1)


@pytest.fixture
def session(monkeypatch):
    http.set_client(fake.fake_client())
    monkeypatch.setattr(http.time, "sleep", lambda s: None)
    db.init_db()
    with Session(db.get_engine()) as s:
        etf, stock = store.add_instrument(s, fake.ETF_ISIN), store.add_instrument(s, fake.ISIN)
        s.execute(delete(Price))
        for instrument, points in ((etf, [("2026-01-02", 10), ("2026-06-01", 12), ("2027-02-01", 15)]),
                                   (stock, [("2026-01-02", 100), ("2026-06-01", 100), ("2027-02-01", 110)])):
            for day, close in points:
                s.add(Price(instrument_id=instrument.id, day=date.fromisoformat(day), close=close,
                            adj_close=close))
        s.commit()
        yield s
    http.set_client(None)


def test_empty(session):
    assert journal.journal(session, TODAY) == {"empty": True}


def test_choices_against_the_etf(session):
    service.add_transaction(session, date(2026, 1, 2), fake.ETF_ISIN, "buy", 7, 10)
    service.add_transaction(session, date(2026, 1, 2), fake.ISIN, "buy", 0.3, 100)
    session.add(MonthlyPlan(month="2026-01", status="approved", note="Je suis le plan.",
                            data={"source": "agent", "orders": [{"name": "ETF", "amount": 70}]}))
    session.commit()
    j = journal.journal(session, TODAY)
    # Real: 7 x 15 + 0.3 x 110 = 138 €. Same 100 € on the ETF the same day: 10 shares x 15 = 150 €.
    assert j["value"] == pytest.approx(138) and j["if_etf"] == pytest.approx(150)
    assert j["difference"] == pytest.approx(-12) and j["invested"] == pytest.approx(100)
    stock, core = j["lines"]
    assert stock["role"] == "satellite" and stock["difference"] == pytest.approx(-12)
    assert stock["return"] == pytest.approx(0.10) and stock["etf_return"] == pytest.approx(0.50)
    assert core["difference"] == pytest.approx(0)  # the ETF line is its own benchmark
    assert j["xirr"] is not None and j["xirr"] < j["etf_xirr"]
    assert "12 € de moins" in j["verdict"] and "augmenter la part de l'ETF" in j["verdict"]
    [month] = j["by_month"]
    assert month["plan"]["note"] == "Je suis le plan." and len(month["trades"]) == 2
    assert j["chart"]["days"][0] == "2026-01-02" and j["chart"]["mine"][-1] == pytest.approx(138)


def test_a_sale_leaves_both_portfolios(session):
    service.add_transaction(session, date(2026, 1, 2), fake.ISIN, "buy", 1, 100)
    service.add_transaction(session, date(2026, 6, 1), fake.ISIN, "sell", 1, 100)
    j = journal.journal(session, TODAY)
    # Sold at the price paid: nothing left, nothing gained. The ETF side sold 100 € at 12 after buying at 10.
    assert j["value"] == pytest.approx(0) and j["invested"] == pytest.approx(0)
    assert j["if_etf"] == pytest.approx((10 - 100 / 12) * 15)
    assert j["lines"][0]["value"] == pytest.approx(100)


def test_short_history_is_not_a_verdict(session):
    service.add_transaction(session, date(2026, 12, 1), fake.ETF_ISIN, "buy", 7, 10)
    j = journal.journal(session, TODAY)
    assert "Trop tôt" in j["verdict"] and j["xirr"] is None


def test_api(session):
    from trade_assistant.api import app

    with TestClient(app) as client:
        assert client.get("/api/journal").json()["empty"] is True
