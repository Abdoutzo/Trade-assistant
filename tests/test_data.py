from __future__ import annotations

from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from trade_assistant import db
from trade_assistant.data import __main__ as cli
from trade_assistant.data import esef, euronext, http, store, universe, yahoo

from . import fake_sources as fake


@pytest.fixture(autouse=True)
def sources(monkeypatch):
    http.set_client(fake.fake_client())
    monkeypatch.setattr(http.time, "sleep", lambda s: None)
    monkeypatch.setattr(cli.time, "sleep", lambda s: None)
    yield
    http.set_client(None)


@pytest.fixture
def session():
    db.init_db()
    with Session(db.get_engine()) as s:
        yield s


# --- Rules ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("isin, ok", [
    ("FR0000120073", True), ("NL0010273215", True), ("FR001400U5Q4", True),
    ("FR0000120074", False), ("FR000012007", False), ("1R0000120073", False)])
def test_isin_check_digit(isin, ok):
    assert universe.is_valid_isin(isin) is ok


def test_seed_isins_are_valid_and_unique():
    assert all(universe.is_valid_isin(i) for i in universe.SEED)
    assert len(set(universe.SEED)) == len(universe.SEED)


@pytest.mark.parametrize("kind, isin, country, eligible", [
    ("stock", "FR0000120073", "FR", True),
    ("stock", "NL0000235190", "NL", True),  # Airbus: Dutch company listed in Paris
    ("stock", "DK0062498333", "DK", True),
    ("stock", "CH0038863350", "CH", False),  # Switzerland is not in the EEA
    ("stock", "GB0002374006", "GB", False),  # nor the UK since Brexit
    ("stock", "FR0000000000", None, True),  # no registry answer: country from the ISIN
    ("etf", "FR001400U5Q4", None, True),
    ("etf", "IE00B4L5Y983", None, None),  # unknown ETF: not decided automatically
])
def test_pea_status(kind, isin, country, eligible):
    assert universe.pea_status(kind, isin, country)[0] is eligible


# --- Sources -------------------------------------------------------------------------------------

def test_yahoo_search_prefers_home_market_and_skips_funds():
    assert [q.symbol for q in yahoo.search(fake.ISIN)] == ["AI.PA", "AIL.DE"]


def test_yahoo_chart_local_days_and_missing_sessions():
    c = yahoo.chart(fake.SYMBOL)
    assert [r.day for r in c.rows] == [date(2025, 10, 20), date(2026, 10, 21), date(2026, 10, 22)]
    assert c.rows[0].adj_close == 145.0 and c.kind == "stock" and c.currency == "EUR"


def test_yahoo_fundamentals_spending_is_positive():
    figures = {(f.metric, f.period_end.year): f.value for f in yahoo.fundamentals(fake.SYMBOL)}
    assert figures[("capex", 2025)] == 3_843_400_000
    assert figures[("revenue", 2023)] == 27_607_600_000


def test_esef_keeps_annual_whole_company_figures():
    figures = {(f.metric, f.period_end): f.value for f in esef.read(fake.ESEF_2024)}
    assert figures == {
        ("revenue", date(2024, 12, 31)): 27_057_800_000,
        ("revenue", date(2023, 12, 31)): 27_607_600_000,
        ("net_income", date(2024, 12, 31)): 3_306_100_000,  # owners of the parent, not total profit
        ("equity", date(2024, 12, 31)): 26_860_000_000,  # not the mid-year balance
        ("capex", date(2024, 12, 31)): 3_400_000_000,
        ("eps_diluted", date(2024, 12, 31)): 5.72,
    }


def test_esef_quarterly_report_yields_nothing():
    assert esef.read(fake.ESEF_Q3) == []


def test_esef_filings_latest_per_year_and_converted_only():
    filings = esef.filings(fake.LEI)
    assert [(f.period_end, f.json_url.rsplit("/", 1)[1]) for f in filings] == [
        (date(2024, 12, 31), "2024.json"), (date(2025, 9, 30), "q3.json")]


def test_esef_company_unknown_to_the_collector_has_no_report():
    assert esef.filings("529900D6BF99LW9R2E68") == []  # 404, like German companies today


def test_euronext_listing_to_yahoo_symbol():
    payload = [{"isin": "FR001400U5Q4", "mic": "XPAR",
                "label": "<span class='name'><a href='/x'>AMUNDI PEA MONDE</a></span>"
                         "<span class='symbol'>DCAM</span><span class='mic'>XPAR</span>"},
               {"isin": "", "mic": "", "label": "See all results"}]
    http.set_client(fake.fake_client(lambda r: httpx.Response(200, json=payload)))
    [listing] = euronext.search("FR001400U5Q4")
    assert (listing.symbol, listing.name, listing.yahoo_symbol) == ("DCAM", "AMUNDI PEA MONDE", "DCAM.PA")


def test_http_retries_after_429_then_gives_up():
    calls = []

    def flaky(request):
        calls.append(1)
        return httpx.Response(429) if len(calls) < 3 else httpx.Response(200, json={"ok": True})

    http.set_client(fake.fake_client(flaky))
    assert http.get_json("https://example.org") == {"ok": True}
    http.set_client(fake.fake_client(lambda r: httpx.Response(429)))
    with pytest.raises(http.SourceError, match="429"):
        http.get_json("https://example.org")


