"""Euronext instrument search: ISIN -> ticker when Yahoo's search does not know the ISIN."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .http import get_json

# Euronext market (MIC) -> suffix of the Yahoo ticker.
YAHOO_SUFFIX = {"XPAR": ".PA", "XAMS": ".AS", "XBRU": ".BR", "XLIS": ".LS", "XMIL": ".MI", "MTAA": ".MI",
                "XDUB": ".IR", "XOSL": ".OL", "ETLX": ".MI"}


@dataclass(frozen=True)
class Listing:
    isin: str
    symbol: str  # Euronext ticker, e.g. DCAM
    mic: str
    name: str

    @property
    def yahoo_symbol(self) -> str | None:
        suffix = YAHOO_SUFFIX.get(self.mic)
        return self.symbol + suffix if suffix else None


def _text(html: str, css_class: str) -> str:
    m = re.search(rf"class='{css_class}'>(?:<a[^>]*>)?([^<]+)", html)
    return m.group(1).strip() if m else ""


def search(isin: str) -> list[Listing]:
    rows = get_json("https://live.euronext.com/en/instrumentSearch/searchJSON", {"q": isin})
    listings = []
    for row in rows or []:
        if row.get("isin", "").upper() != isin.upper():
            continue
        label = row.get("label", "")
        symbol = _text(label, "symbol")
        if symbol:
            listings.append(Listing(isin=row["isin"], symbol=symbol, mic=row.get("mic", ""),
                                    name=_text(label, "name")))
    return listings
