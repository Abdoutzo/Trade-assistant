"""What the monthly e-mail says, gathered from the other bricks (no AI call: the plan already has it)."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agent import pipeline
from ..guide import service as guide
from ..models import MonthlyPlan, utcnow
from ..news import service as news
from ..portfolio import service as portfolio

MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
          "novembre", "décembre"]


def month_label(month: str) -> str:
    """'2026-12' -> 'décembre 2026'."""
    year, number = month.split("-")
    return f"{MONTHS[int(number) - 1]} {year}"


def gather(session: Session) -> dict:
    plan_row = session.scalar(select(MonthlyPlan).order_by(MonthlyPlan.created_at.desc()).limit(1))
    plan = pipeline.as_dict(plan_row) if plan_row else None
    pf = portfolio.portfolio(session)
    since = (utcnow() - timedelta(days=35)).isoformat()
    alerts = [a for a in news.alerts(session, limit=50) if a["created_at"] >= since and a["severity"] >= 2]
    summary = guide.summary(session)
    nxt = next((c for c in summary["chapters"] if c["id"] == summary["next"]), None)
    changes = [a for a in (plan or {}).get("actions", []) if a["kind"] != "keep"]
    return {
        "plan": plan, "portfolio": pf, "alerts": alerts[:6], "changes": changes,
        "objections": sorted([o for o in (plan or {}).get("critic", []) if o["severity"] >= 3],
                             key=lambda o: o["name"]),
        "guide_next": nxt, "guide_read": summary["read"], "guide_total": summary["total"],
    }


def subject(report: dict) -> str:
    plan = report["plan"]
    if plan is None:
        return "Trade Assistant : ton point du mois"
    month = month_label(plan["month"])
    n = len(report["changes"])
    if not plan.get("actions"):
        todo = "à valider"
    elif n == 0:
        todo = "rien à changer dans Trade Republic"
    else:
        todo = f"{n} changement{'s' if n > 1 else ''} dans Trade Republic"
    return f"Plan de {month} : {todo}"
