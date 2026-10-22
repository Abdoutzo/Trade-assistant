"""Portfolio glue: transactions, valuation, stock selection, monthly plans, simulation."""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..analysis import service as analysis
from ..data import store, yahoo
from ..data.http import SourceError
from ..models import Instrument, InvestorProfile, SatelliteChoice, Transaction
from ..profile import get_profile
from . import allocation, backtest, positions

log = logging.getLogger(__name__)

DEFAULT_CORE_ISIN = "FR001400U5Q4"  # Amundi PEA Monde (MSCI World), 0 fee savings plans
REFERENCE_ISIN = "IE00B4L5Y983"  # iShares Core MSCI World: same index, prices since 2009, for simulations
DEFAULTS = {"satellites_count": 5, "max_position_share": 0.10, "min_order_eur": 10.0}
MIN_SCORE = 60  # below, a stock is not proposed
MAX_PER_SECTOR = 2  # diversification of the satellites
LONG_RUN_RATE = 0.07  # world equities over a century, roughly: the prudent projection uses it


def rules(profile: InvestorProfile) -> dict:
    def pick(value, default):
        return default if value is None else value

    return {
        "core_isin": profile.core_isin or DEFAULT_CORE_ISIN,
        "satellites_count": pick(profile.satellites_count, DEFAULTS["satellites_count"]),
        "max_position_share": pick(profile.max_position_share, DEFAULTS["max_position_share"]),
        "min_order_eur": pick(profile.min_order_eur, DEFAULTS["min_order_eur"]),
    }


# --- Transactions and positions ------------------------------------------------------------------

def transactions(session: Session) -> list[Transaction]:
    return list(session.scalars(select(Transaction).order_by(Transaction.day.desc(), Transaction.id.desc())))


def _eur_price(session: Session, instrument: Instrument) -> tuple[float, date] | None:
    series = store.prices(session, instrument, since=date.today().replace(year=date.today().year - 1))
    if not series:
        return None
    rate = 1.0
    if instrument.currency and instrument.currency != "EUR":
        try:
            rate = yahoo.fx_rate(instrument.currency, "EUR")
        except SourceError:
            return None
    return series[-1].close * rate, series[-1].day


def portfolio(session: Session) -> dict:
    """Positions valued at the last close, weights against the targets, and what deserves a look."""
    profile = get_profile(session)
    r = rules(profile)
    book = positions.build([positions.TradeIn(t.day, t.isin, t.side, t.quantity, t.price_eur, t.fees_eur)
                            for t in transactions(session)])
    lines, total = [], 0.0
    for isin, p in book.positions.items():
        if p.quantity <= 1e-9:
            continue
        instrument = store.get_instrument(session, isin)
        priced = _eur_price(session, instrument) if instrument else None
        value = p.quantity * priced[0] if priced else None
        total += value or 0.0
        lines.append({"isin": isin, "name": instrument.name if instrument else isin,
                      "kind": instrument.kind if instrument else None,
                      "sector": instrument.sector if instrument else None,
                      "pea_eligible": instrument.pea_eligible if instrument else None,
                      "role": "core" if isin == r["core_isin"] or (instrument and instrument.kind == "etf")
                      else "satellite",
                      "quantity": p.quantity, "average_cost": p.average_cost, "cost": p.cost_eur,
                      "price": priced[0] if priced else None,
                      "price_day": priced[1].isoformat() if priced else None,
                      "value": value, "gain": value - p.cost_eur if value is not None else None,
                      "gain_pct": (value / p.cost_eur - 1) if value and p.cost_eur else None,
                      "realized": p.realized_eur})
    for line in lines:
        line["weight"] = line["value"] / total if total and line["value"] is not None else None
    lines.sort(key=lambda x: -(x["value"] or 0))

    core_value = sum(x["value"] or 0 for x in lines if x["role"] == "core")
    satellite_value = total - core_value
    sectors: dict[str, float] = {}
    for x in lines:
        if x["role"] == "satellite" and x["value"]:
            sectors[x["sector"] or "Inconnu"] = sectors.get(x["sector"] or "Inconnu", 0) + x["value"]

    warnings = list(book.errors)
    for x in lines:
        if x["role"] == "satellite" and x["weight"] and x["weight"] > r["max_position_share"]:
            warnings.append(f"{x['name']} pèse {x['weight']:.0%} du portefeuille (plafond "
                            f"{r['max_position_share']:.0%}) : elle ne sera plus renforcée tant "
                            "qu'elle dépasse.")
        if profile.account_type == "PEA" and x["pea_eligible"] is False:
            warnings.append(f"{x['name']} n'est pas éligible au PEA.")
    if total and abs(core_value / total - profile.core_share) > 0.10:
        warnings.append(f"Le cœur (ETF) fait {core_value / total:.0%} du portefeuille pour une cible de "
                        f"{profile.core_share:.0%} : les prochains versements corrigeront l'écart.")
    for sector, value in sectors.items():
        if satellite_value and value / satellite_value > 0.40 and len(sectors) > 1:
            warnings.append(f"Le secteur {sector} fait {value / satellite_value:.0%} des actions choisies : "
                            "peu diversifié.")

    return {
        "total_value": total, "contributions": book.contributions_eur, "gain": total - book.contributions_eur,
        "core_value": core_value, "satellite_value": satellite_value,
        "core_weight": core_value / total if total else None, "core_target": profile.core_share,
        "sectors": dict(sorted(sectors.items(), key=lambda kv: -kv[1])), "positions": lines,
        "warnings": warnings, "rules": r,
    }


