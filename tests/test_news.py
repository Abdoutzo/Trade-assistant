from __future__ import annotations

import json
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from trade_assistant import config, db, llm
from trade_assistant.data import http, store
from trade_assistant.models import NewsItem, Price
from trade_assistant.news import digest, service, sources, triage

from . import fake_sources as fake


@pytest.fixture(autouse=True)
def fake_web(monkeypatch):
    http.set_client(fake.fake_client())
    monkeypatch.setattr(http.time, "sleep", lambda s: None)
    yield
    http.set_client(None)


def fake_llm(monkeypatch, answer_for):
    """Replaces the model: answer_for(role, prompt) -> text."""
    monkeypatch.setattr(llm, "ask", lambda role, prompt, system=None: llm.Answer(
        answer_for(role, prompt), "fake", "model-test"))


TRIAGE_ANSWER = json.dumps([
    {"n": 1, "category": "previsions", "sentiment": -2, "importance": 3,
     "summary": "Air Liquide abaisse ses prévisions annuelles."},
    {"n": 2, "category": "actionnaires", "sentiment": 1, "importance": 2,
     "summary": "Programme de rachat d'actions de 4 milliards d'euros."},
    {"n": 3, "category": "marche", "sentiment": 0, "importance": 0, "summary": "Hausse du jour."},
])


# --- Sources -------------------------------------------------------------------------------------

def test_google_titles_lose_the_publisher_suffix():
    items = sources.google_news("Air Liquide")
    assert items[0].title == "Air Liquide abaisse ses prévisions annuelles"
    assert items[0].source == "Les Echos" and items[0].snippet is None


def test_collect_dedupes_and_drops_unrelated_articles():
    articles, errors = sources.collect(fake.ISIN, "L'Air Liquide S.A.", "AI.PA")
    titles = [a.title for a in articles]
    assert errors == []
    assert titles.count("Air Liquide abaisse ses prévisions annuelles") == 1  # in 3 feeds, kept once
    assert not any("TotalEnergies" in t for t in titles)


def test_search_names():
    assert sources.search_name("X", "ASML Holding N.V.") == "ASML"
    assert sources.search_name("X", "Enel SpA") == "Enel"
    lvmh = "LVMH Moët Hennessy - Louis Vuitton, Société Européenne"
    assert sources.search_name("FR0000121014", lvmh) == "LVMH"


def test_source_failure_is_reported_not_raised():
    import httpx

    http.set_client(fake.fake_client(lambda r: httpx.Response(503)))
    articles, errors = sources.collect(fake.ISIN, "Air Liquide", "AI.PA")
    assert articles == [] and len(errors) == 3


# --- Triage --------------------------------------------------------------------------------------

def test_parse_answer_is_strict_but_tolerant_of_wrapping():
    text = "Voici :\n```json\n" + json.dumps([
        {"n": 1, "category": "inconnue", "sentiment": 1, "importance": 2, "summary": "ok"},
        {"n": 2, "category": "resultats", "sentiment": 5, "importance": 2, "summary": "hors bornes"},
        {"category": "resultats"},
    ]) + "\n```"
    items = triage.parse_answer(text)
    assert [(i.n, i.category) for i in items] == [(1, "autre")]
    assert triage.parse_answer("pas de JSON") == []


@pytest.mark.parametrize("title, category, negative", [
    ("Air Liquide abaisse ses prévisions annuelles", "previsions", True),
    ("Enquête de la Commission européenne sur Air Liquide", "juridique", True),
    ("Air Liquide annonce un rachat d'actions", "actionnaires", False),
    ("Bernstein relève son objectif de cours", "analystes", False),
])
def test_keyword_rules(title, category, negative):
    t = triage.with_rules(title, None)
    assert t.category == category and (t.sentiment < 0) == negative and t.by == "mots-clés"


def test_triage_falls_back_to_rules_without_model():
    assert config.get_settings().nvidia_api_key == ""
    [t] = triage.triage("Air Liquide", [("Air Liquide abaisse ses prévisions", None)])
    assert t.by == "mots-clés" and t.category == "previsions"


def test_triage_mixes_ai_and_rules_when_the_answer_is_partial(monkeypatch):
    fake_llm(monkeypatch, lambda role, p: json.dumps([{"n": 2, "category": "resultats", "sentiment": 1,
                                                       "importance": 2, "summary": "Bons résultats."}]))
    out = triage.triage("X", [("Titre un", None), ("Titre deux", None)])
    assert [t.by for t in out] == ["mots-clés", "fake:model-test"]


# --- Digest --------------------------------------------------------------------------------------

