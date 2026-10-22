"""API of brick 1: the universe of instruments, their prices and annual accounts."""
from __future__ import annotations

import logging
import threading
from datetime import date, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import auth
from .data import store, universe
from .data.http import SourceError
from .db import get_engine, get_session
from .models import EsefFiling, Instrument

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", dependencies=[Depends(auth.require_auth)])

PERIODS = {"1m": 31, "6m": 183, "1y": 365, "3y": 3 * 365, "5y": 5 * 365, "10y": 3660}


def _instrument_or_404(session: Session, isin: str) -> Instrument:
    instrument = store.get_instrument(session, isin)
    if not instrument:
        raise HTTPException(404, f"{isin} n'est pas dans l'univers")
    return instrument


def _summary(session: Session, i: Instrument) -> dict:
    series = store.prices(session, i, since=date.today() - timedelta(days=400))
    last = series[-1] if series else None
    year_ago = next((p for p in reversed(series) if last and (last.day - p.day).days >= 365), None)
    return {
        "isin": i.isin, "symbol": i.symbol, "name": i.name, "kind": i.kind, "currency": i.currency,
        "exchange": i.exchange, "country": i.country, "sector": i.sector, "industry": i.industry,
        "pea_eligible": i.pea_eligible, "pea_reason": i.pea_reason,
        "last_close": last.close if last else None, "last_day": last.day.isoformat() if last else None,
        "change_1y": (last.adj_close / year_ago.adj_close - 1) if last and year_ago else None,
        "prices_updated_at": i.prices_updated_at, "fundamentals_updated_at": i.fundamentals_updated_at,
    }


@router.get("/instruments")
def list_instruments(session: Session = Depends(get_session)) -> list[dict]:
    return [_summary(session, i) for i in store.list_instruments(session)]


class AddRequest(BaseModel):
    isin: str


@router.post("/instruments")
def add_instrument(body: AddRequest, background: BackgroundTasks,
                   session: Session = Depends(get_session)) -> dict:
    """Identify the ISIN and load its prices now; the annual reports (slower) load in background."""
    try:
        instrument = store.add_instrument(session, body.isin)
        store.refresh_prices(session, instrument)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except SourceError as e:
        raise HTTPException(502, f"Source de données indisponible : {e}") from e
    if instrument.kind == "stock":
        background.add_task(_refresh_fundamentals, instrument.isin)
    return _summary(session, instrument)


def _refresh_fundamentals(isin: str) -> None:
    with Session(get_engine()) as session:
        instrument = store.get_instrument(session, isin)
        if instrument:
            store.refresh_fundamentals(session, instrument)


@router.get("/instruments/{isin}")
def instrument_detail(isin: str, session: Session = Depends(get_session)) -> dict:
    i = _instrument_or_404(session, isin)
    table = store.fundamentals_table(session, i)
    years = [d.isoformat() for d in table]
    metrics = sorted({m for row in table.values() for m in row})
    rows = {m: [None if (c := table[d].get(m)) is None else
                {"value": c.value, "source": c.source, "url": c.source_url, "currency": c.currency,
                 "other_value": c.other_value, "gap": c.gap} for d in table] for m in metrics}
    filings = session.query(EsefFiling).filter(EsefFiling.instrument_id == i.id, EsefFiling.facts_found > 0) \
        .order_by(EsefFiling.period_end.desc()).all()
    return {**_summary(session, i), "lei": i.lei, "years": years, "fundamentals": rows,
            "reports": [{"period_end": f.period_end.isoformat(), "url": f.viewer_url or f.json_url}
                        for f in filings]}


@router.get("/instruments/{isin}/prices")
def instrument_prices(isin: str, period: str = "1y", session: Session = Depends(get_session)) -> list[dict]:
    if period not in PERIODS:
        raise HTTPException(422, f"Période inconnue, choisis parmi {', '.join(PERIODS)}")
    i = _instrument_or_404(session, isin)
    series = store.prices(session, i, since=date.today() - timedelta(days=PERIODS[period]))
    return [{"day": p.day.isoformat(), "close": p.close, "adj_close": p.adj_close} for p in series]


@router.post("/instruments/{isin}/refresh")
def refresh_instrument(isin: str, background: BackgroundTasks,
                       session: Session = Depends(get_session)) -> dict:
    i = _instrument_or_404(session, isin)
    try:
        store.refresh_prices(session, i)
    except SourceError as e:
        raise HTTPException(502, f"Source de données indisponible : {e}") from e
    if i.kind == "stock":
        background.add_task(_refresh_fundamentals, i.isin)
    return _summary(session, i)


@router.delete("/instruments/{isin}")
def delete_instrument(isin: str, session: Session = Depends(get_session)) -> dict:
    store.remove_instrument(session, _instrument_or_404(session, isin))
    return {"deleted": isin}


# --- Loading the starting universe from the website (no terminal needed) ------------------------

class _Job:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.running = False
        self.done = 0
        self.total = 0
        self.current: str | None = None
        self.errors: list[str] = []

    def state(self) -> dict:
        return {"running": self.running, "done": self.done, "total": self.total, "current": self.current,
                "errors": self.errors[-20:]}


seed_job = _Job()


def _run_seed() -> None:
    with Session(get_engine()) as session:
        for isin in universe.SEED:
            seed_job.current = isin
            try:
                instrument = store.get_instrument(session, isin) or store.add_instrument(session, isin)
                store.refresh_prices(session, instrument)
                if instrument.kind == "stock" and store.is_stale(instrument.fundamentals_updated_at,
                                                                 timedelta(days=7)):
                    result = store.refresh_fundamentals(session, instrument)
                    seed_job.errors += [f"{isin}: {e}" for e in result.errors]
            except Exception as e:  # one bad instrument never stops the others
                session.rollback()
                seed_job.errors.append(f"{isin}: {e}")
                log.exception("Seeding %s failed", isin)
            seed_job.done += 1
    seed_job.current = None
    seed_job.running = False


@router.post("/universe/seed")
def seed_universe(background: BackgroundTasks) -> dict:
    with seed_job.lock:
        if not seed_job.running:
            seed_job.running, seed_job.done, seed_job.total, seed_job.errors = True, 0, len(universe.SEED), []
            background.add_task(_run_seed)
    return seed_job.state()


@router.get("/universe/seed")
def seed_status() -> dict:
    return seed_job.state()
