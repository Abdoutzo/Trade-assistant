from __future__ import annotations

import math
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from trade_assistant import db
from trade_assistant.analysis import ratios, risk, scoring, service
from trade_assistant.data import http, store, yahoo
from trade_assistant.models import Instrument, Price

from . import fake_sources as fake

D = [date(y, 12, 31) for y in range(2020, 2026)]


# --- Ratios --------------------------------------------------------------------------------------

def test_a_ratio_never_mixes_sources():
    accounts = {
        "esef": {D[4]: {"net_income": 10.0}},  # no equity in the official report that year
        "yahoo": {D[4]: {"net_income": 8.0, "equity": 100.0}},
    }
    point = ratios.yearly(accounts)["roe"][D[4]]
    assert (point.value, point.source) == (0.08, "yahoo")  # 8/100, not 10/100


def test_free_cash_flow_derived_when_missing():
    accounts = {"esef": {D[4]: {"operating_cash_flow": 50.0, "capex": 20.0, "revenue": 300.0}}}
    assert ratios.yearly(accounts)["fcf_margin"][D[4]].value == pytest.approx(0.1)


def test_undefined_ratios_are_skipped():
    accounts = {"yahoo": {D[4]: {"net_income": -5.0, "equity": 100.0, "free_cash_flow": 3.0,
                                 "total_debt": 10.0, "cash": 1.0, "ebitda": -2.0}}}
    y = ratios.yearly(accounts)
    assert y["roe"][D[4]].value == -0.05  # a loss gives a negative ROE...
    assert D[4] not in y["cash_conversion"]  # ...but no conversion of a loss into cash
    assert D[4] not in y["net_debt_to_ebitda"]  # nor debt/EBITDA with a negative EBITDA


def test_roic_uses_bounded_tax_rate():
    row = {"operating_income": 100.0, "invested_capital": 500.0,
           "tax_provision": 90.0, "pretax_income": 100.0}  # 90 % tax: capped at 40 %
    assert ratios.yearly({"yahoo": {D[4]: row}})["roic"][D[4]].value == pytest.approx(100 * 0.6 / 500)


def test_recent_mean_last_three_years():
    series = {d: ratios.Point(v, "esef") for d, v in zip(D, [0.1, 0.2, 0.3, 0.4, 0.5], strict=False)}
    mean, days = ratios.recent_mean(series)
    assert mean == pytest.approx(0.4) and days == D[2:5]


def test_cagr_and_consistency():
    series = {d: 100 * 1.1 ** i for i, d in enumerate(D)}
    assert ratios.cagr(series) == pytest.approx(0.1, abs=1e-3)
    assert ratios.cagr({D[0]: 1.0, D[1]: 2.0}) is None  # two points are not a trend
    assert ratios.cagr({D[0]: -1.0, D[1]: 1.0, D[2]: 2.0}) is None  # undefined from a loss
    assert ratios.growth_consistency({D[0]: 1, D[1]: 2, D[2]: 1.5, D[3]: 3}) == pytest.approx(2 / 3)


def test_series_extended_with_recent_years_when_sources_agree():
    accounts = {"esef": {D[2]: {"revenue": 100.0}, D[3]: {"revenue": 110.0}, D[4]: {"revenue": 120.0}},
                "yahoo": {D[3]: {"revenue": 111.0}, D[4]: {"revenue": 120.0}, D[5]: {"revenue": 90.0}}}
    series, source = ratios.metric_series(accounts, "revenue")
    assert list(series.values()) == [100.0, 110.0, 120.0, 90.0] and source == "esef+yahoo"


def test_series_not_extended_when_sources_disagree():
    accounts = {"esef": {D[2]: {"revenue": 100.0}, D[3]: {"revenue": 110.0}, D[4]: {"revenue": 120.0}},
                "yahoo": {D[4]: {"revenue": 150.0}, D[5]: {"revenue": 160.0}}}  # other GAAP
    series, source = ratios.metric_series(accounts, "revenue")
    assert D[5] not in series and source == "esef"


