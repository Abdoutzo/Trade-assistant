"""Single-user login: one password (APP_PASSWORD), then a signed, HTTP-only session cookie.

Your portfolio is personal data: once deployed, nothing but /api/health and the login page is
reachable without the cookie.
"""
from __future__ import annotations

import hmac

from fastapi import HTTPException, Request, Response, status
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner

from .config import Settings, get_settings

COOKIE = "ta_session"
_PAYLOAD = "owner"


def _signer(settings: Settings) -> TimestampSigner:
    return TimestampSigner(settings.secret_key, salt="trade-assistant-session")


def login_enabled(settings: Settings | None = None) -> bool:
    return bool((settings or get_settings()).app_password)


def check_password(password: str, settings: Settings | None = None) -> bool:
    expected = (settings or get_settings()).app_password
    # Constant-time comparison: the time taken reveals nothing about the password.
    return bool(expected) and hmac.compare_digest(password.encode(), expected.encode())


def open_session(response: Response, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    token = _signer(settings).sign(_PAYLOAD).decode()
    response.set_cookie(COOKIE, token, max_age=settings.session_days * 86400, httponly=True,
                        secure=settings.is_prod, samesite="lax", path="/")


def close_session(response: Response) -> None:
    response.delete_cookie(COOKIE, path="/")


def is_authenticated(request: Request, settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    if not login_enabled(settings):
        return True  # dev mode without password
    token = request.cookies.get(COOKIE)
    if not token:
        return False
    try:
        value = _signer(settings).unsign(token, max_age=settings.session_days * 86400)
    except (BadSignature, SignatureExpired):
        return False
    return value.decode() == _PAYLOAD


def require_auth(request: Request) -> None:
    """FastAPI dependency protecting every private route."""
    if not is_authenticated(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Connexion requise")
