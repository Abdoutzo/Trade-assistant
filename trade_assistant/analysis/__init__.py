"""Brick 2: fundamental analysis. Pure calculations (ratios, risk, scoring) + a cached service.

    ratios.py   yearly ratios from the annual accounts, never mixing two sources in one ratio
    risk.py     returns, volatility, drawdown, beta from daily prices
    scoring.py  every metric's definition, thresholds and explanation; pillars; the score /100
    service.py  loads the data, converts currencies, caches the result per instrument
"""
