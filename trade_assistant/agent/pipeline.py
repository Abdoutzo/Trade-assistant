"""Runs the agent: facts -> analyst -> devil's advocate -> manager -> checks -> draft plan."""
from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from .. import llm
from ..models import MonthlyPlan, utcnow
from . import checks, facts, roles

log = logging.getLogger(__name__)
ROLE_NAMES = {"target": "sélectionnée", "held": "détenue", "alternative": "alternative possible"}
STEP_LABELS = {"analyst": "L'analyste étudie chaque dossier",
               "critic": "L'avocat du diable cherche les failles",
               "manager": "Le gérant décide du plan"}


def _companies_block(ctx: facts.Context) -> str:
    parts = [ctx.render(ctx.general)]
    for c in ctx.companies.values():
        parts.append(f"\n## {c.name} (ISIN {c.isin}, {ROLE_NAMES[c.role]})\n{ctx.render(c.facts)}")
    return "\n".join(parts)


def _checklist(orders: list[dict], first: list[dict] | None) -> list[str]:
    steps = ["Ouvre Trade Republic > ton PEA > Plans d'investissement."]
    for o in orders:
        steps.append(f"Plan mensuel {o['name']} ({o['isin']}) : {o['amount']:.0f} € "
                     "(crée-le s'il n'existe pas, sinon vérifie le montant).")
    steps.append("Supprime les plans des valeurs qui ne figurent plus dans la liste.")
    if first:
        steps.append("Premier versement (ordres ponctuels, 1 € de frais chacun) : "
                     + ", ".join(f"{o['name']} {o['amount']:.0f} €" for o in first) + ".")
    steps.append("Après les premières exécutions, enregistre les achats dans Portefeuille > Transactions.")
    return steps


