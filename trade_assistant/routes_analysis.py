"""API of brick 2: the ranking of the universe and the analysis of each company."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from . import auth
from .analysis import scoring, service
from .data import store
from .db import get_engine, get_session

router = APIRouter(prefix="/api", dependencies=[Depends(auth.require_auth)])

RANKING_METRICS = ("pe", "fcf_yield", "dividend_yield", "roic", "roe", "revenue_cagr", "net_debt_to_ebitda")


def _metric_values(data: dict) -> dict[str, float | None]:
    return {m["key"]: m["value"] for p in (data.get("pillars") or {}).values() for m in p["metrics"]}


@router.get("/ranking")
def ranking(session: Session = Depends(get_session)) -> dict:
    """Every stock with its score, pillars and a few key figures, best first."""
    rows = []
    for instrument, data in service.all_analyses(session):
        if instrument.kind != "stock":
            continue
        values = _metric_values(data)
        rows.append({
            "isin": instrument.isin, "name": instrument.name, "sector": instrument.sector,
            "pea_eligible": instrument.pea_eligible, "score": data.get("score"),
            "verdict": data.get("verdict"),
            "pillars": {k: p["score"] for k, p in (data.get("pillars") or {}).items()},
            "metrics": {k: values.get(k) for k in RANKING_METRICS},
            "return_1y": (data.get("info") or {}).get("return_1y"),
        })
    rows.sort(key=lambda r: (r["score"] is None, -(r["score"] or 0)))
    return {"pillars": {k: label for k, (label, _, _) in scoring.PILLARS.items()}, "rows": rows}


@router.get("/instruments/{isin}/analysis")
def instrument_analysis(isin: str, session: Session = Depends(get_session)) -> dict:
    instrument = store.get_instrument(session, isin)
    if not instrument:
        raise HTTPException(404, f"{isin} n'est pas dans l'univers")
    data = service.get_analysis(session, instrument)
    medians = service.sector_medians(service.all_analyses(session)).get(instrument.sector or "", {})
    return {**data, "sector_medians": medians, "info_labels": scoring.INFO}


@router.post("/analysis/refresh")
def refresh_all(background: BackgroundTasks) -> dict:
    """Recompute every analysis (after changing thresholds, for example)."""
    background.add_task(_recompute)
    return {"started": True}


def _recompute() -> None:
    with Session(get_engine()) as session:
        service.all_analyses(session, force=True)
