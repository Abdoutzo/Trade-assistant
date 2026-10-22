"""Yahoo Finance (unofficial, free, no key): ISIN search, daily prices, standardised annual accounts.

Unofficial means it can change or throttle without notice: every call goes through http.get_json
(retries), and the official reports (esef.py) cross-check the accounts.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from .http import SourceError, get_json

BASE = "https://query2.finance.yahoo.com"

# Preferred listing when a share trades in several places: its home market in euros first.
EXCHANGE_PREFERENCE = ["PAR", "AMS", "GER", "MIL", "MCE", "BRU", "LIS", "DUB", "HEL", "CPH", "STO", "OSL",
                       "VIE", "FRA"]


@dataclass(frozen=True)
class Quote:
    symbol: str
    name: str
    kind: str  # "stock" or "etf"
    exchange: str | None
    sector: str | None = None
    industry: str | None = None


def search(query: str) -> list[Quote]:
    """Listings matching an ISIN, a ticker or a name; only shares and ETFs, home market first."""
    data = get_json(f"{BASE}/v1/finance/search", {"q": query, "quotesCount": 10, "newsCount": 0})
    quotes = []
    for q in data.get("quotes", []):
        kind = {"EQUITY": "stock", "ETF": "etf"}.get(q.get("quoteType", ""))
        if not kind or not q.get("symbol"):
            continue
        quotes.append(Quote(symbol=q["symbol"], name=q.get("longname") or q.get("shortname") or q["symbol"],
                            kind=kind, exchange=q.get("exchange"), sector=q.get("sector"),
                            industry=q.get("industry")))
    rank = {ex: i for i, ex in enumerate(EXCHANGE_PREFERENCE)}
    return sorted(quotes, key=lambda q: rank.get(q.exchange or "", len(rank)))


@dataclass(frozen=True)
class PriceRow:
    day: date
    close: float
    adj_close: float
    volume: float | None


@dataclass(frozen=True)
class Chart:
    symbol: str
    name: str | None
    currency: str | None
    exchange: str | None
    kind: str | None
    rows: list[PriceRow]


def chart(symbol: str, range_: str = "10y") -> Chart:
    """Daily prices over a range (1mo, 3mo, 1y, 5y, 10y, max)."""
    data = get_json(f"{BASE}/v8/finance/chart/{symbol}", {"range": range_, "interval": "1d"})
    result = (data.get("chart") or {}).get("result")
    if not result:
        raise SourceError(f"Yahoo has no prices for {symbol}")
    r = result[0]
    meta = r.get("meta", {})
    offset = timedelta(seconds=meta.get("gmtoffset") or 0)  # timestamps are UTC, the day is local
    quote = (r.get("indicators", {}).get("quote") or [{}])[0]
    adj = (r.get("indicators", {}).get("adjclose") or [{}])[0].get("adjclose") or quote.get("close", [])
    rows = []
    for ts, close, adj_close, volume in zip(r.get("timestamp") or [], quote.get("close", []), adj,
                                            quote.get("volume", []), strict=False):
        if close is None:
            continue  # holiday or suspended session
        day = (datetime.fromtimestamp(ts, UTC) + offset).date()
        rows.append(PriceRow(day, float(close), float(adj_close if adj_close is not None else close),
                             float(volume) if volume is not None else None))
    kind = {"EQUITY": "stock", "ETF": "etf"}.get(meta.get("instrumentType", ""))
    return Chart(symbol=symbol, name=meta.get("longName") or meta.get("shortName"),
                 currency=meta.get("currency"), exchange=meta.get("exchangeName"), kind=kind, rows=rows)


# Our metric name -> Yahoo series. Spending (capex, dividends) is stored as a positive amount.
FUNDAMENTALS = {
    "revenue": "TotalRevenue",
    "gross_profit": "GrossProfit",
    "operating_income": "OperatingIncome",
    "ebit": "EBIT",
    "ebitda": "EBITDA",
    "pretax_income": "PretaxIncome",
    "tax_provision": "TaxProvision",
    "net_income": "NetIncomeCommonStockholders",
    "eps_diluted": "DilutedEPS",
    "interest_expense": "InterestExpense",
    "operating_cash_flow": "OperatingCashFlow",
    "capex": "CapitalExpenditure",
    "free_cash_flow": "FreeCashFlow",
    "dividends_paid": "CashDividendsPaid",
    "equity": "StockholdersEquity",
    "total_assets": "TotalAssets",
    "current_assets": "CurrentAssets",
    "current_liabilities": "CurrentLiabilities",
    "total_debt": "TotalDebt",
    "cash": "CashAndCashEquivalents",
    "invested_capital": "InvestedCapital",
    "shares": "OrdinarySharesNumber",
}
POSITIVE = {"capex", "dividends_paid"}


@dataclass(frozen=True)
class Figure:
    period_end: date
    metric: str
    value: float
    currency: str | None


def fundamentals(symbol: str) -> list[Figure]:
    """Annual accounts, usually the last 4 fiscal years, in the reporting currency."""
    types = ",".join("annual" + series for series in FUNDAMENTALS.values())
    data = get_json(f"{BASE}/ws/fundamentals-timeseries/v1/finance/timeseries/{symbol}",
                    {"type": types, "period1": 946684800, "period2": int(datetime.now(UTC).timestamp())})
    metric_of = {"annual" + series: metric for metric, series in FUNDAMENTALS.items()}
    figures = []
    for result in (data.get("timeseries") or {}).get("result") or []:
        series = (result.get("meta", {}).get("type") or [None])[0]
        metric = metric_of.get(series)
        if not metric:
            continue
        for point in result.get(series) or []:
            raw = ((point or {}).get("reportedValue") or {}).get("raw")
            if raw is None or not point.get("asOfDate"):
                continue
            value = abs(float(raw)) if metric in POSITIVE else float(raw)
            figures.append(Figure(date.fromisoformat(point["asOfDate"]), metric, value,
                                  point.get("currencyCode")))
    return figures


_fx_cache: dict[tuple[str, str, date], float] = {}


def fx_rate(from_ccy: str, to_ccy: str) -> float:
    """How many to_ccy for 1 from_ccy (latest close), e.g. EUR -> USD for a company reporting in dollars."""
    if from_ccy == to_ccy:
        return 1.0
    key = (from_ccy, to_ccy, date.today())
    if key not in _fx_cache:
        rows = chart(f"{from_ccy}{to_ccy}=X", "5d").rows
        if not rows:
            raise SourceError(f"Pas de taux de change {from_ccy}/{to_ccy}")
        _fx_cache[key] = rows[-1].close
    return _fx_cache[key]
