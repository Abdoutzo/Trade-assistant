"""Assembles the analysis of an instrument from the database, and caches it.

Recomputed when the instrument's prices or accounts changed, or after 20 hours (valuation moves
with the price every day).
"""
from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..data import store, yahoo
from ..data.http import SourceError
from ..models import Analysis, Instrument, utcnow
from . import ratios, risk, scoring

log = logging.getLogger(__name__)

# Amundi PEA MSCI Europe: the market the universe's companies belong to, ~8 years of prices.
BENCHMARK_ISIN = "FR0013412038"
MAX_AGE = timedelta(hours=20)
FINANCIAL_SECTORS = {"Financial Services"}
QUALITY_AVERAGED = ("roic", "roe", "operating_margin", "fcf_margin", "cash_conversion")
SOLIDITY_LATEST = ("net_debt_to_ebitda", "interest_coverage", "current_ratio", "equity_ratio")
YEARLY_SHOWN = ("roic", "roe", "operating_margin", "net_margin", "fcf_margin", "cash_conversion",
                "net_debt_to_ebitda", "interest_coverage", "payout_ratio")


def _aware(dt: datetime | None) -> datetime | None:
    return dt.replace(tzinfo=UTC) if dt is not None and dt.tzinfo is None else dt


def _years(days: list[date]) -> str:
    years = sorted({d.year for d in days})
    return str(years[0]) if len(years) == 1 else f"{years[0]}-{years[-1]}"


def _source_name(source: str | None) -> str:
    names = {"esef": "rapport officiel", "yahoo": "Yahoo"}
    return " puis ".join(names.get(s, s) for s in (source or "").split("+") if s)


def latest_row(accounts: ratios.Accounts,
               needed: tuple[str, ...]) -> tuple[dict[str, float], date, str] | None:
    """The most recent fiscal year where one source has every needed figure."""
    years = sorted({d for src in accounts.values() for d in src}, reverse=True)
    for day in years:
        for source in ratios.SOURCES:
            row = accounts.get(source, {}).get(day)
            if row and all(k in row for k in needed):
                return row, day, source
    return None