def add_transaction(session: Session, day: date, isin: str, side: str, quantity: float, price_eur: float,
                    fees_eur: float = 0.0, note: str | None = None) -> Transaction:
    isin = isin.strip().upper()
    if store.get_instrument(session, isin) is None:
        raise LookupError(f"{isin} n'est pas dans l'univers : ajoute-le d'abord (Univers et analyses).")
    if side == "sell":
        held = positions.build([positions.TradeIn(t.day, t.isin, t.side, t.quantity, t.price_eur, t.fees_eur)
                                for t in transactions(session) if t.isin == isin]).positions.get(isin)
        if held is None or quantity > held.quantity + 1e-9:
            raise ValueError(f"Tu ne détiens que {held.quantity if held else 0:g} part(s) de {isin}.")
    t = Transaction(day=day, isin=isin, side=side, quantity=quantity, price_eur=price_eur, fees_eur=fees_eur,
                    note=note)
    session.add(t)
    session.commit()
    return t


# --- Selection of the satellites and monthly plans -----------------------------------------------

def choices(session: Session) -> dict[str, str]:
    return {c.isin: c.status for c in session.scalars(select(SatelliteChoice))}


def set_choice(session: Session, isin: str, status: str | None) -> None:
    row = session.scalar(select(SatelliteChoice).where(SatelliteChoice.isin == isin))
    if status is None:
        if row:
            session.delete(row)
    elif row:
        row.status = status
    else:
        session.add(SatelliteChoice(isin=isin, status=status))
    session.commit()


def selection(session: Session, held: dict[str, float] | None = None) -> list[dict]:
    """The stocks to buy: held ones, pinned ones, then the best scores, 2 per sector at most."""
    profile = get_profile(session)
    r = rules(profile)
    picks = choices(session)
    held = held or {}
    analyses = {i.isin: (i, d) for i, d in analysis.all_analyses(session) if i.kind == "stock"}

    def allowed(i: Instrument) -> bool:
        return picks.get(i.isin) != "excluded" and (profile.account_type != "PEA" or i.pea_eligible is True)

    chosen: list[dict] = []

    def add(i: Instrument, data: dict, reason: str) -> None:
        if all(c["isin"] != i.isin for c in chosen):
            chosen.append({"isin": i.isin, "name": i.name, "sector": i.sector, "score": data.get("score"),
                           "pinned": picks.get(i.isin) == "pinned", "held": held.get(i.isin, 0) > 0,
                           "reason": reason})

    for isin in sorted(held, key=lambda k: -held[k]):
        if isin in analyses and allowed(analyses[isin][0]):
            add(*analyses[isin], "déjà en portefeuille")
    for isin, status in picks.items():
        if status == "pinned" and isin in analyses and allowed(analyses[isin][0]):
            add(*analyses[isin], "épinglée par toi")
    per_sector: dict[str | None, int] = {}
    for c in chosen:
        per_sector[c["sector"]] = per_sector.get(c["sector"], 0) + 1
    ranked = sorted(analyses.values(), key=lambda x: -(x[1].get("score") or 0))
    for i, data in ranked:
        if len(chosen) >= r["satellites_count"]:
            break
        too_many = per_sector.get(i.sector, 0) >= MAX_PER_SECTOR
        if not allowed(i) or (data.get("score") or 0) < MIN_SCORE or too_many:
            continue
        per_sector[i.sector] = per_sector.get(i.sector, 0) + 1
        add(i, data, f"note {data.get('score')}/100, parmi les meilleures de l'univers")
    return chosen


def plan(session: Session) -> dict:
    """This month's savings plans on Trade Republic, and why."""
    profile = get_profile(session)
    r = rules(profile)
    current = portfolio(session)
    values = {p["isin"]: p["value"] or 0.0 for p in current["positions"]}
    targets = selection(session, {p["isin"]: p["value"] or 0.0 for p in current["positions"]
                                  if p["role"] == "satellite"})
    orders = allocation.split(profile.monthly_amount_eur, profile.core_share, r["core_isin"],
                              [t["isin"] for t in targets], values, r["max_position_share"],
                              r["min_order_eur"])
    names = {t["isin"]: t["name"] for t in targets}
    core = store.get_instrument(session, r["core_isin"])
    names[r["core_isin"]] = core.name if core else r["core_isin"]
    return {
        "monthly_amount": profile.monthly_amount_eur,
        "orders": [{"isin": o.isin, "name": names.get(o.isin, o.isin), "amount": o.amount_eur, "role": o.role,
                    "reason": o.reason} for o in orders if o.amount_eur > 0],
        "targets": targets, "rules": r,
        "first_payment": None if current["positions"] else allocation_first(session, profile, r, targets),
    }


