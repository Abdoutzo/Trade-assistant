from __future__ import annotations

import pytest

from trade_assistant import db


@pytest.mark.parametrize("url, expected", [
    ("postgresql://u:p@ep-x.eu-central-1.aws.neon.tech/db?sslmode=require",
     "postgresql+psycopg://u:p@ep-x.eu-central-1.aws.neon.tech/db?sslmode=require"),
    ("postgres://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
    ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
    ("sqlite:///data/x.db", "sqlite:///data/x.db"),
])
def test_normalize_url(url, expected):
    assert db.normalize_url(url) == expected


def test_init_db_creates_tables():
    db.init_db()
    assert db.ping()


def test_empty_database_url_falls_back_to_sqlite(monkeypatch):
    from trade_assistant import config

    monkeypatch.setenv("DATABASE_URL", "  ")
    config.get_settings.cache_clear()
    assert config.get_settings().database_url == config.DEFAULT_DATABASE_URL


def test_new_nullable_columns_are_added_to_existing_tables():
    from sqlalchemy import MetaData, Table, inspect

    from trade_assistant.models import InvestorProfile

    engine = db.get_engine()
    new_columns = {"core_isin", "satellites_count", "max_position_share", "min_order_eur"}
    old = MetaData()  # the table as the previous version of the app created it on Neon
    Table(InvestorProfile.__tablename__, old,
          *[c._copy() for c in InvestorProfile.__table__.columns if c.name not in new_columns])
    old.create_all(engine)
    db.init_db()
    columns = {c["name"] for c in inspect(engine).get_columns(InvestorProfile.__tablename__)}
    assert new_columns <= columns
    assert db.add_missing_columns(engine) == []  # idempotent