def test_per_share_series_from_one_source_only():
    accounts = {"esef": {d: {"eps_diluted": 5.0} for d in D[:5]},  # more years, but not restated
                "yahoo": {d: {"eps_diluted": 4.0} for d in D[3:]}}
    series, source = ratios.metric_series(accounts, "eps_diluted", prefer=("yahoo", "esef"), strict=True)
    assert source == "yahoo" and set(series.values()) == {4.0}


# --- Risk ----------------------------------------------------------------------------------------

def _days(n: int, start: date = date(2020, 1, 1)) -> list[date]:
    return [start + timedelta(days=i) for i in range(n)]


def test_returns():
    series = [(d, 100 * 1.1 ** (i / 365.25)) for i, d in enumerate(_days(3 * 366))]
    assert risk.total_return(series, 1) == pytest.approx(0.1, abs=2e-3)
    assert risk.total_return(series, 3) == pytest.approx(0.1, abs=2e-3)
    assert risk.total_return(series, 5) is None  # not enough history


def test_volatility_of_alternating_moves():
    series = [(d, 100 * (1.01 if i % 2 else 1.0)) for i, d in enumerate(_days(400))]
    assert risk.volatility(series) == pytest.approx(math.log(1.01) * math.sqrt(252), rel=0.01)
    assert risk.volatility(series[:30]) is None


def test_max_drawdown():
    prices = [100, 120, 60, 90, 130, 117] + [117] * 60  # worst: 120 -> 60
    series = list(zip(_days(len(prices)), prices, strict=False))
    assert risk.max_drawdown(series) == pytest.approx(-0.5)


def test_beta_of_a_leveraged_copy_is_two():
    market = [(d, 100 * (1 + 0.02 * math.sin(i / 3))) for i, d in enumerate(_days(800))]
    weekly = risk._weekly(market)
    keys = sorted(weekly)
    # A security moving exactly twice as much as the market each week.
    copy, v = [], 100.0
    for k1, k2 in zip(keys, keys[1:], strict=False):
        v *= 1 + 2 * (weekly[k2] / weekly[k1] - 1)
        copy.append((date.fromisocalendar(k2[0], k2[1], 5), v))
    market_fri = [(date.fromisocalendar(k[0], k[1], 5), weekly[k]) for k in keys]
    assert risk.beta(copy, market_fri) == pytest.approx(2.0, abs=1e-6)


def test_price_on_takes_last_close_before():
    series = [(date(2025, 12, 30), 10.0), (date(2026, 1, 2), 11.0)]
    assert risk.price_on(series, date(2025, 12, 31)) == 10.0
    assert risk.price_on(series, date(2025, 1, 1)) is None


# --- Scoring -------------------------------------------------------------------------------------

def test_metric_score_linear_both_directions():
    assert scoring.metric_score(scoring.METRICS["roic"], 0.125) == pytest.approx(50)
    assert scoring.metric_score(scoring.METRICS["roic"], 0.5) == 100
    assert scoring.metric_score(scoring.METRICS["pe"], 12) == 100  # lower is better
    assert scoring.metric_score(scoring.METRICS["pe"], 40) == 0


def test_score_needs_three_pillars():
    one = scoring.score({"roic": (0.2, None), "pe": (12.0, None)}, is_financial=False)
    assert one["score"] is None and one["verdict"] == "Données insuffisantes pour un avis"
    three = scoring.score({"roic": (0.2, None), "pe": (12.0, None), "volatility": (0.15, None)}, False)
    assert three["score"] == 100 and three["strengths"]


def test_financials_skip_industrial_metrics():
    result = scoring.score({"roic": (0.3, None), "roe": (0.12, None), "pb": (1.0, None)}, is_financial=True)
    keys = {m["key"] for p in result["pillars"].values() for m in p["metrics"]}
    assert "roic" not in keys and "net_debt_to_ebitda" not in keys and "pb" in keys
    assert "pb" not in {m["key"] for p in scoring.score({}, False)["pillars"].values() for m in p["metrics"]}


def test_every_metric_is_explained():
    for metric in scoring.METRICS.values():
        assert metric.pillar in scoring.PILLARS and len(metric.help) > 40 and metric.good != metric.bad
    assert sum(w for _, w, _ in scoring.PILLARS.values()) == pytest.approx(1.0)