def test_digest_drops_points_without_valid_sources():
    text = json.dumps({"points": [{"text": "Un fait bien sourcé ici.", "sources": [1, 9]},
                                  {"text": "Un fait inventé sans source.", "sources": [7]}],
                       "watch": [{"text": "Prochaine publication.", "sources": [2]}]})
    points, watch, dropped = digest.parse_answer(text, n_sources=2)
    assert points == [{"text": "Un fait bien sourcé ici.", "sources": [1]}] and dropped == 1
    assert watch[0]["sources"] == [2]


def test_digest_unusable_answer_is_an_error(monkeypatch):
    fake_llm(monkeypatch, lambda role, p: "Je ne sais pas.")
    with pytest.raises(ValueError):
        digest.summarize("X", [{"title": "a", "date": "01/01/2026"}, {"title": "b", "date": "01/01/2026"}])


# --- Service and API -----------------------------------------------------------------------------

@pytest.fixture
def session():
    db.init_db()
    with Session(db.get_engine()) as s:
        yield s


def test_refresh_stores_triages_and_alerts_once(session, monkeypatch):
    fake_llm(monkeypatch, lambda role, p: TRIAGE_ANSWER)
    i = store.add_instrument(session, fake.ISIN)
    r = service.refresh(session, i)
    # Alert for the profit warning (major, negative); none for the buyback (notable but positive).
    assert r.new == 3 and r.triaged_by_ai == 3 and r.alerts == 1
    assert service.refresh(session, i).new == 0  # nothing twice
    alerts = service.alerts(session)
    assert alerts[-1]["severity"] == 3 and "prévisions" in alerts[-1]["title"].lower()
    assert service.mark_read(session) == 1 and service.alerts(session, unread_only=True) == []


def test_price_alert_on_a_big_move(session):
    i = store.add_instrument(session, fake.ISIN)
    session.query(Price).filter(Price.instrument_id == i.id).delete()
    today = date.today()
    session.add_all([Price(instrument_id=i.id, day=today - timedelta(days=1), close=100, adj_close=100),
                     Price(instrument_id=i.id, day=today, close=90, adj_close=90)])
    session.commit()
    assert service.price_alert(session, i) and not service.price_alert(session, i)
    assert service.alerts(session)[0]["severity"] == 3 and "-10.0%" in service.alerts(session)[0]["title"]


def test_digest_numbered_sources(session, monkeypatch):
    def answer(role, prompt):
        if role == "fast":
            return TRIAGE_ANSWER
        return json.dumps({"points": [{"text": "Les prévisions baissent, à suivre de près.", "sources": [1]}],
                           "watch": []})
    fake_llm(monkeypatch, answer)
    i = store.add_instrument(session, fake.ISIN)
    service.refresh(session, i)
    row = service.make_digest(session, i)
    assert row.points[0]["sources"] == [1] and len(row.sources) == 2  # the noise (importance 0) is left out
    assert row.sources[0]["n"] == 1 and service.latest_digest(session, i)["model"] == "fake:model-test"


def test_old_articles_are_purged(session, monkeypatch):
    fake_llm(monkeypatch, lambda role, p: TRIAGE_ANSWER)
    i = store.add_instrument(session, fake.ISIN)
    service.refresh(session, i)
    item = session.query(NewsItem).first()
    item.published_at = item.published_at - timedelta(days=400)
    session.commit()
    service.refresh(session, i)
    assert session.query(NewsItem).count() == 2


def test_api(monkeypatch):
    fake_llm(monkeypatch, lambda role, p: TRIAGE_ANSWER)
    from trade_assistant.api import app

    with TestClient(app) as client:
        client.post("/api/instruments", json={"isin": fake.ISIN})
        r = client.post(f"/api/instruments/{fake.ISIN}/news/refresh").json()
        assert r["new"] == 3
        feed = client.get("/api/news?scope=all").json()
        assert [x["importance"] for x in feed["items"]] == [3, 2]  # noise hidden by default
        assert client.get("/api/news?scope=mine").json()["items"] == []  # nothing held or selected yet
        detail = client.get(f"/api/instruments/{fake.ISIN}/news").json()
        assert len(detail["items"]) == 3 and detail["digest"] is None
        alerts = client.get("/api/alerts?unread=true").json()
        client.post(f"/api/alerts/{alerts[0]['id']}/read")
        assert len(client.get("/api/alerts?unread=true").json()) == len(alerts) - 1
        assert client.post("/api/instruments/FR0000120271/digest").status_code == 404


def test_one_alert_per_story_and_good_news_is_only_informative(session, monkeypatch):
    answer = json.dumps([{"n": k, "category": "actionnaires", "sentiment": 2, "importance": 3,
                          "summary": f"Rachat d'actions de 4 Md€ (article {k})."} for k in (1, 2, 3)])
    fake_llm(monkeypatch, lambda role, p: answer)
    i = store.add_instrument(session, fake.ISIN)
    assert service.refresh(session, i).alerts == 1  # three articles, one story
    assert service.alerts(session)[0]["severity"] == 1
