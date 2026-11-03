"""API of brick 8: the journal (your choices against everything on the world ETF)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from . import auth, journal
from .db import get_session

router = APIRouter(prefix="/api/journal", dependencies=[Depends(auth.require_auth)])


@router.get("")
def read(session: Session = Depends(get_session)) -> dict:
    return journal.journal(session)
