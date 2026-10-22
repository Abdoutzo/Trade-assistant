"""Brick 1: market data from free sources.

    yahoo.py     prices, standardised annual accounts, ISIN -> ticker (unofficial API)
    euronext.py  ISIN -> ticker fallback for European listings
    gleif.py     ISIN -> legal entity (LEI, registered office country)
    esef.py      official annual reports of EU listed companies (filings.xbrl.org)
    universe.py  PEA eligibility rules and the starting universe
    store.py     everything that reads or writes the database
"""
