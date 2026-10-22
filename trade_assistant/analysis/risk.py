"""Market risk and returns from daily prices (adjusted for dividends and splits)."""
from __future__ import annotations

import math
from datetime import date, timedelta

Series = list[tuple[date, float]]  # (day, adjusted close), oldest first


def _since(series: Series, days: int) -> Series:
    if not series:
        return []
    start = series[-1][0] - timedelta(days=days)
    return [p for p in series if p[0] >= start]


def total_return(series: Series, years: float) -> float | None:
    """Annualised return over the period (simple return for one year or less)."""
    window = _since(series, int(years * 365.25))
    if len(window) < 2 or (window[-1][0] - window[0][0]).days < years * 365.25 * 0.95:
        return None  # not enough history
    growth = window[-1][1] / window[0][1]
    return growth - 1 if years <= 1 else growth ** (1 / years) - 1


def volatility(series: Series, days: int = 365) -> float | None:
    """Annualised standard deviation of daily returns: how much the price shakes."""
    window = _since(series, days)
    rets = [math.log(b[1] / a[1]) for a, b in zip(window, window[1:], strict=False) if a[1] > 0 and b[1] > 0]
    if len(rets) < 60:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var) * math.sqrt(252)


def max_drawdown(series: Series, days: int = 5 * 365) -> float | None:
    """Worst fall from a peak, e.g. -0.35: the pain an investor had to sit through."""
    window = _since(series, days)
    if len(window) < 60:
        return None
    peak, worst = window[0][1], 0.0
    for _, price in window:
        peak = max(peak, price)
        worst = min(worst, price / peak - 1)
    return worst


def _weekly(series: Series) -> dict[tuple[int, int], float]:
    weeks: dict[tuple[int, int], float] = {}
    for day, price in series:
        iso = day.isocalendar()
        weeks[(iso[0], iso[1])] = price  # last close of the week
    return weeks


def beta(series: Series, benchmark: Series, days: int = 3 * 365) -> float | None:
    """Sensitivity to the market: 1.3 means +-13 % when the market moves +-10 %.

    Weekly returns: daily closes of different exchanges are not synchronous.
    """
    a, b = _weekly(_since(series, days)), _weekly(_since(benchmark, days))
    keys = sorted(a.keys() & b.keys())
    pairs = [(a[k2] / a[k1] - 1, b[k2] / b[k1] - 1) for k1, k2 in zip(keys, keys[1:], strict=False)]
    if len(pairs) < 52:
        return None
    mx = sum(x for x, _ in pairs) / len(pairs)
    my = sum(y for _, y in pairs) / len(pairs)
    cov = sum((x - mx) * (y - my) for x, y in pairs)
    var = sum((y - my) ** 2 for _, y in pairs)
    return cov / var if var else None


def price_on(series: list[tuple[date, float]], day: date) -> float | None:
    """Last close on or before a day (a fiscal year can end on a weekend)."""
    before = [p for d, p in series if d <= day]
    return before[-1] if before and (day - max(d for d, _ in series if d <= day)).days <= 10 else None
