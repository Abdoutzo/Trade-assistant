"""Your Trade Republic purchases from the command line (and from GitHub Actions, without a terminal).

    python -m trade_assistant.portfolio add 2026-11-02 ES0148396007 56.96 --quantity 1
    python -m trade_assistant.portfolio add 2026-11-02 FR001400U5Q4 433.08
    python -m trade_assistant.portfolio show
    python -m trade_assistant.portfolio plans "FR001400U5Q4:80:monthly,ES0148396007:60:quarterly"

The amount is what Trade Republic shows ("You saved 433.08 €"). Without --quantity, the number of
shares is deduced from the closing price of that day: in a PEA, Trade Republic only buys whole
shares, so amount / price lands close to a whole number. Adding the same purchase twice does nothing.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

from sqlalchemy.orm import Session

from ..data import store
from ..db import get_engine, init_db
from . import service, tradeplans

TOLERANCE = 0.03  # the deduced price must stay within 3 % of the day's close


def deduce_quantity(session: Session, isin: str, day: date, amount: float) -> tuple[int, float]:
    """Whole number of shares for this amount, from the close of that day (or the last day before)."""
    instrument = store.get_instrument(session, isin)
    if instrument is None:
        raise LookupError(f"{isin} n'est pas dans l'univers : ajoute-le d'abord (Univers et analyses).")
    rows = [p for p in store.prices(session, instrument, since=day - timedelta(days=7)) if p.day <= day]
    if not rows or rows[-1].day < day:
        store.refresh_prices(session, instrument)
        rows = [p for p in store.prices(session, instrument, since=day - timedelta(days=7)) if p.day <= day]
    if not rows:
        raise LookupError(f"Pas de cours connu pour {isin} autour du {day} : indique --quantity.")
    close = rows[-1].close
    quantity = round(amount / close)
    if quantity < 1 or abs(amount / quantity - close) / close > TOLERANCE:
        raise ValueError(f"{amount} € ne fait pas un nombre entier de parts au cours de {close:.2f} € : "
                         "indique --quantity (visible dans le détail de l'achat sur Trade Republic).")
    return quantity, close


def _exists(session: Session, day: date, isin: str, side: str, quantity: float) -> bool:
    return any(t.day == day and t.isin == isin and t.side == side and abs(t.quantity - quantity) < 1e-9
               for t in service.transactions(session))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m trade_assistant.portfolio")
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add", help="enregistrer un achat ou une vente")
    add.add_argument("day", type=date.fromisoformat, help="date d'exécution, AAAA-MM-JJ")
    add.add_argument("isin")
    add.add_argument("amount", type=float, help="montant total en euros, hors frais")
    add.add_argument("--quantity", type=float, help="nombre de parts (déduit du cours si absent)")
    add.add_argument("--side", choices=["buy", "sell"], default="buy")
    add.add_argument("--fees", type=float, default=0.0)
    add.add_argument("--note")
    sub.add_parser("show", help="afficher les transactions et les positions")
    plans = sub.add_parser("plans", help="enregistrer tes plans Trade Republic en cours")
    plans.add_argument("plans", nargs="?", default="",
                       help="ISIN:montant:fréquence (monthly, quarterly...), séparés par des virgules")
    args = parser.parse_args(argv)

    init_db()
    with Session(get_engine()) as session:
        if args.command == "add":
            isin = args.isin.strip().upper()
            try:
                if args.quantity:
                    quantity = args.quantity
                    print(f"{quantity:g} part(s) indiquée(s).")
                else:
                    quantity, close = deduce_quantity(session, isin, args.day, args.amount)
                    print(f"{quantity} part(s) déduite(s) du cours de clôture ({close:.2f} €). "
                          "Vérifie-le dans le détail de l'achat sur Trade Republic.")
                if _exists(session, args.day, isin, args.side, quantity):
                    print("Cette transaction est déjà enregistrée : rien n'est ajouté.")
                else:
                    t = service.add_transaction(session, args.day, isin, args.side, quantity,
                                                round(args.amount / quantity, 4), args.fees, args.note)
                    print(f"Enregistré : {t.day} {t.side} {t.quantity:g} x {t.isin} à {t.price_eur:.4f} €.")
            except (LookupError, ValueError) as e:
                print(f"Erreur : {e}", file=sys.stderr)
                return 1
        if args.command == "plans" and args.plans.strip():
            try:
                parsed = []
                for item in args.plans.split(","):
                    isin, amount, frequency = (x.strip() for x in item.split(":"))
                    parsed.append({"isin": isin.upper(), "amount": float(amount), "frequency": frequency})
                tradeplans.replace(session, parsed)
            except (LookupError, ValueError) as e:
                print(f"Erreur : {e} (format : ISIN:montant:fréquence, séparés par des virgules)",
                      file=sys.stderr)
                return 1
        print("Plans Trade Republic en cours :")
        for p in tradeplans.current(session) or [{"name": "aucun", "amount": 0, "frequency_label": ""}]:
            print(f"  {p['name']} : {p['amount']:.0f} € {p['frequency_label']}")
        print("\nTransactions :")
        for t in service.transactions(session):
            print(f"  {t.day}  {t.side:4}  {t.quantity:>8g} x {t.isin}  à {t.price_eur:.4f} €"
                  f"  = {t.quantity * t.price_eur:.2f} €  (frais {t.fees_eur:.2f} €)")
        pf = service.portfolio(session)
        print(f"\nPortefeuille : valeur {pf['total_value'] or 0:.2f} €, versé {pf['contributions']:.2f} €")
        for p in pf["positions"]:
            print(f"  {p['name']}: {p['quantity']:g} part(s), {p['value'] or 0:.2f} €")
    return 0


if __name__ == "__main__":
    sys.exit(main())
