"""Guards between the AI and you: invented figures are flagged, an off-rules plan is rejected."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .facts import Context

_NUMBER = re.compile(r"(?<![\w.])\d+(?:[  ]\d{3})*(?:[.,]\d+)?")
_FACT_ID = re.compile(r"\[?F\d+\]?")


def numbers(text: str) -> list[float]:
    """Figures written in a text ('31,3', '4 000', '13 %'); fact ids like F12 are not figures."""
    text = _FACT_ID.sub(" ", text)
    out = []
    for raw in _NUMBER.findall(text):
        try:
            out.append(float(raw.replace(" ", "").replace(" ", "").replace(",", ".")))
        except ValueError:
            continue
    return out


def unverified(text: str, ctx: Context) -> list[float]:
    """Figures of the text found in no fact (small counts like '2 actions' are not checked)."""
    known = {n for fact in ctx.facts.values() for n in numbers(fact)}
    known |= {float(ctx.profile.get("monthly", 0)), float(ctx.profile.get("min_order_eur", 0))}
    missing = []
    for n in numbers(text):
        if n == int(n) and (n <= 10 or 1990 <= n <= 2100):
            continue  # small counts ("2 actions") and years are not checked
        if not any(_same(n, k) for k in known):
            missing.append(n)
    return missing


def _same(n: float, k: float) -> bool:
    """Equal up to the rounding a writer would do: 31,3 -> 31 is fine, 77,0 -> 77,7 is not."""
    if abs(n - k) <= 0.051:
        return True
    if n == int(n) and abs(n - k) < 0.5:
        return True
    return abs(k) >= 100 and abs(n - k) / abs(k) <= 0.005


def known_facts(ids: list[str], ctx: Context) -> list[str]:
    return [i for i in ids if i in ctx.facts]


@dataclass
class OrderCheck:
    ok: bool
    errors: list[str]
    orders: list[dict]


def check_orders(orders: list[dict], ctx: Context) -> OrderCheck:
    """The manager's plan must respect every rule of brick 3, exactly."""
    p = ctx.profile
    budget, core_isin, min_order = p["monthly"], p["core_isin"], p["min_order_eur"]
    core_min = round(budget * p["core_share"])
    allowed = {core_isin} | set(ctx.companies)
    total_after = (ctx.portfolio.get("total_value") or 0) + budget
    values = {x["isin"]: x["value"] or 0 for x in ctx.portfolio.get("positions", [])}
    errors = []
    seen = set()
    clean = []
    for o in orders:
        isin, amount = o["isin"], float(o["amount"])
        if isin in seen:
            errors.append(f"{isin} apparaît deux fois")
        seen.add(isin)
        if isin not in allowed:
            errors.append(f"{isin} n'est pas dans la liste autorisée")
        if amount != int(amount) or amount < 0:
            errors.append(f"montant non entier ou négatif pour {isin}")
        if isin == core_isin:
            if amount < core_min:
                errors.append(f"l'ETF monde reçoit {amount:.0f} € au lieu d'au moins {core_min} €")
        elif amount > 0:
            if amount < min_order:
                errors.append(f"{isin} reçoit {amount:.0f} €, sous le minimum de {min_order:.0f} €")
            if values.get(isin, 0) >= p["max_position_share"] * total_after:
                errors.append(f"{isin} est déjà au plafond de {p['max_position_share'] * 100:.0f} %")
        if amount > 0:
            clean.append({**o, "amount": amount})
    if core_isin not in seen:
        errors.append("l'ETF monde est absent du plan")
    total = sum(o["amount"] for o in clean)
    if abs(total - budget) > 0.5:
        errors.append(f"le total fait {total:.0f} € au lieu de {budget:.0f} €")
    return OrderCheck(not errors, errors, clean)