# --- Service and API -----------------------------------------------------------------------------

@pytest.fixture
def session(monkeypatch):
    http.set_client(fake.fake_client())
    monkeypatch.setattr(http.time, "sleep", lambda s: None)
    yahoo._fx_cache.clear()
    db.init_db()
    with Session(db.get_engine()) as s:
        yield s
    http.set_client(None)


def _stock_with_history(session: Session) -> Instrument:
    """Air Liquide from the fake sources, plus 6 years of synthetic prices."""
    i = store.add_instrument(session, fake.ISIN)
    store.refresh_fundamentals(session, i)
    start = date(2020, 1, 1)
    session.add_all(Price(instrument_id=i.id, day=start + timedelta(days=k), close=100 + k * 0.03,
                          adj_close=100 + k * 0.03) for k in range(6 * 365))
    session.commit()
    return i


def test_analysis_of_a_stock(session):
    i = _stock_with_history(session)
    data = service.get_analysis(session, i)
    v = data["valuation"]
    assert data["kind"] == "stock" and "pillars" in data
    assert data["pillars"]["growth"]["metrics"][0]["key"] == "revenue_cagr"
    # The fake Yahoo gives no share count: no market value, said plainly rather than guessed.
    assert v == {} and any("Nombre d'actions" in w for w in data["warnings"])
    assert data["risk"]["volatility"] is not None


def test_valuation_with_currency_conversion(session, monkeypatch):
    i = _stock_with_history(session)
    store._replace(session, i, "yahoo", [yahoo.Figure(date(2025, 12, 31), "shares", 600e6, None)], None)
    for f in session.query(store.Fundamental).filter_by(instrument_id=i.id):
        f.currency = "USD" if f.metric != "shares" else None
    session.commit()
    monkeypatch.setattr(yahoo, "fx_rate", lambda a, b: 1.1 if (a, b) == ("EUR", "USD") else 1.0)
    data = service.get_analysis(session, i, force=True)
    price = 100 + (6 * 365 - 1) * 0.03
    assert data["valuation"]["market_cap"] == pytest.approx(price * 1.1 * 600e6)
    assert data["valuation"]["pe"] == pytest.approx(price * 1.1 * 600e6 / 3_517_900_000)
    assert any("comptes en USD" in w for w in data["warnings"])


def test_etf_gets_risk_but_no_score(session):
    i = store.add_instrument(session, fake.ETF_ISIN)
    store.refresh_prices(session, i)
    data = service.get_analysis(session, i)
    assert data["score"] is None and data["verdict"].startswith("ETF")


def test_cache_reused_until_data_changes(session, monkeypatch):
    i = _stock_with_history(session)
    first = service.get_analysis(session, i)
    calls = []
    monkeypatch.setattr(service, "analyze", lambda *a, **k: calls.append(1) or first)
    service.get_analysis(session, i)
    assert calls == []  # fresh: served from the cache
    i.prices_updated_at = store.utcnow() + timedelta(seconds=1)
    session.commit()
    service.get_analysis(session, i)
    assert calls == [1]  # new prices: recomputed


def test_api_ranking_and_analysis(session):
    from trade_assistant.api import app

    _stock_with_history(session)
    with TestClient(app) as client:
        ranking = client.get("/api/ranking").json()
        assert [r["isin"] for r in ranking["rows"]] == [fake.ISIN]
        assert set(ranking["pillars"]) == set(scoring.PILLARS)
        detail = client.get(f"/api/instruments/{fake.ISIN}/analysis").json()
        assert "pillars" in detail and "sector_medians" in detail
        assert client.get("/api/instruments/FR0000120271/analysis").status_code == 404


def test_concurrent_computation_of_the_same_analysis(session):
    """Two pages opened together: the second writer updates instead of failing on the unique key."""
    i = _stock_with_history(session)
    with Session(db.get_engine()) as other:
        service.get_analysis(other, other.get(Instrument, i.id))  # the other request wrote first
    service._save(session, i, None, {"score": 42})  # this one still believed there was no row
    from trade_assistant.models import Analysis

    rows = session.query(Analysis).filter_by(instrument_id=i.id).all()
    assert len(rows) == 1 and rows[0].score == 42
