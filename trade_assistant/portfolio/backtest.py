"""Replays the monthly rules on past prices, and projects a range of outcomes.

Month by month: on the first trading day, the payment is split by allocation.split exactly as it
would be today, and the shares are bought at that day's price (dividends reinvested: adjusted
prices). No fees (savings plans) and no tax (PEA held over 5 years).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import date

from . import allocation

Month = tuple[int, int]


def first_of_month(series: list[tuple[date, float]]) -> dict[Month, tuple[date, float]]:
    """The first trading day of each month and its price."""
    out: dict[Month, tuple[date, float]] = {}
    for day, price in series:
        out.setdefault((day.year, day.month), (day, price))
    return out


@dataclass
class Simulation:
    days: list[date] = field(default_factory=list)
    values: list[float] = field(default_factory=list)  # portfolio value right after each payment
    invested: list[float] = field(default_factory=list)  # cumulated payments
    returns: list[float] = field(default_factory=list)  # monthly time-weighted returns
    units: dict[str, float] = field(default_factory=dict)
    final_value: float = 0.0
    final_day: date | None = None


def simulate(prices: dict[str, dict[Month, tuple[date, float]]], months: list[Month], core_isin: str,
             satellites: list[str], initial: float, monthly: float, core_share: float,
             max_position_share: float = 0.10, min_order: float = 10.0) -> Simulation:
    sim = Simulation()
    last_price: dict[str, float] = {}
    previous_after: float | None = None
    for month in months:
        for isin, by_month in prices.items():
            if month in by_month:
                last_price[isin] = by_month[month][1]
        if core_isin not in last_price:
            continue
        values = {i: u * last_price[i] for i, u in sim.units.items() if i in last_price}
        before = sum(values.values())
        if previous_after:
            sim.returns.append(before / previous_after - 1)
        payment = initial if not sim.days else monthly
        available = [s for s in satellites if s in last_price and month in prices.get(s, {})]
        for order in allocation.split(payment, core_share, core_isin, available, values,
                                      max_position_share, min_order):
            sim.units[order.isin] = sim.units.get(order.isin, 0.0) + order.amount_eur / last_price[order.isin]
        after = before + payment
        sim.days.append(prices[core_isin][month][0] if month in prices[core_isin] else date(*month, 1))
        sim.values.append(after)
        sim.invested.append((sim.invested[-1] if sim.invested else 0.0) + payment)
        previous_after = after
    # Final valuation at the latest price of each line.
    latest = {i: max(by_month.values())[1] for i, by_month in prices.items() if by_month}
    sim.final_value = sum(u * latest.get(i, last_price.get(i, 0.0)) for i, u in sim.units.items())
    sim.final_day = max((max(by_month.values())[0] for by_month in prices.values() if by_month), default=None)
    if previous_after and sim.final_value:
        sim.returns.append(sim.final_value / previous_after - 1)
    return sim


def xirr(flows: list[tuple[date, float]]) -> float | None:
    """Annual money-weighted return: the rate at which payments grow into the final value.

    flows: payments negative, final value positive. Bisection, robust and dependency-free.
    """
    if len(flows) < 2 or not any(v > 0 for _, v in flows) or not any(v < 0 for _, v in flows):
        return None
    t0 = flows[0][0]

    def npv(rate: float) -> float:
        return sum(v / (1 + rate) ** ((d - t0).days / 365.25) for d, v in flows)

    low, high = -0.99, 2.0
    if npv(low) * npv(high) > 0:
        return None
    for _ in range(200):
        mid = (low + high) / 2
        if npv(low) * npv(mid) <= 0:
            high = mid
        else:
            low = mid
    return (low + high) / 2


def stats(sim: Simulation) -> dict:
    if not sim.days:
        return {}
    invested = sim.invested[-1]
    flows = [(d, -(sim.invested[i] - (sim.invested[i - 1] if i else 0.0))) for i, d in enumerate(sim.days)]
    flows.append((sim.final_day or sim.days[-1], sim.final_value))
    index, peak, worst_drawdown = 1.0, 1.0, 0.0
    indexes = [1.0]
    for r in sim.returns:
        index *= 1 + r
        indexes.append(index)
        peak = max(peak, index)
        worst_drawdown = min(worst_drawdown, index / peak - 1)
    rolling = [indexes[i + 12] / indexes[i] - 1 for i in range(len(indexes) - 12)]
    n = len(sim.returns)
    mean = sum(sim.returns) / n if n else 0.0
    vol = (sum((r - mean) ** 2 for r in sim.returns) / (n - 1)) ** 0.5 * 12 ** 0.5 if n > 2 else None
    years = n / 12
    return {
        "final_value": sim.final_value, "invested": invested, "gain": sim.final_value - invested,
        "money_weighted_return": xirr(flows),
        "time_weighted_return": index ** (1 / years) - 1 if years >= 1 else None,
        "volatility": vol, "max_drawdown": worst_drawdown,
        "worst_12_months": min(rolling) if rolling else None,
        "months": len(sim.days),
    }


def project(monthly_returns: list[float], initial: float, monthly: float, months: int, paths: int = 2000,
            block: int = 12, seed: int = 7) -> dict | None:
    """Range of outcomes: replays random 12-month blocks of the past, thousands of times.

    Blocks keep the real rhythm of markets (a bad year often follows another). The result is a
    range, not a forecast: p10 means 1 chance in 10 of ending below.
    """
    if len(monthly_returns) < 3 * block or months <= 0:
        return None
    rng = random.Random(seed)
    finals = []
    starts = len(monthly_returns) - block + 1
    for _ in range(paths):
        value, m = initial, 0
        while m < months:
            start = rng.randrange(starts)
            for r in monthly_returns[start:start + block]:
                if m >= months:
                    break
                value = value * (1 + r) + monthly
                m += 1
        finals.append(value)
    finals.sort()

    def pct(q: float) -> float:
        return finals[min(len(finals) - 1, int(q * len(finals)))]

    invested = initial + monthly * months
    return {"months": months, "invested": invested, "p10": pct(0.10), "p50": pct(0.50), "p90": pct(0.90),
            "loss_probability": sum(1 for v in finals if v < invested) / paths}


def normalize(monthly_returns: list[float], reference: list[float],
              target_annual: float = 0.07) -> list[float]:
    """Same ups and downs, lower average: shifts the returns so that the reference (the world
    index) averages target_annual per year instead of what the last decade gave.

    The same shift applies to every strategy, so their differences are kept.
    """
    if not reference:
        return monthly_returns
    ref_mean = sum(math.log1p(r) for r in reference) / len(reference)
    shift = ref_mean - math.log1p(target_annual) / 12
    return [math.expm1(math.log1p(r) - shift) for r in monthly_returns]
