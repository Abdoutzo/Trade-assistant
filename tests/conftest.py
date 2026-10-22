"""Every test runs on a fresh SQLite file and a clean environment: no real key, no real network."""
from __future__ import annotations

import pytest

from trade_assistant import config, db, llm

ENV_VARS = ("APP_PASSWORD", "SECRET_KEY", "ENV", "NVIDIA_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY",
            "OPENROUTER_API_KEY", "LLM_CHAIN_REASONING", "LLM_CHAIN_LONG_CONTEXT", "LLM_CHAIN_FAST")


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)  # no .env picked up from the repository
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    _clear_caches()
    yield
    _clear_caches()


def _clear_caches():
    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
    llm._rate_limiter.cache_clear()
