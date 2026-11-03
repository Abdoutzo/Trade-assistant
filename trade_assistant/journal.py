"""Brick 8: the journal. Did your choices beat the simplest alternative, everything on the world ETF?

Every euro you really put in (each purchase, on its day) is replayed in a "shadow" portfolio that
buys the world ETF instead; every sale takes the same euros out of it. Comparing both, overall, per
line and per month of purchase, says whether picking stocks adds anything. Only years can tell: the
journal says so as long as the history is short.

Simplifications: values use closing prices; dividends paid in cash by the stocks are not recorded
(the world ETF reinvests its own), which slightly favours the ETF.
"""
from __future__ import annotations

from bisect import bisect_right
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .data import store
from .models import MonthlyPlan
from .portfolio import service
from .portfolio.backtest import xirr
from .profile import get_profile

MIN_MONTHS = 12  # below, a difference says nothing


class Prices:
    """Closing prices in euros, looked up at a date (last known close at or before it)."""

    def __init__(self, session: Session, isins: set[str], since: date) -> None:
        self.days: dict[str, list[date]] = {}
        self.closes: dict[str, list[float]] = {}
        now = service.share_prices(session, sorted(isins))
        for isin in isins:
            instrument = store.get_instrument(session, isin)
            rows = store.prices(session, instrument, since=since - timedelta(days=10)) if instrument else []
            # Same conversion rate as today's euro price (the PEA universe is almost all in euros).
            rate = now[isin] / rows[-1].close if rows and now.get(isin) else 1.0
            self.days[isin] = [r.day for r in rows]
            self.closes[isin] = [r.close * rate for r in rows]

    def at(self, isin: str, day: date) -> float | None:
        days = self.days.get(isin) or []
        if not days:
            return None
        k = bisect_right(days, day) - 1
        return self.closes[isin][max(k, 0)]  # before the first known day: the first close


def _cash(t) -> float:
    """Euros that left your pocket (a buy, fees included) or came back (a sale, fees deducted)."""
    amount = t.quantity * t.price_eur
    return amount + t.fees_eur if t.side == "buy" else -(amount - t.fees_eur)


