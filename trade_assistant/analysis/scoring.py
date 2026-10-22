"""Every metric: what it measures, its thresholds, how it scores. Then pillars and a score /100.

A metric scores 0 at its "bad" threshold, 100 at its "good" one, linearly in between. The
thresholds are classic rules of thumb for large European companies, written down so they can be
read and challenged, never hidden in a black box.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Metric:
    label: str
    pillar: str
    bad: float
    good: float
    fmt: str  # "pct", "x" (multiple), "num"
    help: str
    for_financials: bool = True  # False: meaningless for a bank or an insurer
    financials_only: bool = False


PILLARS = {
    "quality": ("Qualité", 0.30, "L'entreprise gagne-t-elle beaucoup d'argent avec le capital qu'elle utilise ?"),
    "solidity": ("Solidité", 0.20, "Peut-elle traverser une crise sans s'endetter dangereusement ?"),
    "growth": ("Croissance", 0.20, "Ses ventes et ses bénéfices progressent-ils dans la durée ?"),
    "valuation": ("Valorisation", 0.20, "Le prix payé aujourd'hui est-il raisonnable pour ce qu'on achète ?"),
    "risk": ("Risque de marché", 0.10, "À quel point le cours secoue-t-il ?"),
}

METRICS: dict[str, Metric] = {
    # Quality
    "roic": Metric("Rentabilité du capital investi (ROIC)", "quality", 0.05, 0.20, "pct",
                   "Bénéfice d'exploitation après impôt / capital investi (fonds propres + dette). Au-dessus de "
                   "15 %, l'entreprise a un avantage durable (marque, technologie, réseau) ; sous 7 %, elle "
                   "rapporte à peine plus que son coût de financement.", for_financials=False),
    "roe": Metric("Rentabilité des fonds propres (ROE)", "quality", 0.05, 0.20, "pct",
                  "Bénéfice net / capitaux propres : ce que rapporte chaque euro des actionnaires. Bon au-dessus "
                  "de 15 %, mais méfiance si la dette le gonfle (regarde aussi la solidité)."),
    "operating_margin": Metric("Marge opérationnelle", "quality", 0.05, 0.25, "pct",
                               "Part des ventes qui reste en bénéfice d'exploitation. Une marge élevée et stable "
                               "signale un pouvoir de fixer ses prix.", for_financials=False),
    "fcf_margin": Metric("Marge de trésorerie disponible", "quality", 0.0, 0.15, "pct",
                         "Cash réellement disponible (après investissements) pour 1 € de ventes. C'est avec ce "
                         "cash que l'entreprise paie dividendes et rachats.", for_financials=False),
    "cash_conversion": Metric("Conversion du bénéfice en cash", "quality", 0.5, 1.0, "pct",
                              "Trésorerie disponible / bénéfice net. Proche de 100 % : les bénéfices sont bien "
                              "réels. Durablement sous 50 % : bénéfices comptables ou investissements très lourds.",
                              for_financials=False),
    # Solidity
    "net_debt_to_ebitda": Metric("Dette nette / EBITDA", "solidity", 4.0, 0.0, "x",
                                 "Nombre d'années de résultat brut d'exploitation pour rembourser la dette nette. "
                                 "Sous 2 : confortable ; au-dessus de 3,5 : la dette devient un risque. Négatif : "
                                 "plus de trésorerie que de dette.", for_financials=False),
    "interest_coverage": Metric("Couverture des intérêts", "solidity", 2.0, 15.0, "x",
                                "Résultat d'exploitation / charges d'intérêts. Sous 3, une hausse des taux ou une "
                                "mauvaise année peut mettre l'entreprise en difficulté.", for_financials=False),
    "current_ratio": Metric("Liquidité courante", "solidity", 0.8, 1.5, "x",
                            "Actifs à moins d'un an / dettes à moins d'un an. Au-dessus de 1 : elle peut payer "
                            "ses échéances proches.", for_financials=False),
    "equity_ratio": Metric("Fonds propres / total du bilan", "solidity", 0.2, 0.5, "pct",
                           "Part du bilan financée par les actionnaires plutôt que par la dette.",
                           for_financials=False),
    # Growth
    "revenue_cagr": Metric("Croissance annuelle des ventes", "growth", -0.02, 0.10, "pct",
                           "Progression moyenne par an du chiffre d'affaires sur les dernières années. Sans "
                           "croissance des ventes, les bénéfices finissent par plafonner."),
    "revenue_recent": Metric("Croissance récente des ventes (2 ans)", "growth", -0.02, 0.08, "pct",
                             "La tendance des deux derniers exercices. Elle corrige l'effet d'une année de départ "
                             "exceptionnelle (2020, l'année du Covid, gonfle la croissance sur 5 ans) et montre si "
                             "l'entreprise accélère ou ralentit."),
    "eps_cagr": Metric("Croissance annuelle du bénéfice par action", "growth", -0.02, 0.12, "pct",
                       "C'est elle qui fait monter le cours à long terme. Elle compte les rachats d'actions et "
                       "pénalise la dilution."),
    "revenue_consistency": Metric("Régularité de la croissance", "growth", 0.4, 1.0, "pct",
                                  "Part des années où les ventes ont progressé. Une croissance régulière est plus "
                                  "prévisible, donc moins risquée, qu'une croissance en dents de scie."),
    # Valuation
    "pe": Metric("PER (cours / bénéfice)", "valuation", 30.0, 12.0, "x",
                 "Combien d'années de bénéfice actuel on paie. Autour de 15 : prix moyen ; au-dessus de 25 : "
                 "le marché attend beaucoup de croissance, la moindre déception coûte cher."),
    "pe_vs_history": Metric("PER par rapport à son historique", "valuation", 1.3, 0.8, "x",
                            "PER actuel / PER médian des dernières années. Sous 1 : l'action est moins chère "
                            "que d'habitude ; à vérifier : est-ce une opportunité ou un vrai problème ?"),
    "fcf_yield": Metric("Rendement de la trésorerie disponible", "valuation", 0.01, 0.06, "pct",
                        "Trésorerie disponible / capitalisation : le « loyer » en cash que rapporte l'entreprise "
                        "à ce prix. Au-dessus de 5 % : bon marché ; sous 2 % : cher.", for_financials=False),
    "ev_ebit": Metric("Valeur d'entreprise / résultat d'exploitation", "valuation", 25.0, 10.0, "x",
                      "Comme le PER, mais en comptant la dette : compare des entreprises plus ou moins endettées.",
                      for_financials=False),
    "pb": Metric("Cours / valeur comptable", "valuation", 2.5, 0.8, "x",
                 "Pour une banque ou une assurance : prix payé pour 1 € de fonds propres. Sous 1 : décote, "
                 "souvent justifiée par une rentabilité faible.", financials_only=True),
    "dividend_yield": Metric("Rendement du dividende", "valuation", 0.0, 0.04, "pct",
                             "Dividendes versés / capitalisation. Un rendement très élevé (> 7 %) annonce "
                             "souvent une baisse du dividende : regarde le taux de distribution."),
    # Market risk
    "volatility": Metric("Volatilité sur 1 an", "risk", 0.40, 0.15, "pct",
                         "Amplitude annuelle habituelle des variations du cours. 20 % : une année normale peut "
                         "finir entre -20 % et +20 %."),
    "max_drawdown": Metric("Pire baisse sur 5 ans", "risk", -0.50, -0.15, "pct",
                           "Plus forte chute depuis un sommet. C'est ce qu'il aurait fallu supporter sans vendre."),
    "beta": Metric("Sensibilité au marché (bêta)", "risk", 1.5, 0.7, "num",
                   "1,3 : l'action bouge de 13 % quand le marché européen bouge de 10 %. Sous 1 : plus calme "
                   "que le marché."),
}

# Shown on the page to understand the company, but not scored.
INFO = {
    "net_margin": ("Marge nette", "pct"), "gross_margin": ("Marge brute", "pct"),
    "payout_ratio": ("Taux de distribution", "pct"), "return_1y": ("Performance 1 an", "pct"),
    "return_3y": ("Performance annuelle sur 3 ans", "pct"), "return_5y": ("Performance annuelle sur 5 ans", "pct"),
    "dividend_cagr": ("Croissance annuelle du dividende", "pct"),
}


def metric_score(metric: Metric, value: float) -> float:
    span = metric.good - metric.bad
    return max(0.0, min(100.0, (value - metric.bad) / span * 100))


@dataclass
class Scored:
    key: str
    value: float
    score: float
    detail: str | None = None  # e.g. "moyenne 2023-2025, rapport officiel"


def score(values: dict[str, tuple[float, str | None]], is_financial: bool) -> dict:
    """values: metric -> (value, detail). Returns pillars, the score /100, strengths and weaknesses."""
    pillars: dict[str, dict] = {}
    for key, (label, weight, question) in PILLARS.items():
        pillars[key] = {"label": label, "question": question, "weight": weight, "score": None, "metrics": []}
    for key, metric in METRICS.items():
        if (is_financial and not metric.for_financials) or (metric.financials_only and not is_financial):
            continue
        entry = {"key": key, "label": metric.label, "fmt": metric.fmt, "help": metric.help,
                 "good": metric.good, "bad": metric.bad, "value": None, "score": None, "detail": None}
        if key in values and values[key][0] is not None:
            value, detail = values[key]
            entry.update(value=value, score=round(metric_score(metric, value)), detail=detail)
        pillars[metric.pillar]["metrics"].append(entry)

    total, weights = 0.0, 0.0
    for p in pillars.values():
        scores = [m["score"] for m in p["metrics"] if m["score"] is not None]
        if scores:
            p["score"] = round(sum(scores) / len(scores))
            total += p["score"] * p["weight"]
            weights += p["weight"]
    scored_pillars = sum(1 for p in pillars.values() if p["score"] is not None)
    # Fewer than 3 pillars measured: not enough to judge a company.
    overall = round(total / weights) if weights and scored_pillars >= 3 else None

    measured = [m for p in pillars.values() for m in p["metrics"] if m["score"] is not None]
    strengths = [m["label"] for m in sorted(measured, key=lambda m: -m["score"]) if m["score"] >= 75][:3]
    weaknesses = [m["label"] for m in sorted(measured, key=lambda m: m["score"]) if m["score"] <= 25][:3]
    return {"score": overall, "verdict": verdict(overall), "pillars": pillars, "strengths": strengths,
            "weaknesses": weaknesses}


def verdict(overall: int | None) -> str:
    if overall is None:
        return "Données insuffisantes pour un avis"
    if overall >= 70:
        return "Dossier solide : qualité et prix réunis"
    if overall >= 55:
        return "Dossier correct, avec des points à surveiller"
    if overall >= 40:
        return "Dossier mitigé : les faiblesses pèsent autant que les forces"
    return "Dossier fragile ou trop cher en l'état"
