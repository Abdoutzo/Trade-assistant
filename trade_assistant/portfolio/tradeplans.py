"""From "how many euros per month on each line" to savings plans that Trade Republic can really run.

Two constraints of Trade Republic shape the plans:
- in a PEA, only whole shares are bought: a plan of 10 euros never buys a 57-euro share;
- a plan runs weekly, twice a month, monthly or quarterly, nothing longer.

So a line whose share costs more than its monthly amount becomes a quarterly plan (3 months of
money, enough for at least one share), and a line still too expensive gives its money to another
stock of the plan, or to the world ETF. Then the result is compared with the plans you already run:
each month you only touch what changes.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..data import store
from ..models import TradePlan

FREQUENCIES = {  # executions per month, label
    "weekly": (52 / 12, "chaque semaine"),
    "twice_monthly": (2.0, "deux fois par mois"),
    "monthly": (1.0, "chaque mois"),
    "quarterly": (1 / 3, "tous les 3 mois"),
}
MARGIN = 1.03  # the price moves until the execution day: keep 3 % of room above one share


def _eur(x: float, digits: int = 0) -> str:
    return f"{x:,.{digits}f} €".replace(",", " ").replace(".", ",")


def label(frequency: str) -> str:
    return FREQUENCIES[frequency][1]


def monthly(amount: float, frequency: str) -> float:
    return amount * FREQUENCIES[frequency][0]


# --- The plans you run today ---------------------------------------------------------------------

def current(session: Session) -> list[dict]:
    out = []
    for p in session.scalars(select(TradePlan).order_by(TradePlan.amount_eur.desc())):
        instrument = store.get_instrument(session, p.isin)
        out.append({"isin": p.isin, "name": instrument.name if instrument else p.isin, "amount": p.amount_eur,
                    "frequency": p.frequency, "frequency_label": label(p.frequency),
                    "monthly": round(monthly(p.amount_eur, p.frequency), 2)})
    return out


def replace(session: Session, plans: list[dict]) -> list[dict]:
    """Your plans as they are now on Trade Republic (the whole list replaces the previous one)."""
    for p in plans:
        if p["frequency"] not in FREQUENCIES:
            raise ValueError(f"Fréquence inconnue : {p['frequency']}")
        if store.get_instrument(session, p["isin"]) is None:
            raise LookupError(f"{p['isin']} n'est pas dans l'univers : ajoute-le d'abord (Univers et analyses).")
    if len({p["isin"] for p in plans}) != len(plans):
        raise ValueError("Un seul plan par titre.")
    for row in session.scalars(select(TradePlan)):
        session.delete(row)
    session.flush()
    for p in plans:
        session.add(TradePlan(isin=p["isin"].upper(), amount_eur=float(p["amount"]), frequency=p["frequency"]))
    session.commit()
    return current(session)


# --- What Trade Republic can run -----------------------------------------------------------------

def _fit(amount: float, price: float | None, whole_shares: bool) -> tuple[str, float] | None:
    """(frequency, amount per execution) for this monthly amount, or None if no share fits."""
    if not whole_shares or price is None or price * MARGIN <= amount:
        return "monthly", float(round(amount))
    if price * MARGIN <= 3 * amount:
        return "quarterly", float(round(3 * amount))
    return None


def practical(orders: list[dict], prices: dict[str, float | None], whole_shares: bool) -> tuple[list[dict], list[str]]:
    """orders: monthly amounts per line, most important first. Returns the plans and the notes."""
    plans: dict[str, dict] = {}
    notes: list[str] = []
    pooled, too_expensive = 0.0, []
    for o in orders:
        if o["amount"] <= 0:
            continue
        fit = _fit(o["amount"], prices.get(o["isin"]), whole_shares)
        if fit:
            plans[o["isin"]] = {**o, "monthly": o["amount"]}
        else:
            pooled += o["amount"]
            too_expensive.append(o)
    if pooled:
        # The money of the stocks out of reach goes to the first stock it makes affordable.
        receiver = None
        for o in [x for x in orders if x["role"] == "satellite"]:
            base = plans[o["isin"]]["monthly"] if o["isin"] in plans else 0.0  # else: already pooled
            if _fit(base + pooled, prices.get(o["isin"]), whole_shares):
                receiver = o
                break
        if receiver:
            base = plans[receiver["isin"]]["monthly"] if receiver["isin"] in plans else 0.0
            plans[receiver["isin"]] = {**receiver, "monthly": base + pooled}
            target = receiver["name"]
        else:
            core = next(o for o in orders if o["role"] == "core")
            plans[core["isin"]]["monthly"] += pooled
            target = "l'ETF monde"
        for o in too_expensive:
            if o["isin"] in plans:  # the receiver itself: made affordable by the pooled money
                continue
            price = prices.get(o["isin"])
            notes.append(f"{o['name']} : une action coûte {_eur(price)}, plus que ton budget actions sur 3 mois ; "
                         f"ses {_eur(o['amount'])} par mois vont à {target}.")
    out = []
    for o in sorted(plans.values(), key=lambda x: (x["role"] != "core", -x["monthly"])):
        frequency, amount = _fit(o["monthly"], prices.get(o["isin"]), whole_shares)
        price = prices.get(o["isin"])
        out.append({"isin": o["isin"], "name": o["name"], "role": o["role"], "amount": amount,
                    "frequency": frequency, "frequency_label": label(frequency), "monthly": round(o["monthly"], 2),
                    "share_price": round(price, 2) if price else None})
        if frequency == "quarterly":
            notes.append(f"{o['name']} : une action coûte {_eur(price, 2)}, plus que {_eur(o['monthly'])} par mois ; "
                         f"plan trimestriel de {_eur(amount)} (les {_eur(o['monthly'])} mis de côté chaque mois "
                         "restent en espèces sur ton compte jusqu'à l'achat).")
    return out, notes


def actions(proposed: list[dict], running: list[dict]) -> list[dict]:
    """What to do in Trade Republic: keep, update, create or delete each plan."""
    now = {p["isin"]: p for p in running}
    out = []
    for p in proposed:
        c = now.pop(p["isin"], None)
        target = f"{p['amount']:.0f} € {p['frequency_label']}"
        if c is None:
            out.append({"kind": "create", "isin": p["isin"], "name": p["name"],
                        "text": f"Crée un plan {p['name']} ({p['isin']}) : {target}."})
        elif c["frequency"] == p["frequency"] and abs(c["amount"] - p["amount"]) < 1:
            out.append({"kind": "keep", "isin": p["isin"], "name": p["name"],
                        "text": f"Garde le plan {p['name']} : {target}."})
        else:
            out.append({"kind": "update", "isin": p["isin"], "name": p["name"],
                        "text": f"Modifie le plan {p['name']} : {c['amount']:.0f} € {c['frequency_label']} "
                                f"→ {target}."})
    for c in now.values():
        out.append({"kind": "delete", "isin": c["isin"], "name": c["name"],
                    "text": f"Supprime le plan {c['name']} (tu gardes les parts déjà achetées)."})
    return out


def checklist(todo: list[dict], first_payment: list[dict] | None, running: list[dict]) -> list[str]:
    changes = [a for a in todo if a["kind"] != "keep"]
    if running and not changes:
        steps = ["Rien à changer dans Trade Republic : tes plans en cours correspondent au plan du mois."]
    else:
        steps = ["Ouvre Trade Republic > PEA > Plans d'investissement."] + [a["text"] for a in todo]
        if not running:
            steps.append("Puis enregistre tes plans dans Portefeuille > Mes plans Trade Republic : le mois "
                         "prochain, l'outil ne te dira que ce qui change.")
        else:
            steps.append("Puis mets à jour Portefeuille > Mes plans Trade Republic.")
    if first_payment:
        steps.append("Premier versement (ordres ponctuels, 1 € de frais chacun) : "
                     + ", ".join(f"{o['name']} {o['amount']:.0f} €" for o in first_payment) + ".")
    steps.append("Après les exécutions, enregistre les achats dans Portefeuille > Transactions.")
    return steps


def realize(orders: list[dict], prices: dict[str, float | None], whole_shares: bool, running: list[dict],
            first_payment: list[dict] | None = None) -> dict:
    plans, notes = practical(orders, prices, whole_shares)
    todo = actions(plans, running)
    return {"trade_plans": plans, "plan_notes": notes, "actions": todo,
            "checklist": checklist(todo, first_payment, running)}
