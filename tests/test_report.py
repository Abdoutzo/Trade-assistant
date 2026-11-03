from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.orm import Session

from trade_assistant import config, db
from trade_assistant.data import http, store
from trade_assistant.models import MonthlyPlan
from trade_assistant.portfolio import service
from trade_assistant.report import __main__ as cli
from trade_assistant.report import content, mail, render

from . import fake_sources as fake

PLAN = {
    "month": "2026-12", "budget": 100, "source": "agent", "fallback_reason": None,
    "orders": [{"isin": fake.ETF_ISIN, "name": "ETF monde", "amount": 80, "role": "core"}],
    "summary": "On garde le cap <b>prudent</b>.", "change_my_mind": "Une baisse forte.",
    "critic": [{"isin": fake.ISIN, "name": "Air Liquide", "text": "Valorisation tendue.", "severity": 3},
               {"isin": None, "name": "Portefeuille", "text": "Détail.", "severity": 1}],
    "lesson": {"title": "Le temps", "text": "Investir longtemps compte plus que bien choisir le moment."},
    "trade_plans": [{"isin": fake.ETF_ISIN, "name": "ETF monde", "amount": 80, "frequency": "monthly",
                     "frequency_label": "chaque mois", "monthly": 80}],
    "actions": [{"kind": "update", "isin": fake.ETF_ISIN, "name": "ETF monde",
                 "text": "Modifie le plan ETF monde : 440 € chaque mois → 80 € chaque mois."},
                {"kind": "delete", "isin": "OLD", "name": "Ancienne", "text": "Supprime le plan Ancienne."}],
    "plan_notes": ["Hermès : une action coûte 1 340 €."], "checklist": [],
}


@pytest.fixture
def session(monkeypatch):
    http.set_client(fake.fake_client())
    monkeypatch.setattr(http.time, "sleep", lambda s: None)
    db.init_db()
    with Session(db.get_engine()) as s:
        etf = store.add_instrument(s, fake.ETF_ISIN)
        store.refresh_prices(s, etf)
        service.add_transaction(s, date(2026, 10, 22), fake.ETF_ISIN, "buy", 2, 170)
        s.add(MonthlyPlan(month="2026-12", status="draft", data=PLAN))
        s.commit()
        yield s
    http.set_client(None)


def test_report_content(session):
    report = content.gather(session)
    assert content.subject(report) == "Plan de décembre 2026 : 2 changements dans Trade Republic"
    subject, text, html = render.render(report, "https://ta.example.com/")
    assert "Valeur : 346 € pour 340 € versés (+6 €, +1,8 %)" in text
    assert "[Modifier] ETF monde : 80 € chaque mois" in text
    assert "[Supprimer] Supprime le plan Ancienne." in text
    assert "Valorisation tendue." in text and "Détail." not in text  # only the serious objections
    assert "rédigée par l'IA" in text and "https://ta.example.com/plan" in text
    assert "Prochain : « Les bases" in text and "https://ta.example.com/guide/bases" in text
    assert "&lt;b&gt;prudent&lt;/b&gt;" in html and "<b>prudent</b>" not in html  # AI text is escaped


def test_subject_when_nothing_changes():
    report = {"plan": {**PLAN, "actions": [{"kind": "keep"}]}, "changes": []}
    assert content.subject(report) == "Plan de décembre 2026 : rien à changer dans Trade Republic"
    assert content.subject({"plan": None, "changes": []}) == "Trade Assistant : ton point du mois"


def test_sending(session, monkeypatch, capsys):
    sent = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            sent.append((host, port))

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self):
            pass

        def login(self, user, password):
            sent.append((user, password))

        def send_message(self, message):
            sent.append(message)

    monkeypatch.setattr(mail.smtplib, "SMTP", FakeSMTP)
    assert cli.main(["send"]) == 0  # not configured: the e-mail is skipped, not an error
    assert "E-mail non configuré" in capsys.readouterr().out and not sent

    monkeypatch.setenv("SMTP_USER", "moi@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "app-password")
    config.get_settings.cache_clear()
    assert cli.main(["send"]) == 0
    assert "Envoyé à moi@gmail.com" in capsys.readouterr().out
    message = sent[-1]
    assert sent[0] == ("smtp.gmail.com", 587) and message["To"] == "moi@gmail.com"
    assert message["Subject"].startswith("Plan de décembre 2026")


def test_preview(session, tmp_path, capsys):
    out = tmp_path / "r.html"
    assert cli.main(["preview", str(out)]) == 0
    assert "<h1" in out.read_text(encoding="utf-8") and "Objet : Plan de décembre" in capsys.readouterr().out