def run(session: Session, progress: Callable[[str], None] = lambda step: None) -> dict:
    """Prepares this month's plan. Never raises because of the AI: at worst, the calculated plan."""
    progress("Rassemblement des faits (notes, portefeuille, actualités)")
    ctx = facts.build(session)
    # The AI takes minutes: never keep a database transaction open meanwhile (Neon closes it).
    session.commit()
    names = {c.isin: c.name for c in ctx.companies.values()}
    core_isin = ctx.profile["core_isin"]
    names[core_isin] = next((o["name"] for o in ctx.proposal["orders"] if o["isin"] == core_isin),
                            "ETF monde")
    steps: list[dict] = []
    data: dict = {"month": date.today().strftime("%Y-%m"), "budget": ctx.profile["monthly"],
                  "proposal": ctx.proposal["orders"], "facts": ctx.facts, "steps": steps,
                  "first_payment": ctx.proposal.get("first_payment"), "analyst": None, "critic": [],
                  "source": "rules", "fallback_reason": None, "summary": None, "changes": None,
                  "change_my_mind": None, "lesson": None}
    block = _companies_block(ctx)

    def step(role: str, system: str, prompt: str, schema, quiet: bool = False):
        if not quiet:
            progress(STEP_LABELS[role])
        start = time.monotonic()
        try:
            answer, model = roles.ask(system, prompt, schema)
            steps.append({"role": role, "model": model, "seconds": round(time.monotonic() - start),
                          "ok": True})
            return answer
        except (roles.RoleFailed, llm.NoModelAvailable) as e:
            steps.append({"role": role, "model": None, "seconds": round(time.monotonic() - start),
                          "ok": False, "error": str(e)[:400]})
            log.warning("Agent role %s failed: %s", role, e)
            return None

    progress(STEP_LABELS["analyst"])
    analyst = _analyst(ctx, step)
    _merge_steps(steps, "analyst")
    if analyst is None:
        return _fallback(data, ctx, names,
                         "L'analyste (IA) n'a pas pu répondre : plan calculé par les règles.")
    data["analyst"] = {
        "overview": analyst.overview, "overview_unverified": checks.unverified(analyst.overview, ctx),
        "companies": [{"isin": c.isin, "name": names.get(c.isin, c.isin),
                       "role": ctx.companies[c.isin].role if c.isin in ctx.companies else None,
                       "score": ctx.companies[c.isin].score if c.isin in ctx.companies else None,
                       "thesis": c.thesis, "risks": c.risks, "stance": c.stance, "confidence": c.confidence,
                       "facts": checks.known_facts(c.facts, ctx),
                       "unverified": checks.unverified(f"{c.thesis} {c.risks}", ctx)}
                      for c in analyst.companies if c.isin in ctx.companies]}
    analyst_json = json.dumps(analyst.model_dump(), ensure_ascii=False)

    critic = step("critic", roles.CRITIC, f"Faits :\n{block}\n\nAvis de l'analyste :\n{analyst_json}",
                  roles.CriticAnswer)
    critic_json = "[]"
    if critic is not None:
        data["critic"] = [{"isin": o.isin, "name": names.get(o.isin or "", "Portefeuille"), "text": o.text,
                           "severity": o.severity, "facts": checks.known_facts(o.facts, ctx),
                           "unverified": checks.unverified(o.text, ctx)} for o in critic.objections]
        critic_json = json.dumps(critic.model_dump(), ensure_ascii=False)

    p = ctx.profile
    allowed = "\n".join(f"- {isin} : {name}" for isin, name in names.items())
    calculated = [{k: o[k] for k in ("isin", "name", "amount")} for o in ctx.proposal["orders"]]
    constraints = (f"Budget du mois : {p['monthly']:.0f} €. ETF monde (cœur) : {core_isin}, au moins "
                   f"{round(p['monthly'] * p['core_share'])} €. Minimum par action : "
                   f"{p['min_order_eur']:.0f} €.\nListe autorisée :\n{allowed}\n\n"
                   f"Plan calculé par les règles :\n{json.dumps(calculated, ensure_ascii=False)}")
    manager = step("manager", roles.MANAGER, f"Faits :\n{block}\n\nAvis de l'analyste :\n{analyst_json}\n\n"
                   f"Objections de l'avocat du diable :\n{critic_json}\n\n{constraints}", roles.ManagerAnswer)
    if manager is None:
        return _fallback(data, ctx, names,
                         "Le gérant (IA) n'a pas pu répondre : plan calculé par les règles.")

    check = checks.check_orders([o.model_dump() for o in manager.orders], ctx)
    data.update(summary=manager.summary, changes=manager.changes, change_my_mind=manager.change_my_mind,
                lesson=manager.lesson.model_dump() if manager.lesson else None,
                text_unverified=checks.unverified(
                    f"{manager.summary} {manager.changes} {manager.change_my_mind}", ctx))
    if not check.ok:
        return _fallback(data, ctx, names, "Le plan proposé par l'IA ne respectait pas tes règles ("
                         + " ; ".join(check.errors) + ") : plan calculé appliqué.")
    data["source"] = "agent"
    data["orders"] = [{"isin": o["isin"], "name": names.get(o["isin"], o["isin"]), "amount": o["amount"],
                       "role": "core" if o["isin"] == core_isin else "satellite", "reason": o["reason"],
                       "facts": checks.known_facts(o["facts"], ctx),
                       "unverified": checks.unverified(o["reason"], ctx)}
                      for o in sorted(check.orders, key=lambda o: (o["isin"] != core_isin, -o["amount"]))]
    data["checklist"] = _checklist(data["orders"], data["first_payment"])
    return data


def _merge_steps(steps: list[dict], role: str) -> None:
    """The analyst runs once per company: one line in the report, with the slowest call's time."""
    mine = [s for s in steps if s["role"] == role]
    if len(mine) <= 1:
        return
    ok = [s for s in mine if s["ok"]]
    merged = {"role": role, "model": ", ".join(sorted({s["model"] for s in ok})) or None,
              "seconds": max(s["seconds"] for s in mine), "ok": bool(ok), "calls": len(mine)}
    if len(ok) < len(mine):
        merged["error"] = f"{len(mine) - len(ok)} entreprise(s) sur {len(mine)} sans réponse"
    steps[:] = [s for s in steps if s["role"] != role] + [merged]