def _month_ends(first: date, last: date) -> list[date]:
    out, d = [], date(first.year, first.month, 1)
    while d <= last:
        nxt = date(d.year + d.month // 12, d.month % 12 + 1, 1)
        out.append(min(nxt - timedelta(days=1), last))
        d = nxt
    if out[-1] != last:
        out.append(last)
    return out


def journal(session: Session, today: date | None = None) -> dict:
    today = today or date.today()
    r = service.rules(get_profile(session))
    core = r["core_isin"]
    trades = sorted(service.transactions(session), key=lambda t: (t.day, t.id))
    if not trades:
        return {"empty": True}
    names = {}
    for t in trades:
        instrument = store.get_instrument(session, t.isin)
        names[t.isin] = instrument.name if instrument else t.isin
    prices = Prices(session, {t.isin for t in trades} | {core}, trades[0].day)
    if prices.at(core, today) is None:
        return {"empty": True, "error": "Pas de cours pour l'ETF monde : actualise les données."}

    def units(t) -> float:
        """ETF shares the shadow buys (or sells) for this trade: the real ones for the ETF itself."""
        if t.isin == core:
            return t.quantity if t.side == "buy" else -t.quantity
        return _cash(t) / prices.at(core, t.day)

    def state(day: date) -> tuple[float, float, float]:
        """(your value, shadow value, money put in) at the end of a day."""
        held: dict[str, float] = {}
        shares = invested = 0.0
        for t in trades:
            if t.day > day:
                break
            held[t.isin] = held.get(t.isin, 0.0) + (t.quantity if t.side == "buy" else -t.quantity)
            shares += units(t)
            invested += _cash(t)
        value = sum(q * (prices.at(i, day) or 0.0) for i, q in held.items() if q > 1e-9)
        return value, shares * prices.at(core, day), invested

    value, shadow, invested = state(today)
    flows = [(t.day, -_cash(t)) for t in trades]

    lines = []
    for isin in dict.fromkeys(t.isin for t in trades):
        mine = [t for t in trades if t.isin == isin]
        quantity = sum(t.quantity if t.side == "buy" else -t.quantity for t in mine)
        now = quantity * (prices.at(isin, today) or 0.0)
        sold = sum(-_cash(t) for t in mine if t.side == "sell")
        cost = sum(_cash(t) for t in mine if t.side == "buy")
        etf = sum(units(t) for t in mine) * prices.at(core, today) + sold
        lines.append({"isin": isin, "name": names[isin], "role": "core" if isin == core else "satellite",
                      "since": mine[0].day.isoformat(), "quantity": quantity, "invested": cost,
                      "value": now + sold, "if_etf": etf, "difference": now + sold - etf,
                      "return": (now + sold) / cost - 1 if cost else None,
                      "etf_return": etf / cost - 1 if cost else None})
    lines.sort(key=lambda x: (x["role"] != "satellite", x["difference"]))

    plans = {}
    for p in session.scalars(select(MonthlyPlan).where(MonthlyPlan.status.in_(["approved", "rejected"]))
                             .order_by(MonthlyPlan.created_at)):
        plans[p.month] = p  # the last decision of each month
    months = []
    for month in sorted({t.day.strftime("%Y-%m") for t in trades} | set(plans)):
        bought = [t for t in trades if t.day.strftime("%Y-%m") == month]
        now = sum((t.quantity if t.side == "buy" else -t.quantity) * (prices.at(t.isin, today) or 0.0)
                  for t in bought)
        etf = sum(units(t) for t in bought) * prices.at(core, today)
        plan = plans.get(month)
        decided = (plan.data or {}) if plan else {}
        months.append({
            "month": month, "invested": sum(_cash(t) for t in bought), "value": now, "if_etf": etf,
            "difference": now - etf,
            "trades": [{"name": names[t.isin], "side": t.side, "quantity": t.quantity, "amount": _cash(t)}
                       for t in bought],
            "plan": {"id": plan.id, "status": plan.status, "note": plan.note, "source": decided.get("source"),
                     "orders": [{"name": o["name"], "amount": o["amount"]}
                                for o in decided.get("orders", ())]}
            if plan else None})

    chart = {"days": [], "mine": [], "etf": [], "invested": []}
    for day in dict.fromkeys([trades[0].day, *_month_ends(trades[0].day, today)]):
        v, s, i = state(day)
        chart["days"].append(day.isoformat())
        chart["mine"].append(round(v, 2))
        chart["etf"].append(round(s, 2))
        chart["invested"].append(round(i, 2))

    age = (today - trades[0].day).days / 30.44
    return {
        "empty": False, "since": trades[0].day.isoformat(), "months": round(age, 1),
        "value": value, "if_etf": shadow, "invested": invested, "difference": value - shadow,
        "xirr": xirr(flows + [(today, value)]) if age >= MIN_MONTHS else None,
        "etf_xirr": xirr(flows + [(today, shadow)]) if age >= MIN_MONTHS else None,
        "verdict": verdict(value - shadow, invested, age), "lines": lines, "by_month": months[::-1],
        "chart": chart,
    }


def verdict(difference: float, invested: float, months: float) -> str:
    gap = f"{abs(difference):,.0f} €".replace(",", " ")
    share = f"{abs(difference) / invested * 100 if invested else 0:.1f}".replace(".", ",")
    if abs(difference) < 1:
        where = "Tes choix font pour l'instant à peu près comme l'ETF monde seul (moins de 1 € d'écart)."
    else:
        how = "de mieux" if difference > 0 else "de moins"
        where = (f"Tes choix font pour l'instant {gap} {how} que l'ETF monde seul ({share} % de ce "
                 "que tu as versé).")
    if months < MIN_MONTHS:
        return (f"{where} Trop tôt pour en tirer une conclusion : {months:.0f} mois d'historique, il faut au "
                "moins un an, idéalement 3 à 5.")
    if difference < 0:
        return (f"{where} Si l'écart persiste sur plusieurs années, la décision rationnelle est "
                "d'augmenter la part de l'ETF (Réglages).")
    return f"{where} À confirmer dans la durée : un bon début ne prouve pas encore un talent."


def summary_line(session: Session) -> str | None:
    """One sentence for the e-mail and the agent."""
    j = journal(session)
    return None if j["empty"] else j["verdict"]
