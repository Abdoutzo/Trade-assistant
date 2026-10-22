"""News storage, alerts and what the site shows."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..data import store
from ..models import Alert, Digest, Instrument, NewsItem, utcnow
from . import digest, sources, triage

log = logging.getLogger(__name__)

KEEP_DAYS = 180  # older articles are deleted: the database stays small (Neon free = 0.5 GB)
PRICE_MOVE = 0.05  # a daily move of 5 % or more on a watched stock raises an alert
RISK_CATEGORIES = {"previsions", "juridique", "dirigeants", "resultats", "operations", "actionnaires"}


def _aware(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


@dataclass
class Refresh:
    new: int = 0
    triaged_by_ai: int = 0
    alerts: int = 0
    errors: list[str] = field(default_factory=list)


def refresh(session: Session, instrument: Instrument) -> Refresh:
    """Collects new articles, triages them, raises alerts for the ones that matter."""
    result = Refresh()
    articles, result.errors = sources.collect(instrument.isin, instrument.name, instrument.symbol)
    known = set(session.scalars(select(NewsItem.url).where(NewsItem.instrument_id == instrument.id)))
    horizon = utcnow() - timedelta(days=KEEP_DAYS)
    fresh = [a for a in articles if a.url not in known and a.published_at > horizon]
    items = [NewsItem(instrument_id=instrument.id, url=a.url, title=a.title, source=a.source,
                      published_at=a.published_at, lang=a.lang, snippet=a.snippet) for a in fresh]
    company = sources.search_name(instrument.isin, instrument.name)
    for item, t in zip(items, triage.triage(company, [(i.title, i.snippet) for i in items]), strict=True):
        item.category, item.sentiment, item.importance = t.category, t.sentiment, t.importance
        item.summary, item.triaged_by = t.summary, t.by
        result.triaged_by_ai += t.by != "mots-clés"
    session.add_all(items)
    session.flush()
    result.new = len(items)
    result.alerts = sum(_news_alert(session, instrument, i) for i in items)
    session.query(NewsItem).filter(NewsItem.instrument_id == instrument.id,
                                   NewsItem.published_at < horizon).delete()
    session.commit()
    return result


def _news_alert(session: Session, instrument: Instrument, item: NewsItem) -> bool:
    major = (item.importance or 0) >= 3
    worrying = ((item.importance or 0) >= 2 and (item.sentiment or 0) <= -1
                and item.category in RISK_CATEGORIES)
    if not (major or worrying):
        return False
    # Bad and major: important. Bad and notable: attention. Good and major: for information.
    severity = 3 if major and (item.sentiment or 0) < 0 else 2 if worrying else 1
    label = triage.CATEGORIES.get(item.category or "autre")
    # The same story is repeated by many outlets: one alert per company and category every 3 days.
    recent = session.scalars(select(Alert.title).where(
        Alert.instrument_id == instrument.id, Alert.kind == "news",
        Alert.created_at >= utcnow() - timedelta(days=3)))
    if any(title.startswith(f"{label} :") for title in recent):
        return False
    return _alert(session, instrument, f"news:{item.url[:150]}", "news", severity,
                  f"{label} : {item.summary or item.title}",
                  f"{item.source or ''}, {_aware(item.published_at):%d/%m/%Y}", item.url)


def price_alert(session: Session, instrument: Instrument) -> bool:
    """A daily move of 5 % or more: something happened, look for the reason before acting."""
    series = store.prices(session, instrument, since=(utcnow() - timedelta(days=10)).date())
    if len(series) < 2:
        return False
    before, last = series[-2], series[-1]
    move = last.adj_close / before.adj_close - 1
    if abs(move) < PRICE_MOVE:
        return False
    severity = 3 if abs(move) >= 0.08 else 2
    word = "bondit" if move > 0 else "chute"
    return _alert(session, instrument, f"price:{last.day.isoformat()}", "price", severity,
                  f"{instrument.name} {word} de {move:+.1%} le {last.day:%d/%m/%Y}",
                  "Variation inhabituelle : cherche la cause dans l'actualité avant toute décision. Une "
                  "forte baisse sans mauvaise nouvelle de fond peut être une opportunité ; avec, c'est un "
                  "signal.")


def _alert(session: Session, instrument: Instrument, key: str, kind: str, severity: int, title: str,
           detail: str | None, url: str | None = None) -> bool:
    exists = session.scalar(select(Alert.id).where(Alert.instrument_id == instrument.id, Alert.key == key))
    if exists:
        return False
    session.add(Alert(instrument_id=instrument.id, key=key, kind=kind, severity=severity, title=title,
                      detail=detail, url=url))
    session.flush()
    return True


def refresh_all(session: Session, watched: set[str]) -> dict[str, Refresh]:
    """Every stock of the universe; price alerts only for what you hold or plan to buy."""
    out = {}
    for instrument in store.list_instruments(session):
        if instrument.kind != "stock" and instrument.isin not in watched:
            continue
        try:
            out[instrument.isin] = refresh(session, instrument)
            if instrument.isin in watched and price_alert(session, instrument):
                out[instrument.isin].alerts += 1
            session.commit()
        except Exception as e:  # one company failing never stops the others
            session.rollback()
            log.exception("News refresh failed for %s", instrument.isin)
            out[instrument.isin] = Refresh(errors=[str(e)])
    return out


# --- Reading -------------------------------------------------------------------------------------

def item_dict(item: NewsItem, instrument: Instrument | None = None) -> dict:
    return {"id": item.id, "isin": instrument.isin if instrument else None,
            "company": instrument.name if instrument else None, "title": item.title, "url": item.url,
            "source": item.source, "published_at": _aware(item.published_at).isoformat(), "lang": item.lang,
            "category": item.category, "category_label": triage.CATEGORIES.get(item.category or "autre"),
            "sentiment": item.sentiment, "importance": item.importance, "summary": item.summary,
            "triaged_by": item.triaged_by}


def feed(session: Session, isins: set[str] | None = None, days: int = 30, min_importance: int = 1,
         category: str | None = None, limit: int = 200) -> list[dict]:
    query = (select(NewsItem, Instrument).join(Instrument, NewsItem.instrument_id == Instrument.id)
             .where(NewsItem.published_at >= utcnow() - timedelta(days=days),
                    NewsItem.importance >= min_importance))
    if isins is not None:
        query = query.where(Instrument.isin.in_(isins))
    if category:
        query = query.where(NewsItem.category == category)
    rows = session.execute(query.order_by(NewsItem.published_at.desc()).limit(limit)).all()
    return [item_dict(item, instrument) for item, instrument in rows]


def alerts(session: Session, unread_only: bool = False, limit: int = 50) -> list[dict]:
    query = select(Alert, Instrument).join(Instrument, Alert.instrument_id == Instrument.id)
    if unread_only:
        query = query.where(Alert.read_at.is_(None))
    rows = session.execute(query.order_by(Alert.created_at.desc()).limit(limit)).all()
    return [{"id": a.id, "isin": i.isin, "company": i.name, "kind": a.kind, "severity": a.severity,
             "title": a.title, "detail": a.detail, "url": a.url,
             "created_at": _aware(a.created_at).isoformat(), "read": a.read_at is not None} for a, i in rows]


def mark_read(session: Session, alert_id: int | None = None) -> int:
    query = session.query(Alert).filter(Alert.read_at.is_(None))
    if alert_id is not None:
        query = query.filter(Alert.id == alert_id)
    count = query.update({Alert.read_at: utcnow()})
    session.commit()
    return count


# --- Digest --------------------------------------------------------------------------------------

def make_digest(session: Session, instrument: Instrument, days: int = 45, max_items: int = 25) -> Digest:
    items = session.scalars(select(NewsItem).where(
        NewsItem.instrument_id == instrument.id, NewsItem.importance >= 1,
        NewsItem.published_at >= utcnow() - timedelta(days=days))).all()
    # The most important first, then the most recent; then numbered by date for the reader.
    chosen = sorted(items, key=lambda i: (-(i.importance or 0),
                                          -_aware(i.published_at).timestamp()))[:max_items]
    chosen.sort(key=lambda i: _aware(i.published_at), reverse=True)
    if len(chosen) < 2:
        raise LookupError("Pas assez d'actualités significatives sur 45 jours pour une synthèse.")
    articles = [{"title": i.title, "summary": i.summary, "source": i.source,
                 "date": f"{_aware(i.published_at):%d/%m/%Y}", "importance": i.importance} for i in chosen]
    result = digest.summarize(sources.search_name(instrument.isin, instrument.name), articles)
    row = Digest(instrument_id=instrument.id, points=result.points, watch=result.watch, model=result.model,
                 sources=[{"n": k + 1, "title": i.title, "url": i.url, "source": i.source,
                           "date": _aware(i.published_at).date().isoformat()} for k, i in enumerate(chosen)])
    session.add(row)
    session.commit()
    return row


def latest_digest(session: Session, instrument: Instrument) -> dict | None:
    row = session.scalar(select(Digest).where(Digest.instrument_id == instrument.id)
                         .order_by(Digest.created_at.desc()).limit(1))
    if row is None:
        return None
    return {"created_at": _aware(row.created_at).isoformat(), "points": row.points, "watch": row.watch,
            "sources": row.sources, "model": row.model}