def _analyst(ctx: facts.Context, step) -> roles.AnalystAnswer | None:
    """One call per company, 4 at a time: short answers, fast and independent. A company whose
    call fails is simply left out; no answer at all means no analyst."""
    general = ctx.render(ctx.general)
    companies = list(ctx.companies.values())
    if not companies:
        return roles.AnalystAnswer(companies=[],
                                   overview="Aucune action sélectionnée : tout va à l'ETF monde.")

    def one(c: facts.Company) -> roles.AnalystAnswer | None:
        block = f"{general}\n\n## {c.name} (ISIN {c.isin}, {ROLE_NAMES[c.role]})\n{ctx.render(c.facts)}"
        return step("analyst", roles.ANALYST, f"Faits :\n{block}", roles.AnalystAnswer, quiet=True)

    with ThreadPoolExecutor(max_workers=4) as pool:
        answers = list(pool.map(one, companies))
    found = [a for a in answers if a is not None]
    if not found:
        return None
    return roles.AnalystAnswer(companies=[c for a in found for c in a.companies],
                               overview=" ".join(a.overview for a in found[:1] if a.overview),
                               facts=[f for a in found for f in a.facts])


def _fallback(data: dict, ctx: facts.Context, names: dict, reason: str) -> dict:
    data["fallback_reason"] = reason
    data["orders"] = [{"isin": o["isin"], "name": o["name"], "amount": o["amount"], "role": o["role"],
                       "reason": o.get("reason"), "facts": [], "unverified": []}
                      for o in ctx.proposal["orders"]]
    data["checklist"] = _checklist(data["orders"], data["first_payment"])
    return data


# --- Storage and decisions -----------------------------------------------------------------------

def save(session: Session, data: dict) -> MonthlyPlan:
    models = sorted({s["model"] for s in data["steps"] if s.get("model")})
    for attempt in range(2):
        plan = MonthlyPlan(month=data["month"], data=data, model=", ".join(models) or "règles")
        session.add(plan)
        try:
            session.commit()
            return plan
        except DBAPIError:
            # A connection closed by the database during a long wait: retry once on a fresh one.
            session.rollback()
            if attempt:
                raise
    raise AssertionError("unreachable")


def decide(session: Session, plan_id: int, status: str, note: str | None = None) -> MonthlyPlan:
    plan = session.get(MonthlyPlan, plan_id)
    if plan is None:
        raise LookupError("Plan introuvable")
    if status == "approved":
        # One approved plan per month: approving a new one replaces the previous decision.
        for other in session.scalars(select(MonthlyPlan).where(MonthlyPlan.month == plan.month,
                                                               MonthlyPlan.status == "approved",
                                                               MonthlyPlan.id != plan.id)):
            other.status = "replaced"
    plan.status, plan.note, plan.decided_at = status, note, utcnow()
    session.commit()
    return plan


def as_dict(plan: MonthlyPlan) -> dict:
    return {"id": plan.id, "month": plan.month, "created_at": plan.created_at.isoformat(),
            "status": plan.status,
            "model": plan.model, "note": plan.note,
            "decided_at": plan.decided_at.isoformat() if plan.decided_at else None, **plan.data}


def history(session: Session, limit: int = 24) -> list[dict]:
    rows = session.scalars(select(MonthlyPlan).order_by(MonthlyPlan.created_at.desc()).limit(limit))
    return [{"id": p.id, "month": p.month, "created_at": p.created_at.isoformat(), "status": p.status,
             "model": p.model, "source": p.data.get("source"),
             "orders": [{"name": o["name"], "amount": o["amount"]} for o in p.data.get("orders", [])]}
            for p in rows]
