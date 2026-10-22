from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from trade_assistant import db, llm
from trade_assistant.analysis.scoring import METRICS
from trade_assistant.guide import service
from trade_assistant.guide.content import CHAPTERS, GLOSSARY, METRIC_CHAPTER
from trade_assistant.models import MonthlyPlan

# Pages of the website that the chapters may link to (web/src/App.tsx).
ROUTES = {"/", "/analyses", "/classement", "/portefeuille", "/actualites", "/plan", "/journal", "/guide",
          "/reglages"}


@pytest.fixture
def client():
    from trade_assistant.api import app

    with TestClient(app) as c:
        yield c


# --- Content -------------------------------------------------------------------------------------

def test_content_is_consistent():
    ids = [c["id"] for c in CHAPTERS]
    assert len(ids) == len(set(ids)) == 10
    for c in CHAPTERS:
        assert c["sections"] and c["takeaways"] and c["quiz"], c["id"]
        assert all(k in GLOSSARY for k in c["glossary"]), c["id"]
        assert all(path in ROUTES for path, _ in c["links"]), c["id"]
        for question, choices, answer, explanation in c["quiz"]:
            assert 0 <= answer < len(choices) and explanation, question
        bold = "".join(text for _, text in c["sections"]).count("**")
        assert bold % 2 == 0, f"{c['id']}: ** non fermé"
    assert set(METRIC_CHAPTER) == set(METRICS) and set(METRIC_CHAPTER.values()) <= set(ids)


def test_quiz_choices_are_shuffled_but_stable():
    positions = [right for c in CHAPTERS for _, _, right, _ in service.quiz(c["id"])]
    assert max(positions.count(i) for i in range(3)) < 0.6 * len(positions)  # not guessable by place
    assert service.quiz("pea") == service.quiz("pea")
    for c in CHAPTERS:
        pairs = zip(service.quiz(c["id"]), c["quiz"], strict=True)
        for (_, choices, right, _), (_, original, answer, _) in pairs:
            assert choices[right] == original[answer] and sorted(choices) == sorted(original)


def test_tax_figures_are_the_2026_ones():
    text = json.dumps([CHAPTERS, GLOSSARY], ensure_ascii=False)
    assert "18,6 %" in text and "31,4 %" in text
    assert not re.search(r"17,2 %|\b30 % de flat|flat tax de 30", text)


def test_the_app_routes_exist():
    app_tsx = (Path(__file__).parent.parent / "web/src/App.tsx").read_text("utf-8")
    for path in ROUTES - {"/"}:
        assert f'path="{path[1:]}"' in app_tsx, path


# --- Progress and quiz ---------------------------------------------------------------------------

def test_reading_and_quiz(client):
    start = client.get("/api/guide").json()
    assert start["next"] == "bases" and start["read"] == 0 and start["total"] == 10

    chapter = client.get("/api/guide/bases").json()
    assert chapter["number"] == 1 and chapter["previous"] is None and chapter["next"] == "pea"
    assert "answer_index" not in json.dumps(chapter["quiz"])  # graded by the server only
    assert chapter["glossary"][0]["definition"]

    assert client.post("/api/guide/bases/read").json()["read"] is True
    assert client.get("/api/guide").json()["next"] == "pea"

    rights = [q[2] for q in service.quiz("bases")]
    wrong = [(a + 1) % 3 for a in rights]
    result = client.post("/api/guide/bases/quiz", json={"answers": wrong}).json()
    first = result["results"][0]
    assert result["score"] == 0 and not first["correct"] and first["explanation"]
    perfect = client.post("/api/guide/bases/quiz", json={"answers": rights}).json()
    assert perfect["score"] == perfect["total"] == len(rights)
    again = client.post("/api/guide/bases/quiz", json={"answers": wrong}).json()
    assert again["score"] == 0 and again["best"] == len(rights)  # the best score is kept

    summary = client.get("/api/guide").json()
    assert summary["mastered"] == 1 and summary["chapters"][0]["quiz_score"] == len(rights)


def test_quiz_answers_the_pea_chapter_without_reading_first(client):
    rights = [q[2] for q in service.quiz("pea")]
    client.post("/api/guide/pea/quiz", json={"answers": rights})
    summary = client.get("/api/guide").json()
    assert summary["chapters"][1]["read"] is True and summary["next"] == "bases"


def test_errors(client):
    assert client.get("/api/guide/inconnu").status_code == 404
    assert client.post("/api/guide/inconnu/read").status_code == 404
    assert client.post("/api/guide/bases/quiz", json={"answers": [0]}).status_code == 422


def test_glossary(client):
    terms = client.get("/api/guide/glossary").json()
    assert len(terms) == len(GLOSSARY)
    pea = next(t for t in terms if t["key"] == "pea")
    assert pea["chapter"] == "pea" and "18,6 %" in pea["definition"]


# --- AI parts ------------------------------------------------------------------------------------

def test_lessons_from_plans_are_labeled_as_ai(client):
    db.init_db()
    lesson = {"title": "La taille de position", "text": "Une perte totale sur 10 € ne coûte que 1 %."}
    with Session(db.get_engine()) as s:
        for status in ("replaced", "approved"):
            s.add(MonthlyPlan(month="2026-10", status=status, data={"lesson": lesson, "orders": []}))
        s.add(MonthlyPlan(month="2026-10", status="draft", data={"lesson": None, "orders": []}))
        s.commit()
    lessons = client.get("/api/guide").json()["lessons"]
    assert len(lessons) == 1 and lessons[0]["title"] == "La taille de position"
    assert "IA" in lessons[0]["warning"]


def test_ask_cites_chapters_and_flags_invented_figures(client, monkeypatch):
    prompts = []

    def ask(role, prompt, system=None):
        prompts.append((role, prompt))
        reply = {"answer": "Après 5 ans, seuls les prélèvements sociaux de 18,6 % restent, et non 12,5 %.",
                 "chapters": ["pea", "inconnu"], "outside": False}
        return llm.Answer(json.dumps(reply, ensure_ascii=False), "fake", "m")

    monkeypatch.setattr(llm, "ask", ask)
    r = client.post("/api/guide/ask", json={"question": "Combien d'impôt après 5 ans de PEA ?"}).json()
    assert r["chapters"] == [{"id": "pea", "title": service.BY_ID["pea"]["title"]}]
    assert r["unverified"] == [12.5] and "IA" in r["warning"]
    role, prompt = prompts[0]
    assert role == "long_context" and "[pea]" in prompt and "Question : Combien" in prompt


def test_ask_accepts_plain_text_and_needs_a_key(client, monkeypatch):
    assert client.post("/api/guide/ask", json={"question": "Qu'est-ce qu'un ETF ?"}).status_code == 503
    monkeypatch.setattr(llm, "ask", lambda role, prompt, system=None: llm.Answer(
        "Un ETF reproduit un indice, voir [bases].", "fake", "m"))
    r = client.post("/api/guide/ask", json={"question": "Qu'est-ce qu'un ETF ?"}).json()
    assert r["answer"].startswith("Un ETF") and r["chapters"][0]["id"] == "bases"
    assert client.post("/api/guide/ask", json={"question": "?"}).status_code == 422
