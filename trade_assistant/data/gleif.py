"""GLEIF, the global register of legal entities (free, official): who issues an ISIN, and where."""
from __future__ import annotations

from dataclasses import dataclass

from .http import get_json


@dataclass(frozen=True)
class Entity:
    lei: str
    legal_name: str
    country: str  # registered office (legal address), ISO 3166 alpha-2


def entity_for_isin(isin: str) -> Entity | None:
    data = get_json("https://api.gleif.org/api/v1/lei-records", {"filter[isin]": isin})
    records = data.get("data") or []
    if not records:
        return None
    entity = records[0]["attributes"]["entity"]
    return Entity(lei=records[0]["id"], legal_name=entity["legalName"]["name"],
                  country=entity["legalAddress"]["country"])
