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
