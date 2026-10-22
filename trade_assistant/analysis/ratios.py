"""Yearly ratios from the annual accounts.

One ratio never mixes two sources: ASML's official report follows IFRS while Yahoo shows its US GAAP
accounts, and dividing an IFRS profit by a US GAAP equity would mean nothing. For each year, a
ratio uses the official report if it has every input, Yahoo otherwise.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

# accounts[source][period_end][metric] = value
Accounts = dict[str, dict[date, dict[str, float]]]
SOURCES = ("esef", "yahoo")


def with_derived(accounts: Accounts) -> Accounts:
    """Adds free cash flow (operating cash flow - capex) where a source lacks it."""
    out: Accounts = {}
    for source, years in accounts.items():
        out[source] = {}
        for day, row in years.items():
            row = dict(row)
            if "free_cash_flow" not in row and {"operating_cash_flow", "capex"} <= row.keys():
                row["free_cash_flow"] = row["operating_cash_flow"] - row["capex"]
            out[source][day] = row
    return out


def _div(a: float, b: float) -> float | None:
    return a / b if b else None


def _tax_rate(r: dict[str, float]) -> float:
    """Effective tax rate, bounded: a one-off tax gain or loss would distort the ROIC."""
    rate = _div(r.get("tax_provision", 0.0), r.get("pretax_income", 0.0))
    return 0.25 if rate is None else min(max(rate, 0.0), 0.40)


@dataclass(frozen=True)
class Ratio:
    inputs: tuple[str, ...]
    compute: Callable[[dict[str, float]], float | None]


RATIOS: dict[str, Ratio] = {
    "roic": Ratio(("operating_income", "invested_capital"),
                  lambda r: _div(r["operating_income"] * (1 - _tax_rate(r)), r["invested_capital"])),
    "roe": Ratio(("net_income", "equity"),
                 lambda r: _div(r["net_income"], r["equity"]) if r["equity"] > 0 else None),
    "gross_margin": Ratio(("gross_profit", "revenue"), lambda r: _div(r["gross_profit"], r["revenue"])),
    "operating_margin": Ratio(("operating_income", "revenue"),
                              lambda r: _div(r["operating_income"], r["revenue"])),
    "net_margin": Ratio(("net_income", "revenue"), lambda r: _div(r["net_income"], r["revenue"])),
    "fcf_margin": Ratio(("free_cash_flow", "revenue"), lambda r: _div(r["free_cash_flow"], r["revenue"])),
    "cash_conversion": Ratio(("free_cash_flow", "net_income"),
                             lambda r: _div(r["free_cash_flow"], r["net_income"]) if r["net_income"] > 0
                             else None),
    "net_debt_to_ebitda": Ratio(("total_debt", "cash", "ebitda"),
                                lambda r: _div(r["total_debt"] - r["cash"], r["ebitda"]) if r["ebitda"] > 0
                                else None),
    "interest_coverage": Ratio(("ebit", "interest_expense"),
                               lambda r: _div(r["ebit"], abs(r["interest_expense"]))),
    "current_ratio": Ratio(("current_assets", "current_liabilities"),
                           lambda r: _div(r["current_assets"], r["current_liabilities"])),
    "equity_ratio": Ratio(("equity", "total_assets"), lambda r: _div(r["equity"], r["total_assets"])),
    "payout_ratio": Ratio(("dividends_paid", "net_income"),
                          lambda r: _div(r["dividends_paid"], r["net_income"]) if r["net_income"] > 0
                          else None),
}


@dataclass(frozen=True)
class Point:
    value: float
    source: str


def yearly(accounts: Accounts) -> dict[str, dict[date, Point]]:
    """Every ratio for every fiscal year, each computed inside a single source."""
    accounts = with_derived(accounts)
    years = sorted({d for src in accounts.values() for d in src})
    out: dict[str, dict[date, Point]] = {name: {} for name in RATIOS}
    for name, ratio in RATIOS.items():
        for day in years:
            for source in SOURCES:
                row = accounts.get(source, {}).get(day)
                if row and all(k in row for k in ratio.inputs):
                    value = ratio.compute(row)
                    if value is not None:
                        out[name][day] = Point(value, source)
                    break  # the first source with all inputs decides, even if the ratio is undefined
    return out


def recent_mean(series: dict[date, Point], years: int = 3) -> tuple[float | None, list[date]]:
    """Average of the last N fiscal years: one exceptional year should not make the verdict."""
    days = sorted(series)[-years:]
    if not days:
        return None, []
    return sum(series[d].value for d in days) / len(days), days


def metric_series(accounts: Accounts, metric: str, prefer: tuple[str, ...] = SOURCES,
                  strict: bool = False, tolerance: float = 0.03) -> tuple[dict[date, float], str | None]:
    """A metric over time, as consistent as possible.

    Base: the source with the most years (or, if strict, the first preferred source that has the
    metric, for per-share figures that must never mix). Then, if the other source agrees with it
    within 3 % on every common year, its MORE RECENT years extend the series: the official reports
    often stop a year earlier than Yahoo, and a trend that misses the latest year can be wrong.
    """
    counts = {src: sum(1 for row in accounts.get(src, {}).values() if metric in row) for src in prefer}
    available = [src for src in prefer if counts[src]]
    if not available:
        return {}, None
    base = available[0] if strict else max(available, key=lambda src: (counts[src], -prefer.index(src)))
    series = {d: row[metric] for d, row in accounts[base].items() if metric in row}
    label = base
    if not strict:
        for other in available:
            if other == base:
                continue
            extra = {d: row[metric] for d, row in accounts[other].items() if metric in row}
            common = series.keys() & extra.keys()
            agree = common and all(series[d] and abs(extra[d] - series[d]) / abs(series[d]) <= tolerance
                                   for d in common)
            later = {d: v for d, v in extra.items() if d > max(series)}
            if agree and later:
                series.update(later)
                label = f"{base}+{other}"
    return dict(sorted(series.items())), label


def cagr(series: dict[date, float], max_years: int = 5) -> float | None:
    """Compound annual growth between the oldest and latest of the last max_years+1 points."""
    days = sorted(series)[-(max_years + 1):]
    if len(days) < 3:
        return None  # two points are an anecdote, not a trend
    first, last = series[days[0]], series[days[-1]]
    span = (days[-1] - days[0]).days / 365.25
    if first <= 0 or last <= 0 or span < 1:
        return None
    return (last / first) ** (1 / span) - 1


def growth_consistency(series: dict[date, float]) -> float | None:
    """Share of years where the metric grew."""
    values = [series[d] for d in sorted(series)][-6:]
    if len(values) < 3:
        return None
    ups = sum(1 for a, b in zip(values, values[1:], strict=False) if b > a)
    return ups / (len(values) - 1)