def allocation_first(session: Session, profile: InvestorProfile, r: dict, targets: list[dict]) -> list[dict]:
    """The starting amount, split with the same rules (one-off orders, 1 euro each on Trade Republic)."""
    orders = allocation.split(profile.initial_amount_eur, profile.core_share, r["core_isin"],
                              [t["isin"] for t in targets], {}, r["max_position_share"], r["min_order_eur"])
    names = {t["isin"]: t["name"] for t in targets}
    return [{"isin": o.isin, "name": names.get(o.isin, "ETF monde"), "amount": o.amount_eur, "role": o.role}
            for o in orders if o.amount_eur > 0]


# --- Simulation ----------------------------------------------------------------------------------

def ensure_reference(session: Session) -> Instrument | None:
    """The long-history MSCI World series used to simulate the core before the PEA ETF existed."""
    instrument = store.get_instrument(session, REFERENCE_ISIN)
    try:
        if instrument is None:
            instrument = store.add_instrument(session, REFERENCE_ISIN)
        if not instrument.is_reference:
            instrument.is_reference = True
            session.commit()
        if not store.prices(session, instrument, since=date.today().replace(year=date.today().year - 1)):
            store.refresh_prices(session, instrument)
    except (SourceError, LookupError) as e:
        log.warning("Reference series unavailable: %s", e)
        return None
    return instrument


def simulation(session: Session, years: int = 10, satellites: list[str] | None = None) -> dict:
    profile = get_profile(session)
    r = rules(profile)
    reference = ensure_reference(session)
    if reference is None:
        raise LookupError("Série de référence MSCI World indisponible pour l'instant.")
    if satellites is None:
        satellites = [t["isin"] for t in selection(session)]
    def monthly(instrument: Instrument) -> dict:
        return backtest.first_of_month([(p.day, p.adj_close) for p in store.prices(session, instrument)])

    series = {REFERENCE_ISIN: monthly(reference)}
    names = {}
    for isin in satellites:
        instrument = store.get_instrument(session, isin)
        if instrument:
            names[isin] = instrument.name
            series[isin] = monthly(instrument)
    months = sorted(series[REFERENCE_ISIN])[-(years * 12):]
    if len(months) < 24:
        raise LookupError("Moins de 2 ans d'historique : simulation impossible.")

    args = dict(initial=profile.initial_amount_eur, monthly=profile.monthly_amount_eur,
                max_position_share=r["max_position_share"], min_order=r["min_order_eur"])
    strategy = backtest.simulate(series, months, REFERENCE_ISIN, list(names), core_share=profile.core_share,
                                 **args)
    core_only = backtest.simulate(series, months, REFERENCE_ISIN, [], core_share=1.0, **args)
    horizon = profile.horizon_years * 12

    def project(returns: list[float]) -> dict | None:
        return backtest.project(returns, profile.initial_amount_eur, profile.monthly_amount_eur, horizon)

    late = [names[i] for i in names if min(series[i]) > months[0]]
    warnings = [
        "Biais rétrospectif : ces actions sont choisies aujourd'hui, avec ce que l'on sait aujourd'hui "
        "de leur succès. Il y a 10 ans, rien ne garantissait de les choisir. Le vrai test, c'est le "
        "journal (brique 8).",
        "Le cœur est simulé avec l'iShares Core MSCI World (même indice, cours depuis 2009), l'ETF PEA "
        "n'existant que depuis peu. Frais de gestion comparables.",
    ]
    core_rate = backtest.stats(core_only).get("time_weighted_return")
    if core_rate and core_rate > LONG_RUN_RATE + 0.02:
        warnings.append(f"Sur cette période, l'indice monde a fait {core_rate:.1%} par an, bien plus "
                        f"que sa moyenne de long terme (environ {LONG_RUN_RATE:.0%}) : la projection "
                        "prudente en tient compte.")
    if late:
        warnings.append("Entrées en cours de route (cotées après le début) : " + ", ".join(late) + ".")
    return {
        "years": len(months) / 12, "satellites": [{"isin": i, "name": n} for i, n in names.items()],
        "chart": {"days": [d.isoformat() for d in strategy.days], "strategy": strategy.values,
                  "core_only": core_only.values, "invested": strategy.invested},
        "strategy": backtest.stats(strategy), "core_only": backtest.stats(core_only),
        "projection": {
            "horizon_years": profile.horizon_years,
            "long_run_rate": LONG_RUN_RATE,
            "strategy": project(strategy.returns),
            "core_only": project(core_only.returns),
            # Same ups and downs, but a world index averaging 7 %/year: the long-run norm.
            "strategy_normalized": project(backtest.normalize(strategy.returns, core_only.returns,
                                                              LONG_RUN_RATE)),
            "core_only_normalized": project(backtest.normalize(core_only.returns, core_only.returns,
                                                               LONG_RUN_RATE)),
        },
        "warnings": warnings,
    }
