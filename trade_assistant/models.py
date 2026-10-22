"""Tables. Each brick adds its own here (instruments, prices, recommendations, journal...)."""
from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
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
    # A reference series (e.g. the long-history MSCI World for simulations), never proposed to buy.
    is_reference: Mapped[bool | None] = mapped_column(default=None)


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
    # Brick 3 (nullable: added to existing databases by db.add_missing_columns; None = default).
    core_isin: Mapped[str | None] = mapped_column(String(12), default=None)  # the world ETF bought monthly
    satellites_count: Mapped[int | None] = mapped_column(Integer, default=None)  # target number of stocks
    max_position_share: Mapped[float | None] = mapped_column(Float, default=None)  # cap per stock
    min_order_eur: Mapped[float | None] = mapped_column(Float, default=None)  # smallest useful order


# --- Brick 2: analysis ---------------------------------------------------------------------------

class Analysis(Base):
    """Latest analysis of an instrument (ratios, risk, score), recomputed when its data changes."""

    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="CASCADE"), unique=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    score: Mapped[float | None] = mapped_column(Float, default=None)
    data: Mapped[dict] = mapped_column(JSON)


# --- Brick 3: portfolio --------------------------------------------------------------------------

class Transaction(Base):
    """A buy or a sell done on Trade Republic, entered on the site. Positions are computed from these."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    isin: Mapped[str] = mapped_column(String(12), index=True)
    side: Mapped[str] = mapped_column(String(4))  # "buy" or "sell"
    quantity: Mapped[float] = mapped_column(Float)  # fractions allowed (savings plans buy fractions)
    price_eur: Mapped[float] = mapped_column(Float)  # price per share paid, in euros
    fees_eur: Mapped[float] = mapped_column(Float, default=0.0)
    note: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SatelliteChoice(Base):
    """Your say on the stock selection: "pinned" (keep it) or "excluded" (never propose it)."""

    __tablename__ = "satellite_choices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    isin: Mapped[str] = mapped_column(String(12), unique=True)
    status: Mapped[str] = mapped_column(String(8))


# --- Brick 4: news -------------------------------------------------------------------------------

class NewsItem(Base):
    """An article about an instrument, with its triage (category, tone, importance, summary)."""

    __tablename__ = "news_items"
    __table_args__ = (UniqueConstraint("instrument_id", "url"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(128), default=None)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    lang: Mapped[str | None] = mapped_column(String(4), default=None)
    snippet: Mapped[str | None] = mapped_column(Text, default=None)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # Triage: None until done.
    category: Mapped[str | None] = mapped_column(String(24), default=None)
    sentiment: Mapped[int | None] = mapped_column(Integer, default=None)  # -2 .. +2
    importance: Mapped[int | None] = mapped_column(Integer, default=None)  # 0 (noise) .. 3 (major)
    summary: Mapped[str | None] = mapped_column(Text, default=None)  # one line, in French
    triaged_by: Mapped[str | None] = mapped_column(String(128), default=None)  # model, or "mots-clés"


class Alert(Base):
    """Something that deserves your attention: a major news item or an unusual price move."""

    __tablename__ = "alerts"
    __table_args__ = (UniqueConstraint("instrument_id", "key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(160))  # dedupe: "news:<id>" or "price:<day>"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    kind: Mapped[str] = mapped_column(String(8))  # "news" | "price"
    severity: Mapped[int] = mapped_column(Integer)  # 1 info, 2 attention, 3 important
    title: Mapped[str] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text, default=None)
    url: Mapped[str | None] = mapped_column(Text, default=None)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class Digest(Base):
    """An AI summary of a company's recent news, every point tied to its sources."""

    __tablename__ = "digests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    points: Mapped[list] = mapped_column(JSON)  # [{"text", "sources": [n]}]
    watch: Mapped[list] = mapped_column(JSON)  # [{"text", "sources": [n]}]
    sources: Mapped[list] = mapped_column(JSON)  # [{"n", "title", "url", "source", "date"}]
    model: Mapped[str] = mapped_column(String(160))


# --- Brick 5: the agent's monthly plans ----------------------------------------------------------

class MonthlyPlan(Base):
    """A plan prepared by the agent. Nothing happens until you approve it, and even then you are the
    one who sets the savings plans in Trade Republic."""

    __tablename__ = "monthly_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    month: Mapped[str] = mapped_column(String(7), index=True)  # "2026-10"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[str] = mapped_column(String(10), default="draft")  # draft | approved | rejected
    data: Mapped[dict] = mapped_column(JSON)
    model: Mapped[str | None] = mapped_column(String(160), default=None)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    note: Mapped[str | None] = mapped_column(Text, default=None)  # your comment when deciding
