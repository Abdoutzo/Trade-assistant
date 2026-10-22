"""The rules that turn your monthly payment into Trade Republic savings plans.

Why savings plans: on Trade Republic they cost nothing, a manual order costs 1 euro (10 % of a
10-euro order). So the output is a list of plans with a fixed amount per line, meant to stay the
same month after month; you only edit a plan when the proposal changes.

Rules, in order:
1. The core (world ETF) receives its share of the payment, every month.
2. The satellites receive the rest, split equally between as many stocks as the budget allows
   with at least min_order euros each.
3. When there are more selected stocks than the budget can fund, the most underweight ones are
   fed first: the portfolio rebalances itself through new money, without selling (no tax).
4. A stock above max_position_share of the portfolio is not bought again until it falls back.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Order:
    isin: str
    amount_eur: float
    role: str  # "core" | "satellite"
    reason: str


def split(budget: float, core_share: float, core_isin: str, satellites: list[str], values: dict[str, float],
          max_position_share: float = 0.10, min_order: float = 10.0) -> list[Order]:
    """values: current market value in euros of each held line (any isin, core included)."""
    if budget <= 0:
        return []
    total_after = sum(values.values()) + budget
    core_amount = round(budget * core_share)
    satellite_budget = budget - core_amount

    # Rule 4: stocks already at their cap are skipped this month.
    cap = max_position_share * total_after
    eligible = [s for s in satellites if values.get(s, 0.0) < cap]
    capped = [s for s in satellites if s not in eligible]

    count = min(len(eligible), int(satellite_budget // min_order)) if min_order > 0 else len(eligible)
    orders: list[Order] = []
    if count:
        # Rule 3: equal target weight for every selected stock, the furthest below it first.
        target = (sum(values.get(s, 0.0) for s in satellites) + satellite_budget) / len(satellites)
        chosen = sorted(eligible, key=lambda s: (values.get(s, 0.0) - target, satellites.index(s)))[:count]
        base, rest = divmod(round(satellite_budget), count)
        for k, isin in enumerate(sorted(chosen, key=satellites.index)):
            amount = base + (1 if k < rest else 0)
            gap = target - values.get(isin, 0.0)
            reason = ("nouvelle ligne" if values.get(isin, 0.0) == 0 else
                      f"sous la cible de {gap:,.0f} €".replace(",", " ") if gap > 0 else "à la cible")
            orders.append(Order(isin, float(amount), "satellite", reason))
    else:
        core_amount = budget  # nothing fundable: everything to the core

    funded = sum(o.amount_eur for o in orders)
    core_amount = budget - funded
    reason = f"{round(core_amount / budget * 100)} % du versement sur l'ETF monde"
    if capped:
        reason += f" ; {len(capped)} action(s) au plafond de {max_position_share:.0%} non achetée(s)"
    if satellites and count < len(eligible):
        reason += (f" ; {len(eligible) - count} action(s) attendent leur tour (minimum {min_order:.0f} € "
                   f"par ligne)")
    return [Order(core_isin, float(core_amount), "core", reason)] + orders
