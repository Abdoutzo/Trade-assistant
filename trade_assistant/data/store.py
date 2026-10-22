"""Everything that reads or writes market data in the database."""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..models import EsefFiling, Fundamental, Instrument, Price, utcnow
from . import esef, euronext, gleif, universe, yahoo
from .http import SourceError

log = logging.getLogger(__name__)


class NotFound(LookupError):
    pass


# --- Instruments ---------------------------------------------------------------------------------

def get_instrument(session: Session, isin: str) -> Instrument | None:
    return session.scalar(select(Instrument).where(Instrument.isin == isin.strip().upper()))


def add_instrument(session: Session, isin: str) -> Instrument:
    """Identify an ISIN (ticker, name, type, country, LEI, PEA status) and add it to the universe."""
    isin = isin.strip().upper()
    if not universe.is_valid_isin(isin):
        raise ValueError(f"{isin!r} n'est pas un ISIN valide (12 caractères, ex. FR0000120073)")
    existing = get_instrument(session, isin)
    if existing:
        return existing

    quotes = yahoo.search(isin)
    symbol = universe.PEA_ETFS.get(isin) or (quotes[0].symbol if quotes else None)
    if not symbol:
        listing = next((x for x in euronext.search(isin) if x.yahoo_symbol), None)
        symbol = listing.yahoo_symbol if listing else None
    if not symbol:
        raise NotFound(f"Aucune cotation trouvée pour {isin}")
    quote = next((q for q in quotes if q.symbol == symbol), None)
    meta = yahoo.chart(symbol, "5d")  # confirms the ticker works and gives currency and exchange

    kind = (quote.kind if quote else None) or meta.kind or "stock"
    entity = gleif.entity_for_isin(isin) if kind == "stock" else None
    country = entity.country if entity else (isin[:2] if kind == "stock" else None)
    eligible, reason = universe.pea_status(kind, isin, country)
    instrument = Instrument(
        isin=isin, symbol=symbol, name=(quote.name if quote else None) or meta.name or symbol, kind=kind,
        currency=meta.currency, exchange=meta.exchange, country=country,
        sector=quote.sector if quote else None, industry=quote.industry if quote else None,
        lei=entity.lei if entity else None, pea_eligible=eligible, pea_reason=reason)
    session.add(instrument)
    session.commit()
    return instrument


def list_instruments(session: Session) -> list[Instrument]:
    return list(session.scalars(select(Instrument).order_by(Instrument.kind.desc(), Instrument.name)))


def remove_instrument(session: Session, instrument: Instrument) -> None:
    for table in (Price, Fundamental, EsefFiling):
        session.execute(delete(table).where(table.instrument_id == instrument.id))
    session.delete(instrument)
    session.commit()


# --- Prices --------------------------------------------------------------------------------------

def refresh_prices(session: Session, instrument: Instrument) -> int:
    """Download 10 years the first time, then only the last 3 months. Returns the rows downloaded."""
    has_prices = session.scalar(select(Price.id).where(Price.instrument_id == instrument.id).limit(1))
    chart = yahoo.chart(instrument.symbol, "3mo" if has_prices else "10y")
    # The downloaded window replaces what we had on those dates: Yahoo corrects the last session
    # and adjusts past prices for dividends.
    if chart.rows:
        session.execute(delete(Price).where(Price.instrument_id == instrument.id,
                                            Price.day >= min(r.day for r in chart.rows)))
    session.add_all(Price(instrument_id=instrument.id, day=r.day, close=r.close, adj_close=r.adj_close,
                          volume=r.volume) for r in chart.rows)
    instrument.prices_updated_at = utcnow()
    session.commit()
    return len(chart.rows)


def prices(session: Session, instrument: Instrument, since: date | None = None) -> list[Price]:
    query = select(Price).where(Price.instrument_id == instrument.id)
    if since:
        query = query.where(Price.day >= since)
    return list(session.scalars(query.order_by(Price.day)))


# --- Annual accounts -----------------------------------------------------------------------------

@dataclass
class FundamentalsRefresh:
    yahoo_figures: int = 0
    esef_reports_read: int = 0
    esef_figures: int = 0
    errors: list[str] = field(default_factory=list)


