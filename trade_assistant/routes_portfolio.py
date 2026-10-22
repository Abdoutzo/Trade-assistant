"""API of brick 3: transactions, positions, monthly savings plans, simulation."""
from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import auth
from .db import get_session
from .models import Transaction
from .portfolio import service

router = APIRouter(prefix="/api/portfolio", dependencies=[Depends(auth.require_auth)])


def _tx(t: Transaction) -> dict:
    return {"id": t.id, "day": t.day.isoformat(), "isin": t.isin, "side": t.side, "quantity": t.quantity,
            "price_eur": t.price_eur, "fees_eur": t.fees_eur, "note": t.note}


@router.get("")
def read_portfolio(session: Session = Depends(get_session)) -> dict:
    return {**service.portfolio(session), "transactions": [_tx(t) for t in service.transactions(session)]}


class TransactionIn(BaseModel):
    day: date
    isin: str = Field(min_length=12, max_length=12)
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0)
    price_eur: float = Field(gt=0)
    fees_eur: float = Field(default=0, ge=0)
    note: str | None = Field(default=None, max_length=500)


@router.post("/transactions")
def add_transaction(body: TransactionIn, session: Session = Depends(get_session)) -> dict:
    if body.day > date.today():
        raise HTTPException(422, "La date est dans le futur.")
    try:
        t = service.add_transaction(session, **body.model_dump())
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return _tx(t)


@router.delete("/transactions/{tx_id}")
def delete_transaction(tx_id: int, session: Session = Depends(get_session)) -> dict:
    t = session.get(Transaction, tx_id)
    if t is None:
        raise HTTPException(404, "Transaction introuvable")
    session.delete(t)
    session.commit()
    return {"deleted": tx_id}


@router.get("/plan")
def monthly_plan(session: Session = Depends(get_session)) -> dict:
    return service.plan(session)


class ChoiceIn(BaseModel):
    status: Literal["pinned", "excluded"] | None


@router.put("/choices/{isin}")
def set_choice(isin: str, body: ChoiceIn, session: Session = Depends(get_session)) -> dict:
    service.set_choice(session, isin.upper(), body.status)
    return {"isin": isin.upper(), "status": body.status}


class SimulationIn(BaseModel):
    years: int = Field(default=10, ge=2, le=15)
    satellites: list[str] | None = Field(default=None, max_length=15)


@router.post("/simulation")
def simulation(body: SimulationIn, session: Session = Depends(get_session)) -> dict:
    try:
        return service.simulation(session, body.years, body.satellites)
    except LookupError as e:
        raise HTTPException(503, str(e)) from e