def analyze(session: Session, instrument: Instrument, benchmark: risk.Series | None) -> dict:
    """Everything we can say about an instrument from its data. Pure reading, no network except
    an exchange rate when the share trades in another currency than the accounts."""
    series = [(p.day, p.adj_close) for p in store.prices(session, instrument)]
    closes = [(p.day, p.close) for p in store.prices(session, instrument)]
    warnings: list[str] = []
    values: dict[str, tuple[float, str | None]] = {}
    info: dict[str, float | None] = {
        "return_1y": risk.total_return(series, 1), "return_3y": risk.total_return(series, 3),
        "return_5y": risk.total_return(series, 5),
    }
    beta = risk.beta(series, benchmark) if benchmark and instrument.isin != BENCHMARK_ISIN else None
    for key, value, detail in (("volatility", risk.volatility(series), "rendements quotidiens, 1 an"),
                               ("max_drawdown", risk.max_drawdown(series), "5 ans"),
                               ("beta", beta, "3 ans, hebdomadaire, face au MSCI Europe")):
        if value is not None:
            values[key] = (value, detail)

    is_financial = instrument.sector in FINANCIAL_SECTORS
    result: dict = {"isin": instrument.isin, "kind": instrument.kind, "sector": instrument.sector,
                    "is_financial": is_financial, "computed_at": utcnow().isoformat()}
    if instrument.kind != "stock":
        result.update(score=None, verdict="ETF : pas de note d'entreprise, seulement le risque de marché",
                      risk={k: v for k, (v, _) in values.items()}, info=info, warnings=warnings)
        return result

    accounts, currencies = store.fundamentals_by_source(session, instrument)
    yearly = ratios.yearly(accounts)

    # Quality: average of the last 3 years. Solidity: the latest year.
    for key in QUALITY_AVERAGED:
        mean, days = ratios.recent_mean(yearly[key])
        if mean is not None:
            sources = {yearly[key][d].source for d in days}
            names = " + ".join(_source_name(s) for s in sorted(sources))
            values[key] = (mean, f"moyenne {_years(days)}, {names}")
    for key in SOLIDITY_LATEST:
        if yearly[key]:
            day = max(yearly[key])
            point = yearly[key][day]
            values[key] = (point.value, f"exercice {day.year}, {_source_name(point.source)}")

    # Growth, each metric from a single source over time.
    revenue, rev_src = ratios.metric_series(accounts, "revenue")
    eps, eps_src = ratios.metric_series(accounts, "eps_diluted", prefer=("yahoo", "esef"), strict=True)
    dividends, _ = ratios.metric_series(accounts, "dividends_paid")
    for key, value, src, days in (("revenue_cagr", ratios.cagr(revenue), rev_src, list(revenue)[-6:]),
                                  ("revenue_recent", ratios.cagr(revenue, max_years=2), rev_src,
                                   list(revenue)[-3:]),
                                  ("eps_cagr", ratios.cagr(eps), eps_src, list(eps)[-6:]),
                                  ("revenue_consistency", ratios.growth_consistency(revenue), rev_src,
                                   list(revenue)[-6:])):
        if value is not None:
            values[key] = (value, f"{_years(days)}, {_source_name(src)}")
    info["dividend_cagr"] = ratios.cagr(dividends)

    # Valuation: today's market value against the latest accounts.
    valuation = _valuation(instrument, accounts, currencies, closes, warnings)
    for key in ("pe", "pe_vs_history", "fcf_yield", "ev_ebit", "pb", "dividend_yield"):
        if valuation.get(key) is not None:
            values[key] = (valuation[key], valuation.get("detail"))

    years = sorted({d for s in yearly.values() for d in s})[-6:]
    result["yearly"] = {"years": [d.isoformat() for d in years],
                        "rows": {k: [None if d not in yearly[k] else
                                     {"value": yearly[k][d].value, "source": yearly[k][d].source}
                                     for d in years] for k in YEARLY_SHOWN if yearly[k]}}
    if len(years) < 3:
        warnings.append("Moins de 3 années de comptes : les moyennes et les tendances sont fragiles.")
    if is_financial:
        warnings.append("Banque ou assurance : marges, dette et cash ne se lisent pas comme pour une "
                        "industrie ; la solidité (ratios de solvabilité) n'est pas disponible gratuitement.")
    result.update(scoring.score(values, is_financial), valuation=valuation, info=info, warnings=warnings,
                  risk={k: values[k][0] for k in ("volatility", "max_drawdown", "beta") if k in values})
    return result


