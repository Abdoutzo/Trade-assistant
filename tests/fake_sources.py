"""Fake answers of Yahoo, GLEIF, Euronext and filings.xbrl.org, shaped like the real ones."""
from __future__ import annotations

from datetime import UTC, datetime

import httpx

ISIN, SYMBOL, LEI = "FR0000120073", "AI.PA", "969500MMPQVHK671GT54"
ETF_ISIN, ETF_SYMBOL = "FR001400U5Q4", "DCAM.PA"


def ts(day: str) -> int:
    """Yahoo timestamps: market open in UTC (09:00 Paris = 07:00 or 08:00 UTC)."""
    return int(datetime.fromisoformat(day + "T07:00:00").replace(tzinfo=UTC).timestamp())


def chart(symbol: str, kind: str = "EQUITY") -> dict:
    days = ["2025-10-20", "2025-10-21", "2026-10-21", "2026-10-22"]
    return {"chart": {"result": [{
        "meta": {"currency": "EUR", "symbol": symbol, "exchangeName": "PAR", "instrumentType": kind,
                 "longName": "L'Air Liquide S.A." if kind == "EQUITY" else "Amundi PEA Monde",
                 "gmtoffset": 7200},
        "timestamp": [ts(d) for d in days],
        "indicators": {"quote": [{"close": [150.0, None, 170.0, 173.0], "volume": [1e6, None, 2e6, 3e6]}],
                       "adjclose": [{"adjclose": [145.0, None, 170.0, 173.0]}]},
    }]}}


def series(name: str, points: list[tuple[str, float]]) -> dict:
    return {"meta": {"symbol": [SYMBOL], "type": [name]},
            name: [{"asOfDate": d, "periodType": "12M", "currencyCode": "EUR", "reportedValue": {"raw": v}}
                   for d, v in points]}


TIMESERIES = {"timeseries": {"result": [
    series("annualTotalRevenue", [("2023-12-31", 27_607_600_000), ("2024-12-31", 27_057_800_000),
                                  ("2025-12-31", 26_940_200_000)]),
    series("annualNetIncomeCommonStockholders",
           [("2024-12-31", 3_400_000_000), ("2025-12-31", 3_517_900_000)]),
    series("annualCapitalExpenditure", [("2024-12-31", -3_525_100_000), ("2025-12-31", -3_843_400_000)]),
    series("annualDilutedEPS", [("2024-12-31", 5.2), ("2025-12-31", 6.08)]),
    series("annualStockholdersEquity", [("2025-12-31", 26_213_900_000)]),
    {"meta": {"symbol": [SYMBOL], "type": ["annualEBITDA"]}},  # a series with no data
]}}


def fact(concept: str, period: str, value: float, unit: str = "iso4217:EUR", **extra_dims) -> dict:
    return {"value": str(value), "decimals": -5,
            "dimensions": {"concept": concept, "entity": f"scheme:{LEI}", "period": period, "unit": unit,
                           **extra_dims}}


FY23 = "2023-01-01T00:00:00/2024-01-01T00:00:00"
FY24 = "2024-01-01T00:00:00/2025-01-01T00:00:00"
ESEF_2024 = {"documentInfo": {}, "facts": {
    "f1": fact("ifrs-full:RevenueFromContractsWithCustomers", FY24, 27_057_800_000),
    "f2": fact("ifrs-full:RevenueFromContractsWithCustomers", FY23, 27_607_600_000),
    "f3": fact("ifrs-full:ProfitLossAttributableToOwnersOfParent", FY24, 3_306_100_000),
    "f4": fact("ifrs-full:ProfitLoss", FY24, 3_500_000_000),  # less preferred concept
    "f5": fact("ifrs-full:EquityAttributableToOwnersOfParent", "2025-01-01T00:00:00", 26_860_000_000),
    # mid-year balance
    "f6": fact("ifrs-full:EquityAttributableToOwnersOfParent", "2024-07-01T00:00:00", 25_000_000_000),
    "f7": fact("ifrs-full:Revenue", FY24, 9_000_000_000, **{"ifrs-full:SegmentsAxis": "europe"}),  # a segment
    "f8": fact("ifrs-full:Revenue", "2024-07-01T00:00:00/2025-01-01T00:00:00", 13_000_000_000),  # half-year
    "f9": fact("ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities", FY24,
               -3_400_000_000),
    "f10": fact("ifrs-full:DilutedEarningsLossPerShare", FY24, 5.72, "iso4217:EUR/xbrli:shares"),
    "f11": fact("ifrs-full:DisclosureOfBorrowingsExplanatory", FY24, 0),  # text block, not ours
}}
ESEF_Q3 = {"facts": {  # a quarterly report filed in the same format: nothing annual inside
    "q1": fact("ifrs-full:Revenue", "2025-01-01T00:00:00/2025-10-01T00:00:00", 20_000_000_000),
    "q2": fact("ifrs-full:EquityAttributableToOwnersOfParent", "2025-10-01T00:00:00", 27_000_000_000),
}}
FILINGS = {"data": [
    {"attributes": {"period_end": "2024-12-31", "date_added": "2025-03-13", "json_url": "/x/old.json",
                    "viewer_url": "/x/old.html"}},
    {"attributes": {"period_end": "2024-12-31", "date_added": "2025-04-01", "json_url": "/x/2024.json",
                    "viewer_url": "/x/2024.html"}},
    {"attributes": {"period_end": "2025-09-30", "date_added": "2025-11-01", "json_url": "/x/q3.json"}},
    {"attributes": {"period_end": "2023-12-31", "date_added": "2024-03-01", "json_url": None}},  # failed
]}


