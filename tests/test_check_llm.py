from __future__ import annotations

from langchain_core.language_models.fake_chat_models import FakeListChatModel

from trade_assistant import check_llm, config, llm


def test_no_key_fails(capsys):
    assert check_llm.main() == 1
    assert "NVIDIA_API_KEY" in capsys.readouterr().out


def test_nvidia_key_only(monkeypatch, capsys):
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-secret")
    config.get_settings.cache_clear()
    monkeypatch.setattr(llm, "chat_model", lambda *a, **k: FakeListChatModel(responses=["OK"]))
    assert check_llm.main() == 0
    out = capsys.readouterr().out
    assert out.count("[OK]") == 3
    assert "nvapi-secret" not in out