def _valuation(instrument: Instrument, accounts: ratios.Accounts, currencies: dict[str, str],
               closes: list[tuple[date, float]], warnings: list[str]) -> dict:
    shares_series, _ = ratios.metric_series(accounts, "shares", prefer=("yahoo", "esef"), strict=True)
    if not closes or not shares_series:
        warnings.append("Nombre d'actions ou cours manquant : pas de valorisation.")
        return {}
    shares = shares_series[max(shares_series)]
    row = latest_row(accounts, ("net_income",))
    if row is None:
        return {}
    figures, day, source = row
    report_ccy = currencies.get(source) or instrument.currency or "EUR"
    try:
        fx = yahoo.fx_rate(instrument.currency or report_ccy, report_ccy)
    except SourceError as e:
        warnings.append(f"Taux de change indisponible ({e}) : pas de valorisation.")
        return {}
    price = closes[-1][1]
    market_cap = price * fx * shares
    out: dict = {"price": price, "currency": instrument.currency, "report_currency": report_ccy, "fx": fx,
                 "market_cap": market_cap, "fiscal_year": day.year,
                 "detail": f"cours du {closes[-1][0].strftime('%d/%m/%Y')}, comptes {day.year}"}
    if fx != 1:
        warnings.append(f"Cours en {instrument.currency}, comptes en {report_ccy} : conversion au taux "
                        f"du jour ({fx:.4f}).")
    rows = {r: latest_row(accounts, r) for r in (("net_income",), ("free_cash_flow",), ("dividends_paid",),
                                                  ("equity",), ("ebit", "total_debt", "cash"))}
    fcf_row = latest_row(ratios.with_derived(accounts), ("free_cash_flow",))
    ni = figures["net_income"]
    if ni > 0:
        out["pe"] = market_cap / ni
    else:
        warnings.append(f"Perte nette en {day.year} : le PER n'a pas de sens.")
    if fcf_row:
        out["fcf_yield"] = fcf_row[0]["free_cash_flow"] / market_cap
    if rows[("dividends_paid",)]:
        out["dividend_yield"] = rows[("dividends_paid",)][0]["dividends_paid"] / market_cap
    if rows[("equity",)] and rows[("equity",)][0]["equity"] > 0:
        out["pb"] = market_cap / rows[("equity",)][0]["equity"]
    ev_row = rows[("ebit", "total_debt", "cash")]
    if ev_row and ev_row[0]["ebit"] > 0:
        r = ev_row[0]
        out["enterprise_value"] = market_cap + r["total_debt"] - r["cash"]
        out["ev_ebit"] = out["enterprise_value"] / r["ebit"]

    # PER at each past fiscal year end, from one source (shares and profit of the same accounts).
    history = []
    for source in ("yahoo", "esef"):
        for year_end, r in sorted(accounts.get(source, {}).items()):
            past_price = risk.price_on(closes, year_end)
            if {"net_income", "shares"} <= r.keys() and r["net_income"] > 0 and past_price:
                history.append((year_end.year, past_price * fx * r["shares"] / r["net_income"]))
        if history:
            break
    out["pe_history"] = history
    if out.get("pe") and len(history) >= 3:
        out["pe_vs_history"] = out["pe"] / median(pe for _, pe in history)
    return out


# --- Cache ---------------------------------------------------------------------------------------

def _benchmark(session: Session) -> risk.Series | None:
    instrument = store.get_instrument(session, BENCHMARK_ISIN)
    return [(p.day, p.adj_close) for p in store.prices(session, instrument)] if instrument else None


def is_fresh(row: Analysis | None, instrument: Instrument) -> bool:
    if row is None:
        return False
    computed = _aware(row.computed_at)
    changes = [_aware(d) for d in (instrument.prices_updated_at, instrument.fundamentals_updated_at) if d]
    return utcnow() - computed < MAX_AGE and all(computed >= d for d in changes)


def get_analysis(session: Session, instrument: Instrument, benchmark: risk.Series | None = None,
                 force: bool = False) -> dict:
    row = session.scalar(select(Analysis).where(Analysis.instrument_id == instrument.id))
    if not force and is_fresh(row, instrument):
        return row.data
    data = analyze(session, instrument, benchmark if benchmark is not None else _benchmark(session))
    if row is None:
        row = Analysis(instrument_id=instrument.id, data=data)
        session.add(row)
    row.data, row.score, row.computed_at = data, data.get("score"), utcnow()
    session.commit()
    return data


def all_analyses(session: Session, force: bool = False) -> list[tuple[Instrument, dict]]:
    benchmark = _benchmark(session)
    out = []
    for instrument in store.list_instruments(session):
        try:
            out.append((instrument, get_analysis(session, instrument, benchmark, force)))
        except Exception:  # one broken instrument must not hide the whole ranking
            session.rollback()
            log.exception("Analysis of %s failed", instrument.isin)
    return out


def sector_medians(analyses: list[tuple[Instrument, dict]]) -> dict[str, dict[str, float]]:
    """Median of key metrics per sector, to put a company's figures in context."""
    keys = ("pe", "fcf_yield", "dividend_yield", "roic", "operating_margin", "revenue_cagr")
    by_sector: dict[str, dict[str, list[float]]] = {}
    for instrument, data in analyses:
        if instrument.kind != "stock" or not instrument.sector:
            continue
        for pillar in (data.get("pillars") or {}).values():
            for m in pillar["metrics"]:
                if m["key"] in keys and m["value"] is not None:
                    by_sector.setdefault(instrument.sector, {}).setdefault(m["key"], []).append(m["value"])
    return {s: {k: median(v) for k, v in metrics.items() if len(v) >= 2} for s, metrics in by_sector.items()}
