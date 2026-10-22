"""The monthly plan from the command line (and from GitHub Actions, on the 1st of each month).

    python -m trade_assistant.agent run      prepare this month's plan and save it as a draft
"""
from __future__ import annotations

import argparse
import sys

from sqlalchemy.orm import Session

from ..data import store
from ..db import get_engine, init_db
from . import pipeline


def _ensure_data(session: Session) -> None:
    """On an empty database (a test run), load the starting universe first."""
    if store.list_instruments(session):
        return
    from ..data.__main__ import main as data_main

    print("Base vide : chargement de l'univers de départ…")
    data_main(["seed"])


def _fresh_news(session: Session) -> None:
    """Today's news for the companies the agent will discuss (cheap: a few companies)."""
    from ..news import service as news
    from ..news.__main__ import watched

    for isin in sorted(watched(session)):
        instrument = store.get_instrument(session, isin)
        if instrument and instrument.kind == "stock":
            try:
                news.refresh(session, instrument)
            except Exception as e:  # news are a bonus for the plan, never a blocker
                session.rollback()
                print(f"Actualités indisponibles pour {isin} : {e}")


def run() -> int:
    init_db()
    with Session(get_engine()) as session:
        _ensure_data(session)
        _fresh_news(session)
        data = pipeline.run(session, lambda step: print(f"… {step}"))
        plan = pipeline.save(session, data)
    print(f"\nPlan n°{plan.id} ({data['month']}), préparé par : {plan.model}")
    if data["fallback_reason"]:
        print(f"ATTENTION : {data['fallback_reason']}")
    for s in data["steps"]:
        status = "ok" if s["ok"] else "échec"
        print(f"  {s['role']:<8} {status} en {s['seconds']} s ({s.get('model') or s.get('error')})")
    print("\nPlans programmés proposés :")
    for o in data["orders"]:
        flag = f"  [chiffres non vérifiés : {o['unverified']}]" if o.get("unverified") else ""
        print(f"  {o['amount']:>5.0f} €  {o['name']} : {o.get('reason') or ''}{flag}")
    if data.get("summary"):
        print(f"\nDécision : {data['summary']}\nChangements : {data['changes']}")
        print(f"Ce qui me ferait changer d'avis : {data['change_my_mind']}")
    if data.get("analyst"):
        print("\nAnalyste :")
        for c in data["analyst"]["companies"]:
            print(f"  [{c['stance']}, confiance {c['confidence']}/3] {c['name']} : {c['thesis']} "
                  f"Risque : {c['risks']}")
    if data.get("critic"):
        print("\nAvocat du diable :")
        for o in data["critic"]:
            print(f"  [gravité {o['severity']}] {o['name']} : {o['text']}")
    if data.get("lesson"):
        print(f"\nLeçon du mois : {data['lesson']['title']}\n  {data['lesson']['text']}")
    print("\nCe plan attend ta validation sur le site (Plan du mois). Rien n'a été exécuté.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m trade_assistant.agent")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run")
    parser.parse_args(argv)
    return run()


if __name__ == "__main__":
    sys.exit(main())
