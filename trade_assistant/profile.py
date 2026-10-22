"""The investor profile: created from the .env defaults the first time, then edited on the site."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .config import get_settings
from .models import InvestorProfile


class ProfileIn(BaseModel):
    account_type: Literal["PEA", "CTO"]
    initial_amount_eur: float = Field(ge=0, le=10_000_000)
    monthly_amount_eur: float = Field(ge=0, le=1_000_000)
    core_share: float = Field(ge=0, le=1)
    horizon_years: int = Field(ge=1, le=60)


def get_profile(session: Session) -> InvestorProfile:
    profile = session.get(InvestorProfile, 1)
    if profile is None:
        s = get_settings()
        profile = InvestorProfile(id=1, account_type=s.account_type.upper(),
                                  initial_amount_eur=s.initial_amount_eur,
                                  monthly_amount_eur=s.monthly_amount_eur, core_share=s.core_share,
                                  horizon_years=15)
        session.add(profile)
        session.commit()
    return profile


def update_profile(session: Session, data: ProfileIn) -> InvestorProfile:
    profile = get_profile(session)
    for field, value in data.model_dump().items():
        setattr(profile, field, value)
    session.commit()
    return profile


def as_dict(profile: InvestorProfile) -> dict:
    return {"account_type": profile.account_type, "initial_amount_eur": profile.initial_amount_eur,
            "monthly_amount_eur": profile.monthly_amount_eur, "core_share": profile.core_share,
            "satellite_share": round(1 - profile.core_share, 4), "horizon_years": profile.horizon_years,
            "updated_at": profile.updated_at}
