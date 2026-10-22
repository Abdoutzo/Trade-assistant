"""The facts the agent reasons on: every figure computed by bricks 1 to 4, numbered F1, F2...

The models never compute nor look anything up: they read these facts and cite their numbers. A
figure that appears in their text but in no fact is flagged (checks.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy.orm import Session

from ..analysis import service as analysis
from ..models import Instrument, utcnow
from ..news import service as news
from ..portfolio import service as portfolio
from ..profile import get_profile

ALTERNATIVES = 3  # stocks outside the selection the manager may swap in


@dataclass
class Company:
    isin: str
    name: str
    sector: str | None
    role: str  # "target" (selected), "held", "alternative"
    score: float | None
    facts: list[str] = field(default_factory=list)  # fact ids about this company


@dataclass
class Context:
    facts: dict[str, str] = field(default_factory=dict)  # "F12" -> text
    companies: dict[str, Company] = field(default_factory=dict)
    proposal: dict = field(default_factory=dict)  # deterministic plan from brick 3
    portfolio: dict = field(default_factory=dict)
    profile: dict = field(default_factory=dict)
    general: list[str] = field(default_factory=list)  # fact ids about the investor and portfolio

    def add(self, text: str) -> str:
        fid = f"F{len(self.facts) + 1}"
        self.facts[fid] = text
        return fid

    def render(self, ids: list[str]) -> str:
        return "\n".join(f"[{i}] {self.facts[i]}" for i in ids)


def _pct(x: float | None) -> str:
    return "n.d." if x is None else f"{x * 100:+.1f} %".replace(".", ",")


def _num(x: float | None, digits: int = 1) -> str:
    return "n.d." if x is None else f"{x:.{digits}f}".replace(".", ",")


def _metric(data: dict, key: str) -> float | None:
    for pillar in (data.get("pillars") or {}).values():
        for m in pillar["metrics"]:
            if m["key"] == key:
                return m["value"]
    return None


def build(session: Session) -> Context:
    ctx = Context()
    profile = get_profile(session)
    pf = portfolio.portfolio(session)
    proposal = portfolio.plan(session)
    ctx.portfolio, ctx.proposal = pf, proposal
    ctx.profile = {"account_type": profile.account_type, "monthly": profile.monthly_amount_eur,
                   "initial": profile.initial_amount_eur, "core_share": profile.core_share,
                   "horizon": profile.horizon_years, **proposal["rules"]}

    r = proposal["rules"]
    ctx.general += [
        ctx.add(f"Profil : {profile.account_type}, versement mensuel {profile.monthly_amount_eur:.0f} €, part ETF "
                f"monde visée {profile.core_share * 100:.0f} %, horizon {profile.horizon_years} ans."),
        ctx.add(f"Règles : au plus {r['satellites_count']} actions, plafond {r['max_position_share'] * 100:.0f} % "
                f"par action, {r['min_order_eur']:.0f} € minimum par plan programmé, 2 actions par secteur au plus."),
        ctx.add(f"Portefeuille : valeur {pf['total_value']:.0f} €, versé {pf['contributions']:.0f} €, "
                f"gain {pf['gain']:.0f} €, part du cœur ETF "
                + ("n.d." if pf["core_weight"] is None else f"{pf['core_weight'] * 100:.0f} %") + "."),
    ]
    for w in pf["warnings"]:
        ctx.general.append(ctx.add(f"Alerte portefeuille : {w}"))
    lines = ", ".join(f"{o['name']} {o['amount']:.0f} €" for o in proposal["orders"])
    ctx.general.append(ctx.add(f"Plan calculé par les règles (brique 3) : {lines}."))

    # Companies: the selection, what is held, and a few alternatives.
    analyses = {i.isin: (i, d) for i, d in analysis.all_analyses(session) if i.kind == "stock"}
    held = {p["isin"]: p for p in pf["positions"] if p["role"] == "satellite"}
    for t in proposal["targets"]:
        _company(ctx, session, analyses.get(t["isin"]), "target", held.get(t["isin"]))
    for isin, p in held.items():
        if isin not in ctx.companies:
            _company(ctx, session, analyses.get(isin), "held", p)
    excluded = portfolio.choices(session)
    sectors = {}
    for c in ctx.companies.values():
        sectors[c.sector] = sectors.get(c.sector, 0) + 1
    ranked = sorted(analyses.values(), key=lambda x: -(x[1].get("score") or 0))
    for i, data in ranked:
        if sum(1 for c in ctx.companies.values() if c.role == "alternative") >= ALTERNATIVES:
            break
        if (i.isin in ctx.companies or excluded.get(i.isin) == "excluded" or (data.get("score") or 0) < 55
                or (profile.account_type == "PEA" and i.pea_eligible is not True)):
            continue
        _company(ctx, session, (i, data), "alternative", None)
    return ctx


def _company(ctx: Context, session: Session, entry: tuple[Instrument, dict] | None, role: str,
             position: dict | None) -> None:
    if entry is None:
        return
    i, data = entry
    c = Company(i.isin, i.name, i.sector, role, data.get("score"))
    p = {k: v["score"] for k, v in (data.get("pillars") or {}).items()}
    c.facts.append(ctx.add(
        f"{i.name} ({i.sector or 'secteur n.d.'}) : note {data.get('score', 'n.d.')}/100 ; qualité {p.get('quality')}, "
        f"solidité {p.get('solidity')}, croissance {p.get('growth')}, valorisation {p.get('valuation')}, "
        f"risque {p.get('risk')}. Verdict : {data.get('verdict')}."))
    c.facts.append(ctx.add(
        f"{i.name} : PER {_num(_metric(data, 'pe'))}, PER / historique {_num(_metric(data, 'pe_vs_history'), 2)}, "
        f"rendement du cash {_pct(_metric(data, 'fcf_yield'))}, dividende {_pct(_metric(data, 'dividend_yield'))}, "
        f"ROIC {_pct(_metric(data, 'roic'))}, croissance des ventes sur 2 ans {_pct(_metric(data, 'revenue_recent'))} "
        f"par an, dette nette / EBITDA {_num(_metric(data, 'net_debt_to_ebitda'))}."))
    info = data.get("info") or {}
    c.facts.append(ctx.add(
        f"{i.name} : performance 1 an {_pct(info.get('return_1y'))}, 5 ans {_pct(info.get('return_5y'))} par an, "
        f"pire baisse sur 5 ans {_pct(_metric(data, 'max_drawdown'))}, volatilité {_pct(_metric(data, 'volatility'))}."))
    if data.get("strengths") or data.get("weaknesses"):
        c.facts.append(ctx.add(f"{i.name} : points forts {', '.join(data.get('strengths') or ['aucun'])} ; "
                               f"points faibles {', '.join(data.get('weaknesses') or ['aucun'])}."))
    if position:
        c.facts.append(ctx.add(
            f"{i.name} en portefeuille : {position['value'] or 0:.0f} €, poids "
            + ("n.d." if position["weight"] is None else f"{position['weight'] * 100:.1f} %")
            + f", plus-value {_pct(position['gain_pct'])}."))
    for item in news.feed(session, {i.isin}, days=45, min_importance=2, limit=6):
        c.facts.append(ctx.add(f"{i.name}, actualité du {item['published_at'][:10]} ({item['category_label']}, "
                               f"importance {item['importance']}/3, ton {item['sentiment'] or 0:+d}) : "
                               f"{item['summary'] or item['title']} [{item['source']}]"))
    since = utcnow() - timedelta(days=45)
    for a in news.alerts(session, unread_only=False, limit=30):
        if a["isin"] == i.isin and a["created_at"] >= since.isoformat():
            c.facts.append(ctx.add(f"{i.name}, alerte : {a['title']}"))
    ctx.companies[i.isin] = c
