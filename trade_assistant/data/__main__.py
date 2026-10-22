"""Market data from the command line (and from GitHub Actions).

    python -m trade_assistant.data seed                 add the starting universe (ETFs + 35 shares)
    python -m trade_assistant.data add FR0000120073     add any ISIN
    python -m trade_assistant.data refresh [ISIN ...]   prices for all, accounts when older than 7 days
    python -m trade_assistant.data show FR0000120073    what we know about an instrument
    python -m trade_assistant.data check FR0000120073   add + refresh + show (used by the GitHub button)
    python -m trade_assistant.data rank                 the universe ranked by score
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import timedelta

from sqlalchemy.orm import Session

from ..db import get_engine, init_db
from . import store, universe
from .http import SourceError

ACCOUNTS_MAX_AGE = timedelta(days=7)


def _add(session: Session, isins: list[str]) -> int:
    failures = 0
    for isin in isins:
        try:
            i = store.add_instrument(session, isin)
            print(f"[OK] {i.isin} {i.symbol:<10} {i.name}")
        except (ValueError, LookupError, SourceError) as e:
            failures += 1
            print(f"[KO] {isin}: {e}")
        time.sleep(0.3)  # polite with free sources
    return failures


def _refresh(session: Session, isins: list[str], force: bool) -> int:
    instruments = ([store.get_instrument(session, i) for i in isins] if isins
                   else store.list_instruments(session))
    failures = 0
    for i in instruments:
        if i is None:
            failures += 1
            continue
        try:
            n = store.refresh_prices(session, i)
            line = f"{i.isin} {i.symbol:<10} cours: {n}"
            if i.kind == "stock" and (force or store.is_stale(i.fundamentals_updated_at, ACCOUNTS_MAX_AGE)):
                r = store.refresh_fundamentals(session, i)
                line += f", comptes Yahoo: {r.yahoo_figures}, rapports officiels lus: {r.esef_reports_read}"
                if r.errors:
                    line += " | " + "; ".join(r.errors)
            print("[OK] " + line)
        except SourceError as e:
            failures += 1
            print(f"[KO] {i.isin}: {e}")
        time.sleep(0.3)
    from ..analysis import service  # analyses follow the data they are computed from
    service.all_analyses(session, force=True)
    return failures


def _money(x: float) -> str:
    for div, unit in ((1e9, " Md"), (1e6, " M")):
        if abs(x) >= div:
            return f"{x / div:,.2f}{unit}".replace(",", " ")
    return f"{x:,.2f}".replace(",", " ")


def _show(session: Session, isin: str) -> int:
    i = store.get_instrument(session, isin)
    if not i:
        print(f"{isin} n'est pas dans l'univers (ajoute-le avec : add {isin})")
        return 1
    print(f"\n{i.name} ({i.isin}, {i.symbol}, {i.kind}, {i.currency})")
    print(f"PEA : {'oui' if i.pea_eligible else 'non' if i.pea_eligible is False else 'à vérifier'}"
          f" ({i.pea_reason})")
    if i.sector:
        print(f"Secteur : {i.sector} / {i.industry}")
    series = store.prices(session, i)
    if series:
        last = series[-1]
        year_ago = next((p for p in reversed(series) if (last.day - p.day).days >= 365), None)
        change = f", sur 1 an : {last.adj_close / year_ago.adj_close - 1:+.1%}" if year_ago else ""
        print(f"Cours : {last.close:.2f} {i.currency} le {last.day}{change} ({len(series)} séances en base)")
    table = store.fundamentals_table(session, i)
    if table:
        metrics = ["revenue", "operating_income", "net_income", "free_cash_flow", "eps_diluted", "equity"]
        years = list(table)[-5:]
        print("\n" + "".ljust(18) + "".join(str(d.year).rjust(14) for d in years))
        for m in metrics:
            cells = [table[d].get(m) for d in years]
            if any(cells):
                print(m.ljust(18) + "".join((_money(c.value) + ("*" if c.source == "esef" else "")).rjust(14)
                                            if c else "-".rjust(14) for c in cells))
        print("* = rapport annuel officiel (ESEF), sinon Yahoo")
        gaps = [(d, m, c) for d, row in table.items() for m, c in row.items() if c.other_value is not None]
        for d, m, c in gaps:
            print(f"Écart entre sources : {m} {d.year} = {_money(c.value)} ({c.source}) "
                  f"contre {_money(c.other_value)} ({c.gap:.1%})")
    _show_analysis(session, i)
    return 0


def _fmt(value: float | None, fmt: str) -> str:
    if value is None:
        return "-"
    return f"{value:.1%}" if fmt == "pct" else f"{value:.2f}"


def _show_analysis(session: Session, instrument) -> None:
    from ..analysis import service

    data = service.get_analysis(session, instrument, force=True)
    print(f"\nAnalyse : {data.get('score') if data.get('score') is not None else '-'}/100. {data['verdict']}")
    for pillar in (data.get("pillars") or {}).values():
        print(f"  {pillar['label']:<18} {pillar['score'] if pillar['score'] is not None else '-':>4}")
        for m in pillar["metrics"]:
            if m["value"] is not None:
                print(f"      {m['label']:<48} {_fmt(m['value'], m['fmt']):>9}  note {m['score']:>3}"
                      f"  ({m['detail'] or ''})")
    if data.get("strengths"):
        print("Points forts : " + ", ".join(data["strengths"]))
    if data.get("weaknesses"):
        print("Points faibles : " + ", ".join(data["weaknesses"]))
    for w in data.get("warnings", []):
        print("Attention : " + w)


def _rank(session: Session) -> int:
    from ..analysis import service

    rows = [(i, d) for i, d in service.all_analyses(session) if i.kind == "stock"]
    rows.sort(key=lambda x: -(x[1].get("score") or -1))
    print(f"{'Note':>4}  {'Entreprise':<40} {'Qual':>5} {'Sol':>5} {'Croi':>5} {'Valo':>5} {'Risq':>5}")
    for i, d in rows:
        p = {k: v["score"] for k, v in (d.get("pillars") or {}).items()}
        cells = "".join(f"{p.get(k) if p.get(k) is not None else '-':>6}"
                        for k in ("quality", "solidity", "growth", "valuation", "risk"))
        print(f"{d.get('score') if d.get('score') is not None else '-':>4}  {i.name[:40]:<40}{cells}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m trade_assistant.data")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed")
    sub.add_parser("add").add_argument("isins", nargs="+")
    refresh = sub.add_parser("refresh")
    refresh.add_argument("isins", nargs="*")
    refresh.add_argument("--force", action="store_true", help="relire les comptes même s'ils sont récents")
    sub.add_parser("show").add_argument("isin")
    sub.add_parser("check").add_argument("isin")
    sub.add_parser("rank")
    args = parser.parse_args(argv)

    init_db()
    with Session(get_engine()) as session:
        if args.command == "seed":
            return 1 if _add(session, universe.SEED) + _refresh(session, [], force=False) else 0
        if args.command == "add":
            return 1 if _add(session, args.isins) else 0
        if args.command == "refresh":
            return 1 if _refresh(session, args.isins, args.force) else 0
        if args.command == "rank":
            return _rank(session)
        if args.command == "show":
            return _show(session, args.isin.upper())
        failures = _add(session, [args.isin]) or _refresh(session, [args.isin.upper()], force=True)
        return failures or _show(session, args.isin.upper())


if __name__ == "__main__":
    sys.exit(main())
