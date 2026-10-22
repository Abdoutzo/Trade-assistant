from __future__ import annotations

import math
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from trade_assistant import db
from trade_assistant.data import http, store
from trade_assistant.models import Instrument, Price
from trade_assistant.portfolio import allocation, backtest, positions, service

from . import fake_sources as fake

CORE = "FR001400U5Q4"


# --- Positions -----------------------------------------------------------------------------------

def test_average_cost_and_realized_gain():
    book = positions.build([
        positions.TradeIn(date(2026, 1, 5), "A", "buy", 2, 100, 1),
        positions.TradeIn(date(2026, 2, 5), "A", "buy", 2, 200, 1),
        positions.TradeIn(date(2026, 3, 5), "A", "sell", 1, 300, 1),
    ])
    p = book.positions["A"]
    assert p.quantity == 3
    assert p.average_cost == pytest.approx(602 / 4)  # sales do not change the average cost
    assert p.realized_eur == pytest.approx(300 - 1 - 602 / 4)
    assert book.contributions_eur == pytest.approx(201 + 401 - 299)


def test_selling_more_than_held_is_reported_not_applied():
    book = positions.build([positions.TradeIn(date(2026, 1, 5), "A", "buy", 1, 10),
                            positions.TradeIn(date(2026, 1, 6), "A", "sell", 2, 10)])
    assert book.positions["A"].quantity == 1 and book.errors


# --- Allocation ----------------------------------------------------------------------------------

def test_split_core_then_as_many_satellites_as_budget_allows():
    orders = allocation.split(100, 0.7, CORE, ["S1", "S2", "S3", "S4", "S5"], {})
    assert [(o.isin, o.amount_eur) for o in orders] == [(CORE, 70), ("S1", 10), ("S2", 10), ("S3", 10)]
    assert "attendent leur tour" in orders[0].reason
    assert sum(o.amount_eur for o in orders) == 100


def test_split_feeds_the_most_underweight_first():
    values = {CORE: 700, "S1": 100, "S2": 20, "S3": 60}
    orders = allocation.split(100, 0.7, CORE, ["S1", "S2", "S3"], values, max_position_share=0.5)
    # 3 fundable lines: all fed, equal amounts
    assert [o.amount_eur for o in orders[1:]] == [10, 10, 10]
    orders = allocation.split(100, 0.8, CORE, ["S1", "S2", "S3"], values, max_position_share=0.5)
    assert [o.isin for o in orders[1:]] == ["S2", "S3"]  # 20 euros: the two furthest below target


def test_split_skips_stocks_at_their_cap():
    values = {CORE: 500, "S1": 200, "S2": 0}
    orders = allocation.split(100, 0.7, CORE, ["S1", "S2"], values, max_position_share=0.10)
    assert "S1" not in [o.isin for o in orders] and "plafond" in orders[0].reason
    assert sum(o.amount_eur for o in orders) == 100


def test_split_everything_to_core_when_budget_too_small():
    orders = allocation.split(30, 0.7, CORE, ["S1"], {}, min_order=10)
    assert [(o.isin, o.amount_eur) for o in orders] == [(CORE, 30)]


def test_split_rounding_keeps_the_total():
    orders = allocation.split(137, 0.65, CORE, ["S1", "S2", "S3"], {}, min_order=5)
    assert sum(o.amount_eur for o in orders) == 137
    assert all(o.amount_eur == int(o.amount_eur) for o in orders)


# --- Simulation ----------------------------------------------------------------------------------