def test_http_does_not_retry_a_404():
    calls = []
    http.set_client(fake.fake_client(lambda r: calls.append(1) or httpx.Response(404)))
    with pytest.raises(http.NotFoundError):
        http.get_json("https://example.org")
    assert len(calls) == 1


# --- Store ---------------------------------------------------------------------------------------

def test_add_stock_identifies_everything(session):
    i = store.add_instrument(session, " fr0000120073 ")
    assert (i.isin, i.symbol, i.kind, i.country, i.lei, i.pea_eligible, i.sector) == (
        fake.ISIN, "AI.PA", "stock", "FR", fake.LEI, True, "Basic Materials")
    assert store.add_instrument(session, fake.ISIN).id == i.id  # adding twice changes nothing


def test_add_known_etf_uses_verified_ticker(session):
    i = store.add_instrument(session, fake.ETF_ISIN)
    assert (i.symbol, i.kind, i.pea_eligible, i.lei) == ("DCAM.PA", "etf", True, None)


def test_add_rejects_invalid_and_unknown_isins(session):
    with pytest.raises(ValueError):
        store.add_instrument(session, "FR0000120074")
    with pytest.raises(store.NotFound):
        store.add_instrument(session, "NL0010273215")  # valid, but no source knows it here


def test_prices_full_history_then_window_replaced(session):
    i = store.add_instrument(session, fake.ISIN)
    assert store.refresh_prices(session, i) == 3
    assert store.refresh_prices(session, i) == 3  # same window again: no duplicates
    assert len(store.prices(session, i)) == 3
    assert [p.day for p in store.prices(session, i, since=date(2026, 1, 1))] == [date(2026, 10, 21),
                                                                                date(2026, 10, 22)]


def test_fundamentals_merge_official_first_and_cross_check(session):
    i = store.add_instrument(session, fake.ISIN)
    result = store.refresh_fundamentals(session, i)
    assert (result.esef_reports_read, result.errors) == (2, [])
    assert store.refresh_fundamentals(session, i).esef_reports_read == 0  # never read twice

    table = store.fundamentals_table(session, i)
    fy24, fy25 = table[date(2024, 12, 31)], table[date(2025, 12, 31)]
    assert (fy24["revenue"].source, fy24["revenue"].value) == ("esef", 27_057_800_000)
    assert (fy25["revenue"].source, fy25["revenue"].value) == ("yahoo", 26_940_200_000)
    # Net income: 3.306 Md in the report, 3.4 Md at Yahoo -> 2.8 % gap, under the 3 % tolerance
    assert fy24["net_income"].other_value is None
    # EPS from a single source (Yahoo, restated for bonus shares), never mixed with the report
    assert fy24["eps_diluted"].source == "yahoo" and fy24["eps_diluted"].value == 5.2
    assert date(2023, 12, 31) not in table  # only one figure that year: dropped


def test_cross_check_flags_large_gaps(session):
    i = store.add_instrument(session, fake.ISIN)
    store.refresh_fundamentals(session, i)
    store._replace(session, i, "yahoo", [yahoo.Figure(date(2024, 12, 31), "net_income", 4e9, "EUR")], None)
    cell = store.fundamentals_table(session, i)[date(2024, 12, 31)]["net_income"]
    assert cell.other_value == 4e9 and cell.gap == pytest.approx(0.2099, abs=1e-3)


def test_etf_has_no_accounts(session):
    i = store.add_instrument(session, fake.ETF_ISIN)
    assert store.refresh_fundamentals(session, i).yahoo_figures == 0


def test_remove_instrument(session):
    i = store.add_instrument(session, fake.ISIN)
    store.refresh_prices(session, i)
    store.refresh_fundamentals(session, i)
    store.remove_instrument(session, i)
    assert store.list_instruments(session) == []


# --- Command line and API ------------------------------------------------------------------------

def test_cli_check(capsys):
    assert cli.main(["check", fake.ISIN]) == 0
    out = capsys.readouterr().out
    assert "PEA : oui" in out and "27.06 Md*" in out and "sur 1 an : +19.3%" in out


def test_api_add_detail_prices_delete():
    from trade_assistant.api import app

    with TestClient(app) as client:
        r = client.post("/api/instruments", json={"isin": fake.ISIN})
        assert r.status_code == 200 and r.json()["symbol"] == "AI.PA"
        assert client.post("/api/instruments", json={"isin": "bad"}).status_code == 422

        detail = client.get(f"/api/instruments/{fake.ISIN}").json()  # background task already ran
        assert "2024-12-31" in detail["years"]
        assert detail["fundamentals"]["revenue"][detail["years"].index("2024-12-31")]["source"] == "esef"
        assert detail["reports"][0]["url"].endswith("2024.html")

        assert len(client.get(f"/api/instruments/{fake.ISIN}/prices?period=10y").json()) == 3
        assert client.get(f"/api/instruments/{fake.ISIN}/prices?period=2w").status_code == 422
        assert [x["isin"] for x in client.get("/api/instruments").json()] == [fake.ISIN]
        assert client.delete(f"/api/instruments/{fake.ISIN}").status_code == 200
        assert client.get(f"/api/instruments/{fake.ISIN}").status_code == 404
