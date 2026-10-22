"""Official annual reports of EU listed companies (ESEF), read from filings.xbrl.org.

Since 2020 every company listed in the EU must publish its accounts in a machine-readable format
(XBRL, IFRS taxonomy). filings.xbrl.org collects them and converts each one to JSON. These are the
audited figures, the reference: Yahoo only complements and cross-checks them.

Each report gives the current year and the previous one; a later report can restate a year, and
then its figures win.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .http import get_json
from .yahoo import Figure

BASE = "https://filings.xbrl.org"

# Our metric -> IFRS concepts, in order of preference. Companies choose among equivalent concepts
# and sometimes use their own extension instead: a missing figure is then taken from Yahoo.
CONCEPTS: dict[str, list[str]] = {
    "revenue": ["ifrs-full:Revenue", "ifrs-full:RevenueFromContractsWithCustomers"],
    "gross_profit": ["ifrs-full:GrossProfit"],
    "operating_income": ["ifrs-full:ProfitLossFromOperatingActivities"],
    "pretax_income": ["ifrs-full:ProfitLossBeforeTax"],
    "tax_provision": ["ifrs-full:IncomeTaxExpenseContinuingOperations"],
    "net_income": ["ifrs-full:ProfitLossAttributableToOwnersOfParent", "ifrs-full:ProfitLoss"],
    "eps_diluted": ["ifrs-full:DilutedEarningsLossPerShare", "ifrs-full:BasicEarningsLossPerShare"],
    "operating_cash_flow": ["ifrs-full:CashFlowsFromUsedInOperatingActivities"],
    "capex": ["ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
              "ifrs-full:PurchaseOfPropertyPlantAndEquipment"],
    "dividends_paid": ["ifrs-full:DividendsPaidToEquityHoldersOfParentClassifiedAsFinancingActivities",
                       "ifrs-full:DividendsPaidClassifiedAsFinancingActivities", "ifrs-full:DividendsPaid"],
    "equity": ["ifrs-full:EquityAttributableToOwnersOfParent", "ifrs-full:Equity"],
    "total_assets": ["ifrs-full:Assets"],
    "current_assets": ["ifrs-full:CurrentAssets"],
    "current_liabilities": ["ifrs-full:CurrentLiabilities"],
    "cash": ["ifrs-full:CashAndCashEquivalents"],
}
POSITIVE = {"capex", "dividends_paid"}
BASE_DIMENSIONS = {"concept", "entity", "period", "unit"}


@dataclass(frozen=True)
class Filing:
    period_end: date
    json_url: str
    viewer_url: str | None


def filings(lei: str) -> list[Filing]:
    """Annual reports of a company, oldest first, keeping one per fiscal year (the latest filed)."""
    data = get_json(f"{BASE}/api/entities/{lei}/filings")
    by_year: dict[date, tuple[str, Filing]] = {}
    for item in data.get("data") or []:
        a = item.get("attributes", {})
        if not a.get("json_url") or not a.get("period_end"):
            continue  # not converted (yet), or invalid
        filing = Filing(date.fromisoformat(a["period_end"]), BASE + a["json_url"],
                        BASE + a["viewer_url"] if a.get("viewer_url") else None)
        added = a.get("date_added") or a.get("processed") or ""
        if filing.period_end not in by_year or added > by_year[filing.period_end][0]:
            by_year[filing.period_end] = (added, filing)
    return [f for _, f in sorted(by_year.values(), key=lambda x: x[1].period_end)]


def _period(text: str) -> tuple[date, int] | None:
    """'2023-01-01T00:00:00/2024-01-01T00:00:00' -> (2023-12-31, 365 days); an instant -> (day, 0).

    xBRL-JSON writes a period end as the start of the next day, hence the minus one day.
    """
    def parse(t: str) -> date:
        d = datetime.fromisoformat(t)
        return (d - timedelta(days=1)).date() if len(t) > 10 and d.time() == datetime.min.time() else d.date()

    try:
        if "/" in text:
            start, end = text.split("/")
            s, e = datetime.fromisoformat(start).date(), parse(end)
            return e, (e - s).days + 1
        return parse(text), 0
    except ValueError:
        return None


def read(document: dict) -> list[Figure]:
    """Extract our metrics from an xBRL-JSON report: whole-company, full fiscal years only.

    Some companies also file their quarterly reports in this format. They contain no 12-month
    figure, so they yield nothing; and a balance sheet figure (an instant) is kept only on a fiscal
    year end, the day a 12-month figure of the same report ends.
    """
    preference = {concept: (metric, rank)
                  for metric, concepts in CONCEPTS.items() for rank, concept in enumerate(concepts)}
    candidates: list[tuple[date, int, str, int, float, str | None]] = []
    year_ends: set[tuple[int, int]] = set()
    for fact in (document.get("facts") or {}).values():
        dims = fact.get("dimensions", {})
        concept = dims.get("concept")
        if concept not in preference or set(dims) != BASE_DIMENSIONS:
            continue  # unknown concept, or a breakdown (segment, country...) rather than the total
        period = _period(dims.get("period", ""))
        if not period:
            continue
        period_end, days = period
        if days and not 350 <= days <= 380:
            continue  # quarter, half-year or year-to-date figure
        if days:
            year_ends.add((period_end.month, period_end.day))
        try:
            value = float(fact["value"])
        except (KeyError, TypeError, ValueError):
            continue
        metric, rank = preference[concept]
        unit = dims.get("unit", "")
        currency = unit.split(":")[1].split("/")[0] if unit.startswith("iso4217:") else None
        candidates.append((period_end, days, metric, rank, value, currency))

    found: dict[tuple[date, str], tuple[int, Figure]] = {}
    for period_end, days, metric, rank, value, currency in candidates:
        if not days and (period_end.month, period_end.day) not in year_ends:
            continue  # balance sheet at a quarter end
        figure = Figure(period_end, metric, abs(value) if metric in POSITIVE else value, currency)
        key = (period_end, metric)
        if key not in found or rank < found[key][0]:
            found[key] = (rank, figure)
    return [figure for _, figure in found.values()]


def download(filing: Filing) -> list[Figure]:
    return read(get_json(filing.json_url))