def _monthly(start: date, months: int, annual: float) -> list[tuple[date, float]]:
    out = []
    for m in range(months):
        day = date(start.year + (start.month - 1 + m) // 12, (start.month - 1 + m) % 12 + 1, 2)
        out.append((day, 100 * (1 + annual) ** (m / 12)))
    return out


def test_simulation_constant_growth_returns_that_growth():
    prices = {CORE: backtest.first_of_month(_monthly(date(2016, 1, 1), 121, 0.07))}
    months = sorted(prices[CORE])[:120]
    sim = backtest.simulate(prices, months, CORE, [], initial=500, monthly=100, core_share=1.0)
    st = backtest.stats(sim)
    assert st["invested"] == 500 + 119 * 100
    assert st["money_weighted_return"] == pytest.approx(0.07, abs=2e-3)
    assert st["time_weighted_return"] == pytest.approx(0.07, abs=2e-3)
    assert st["max_drawdown"] == 0


def test_simulation_buys_late_listings_only_once_they_exist():
    core = backtest.first_of_month(_monthly(date(2016, 1, 1), 60, 0.05))
    late = backtest.first_of_month(_monthly(date(2018, 1, 1), 36, 0.20))
    sim = backtest.simulate({CORE: core, "S": late}, sorted(core), CORE, ["S"], 500, 100, 0.7)
    assert sim.units["S"] > 0 and sim.final_value > sim.invested[-1]


def test_xirr_known_case():
    assert backtest.xirr([(date(2020, 1, 1), -100), (date(2021, 1, 1), 110)]) == pytest.approx(0.1, abs=1e-3)
    assert backtest.xirr([(date(2020, 1, 1), -100)]) is None


def test_projection_is_reproducible_and_exact_for_constant_returns():
    r = (1.06) ** (1 / 12) - 1
    p = backtest.project([r] * 60, 1000, 100, 120)
    expected = 1000 * (1 + r) ** 120 + 100 * ((1 + r) ** 120 - 1) / r * (1 + r) / (1 + r)
    assert p["p10"] == pytest.approx(p["p90"]) == pytest.approx(expected, rel=1e-6)
    assert p == backtest.project([r] * 60, 1000, 100, 120)
    assert backtest.project([r] * 10, 1000, 100, 120) is None  # too little history


def test_normalize_keeps_the_ups_and_downs_but_lowers_the_mean():
    ref = [0.03, -0.02, 0.025, 0.01] * 30
    out = backtest.normalize(ref, ref, 0.07)
    mean_log = sum(math.log1p(x) for x in out) / len(out)
    assert mean_log == pytest.approx(math.log1p(0.07) / 12)
    assert out[0] > out[1]  # same order of moves


# --- Service and API -----------------------------------------------------------------------------

@pytest.fixture
def client(monkeypatch):
    http.set_client(fake.fake_client())
    monkeypatch.setattr(http.time, "sleep", lambda s: None)
    from trade_assistant.api import app

    with TestClient(app) as c:
        yield c
    http.set_client(None)


def _add_prices(session: Session, instrument: Instrument, years: int = 6, growth: float = 0.08) -> None:
    session.query(Price).filter(Price.instrument_id == instrument.id).delete()
    start = date.today() - timedelta(days=years * 365)
    session.add_all(Price(instrument_id=instrument.id, day=start + timedelta(days=k),
                          close=100 * (1 + growth) ** (k / 365), adj_close=100 * (1 + growth) ** (k / 365))
                    for k in range(years * 365))
    session.commit()


def test_transactions_positions_and_validation(client):
    client.post("/api/instruments", json={"isin": fake.ISIN})
    buy = {"day": "2026-09-01", "isin": fake.ISIN, "side": "buy", "quantity": 0.5, "price_eur": 160,
           "fees_eur": 0}
    assert client.post("/api/portfolio/transactions", json=buy).status_code == 200
    too_much = {**buy, "side": "sell", "quantity": 2}
    assert client.post("/api/portfolio/transactions", json=too_much).status_code == 422
    unknown = {**buy, "isin": "NL0010273215"}
    assert client.post("/api/portfolio/transactions", json=unknown).status_code == 404
    future = {**buy, "day": (date.today() + timedelta(days=2)).isoformat()}
    assert client.post("/api/portfolio/transactions", json=future).status_code == 422

    pf = client.get("/api/portfolio").json()
    [line] = pf["positions"]
    assert line["quantity"] == 0.5 and line["value"] == pytest.approx(0.5 * 173.0)
    assert line["role"] == "satellite" and pf["contributions"] == 80
    assert client.delete(f"/api/portfolio/transactions/{pf['transactions'][0]['id']}").status_code == 200
    assert client.get("/api/portfolio").json()["positions"] == []


def test_plan_selection_and_choices(client):
    client.post("/api/instruments", json={"isin": fake.ISIN})
    with Session(db.get_engine()) as s:
        _add_prices(s, store.get_instrument(s, fake.ISIN))
    plan = client.get("/api/portfolio/plan").json()
    assert plan["orders"][0]["role"] == "core" and plan["first_payment"]
    assert sum(o["amount"] for o in plan["orders"]) == 100
    client.put(f"/api/portfolio/choices/{fake.ISIN}", json={"status": "excluded"})
    assert fake.ISIN not in [t["isin"] for t in client.get("/api/portfolio/plan").json()["targets"]]
    client.put(f"/api/portfolio/choices/{fake.ISIN}", json={"status": None})


def test_simulation_endpoint(client):
    with Session(db.get_engine()) as s:
        ref = Instrument(isin=service.REFERENCE_ISIN, symbol="IWDA.AS", name="MSCI World", kind="etf",
                         currency="EUR", is_reference=True)
        s.add(ref)
        s.commit()
        _add_prices(s, ref, years=11, growth=0.07)
    r = client.post("/api/portfolio/simulation", json={"years": 10, "satellites": []})
    assert r.status_code == 200
    sim = r.json()
    assert sim["strategy"]["money_weighted_return"] == pytest.approx(0.07, abs=5e-3)
    prudent = sim["projection"]["core_only_normalized"]
    assert prudent["p50"] > prudent["invested"]
    assert len(sim["chart"]["days"]) == 120
    assert [i["isin"] for i in client.get("/api/instruments").json()] == []  # reference stays hidden


def test_simulation_without_reference_is_a_clear_error(client):
    r = client.post("/api/portfolio/simulation", json={"years": 10})
    assert r.status_code == 503 and "référence" in r.json()["detail"]


def test_profile_rules_kept_when_the_form_omits_them(client):
    base = {"account_type": "PEA", "initial_amount_eur": 500, "monthly_amount_eur": 100, "core_share": 0.7,
            "horizon_years": 15}
    client.put("/api/profile", json={**base, "satellites_count": 3, "min_order_eur": 15})
    p = client.put("/api/profile", json=base).json()
    assert (p["satellites_count"], p["min_order_eur"], p["max_position_share"]) == (3, 15, 0.10)
