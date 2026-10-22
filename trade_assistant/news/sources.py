"""Free news feeds: Google News search (French and English) and Yahoo Finance RSS per ticker."""
from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote

from ..data.http import SourceError, client

# Company names as the press writes them, when the legal name is far from it.
SEARCH_NAMES = {
    "FR0000121014": "LVMH", "FR0000052292": "Hermès", "ES0148396007": "Inditex", "BE0974293251": "AB InBev",
    "DE0008430026": "Munich Re", "FR0000120073": "Air Liquide", "FR0000121667": "EssilorLuxottica",
    "FR0000120321": "L'Oréal", "FR0000131104": "BNP Paribas", "FR0000120628": "AXA",
    "DE0007236101": "Siemens", "NL0000235190": "Airbus", "IT0000072618": "Intesa Sanpaolo",
}
LEGAL_SUFFIXES = re.compile(
    r"[,\s]+(S\.?A\.?(/NV)?|S\.?E\.?|N\.?V\.?|AG|S\.?p\.?A\.?|A/S|Oyj|plc"
    r"|Aktiengesellschaft.*|Société.*|Holding.*)$",
    re.IGNORECASE)


def search_name(isin: str, name: str) -> str:
    """'ASML Holding N.V.' -> 'ASML'; legal forms and long descriptions removed."""
    if isin in SEARCH_NAMES:
        return SEARCH_NAMES[isin]
    short = name.split(" - ")[0]
    for _ in range(3):
        short = LEGAL_SUFFIXES.sub("", short).strip()
    return short


@dataclass(frozen=True)
class Article:
    url: str
    title: str
    source: str | None
    published_at: datetime
    lang: str
    snippet: str | None


def _text(element: ET.Element | None) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", (element.text or "") if element is not None else "")).strip()


def _get(url: str) -> bytes:
    try:
        r = client().get(url)
    except Exception as e:  # network errors of any kind: the source is unavailable
        raise SourceError(f"{type(e).__name__} on {url}") from e
    if r.status_code != 200:
        raise SourceError(f"HTTP {r.status_code} on {url}")
    return r.content


def parse_rss(content: bytes, lang: str, google: bool) -> list[Article]:
    articles = []
    for item in ET.fromstring(content).findall("./channel/item"):
        title, link = _text(item.find("title")), _text(item.find("link"))
        try:
            published = parsedate_to_datetime(_text(item.find("pubDate"))).astimezone(UTC)
        except (TypeError, ValueError):
            continue
        source = _text(item.find("source")) or None
        if google and source and title.endswith(f" - {source}"):
            title = title[: -len(source) - 3]  # Google appends " - Publisher"
        snippet = None if google else (_text(item.find("description"))[:600] or None)
        if title and link:
            articles.append(Article(link, title, source, published, lang, snippet))
    return articles


def google_news(name: str, lang: str = "fr", days: int = 30) -> list[Article]:
    region = {"fr": ("fr", "FR", "FR:fr"), "en": ("en-US", "US", "US:en")}[lang]
    query = quote(f'"{name}" when:{days}d')
    url = f"https://news.google.com/rss/search?q={query}&hl={region[0]}&gl={region[1]}&ceid={region[2]}"
    return parse_rss(_get(url), lang, google=True)


def yahoo_rss(symbol: str) -> list[Article]:
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={quote(symbol)}&region=FR&lang=fr-FR"
    return parse_rss(_get(url), "fr", google=False)


def relevant(article: Article, name: str, symbol: str) -> bool:
    """Keeps articles that actually name the company (search engines are generous)."""
    text = f"{article.title} {article.snippet or ''}".lower()
    words = [w for w in re.split(r"[\s']+", name.lower()) if len(w) > 2] or [name.lower()]
    ticker = symbol.split(".")[0].lower()
    return name.lower() in text or all(w in text for w in words) or ticker in text.split()


def collect(isin: str, name: str, symbol: str, per_source: int = 25) -> tuple[list[Article], list[str]]:
    """Every source, newest first, deduplicated by title; errors reported, never raised."""
    query = search_name(isin, name)
    found: list[Article] = []
    errors: list[str] = []
    for label, fetch in (("Google Actualités (fr)", lambda: google_news(query, "fr")),
                         ("Google News (en)", lambda: google_news(query, "en")),
                         ("Yahoo Finance", lambda: yahoo_rss(symbol))):
        try:
            found += sorted(fetch(), key=lambda a: a.published_at, reverse=True)[:per_source]
        except (SourceError, ET.ParseError) as e:
            errors.append(f"{label} : {e}")
    seen, unique = set(), []
    for a in sorted(found, key=lambda a: a.published_at, reverse=True):
        key = re.sub(r"\W+", "", a.title.lower())[:80]
        if key not in seen and relevant(a, query, symbol):
            seen.add(key)
            unique.append(a)
    return unique, errors