GOOGLE_RSS = """<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>
<item><title>Air Liquide abaisse ses prévisions annuelles - Les Echos</title>
<link>https://news.google.com/rss/articles/warning</link><pubDate>{d1}</pubDate>
<source url="https://www.lesechos.fr">Les Echos</source></item>
<item><title>Air Liquide progresse de 0,8% - Boursorama</title>
<link>https://news.google.com/rss/articles/noise</link><pubDate>{d2}</pubDate>
<source url="https://www.boursorama.com">Boursorama</source></item>
<item><title>TotalEnergies signe un contrat géant - Reuters</title>
<link>https://news.google.com/rss/articles/other-company</link><pubDate>{d2}</pubDate>
<source url="https://www.reuters.com">Reuters</source></item>
</channel></rss>"""
YAHOO_RSS = """<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>
<item><title>Air Liquide : 4 milliards d'euros de rachats d'actions</title>
<link>https://www.capital.fr/air-liquide-rachats</link><pubDate>{d2}</pubDate>
<description>Le géant des gaz industriels annonce un programme de rachat d'actions.</description></item>
<item><title>Air Liquide abaisse ses prévisions annuelles</title>
<link>https://www.capital.fr/duplicate</link><pubDate>{d2}</pubDate>
<description>Même nouvelle, autre site.</description></item>
</channel></rss>"""


def _rfc822(days_ago: int) -> str:
    from datetime import timedelta
    from email.utils import format_datetime

    return format_datetime(datetime.now(UTC) - timedelta(days=days_ago))


def handler(request: httpx.Request) -> httpx.Response:
    url, q = request.url, request.url.params
    if url.host == "news.google.com":
        return httpx.Response(200, text=GOOGLE_RSS.format(d1=_rfc822(1), d2=_rfc822(3)))
    if url.host == "feeds.finance.yahoo.com":
        return httpx.Response(200, text=YAHOO_RSS.format(d2=_rfc822(2)))
    if url.host == "query2.finance.yahoo.com":
        if url.path == "/v1/finance/search":
            if q["q"] == ISIN:
                return httpx.Response(200, json={"quotes": [
                    {"symbol": "AIL.DE", "quoteType": "EQUITY", "exchange": "GER", "longname": "Air Liquide"},
                    {"symbol": SYMBOL, "quoteType": "EQUITY", "exchange": "PAR",
                     "longname": "L'Air Liquide S.A.", "sector": "Basic Materials",
                     "industry": "Specialty Chemicals"},
                    {"symbol": "X.SG", "quoteType": "MUTUALFUND", "exchange": "STU"}]})
            return httpx.Response(200, json={"quotes": []})
        if url.path == f"/v8/finance/chart/{SYMBOL}":
            return httpx.Response(200, json=chart(SYMBOL))
        if url.path == f"/v8/finance/chart/{ETF_SYMBOL}":
            return httpx.Response(200, json=chart(ETF_SYMBOL, "ETF"))
        if url.path == f"/ws/fundamentals-timeseries/v1/finance/timeseries/{SYMBOL}":
            return httpx.Response(200, json=TIMESERIES)
    if url.host == "api.gleif.org":
        if q.get("filter[isin]") == ISIN:
            return httpx.Response(200, json={"data": [{"id": LEI, "attributes": {"entity": {
                "legalName": {"name": "L'AIR LIQUIDE SA"}, "legalAddress": {"country": "FR"}}}}]})
        return httpx.Response(200, json={"data": []})
    if url.host == "filings.xbrl.org":
        if url.path == f"/api/entities/{LEI}/filings":
            return httpx.Response(200, json=FILINGS)
        if url.path == "/x/2024.json":
            return httpx.Response(200, json=ESEF_2024)
        if url.path == "/x/q3.json":
            return httpx.Response(200, json=ESEF_Q3)
    if url.host == "live.euronext.com":
        return httpx.Response(200, json=[])
    return httpx.Response(404)


def fake_client(fn=handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(fn))
