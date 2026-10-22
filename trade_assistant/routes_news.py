"""API of brick 4: news feed, alerts, per-company news and AI digest."""
from __future__ import annotations

import threading
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from . import auth, llm
from .data import store
from .db import get_engine, get_session
from .news import service, triage
from .news.__main__ import watched

router = APIRouter(prefix="/api", dependencies=[Depends(auth.require_auth)])


@router.get("/news")
def news_feed(scope: Literal["mine", "all"] = "mine", days: int = 30, min_importance: int = 1,
              category: str | None = None, session: Session = Depends(get_session)) -> dict:
    mine = watched(session)
    return {"categories": triage.CATEGORIES, "watched": sorted(mine),
            "items": service.feed(session, mine if scope == "mine" else None, min(days, 180), min_importance,
                                  category)}


@router.get("/alerts")
def list_alerts(unread: bool = False, session: Session = Depends(get_session)) -> list[dict]:
    return service.alerts(session, unread_only=unread)


@router.post("/alerts/read")
def read_all_alerts(session: Session = Depends(get_session)) -> dict:
    return {"marked": service.mark_read(session)}


@router.post("/alerts/{alert_id}/read")
def read_alert(alert_id: int, session: Session = Depends(get_session)) -> dict:
    return {"marked": service.mark_read(session, alert_id)}


def _instrument(session: Session, isin: str):
    instrument = store.get_instrument(session, isin)
    if instrument is None:
        raise HTTPException(404, f"{isin} n'est pas dans l'univers")
    return instrument


@router.get("/instruments/{isin}/news")
def instrument_news(isin: str, session: Session = Depends(get_session)) -> dict:
    instrument = _instrument(session, isin)
    return {"items": service.feed(session, {instrument.isin}, days=60, min_importance=0, limit=60),
            "digest": service.latest_digest(session, instrument), "categories": triage.CATEGORIES}


@router.post("/instruments/{isin}/news/refresh")
def refresh_instrument_news(isin: str, session: Session = Depends(get_session)) -> dict:
    instrument = _instrument(session, isin)
    result = service.refresh(session, instrument)
    return {"new": result.new, "triaged_by_ai": result.triaged_by_ai, "alerts": result.alerts,
            "errors": result.errors}


@router.post("/instruments/{isin}/digest")
def create_digest(isin: str, session: Session = Depends(get_session)) -> dict:
    instrument = _instrument(session, isin)
    try:
        service.make_digest(session, instrument)
    except LookupError as e:
        raise HTTPException(422, str(e)) from e
    except (llm.NoModelAvailable, ValueError) as e:
        raise HTTPException(503, f"Synthèse impossible pour l'instant : {e}") from e
    return service.latest_digest(session, instrument)


# --- Collect the whole universe from the site ----------------------------------------------------

_job = {"running": False, "done": 0, "new": 0, "alerts": 0, "errors": []}
_lock = threading.Lock()


def _collect_all() -> None:
    with Session(get_engine()) as session:
        try:
            results = service.refresh_all(session, watched(session))
            _job.update(done=len(results), new=sum(r.new for r in results.values()),
                        alerts=sum(r.alerts for r in results.values()),
                        errors=[f"{k}: {e}" for k, r in results.items() for e in r.errors][:20])
        finally:
            _job["running"] = False


@router.post("/news/collect")
def collect_all(background: BackgroundTasks) -> dict:
    with _lock:
        if not _job["running"]:
            _job.update(running=True, done=0, new=0, alerts=0, errors=[])
            background.add_task(_collect_all)
    return dict(_job)


@router.get("/news/collect")
def collect_status() -> dict:
    return dict(_job)
