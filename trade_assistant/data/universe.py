"""PEA rules and the starting universe.

PEA rule for shares: the company's registered office must be in the European Union or the European
Economic Area (Iceland, Liechtenstein, Norway). ETFs: only funds built to be PEA-eligible; there is
no public register, so we keep a list checked by hand.

Trade Republic does not publish its catalogue: the app has the final word on availability.
"""
from __future__ import annotations

EU_EEA = {
    "AT": "Autriche", "BE": "Belgique", "BG": "Bulgarie", "HR": "Croatie", "CY": "Chypre", "CZ": "Tchéquie",
    "DK": "Danemark", "EE": "Estonie", "FI": "Finlande", "FR": "France", "DE": "Allemagne", "GR": "Grèce",
    "HU": "Hongrie", "IE": "Irlande", "IT": "Italie", "LV": "Lettonie", "LT": "Lituanie", "LU": "Luxembourg",
    "MT": "Malte", "NL": "Pays-Bas", "PL": "Pologne", "PT": "Portugal", "RO": "Roumanie", "SK": "Slovaquie",
    "SI": "Slovénie", "ES": "Espagne", "SE": "Suède", "IS": "Islande", "LI": "Liechtenstein", "NO": "Norvège",
}

# PEA-eligible ETFs: ISIN -> Yahoo ticker, each checked on Euronext or Yahoo (October 2026).
PEA_ETFS: dict[str, str] = {
    "FR001400U5Q4": "DCAM.PA",  # Amundi PEA Monde (MSCI World) UCITS ETF Acc
    "IE0002XZSHO1": "WPEA.PA",  # iShares MSCI World Swap PEA UCITS ETF
    "FR0011550185": "ESE.PA",  # BNP Paribas Easy S&P 500 UCITS ETF EUR C
    "FR0011871128": "PSP5.PA",  # Amundi PEA S&P 500 UCITS ETF Acc
    "FR0013412285": "PE500.PA",  # Amundi PEA S&P 500 Screened UCITS ETF
    "FR0011871110": "PUST.PA",  # Amundi PEA Nasdaq-100 UCITS ETF Acc
    "FR0013412038": "PCEU.PA",  # Amundi PEA MSCI Europe UCITS ETF Acc
    "FR0013412020": "PAEEM.PA",  # Amundi PEA Emergent (MSCI Emerging) ESG UCITS ETF
}

# Large European companies to start with, each ISIN checked on Yahoo and GLEIF (October 2026).
# More can be added from the website with any ISIN.
SEED_STOCKS: dict[str, str] = {
    "FR0000120073": "Air Liquide", "FR0000121014": "LVMH", "FR0000120321": "L'Oréal",
    "FR0000121972": "Schneider Electric", "FR0000120578": "Sanofi", "FR0000120271": "TotalEnergies",
    "FR0000131104": "BNP Paribas", "FR0000125338": "Capgemini", "FR0000121667": "EssilorLuxottica",
    "FR0000052292": "Hermès", "FR0000073272": "Safran", "FR0000120628": "AXA", "FR0000125486": "Vinci",
    "FR0010307819": "Legrand", "FR0014003TT8": "Dassault Systèmes", "NL0010273215": "ASML",
    "NL0000235190": "Airbus", "NL0011821202": "ING", "NL0000395903": "Wolters Kluwer",
    "NL0012969182": "Adyen",
    "DE0007164600": "SAP", "DE0007236101": "Siemens", "DE0008404005": "Allianz", "DE0008430026": "Munich Re",
    "DE0005557508": "Deutsche Telekom", "DE0005810055": "Deutsche Börse", "DE0006231004": "Infineon",
    "IT0003128367": "Enel", "IT0000072618": "Intesa Sanpaolo", "NL0011585146": "Ferrari",
    "ES0144580Y14": "Iberdrola", "ES0148396007": "Inditex", "BE0974293251": "AB InBev",
    "DK0062498333": "Novo Nordisk", "FI0009000681": "Nokia",
}

SEED = list(PEA_ETFS) + list(SEED_STOCKS)


def is_valid_isin(isin: str) -> bool:
    """Format and check digit (Luhn on the letters converted to numbers)."""
    isin = isin.strip().upper()
    if len(isin) != 12 or not isin[:2].isalpha() or not isin[2:11].isalnum() or not isin[11].isdigit():
        return False
    digits = "".join(str(int(c, 36)) for c in isin[:11])
    total = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d) * (2 if i % 2 == 0 else 1)
        total += n // 10 + n % 10
    return (10 - total % 10) % 10 == int(isin[11])


def pea_status(kind: str, isin: str, country: str | None) -> tuple[bool | None, str]:
    """(eligible, reason). None when it cannot be decided automatically."""
    isin = isin.upper()
    if kind == "etf":
        if isin in PEA_ETFS:
            return True, "ETF éligible PEA (liste vérifiée)"
        return None, ("ETF hors de la liste vérifiée : regarde la fiche de l'émetteur "
                      "(mention « éligible PEA »)")
    country = (country or isin[:2]).upper()
    if country in EU_EEA:
        return True, f"Siège social en {EU_EEA[country]} (UE/EEE)"
    return False, f"Siège social hors UE/EEE ({country}) : pas éligible au PEA"
