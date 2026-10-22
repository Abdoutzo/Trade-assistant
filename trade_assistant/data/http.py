"""One HTTP client for every data source: browser-like identity, timeouts, polite retries."""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

log = logging.getLogger(__name__)

# Yahoo answers 429 to library user agents and, oddly, to full browser ones (no cookies): the
# short generic form is the one it accepts. The other sources do not care.
USER_AGENT = "Mozilla/5.0"
RETRY_STATUSES = {429, 500, 502, 503, 504}

_client: httpx.Client | None = None


def client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=httpx.Timeout(30, read=120),
                               follow_redirects=True)
    return _client


def set_client(c: httpx.Client | None) -> None:
    """Tests plug a client with a fake transport here: no test ever touches the network."""
    global _client
    _client = c


class SourceError(RuntimeError):
    pass


class NotFoundError(SourceError):
    """HTTP 404: the source does not know this item (not an outage)."""


def get_json(url: str, params: dict[str, Any] | None = None, tries: int = 3) -> Any:
    """GET a JSON document; waits 2 s, then 4 s, after a 429 or a server error."""
    for attempt in range(tries):
        try:
            r = client().get(url, params=params)
        except httpx.TransportError as e:
            error: str = f"{type(e).__name__}: {e}"
        else:
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                raise NotFoundError(f"HTTP 404 on {r.request.url}")
            if r.status_code not in RETRY_STATUSES:
                raise SourceError(f"HTTP {r.status_code} on {r.request.url}")
            error = f"HTTP {r.status_code}"
        if attempt < tries - 1:
            log.info("%s on %s, retrying", error, url)
            time.sleep(2 ** (attempt + 1))
    raise SourceError(f"{error} on {url} after {tries} tries")
