"""The web server: a JSON API under /api, and the built website (web/dist) for everything else.

    uvicorn trade_assistant.api:app --reload
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import (
    __version__,
    auth,
    llm,
    profile,
    routes_agent,
    routes_analysis,
    routes_data,
    routes_news,
    routes_portfolio,
)
from .config import get_settings
from .db import get_session, init_db, ping

WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_settings().check()
    init_db()
    yield


app = FastAPI(title="Trade Assistant", version=__version__, lifespan=lifespan,
              docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)

public = APIRouter(prefix="/api")
private = APIRouter(prefix="/api", dependencies=[Depends(auth.require_auth)])


@public.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, "database": ping()}


# --- Login --------------------------------------------------------------------------------------

class LoginRequest(BaseModel):
    password: str


# Failed logins per client IP: 5 tries per 15 minutes, enough for a typo, useless for guessing.
_FAILED: dict[str, deque[float]] = defaultdict(deque)
MAX_FAILURES, WINDOW_S = 5, 15 * 60


def _too_many_failures(ip: str) -> bool:
    attempts = _FAILED[ip]
    while attempts and attempts[0] < time.monotonic() - WINDOW_S:
        attempts.popleft()
    return len(attempts) >= MAX_FAILURES


@public.post("/auth/login")
def login(body: LoginRequest, request: Request, response: Response) -> dict:
    ip = request.client.host if request.client else "unknown"
    if _too_many_failures(ip):
        raise HTTPException(429, "Trop de tentatives, réessaie dans 15 minutes")
    if not auth.check_password(body.password):
        _FAILED[ip].append(time.monotonic())
        raise HTTPException(401, "Mot de passe incorrect")
    _FAILED.pop(ip, None)
    auth.open_session(response)
    return {"authenticated": True}


@public.post("/auth/logout")
def logout(response: Response) -> dict:
    auth.close_session(response)
    return {"authenticated": False}


@public.get("/auth/me")
def me(request: Request) -> dict:
    return {"authenticated": auth.is_authenticated(request), "login_enabled": auth.login_enabled()}


# --- Private API --------------------------------------------------------------------------------

@private.get("/profile")
def read_profile(session: Session = Depends(get_session)) -> dict:
    return profile.as_dict(profile.get_profile(session))


@private.put("/profile")
def write_profile(body: profile.ProfileIn, session: Session = Depends(get_session)) -> dict:
    return profile.as_dict(profile.update_profile(session, body))


@private.get("/llm/status")
def llm_status() -> dict:
    return llm.status()


class LlmTestRequest(BaseModel):
    role: str = "fast"


@private.post("/llm/test")
def llm_test(body: LlmTestRequest) -> dict:
    """Check the keys: a one-line question to the first model that answers for this role."""
    if body.role not in llm.ROLES:
        raise HTTPException(422, f"Rôle inconnu, choisis parmi {', '.join(llm.ROLES)}")
    try:
        answer = llm.ask(body.role, "Réponds seulement : OK", system="Tu es un test de connexion.")
    except llm.NoModelAvailable as e:
        raise HTTPException(503, str(e)) from e
    return {"provider": answer.provider, "model": answer.model, "answer": answer.text.strip()[:200]}


app.include_router(public)
app.include_router(private)
app.include_router(routes_data.router)
app.include_router(routes_analysis.router)
app.include_router(routes_portfolio.router)
app.include_router(routes_news.router)
app.include_router(routes_agent.router)


# --- Website ------------------------------------------------------------------------------------

if WEB_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        """Static files when they exist, index.html otherwise (the site handles its own routes)."""
        if path.startswith("api/"):
            raise HTTPException(404)
        file = (WEB_DIST / path).resolve()
        if path and file.is_file() and file.is_relative_to(WEB_DIST):
            return FileResponse(file)
        return FileResponse(WEB_DIST / "index.html")
