from __future__ import annotations

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from trade_assistant import config, db, llm
from trade_assistant.models import LlmCall


def test_parse_chain():
    assert llm.parse_chain(" nvidia:z-ai/glm-5.3, google:gemini-flash-latest ,") == [
        ("nvidia", "z-ai/glm-5.3"), ("google", "gemini-flash-latest")]


@pytest.mark.parametrize("spec", ["nvidia", "unknown:model", "groq:"])
def test_parse_chain_rejects_bad_entries(spec):
    with pytest.raises(ValueError):
        llm.parse_chain(spec)


def test_default_chains_are_valid():
    for spec in llm.DEFAULT_CHAINS.values():
        assert llm.parse_chain(spec)


def test_chain_keeps_only_providers_with_a_key(monkeypatch):
    assert llm.chain("reasoning") == []
    monkeypatch.setenv("GOOGLE_API_KEY", "k")
    config.get_settings.cache_clear()
    assert llm.chain("reasoning") == [("google", "gemini-flash-latest")]


def test_chain_override_from_env(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setenv("LLM_CHAIN_FAST", "groq:qwen/qwen3-32b")
    config.get_settings.cache_clear()
    assert llm.chain("fast") == [("groq", "qwen/qwen3-32b")]


def test_unknown_role():
    with pytest.raises(ValueError):
        llm.chain("magic")


def test_ask_without_any_key():
    with pytest.raises(llm.NoModelAvailable):
        llm.ask("fast", "bonjour")


class Broken(FakeListChatModel):
    def invoke(self, *args, **kwargs):
        raise RuntimeError("429 Too Many Requests")


def test_ask_falls_back_to_next_model_and_records_calls(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "k")
    monkeypatch.setenv("GOOGLE_API_KEY", "k")
    config.get_settings.cache_clear()
    db.init_db()

    def fake_model(provider, model, role, settings=None):
        return Broken(responses=["x"]) if provider == "nvidia" else FakeListChatModel(responses=["OK"])

    monkeypatch.setattr(llm, "chat_model", fake_model)
    answer = llm.ask("reasoning", "test")  # chain: nvidia, nvidia, google (groq has no key)
    assert (answer.text, answer.provider) == ("OK", "google")

    with Session(db.get_engine()) as s:
        calls = s.scalars(select(LlmCall).order_by(LlmCall.id)).all()
    assert [(c.provider, c.ok) for c in calls] == [("nvidia", False), ("nvidia", False), ("google", True)]
    assert "429" in calls[0].error


def test_ask_reports_every_failure(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "k")
    config.get_settings.cache_clear()
    monkeypatch.setattr(llm, "chat_model", lambda *a, **k: Broken(responses=["x"]))
    with pytest.raises(llm.NoModelAvailable, match="429"):
        llm.ask("reasoning", "test")


def test_text_from_content_blocks():
    assert llm._text([{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]) == "ab"


def test_status_never_exposes_keys(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "secret-groq-key")
    config.get_settings.cache_clear()
    assert "secret-groq-key" not in str(llm.status())
