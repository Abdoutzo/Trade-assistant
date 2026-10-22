"""Database access: SQLite on your machine, Postgres (Neon, free) once deployed. Same code for both."""
from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from sqlalchemy import Engine, create_engine, inspect, text
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
    """Create the missing tables and columns (the models of every brick register on Base)."""
    from . import models  # noqa: F401  (import registers the tables)

    engine = get_engine()
    Base.metadata.create_all(engine)
    add_missing_columns(engine)


def add_missing_columns(engine: Engine) -> list[str]:
    """Light migration: a column added to a model later is added to the existing table.

    create_all only creates missing tables; your Neon database already has the old ones. New
    columns are always nullable, so adding them never breaks existing rows.
    """
    added = []
    inspector = inspect(engine)
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue
        existing = {c["name"] for c in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing:
                continue
            if not column.nullable:
                raise RuntimeError(f"New column {table.name}.{column.name} must be nullable")
            ddl = column.type.compile(dialect=engine.dialect)
            with engine.begin() as conn:
                conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN {column.name} {ddl}'))
            added.append(f"{table.name}.{column.name}")
    return added


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