def refresh_fundamentals(session: Session, instrument: Instrument) -> FundamentalsRefresh:
    """Yahoo's standardised accounts, then every official report not read yet (shares only)."""
    result = FundamentalsRefresh()
    if instrument.kind != "stock":
        return result
    try:
        figures = yahoo.fundamentals(instrument.symbol)
        _replace(session, instrument, "yahoo", figures, None)
        result.yahoo_figures = len(figures)
    except SourceError as e:
        result.errors.append(f"Yahoo : {e}")

    if instrument.lei:
        try:
            read = set(session.scalars(select(EsefFiling.json_url)
                                       .where(EsefFiling.instrument_id == instrument.id)))
            for filing in esef.filings(instrument.lei):
                if filing.json_url in read:
                    continue
                figures = esef.download(filing)
                # Oldest report first: a later report restating a year overwrites it.
                _replace(session, instrument, "esef", figures, filing.viewer_url or filing.json_url)
                session.add(EsefFiling(instrument_id=instrument.id, period_end=filing.period_end,
                                       json_url=filing.json_url, viewer_url=filing.viewer_url,
                                       facts_found=len(figures)))
                session.commit()
                result.esef_reports_read += 1
                result.esef_figures += len(figures)
        except SourceError as e:
            result.errors.append(f"Rapports ESEF : {e}")

    instrument.fundamentals_updated_at = utcnow()
    session.commit()
    return result


def _replace(session: Session, instrument: Instrument, source: str, figures: list[yahoo.Figure],
             url: str | None) -> None:
    for f in figures:
        session.execute(delete(Fundamental).where(
            Fundamental.instrument_id == instrument.id, Fundamental.source == source,
            Fundamental.period_end == f.period_end, Fundamental.metric == f.metric))
    session.add_all(Fundamental(instrument_id=instrument.id, period_end=f.period_end, metric=f.metric,
                                value=f.value, currency=f.currency, source=source, source_url=url)
                    for f in figures)
    session.flush()


# Figures defined the same way in both sources: a gap above 3 % deserves a look (a restatement, or
# an error in one source). Not cash or capex: Yahoo's definitions differ from the IFRS line items.
CROSS_CHECKED = {"revenue", "net_income", "operating_cash_flow", "equity", "total_assets"}
# Per-share figures: Yahoo restates the whole history after splits and bonus shares, the old reports
# do not. Mixing both would create fake jumps, so these come from a single source per company.
SINGLE_SOURCE = {"eps_diluted": ("yahoo", "esef"), "shares": ("yahoo", "esef")}
TOLERANCE = 0.03


@dataclass
class Cell:
    value: float
    source: str
    source_url: str | None
    currency: str | None
    other_value: float | None = None  # the other source, when it disagrees

    @property
    def gap(self) -> float | None:
        if self.other_value is None or not self.value:
            return None
        return abs(self.other_value - self.value) / abs(self.value)


def fundamentals_table(session: Session, instrument: Instrument) -> dict[date, dict[str, Cell]]:
    """One value per fiscal year and metric: the official report first, Yahoo otherwise."""
    rows = session.scalars(select(Fundamental).where(Fundamental.instrument_id == instrument.id))
    by_key: dict[tuple[date, str], dict[str, Fundamental]] = defaultdict(dict)
    for f in rows:
        by_key[(f.period_end, f.metric)][f.source] = f
    available = defaultdict(set)
    for (_, metric), sources in by_key.items():
        available[metric].update(sources)
    table: dict[date, dict[str, Cell]] = defaultdict(dict)
    for (period_end, metric), sources in by_key.items():
        if metric in SINGLE_SOURCE:
            chosen = next(s for s in SINGLE_SOURCE[metric] if s in available[metric])
            if chosen not in sources:
                continue
            order: tuple[str, ...] = (chosen,)
        else:
            order = ("esef", "yahoo")
        main = next(sources[s] for s in order if s in sources)
        cell = Cell(main.value, main.source, main.source_url, main.currency)
        other = next((sources[s] for s in ("esef", "yahoo") if s in sources and s != main.source), None)
        if other and metric in CROSS_CHECKED and main.value:
            if abs(other.value - main.value) / abs(main.value) > TOLERANCE:
                cell.other_value = other.value
        table[period_end][metric] = cell
    # Drop years with a stray figure only (e.g. opening equity of the oldest report).
    table = {d: row for d, row in table.items() if len(row) >= 3}
    return dict(sorted(table.items()))


def is_stale(updated_at: datetime | None, max_age: timedelta) -> bool:
    if updated_at is None:
        return True
    if updated_at.tzinfo is None:  # SQLite returns naive datetimes (stored in UTC)
        updated_at = updated_at.replace(tzinfo=UTC)
    return utcnow() - updated_at > max_age
