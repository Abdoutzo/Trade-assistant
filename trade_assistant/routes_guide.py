"""API of brick 6: the investor's guide."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import auth, llm
from .db import get_session
from .guide import service

router = APIRouter(prefix="/api/guide", dependencies=[Depends(auth.require_auth)])


@router.get("")
def summary(session: Session = Depends(get_session)) -> dict:
    return service.summary(session)


@router.get("/glossary")
def glossary() -> list[dict]:
    return service.glossary()


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)


@router.post("/ask")
def ask(body: Question) -> dict:
    try:
        return service.ask(body.question)
    except llm.NoModelAvailable as e:
        raise HTTPException(503, str(e)) from e


@router.get("/{chapter_id}")
def chapter(chapter_id: str, session: Session = Depends(get_session)) -> dict:
    try:
        return service.chapter(session, chapter_id)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e


@router.post("/{chapter_id}/read")
def read(chapter_id: str, session: Session = Depends(get_session)) -> dict:
    try:
        return service.mark_read(session, chapter_id)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e


class QuizAnswers(BaseModel):
    answers: list[int | None] = Field(max_length=20)


@router.post("/{chapter_id}/quiz")
def quiz(chapter_id: str, body: QuizAnswers, session: Session = Depends(get_session)) -> dict:
    try:
        return service.grade(session, chapter_id, body.answers)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
