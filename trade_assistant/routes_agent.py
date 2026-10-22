"""API of brick 5: prepare the monthly plan, read it, approve or reject it."""
from __future__ import annotations

import threading
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import auth
from .agent import pipeline
from .db import get_engine, get_session
from .models import MonthlyPlan

router = APIRouter(prefix="/api/plans", dependencies=[Depends(auth.require_auth)])

_job: dict = {"running": False, "step": None, "plan_id": None, "error": None}
_lock = threading.Lock()


def _run() -> None:
    try:
        with Session(get_engine()) as session:
            data = pipeline.run(session, lambda step: _job.update(step=step))
            _job["plan_id"] = pipeline.save(session, data).id
    except Exception as e:  # reported on the page rather than lost in the logs
        _job["error"] = f"{type(e).__name__}: {e}"
    finally:
        _job.update(running=False, step=None)


@router.post("/generate")
def generate(background: BackgroundTasks) -> dict:
    """Starts the agent (1 to 3 minutes); follow it with GET /api/plans/job."""
    with _lock:
        if not _job["running"]:
            _job.update(running=True, step="Démarrage", plan_id=None, error=None)
            background.add_task(_run)
    return dict(_job)


@router.get("/job")
def job() -> dict:
    return dict(_job)


@router.get("")
def history(session: Session = Depends(get_session)) -> list[dict]:
    return pipeline.history(session)


@router.get("/latest")
def latest(session: Session = Depends(get_session)) -> dict | None:
    plan = session.scalar(select(MonthlyPlan).order_by(MonthlyPlan.created_at.desc()).limit(1))
    return pipeline.as_dict(plan) if plan else None


@router.get("/{plan_id}")
def read(plan_id: int, session: Session = Depends(get_session)) -> dict:
    plan = session.get(MonthlyPlan, plan_id)
    if plan is None:
        raise HTTPException(404, "Plan introuvable")
    return pipeline.as_dict(plan)


class Decision(BaseModel):
    status: Literal["approved", "rejected"]
    note: str | None = Field(default=None, max_length=1000)


@router.post("/{plan_id}/decision")
def decide(plan_id: int, body: Decision, session: Session = Depends(get_session)) -> dict:
    try:
        return pipeline.as_dict(pipeline.decide(session, plan_id, body.status, body.note))
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
