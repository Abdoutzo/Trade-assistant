"""Brick 4: news watch.

    sources.py  collects articles (Google News in French and English, Yahoo Finance RSS)
    triage.py   classifies each article: category, tone, importance, one-line summary in French
                (AI first, keyword rules when no model answers)
    digest.py   AI summary of a company's news, every point tied to numbered sources
    service.py  storage, alerts (major news, unusual price moves), what the site shows
"""
