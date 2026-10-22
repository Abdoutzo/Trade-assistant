"""Positions from transactions, average cost method (the one used for French taxation)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class TradeIn:
    day: date
    isin: str
    side: str  # "buy" | "sell"
    quantity: float
    price_eur: float
    fees_eur: float = 0.0


@dataclass
class Position:
    isin: str
    quantity: float = 0.0
    cost_eur: float = 0.0  # what the shares still held cost, fees included
    realized_eur: float = 0.0  # gains already locked in by sales
    first_day: date | None = None
    trades: int = 0

    @property
    def average_cost(self) -> float | None:
        return self.cost_eur / self.quantity if self.quantity > 1e-9 else None


@dataclass
class Book:
    positions: dict[str, Position] = field(default_factory=dict)
    contributions_eur: float = 0.0  # money put in (buys + fees - sales proceeds)
    errors: list[str] = field(default_factory=list)


def build(trades: list[TradeIn]) -> Book:
    book = Book()
    for t in sorted(trades, key=lambda t: t.day):
        p = book.positions.setdefault(t.isin, Position(t.isin))
        p.trades += 1
        p.first_day = p.first_day or t.day
        amount = t.quantity * t.price_eur
        if t.side == "buy":
            p.quantity += t.quantity
            p.cost_eur += amount + t.fees_eur
            book.contributions_eur += amount + t.fees_eur
        else:
            if t.quantity > p.quantity + 1e-9:
                book.errors.append(f"{t.isin} : vente de {t.quantity:g} le {t.day:%d/%m/%Y} alors que "
                                   f"seulement {p.quantity:g} détenue(s) ; vente ignorée.")
                continue
            avg = p.cost_eur / p.quantity
            p.realized_eur += amount - t.fees_eur - avg * t.quantity
            p.cost_eur -= avg * t.quantity
            p.quantity -= t.quantity
            book.contributions_eur -= amount - t.fees_eur
    return book
