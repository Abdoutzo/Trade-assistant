"""Database access: SQLite on your machine, Postgres (Neon, free) once deployed. Same code for both."""
from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


def normalize_url(url: str) -> str:
    """Neon gives 'postgresql://...': tell SQLAlchemy to use the psycopg 3 driver we install."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url.removeprefix(prefix)
    return url


@lru_cache
def get_engine() -> Engine:
    url = normalize_url(get_settings().database_url)
    if url.startswith("sqlite:///"):
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(url, connect_args={"check_same_thread": False})
    # Neon suspends idle databases: pre_ping reconnects transparently after a pause.
    return create_engine(url, pool_pre_ping=True, pool_size=3, max_overflow=2)


def init_db() -> None:
    """Create the missing tables (the models of every brick register themselves on Base)."""
    from . import models  # noqa: F401  (import registers the tables)

    Base.metadata.create_all(get_engine())


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed."""
    factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    with factory() as session:
        yield session


def ping() -> bool:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
