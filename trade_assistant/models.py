"""Tables. Each brick adds its own here (instruments, prices, recommendations, journal...)."""
from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class LlmCall(Base):
    """One call to a language model: lets the dashboard show the free-tier consumption per provider."""

    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    role: Mapped[str] = mapped_column(String(32))
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(128))
    ok: Mapped[bool] = mapped_column(default=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, default=None)


# --- Brick 1: market data ------------------------------------------------------------------------

class Instrument(Base):
    """A stock or an ETF of the universe, identified by its ISIN (the code Trade Republic shows)."""

    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    isin: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    symbol: Mapped[str] = mapped_column(String(32))  # Yahoo ticker, e.g. AI.PA
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(8))  # "stock" or "etf"
    currency: Mapped[str | None] = mapped_column(String(8), default=None)
    exchange: Mapped[str | None] = mapped_column(String(16), default=None)
    country: Mapped[str | None] = mapped_column(String(2), default=None)  # registered office
    sector: Mapped[str | None] = mapped_column(String(64), default=None)
    industry: Mapped[str | None] = mapped_column(String(128), default=None)
    lei: Mapped[str | None] = mapped_column(String(20), default=None)  # legal entity id, for ESEF reports
    pea_eligible: Mapped[bool | None] = mapped_column(default=None)  # None = unknown
    pea_reason: Mapped[str | None] = mapped_column(Text, default=None)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    prices_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    fundamentals_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class Price(Base):
    """Daily closing price. adj_close includes dividends and splits: use it for returns."""

    __tablename__ = "prices"
    __table_args__ = (UniqueConstraint("instrument_id", "day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="CASCADE"), index=True)
    day: Mapped[date] = mapped_column(Date)
    close: Mapped[float] = mapped_column(Float)
    adj_close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float | None] = mapped_column(Float, default=None)


class Fundamental(Base):
    """One figure of the annual accounts (revenue, net income...) for one fiscal year and one source.

    The same figure can come from two sources: "esef" (the official annual report, audited) and
    "yahoo" (standardised, more recent years). Keeping both lets us cross-check them.
    """

    __tablename__ = "fundamentals"
    __table_args__ = (UniqueConstraint("instrument_id", "period_end", "metric", "source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="CASCADE"), index=True)
    period_end: Mapped[date] = mapped_column(Date)
    metric: Mapped[str] = mapped_column(String(32))
    value: Mapped[float] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(8), default=None)
    source: Mapped[str] = mapped_column(String(8))
    source_url: Mapped[str | None] = mapped_column(Text, default=None)


class EsefFiling(Base):
    """An official annual report already read, so it is never downloaded twice (they weigh ~15 MB)."""

    __tablename__ = "esef_filings"
    __table_args__ = (UniqueConstraint("instrument_id", "json_url"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="CASCADE"), index=True)
    period_end: Mapped[date] = mapped_column(Date)
    json_url: Mapped[str] = mapped_column(Text)
    viewer_url: Mapped[str | None] = mapped_column(Text, default=None)
    facts_found: Mapped[int] = mapped_column(Integer, default=0)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# --- Investor profile ----------------------------------------------------------------------------

class InvestorProfile(Base):
    """Your investment settings, editable from the website (a single row). Every brick reads it:
    the monthly plan splits monthly_amount_eur, the risk rules depend on horizon_years..."""

    __tablename__ = "investor_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_type: Mapped[str] = mapped_column(String(8))  # "PEA" or "CTO"
    initial_amount_eur: Mapped[float] = mapped_column(Float)
    monthly_amount_eur: Mapped[float] = mapped_column(Float)
    core_share: Mapped[float] = mapped_column(Float)  # part of each payment going to the world ETF
    horizon_years: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
