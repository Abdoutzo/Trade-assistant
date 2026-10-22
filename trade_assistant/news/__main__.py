"""News from the command line (and from GitHub Actions).

    python -m trade_assistant.news collect [ISIN ...]   new articles, triage, alerts (all stocks by default)
    python -m trade_assistant.news digest ISIN          AI summary of a company's recent news
    python -m trade_assistant.news check ISIN           add + collect + show + digest (the GitHub button)
"""
from __future__ import annotations

import argparse
import sys

from sqlalchemy.orm import Session

from .. import llm
from ..data import store
from ..data.http import SourceError
from ..db import get_engine, init_db
from . import service, triage


def watched(session: Session) -> set[str]:
    """What you hold or plan to buy: price alerts are raised for these."""
    from ..portfolio import service as portfolio

    try:
        held = {p["isin"] for p in portfolio.portfolio(session)["positions"]}
        return held | {t["isin"] for t in portfolio.selection(session)}
    except Exception:  # the watch list is a bonus, never a reason to skip the news
        session.rollback()
        return set()


def _collect(session: Session, isins: list[str]) -> int:
    if isins:
        results = {}
        for isin in isins:
            instrument = store.get_instrument(session, isin)
            if instrument is None:
                print(f"[KO] {isin} n'est pas dans l'univers")
                continue
            results[isin] = service.refresh(session, instrument)
            service.price_alert(session, instrument)
            session.commit()
    else:
        results = service.refresh_all(session, watched(session))
    failures = 0
    for isin, r in results.items():
        status = "KO" if r.errors and not r.new else "OK"
        failures += status == "KO"
        print(f"[{status}] {isin} nouveaux articles : {r.new} (dont {r.triaged_by_ai} triés par l'IA), "
              f"alertes : {r.alerts}" + (f" | {'; '.join(r.errors)}" if r.errors else ""))
    return 1 if failures and failures == len(results) else 0


def _show(session: Session, isin: str) -> None:
    for item in service.feed(session, {isin}, days=30, min_importance=1, limit=15):
        tone = {-2: "--", -1: "-", 0: "=", 1: "+", 2: "++"}.get(item["sentiment"], "?")
        print(f"  {item['published_at'][:10]}  {'*' * (item['importance'] or 0):<3} {tone:>2}  "
              f"[{item['category_label']}] {item['summary']}  ({item['source']})")
    for a in service.alerts(session)[:10]:
        if a["isin"] == isin:
            print(f"  ALERTE {'!' * a['severity']} {a['title']}")


def _digest(session: Session, isin: str) -> int:
    instrument = store.get_instrument(session, isin)
    if instrument is None:
        print(f"{isin} n'est pas dans l'univers")
        return 1
    try:
        row = service.make_digest(session, instrument)
    except (LookupError, ValueError, llm.NoModelAvailable) as e:
        print(f"Synthèse impossible : {e}")
        return 1
    print(f"\nSynthèse ({row.model}) :")
    for p in row.points:
        print(f"  - {p['text']} {p['sources']}")
    if row.watch:
        print("À surveiller :")
        for p in row.watch:
            print(f"  - {p['text']} {p['sources']}")
    print("Sources :")
    for s in row.sources:
        print(f"  [{s['n']}] {s['date']} {s['source']} : {s['title'][:90]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m trade_assistant.news")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("collect").add_argument("isins", nargs="*")
    sub.add_parser("digest").add_argument("isin")
    sub.add_parser("check").add_argument("isin")
    args = parser.parse_args(argv)
    init_db()
    with Session(get_engine()) as session:
        if args.command == "collect":
            return _collect(session, [i.upper() for i in args.isins])
        if args.command == "digest":
            return _digest(session, args.isin.upper())
        isin = args.isin.upper()
        try:
            instrument = store.add_instrument(session, isin)
            store.refresh_prices(session, instrument)
        except (ValueError, LookupError, SourceError) as e:
            print(f"[KO] {isin}: {e}")
            return 1
        _collect(session, [isin])
        print(f"\n{instrument.name} : actualités des 30 derniers jours (importance >= 1)")
        print("Légende : * importance, ton -- à ++. Catégories : " + ", ".join(triage.CATEGORIES.values()))
        _show(session, isin)
        return _digest(session, isin)


if __name__ == "__main__":
    sys.exit(main())
