"""LLM router: the best free model for each kind of task, with automatic fallback.

Free tiers are generous but unstable: limits per minute, models that leave the free catalog.
So every task asks for a *role*, and each role is a chain of (provider, model) tried in order:

    reasoning     deep analysis, devil's advocate, monthly plan  -> NVIDIA NIM big models first
    long_context  reading a whole annual report (1M tokens)      -> Gemini Flash first
    fast          news triage, classification, short summaries   -> Groq first (very fast)

A provider without an API key is skipped. A provider that fails (429, timeout, model removed)
hands over to the next one. Override a chain in .env: LLM_CHAIN_REASONING="nvidia:z-ai/glm-5.3,...".
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_core.runnables import Runnable

from .config import Settings, get_settings

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Provider:
    key_field: str  # attribute of Settings holding the API key
    requests_per_second: float  # spacing that respects the free tier
    base_url: str | None = None  # OpenAI-compatible endpoint, None for native SDKs


PROVIDERS: dict[str, Provider] = {
    "nvidia": Provider("nvidia_api_key", 0.6, "https://integrate.api.nvidia.com/v1"),  # ~40 req/min
    "google": Provider("google_api_key", 0.15),  # ~10 req/min on Flash
    "groq": Provider("groq_api_key", 0.45),  # ~30 req/min
    "openrouter": Provider("openrouter_api_key", 0.3, "https://openrouter.ai/api/v1"),  # ~20 req/min
}

# Free endpoints checked in October 2026; the catalog rotates, hence the fallbacks.
DEFAULT_CHAINS: dict[str, str] = {
    "reasoning": "nvidia:nvidia/nemotron-3-ultra-550b-a55b,nvidia:z-ai/glm-5.3,"
                 "google:gemini-flash-latest,groq:openai/gpt-oss-120b",
    "long_context": "google:gemini-flash-latest,nvidia:nvidia/nemotron-3-ultra-550b-a55b",
    "fast": "groq:openai/gpt-oss-120b,nvidia:nvidia/nemotron-3.5-lightning-30b-a3b,"
            "google:gemini-flash-lite-latest",
}
ROLES = tuple(DEFAULT_CHAINS)


class NoModelAvailable(RuntimeError):
    pass


NO_KEY = ("Aucune clé d'IA configurée : ajoute NVIDIA_API_KEY (et éventuellement GOOGLE_API_KEY, "
          "GROQ_API_KEY) dans le fichier .env, dans Render > Environment ou dans les secrets GitHub.")


@dataclass(frozen=True)
class Answer:
    text: str
    provider: str
    model: str


def parse_chain(spec: str) -> list[tuple[str, str]]:
    """'nvidia:z-ai/glm-5.3, google:gemini-flash-latest' -> [('nvidia', 'z-ai/glm-5.3'), ...]."""
    entries = []
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        provider, sep, model = item.partition(":")
        if not sep or not model or provider not in PROVIDERS:
            raise ValueError(f"Invalid LLM chain entry {item!r}: expected provider:model, "
                             f"provider in {', '.join(PROVIDERS)}")
        entries.append((provider, model))
    return entries


def chain(role: str, settings: Settings | None = None) -> list[tuple[str, str]]:
    """The (provider, model) pairs usable for a role, in order, keeping only providers with a key."""
    if role not in DEFAULT_CHAINS:
        raise ValueError(f"Unknown LLM role {role!r}; use one of {', '.join(ROLES)}")
    settings = settings or get_settings()
    spec = getattr(settings, f"llm_chain_{role}") or DEFAULT_CHAINS[role]
    return [(p, m) for p, m in parse_chain(spec) if getattr(settings, PROVIDERS[p].key_field)]


@lru_cache
def _rate_limiter(provider: str) -> InMemoryRateLimiter:
    # One limiter per provider, shared by all its models: the quota is per account, not per model.
    return InMemoryRateLimiter(requests_per_second=PROVIDERS[provider].requests_per_second,
                               check_every_n_seconds=0.1, max_bucket_size=2)


def chat_model(provider: str, model: str, role: str, settings: Settings | None = None) -> BaseChatModel:
    settings = settings or get_settings()
    spec = PROVIDERS[provider]
    api_key = getattr(settings, spec.key_field)
    # A big model that thinks can take minutes: long timeout, and no retry on the same model (the
    # next one of the chain is tried instead, a timeout rarely fixes itself in a few seconds).
    deep = role == "reasoning"
    common: dict[str, Any] = dict(temperature=0, max_retries=0 if deep else 1, timeout=300 if deep else 120,
                                  rate_limiter=_rate_limiter(provider))
    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model, google_api_key=api_key, **common)
    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(model=model, api_key=api_key, **common)
    from langchain_openai import ChatOpenAI
    extra: dict[str, Any] = {}
    if "nemotron" in model:
        # Nemotron "thinks" before answering: worth it for deep analysis, wasted on quick tasks.
        extra["chat_template_kwargs"] = {"enable_thinking": role == "reasoning"}
    # Streaming: the answer arrives in pieces, so a long answer is never cut by the read timeout.
    return ChatOpenAI(model=model, base_url=spec.base_url, api_key=api_key, max_tokens=8000,
                      extra_body=extra or None, streaming=True, stream_usage=True, **common)


def get_model(role: str, tools: list | None = None) -> Runnable:
    """A runnable for the agent: the first model of the chain, the others as fallbacks."""
    entries = chain(role)
    if not entries:
        raise NoModelAvailable(NO_KEY)
    models: list[Runnable] = []
    for provider, model in entries:
        m: Runnable = chat_model(provider, model, role)
        models.append(m.bind_tools(tools) if tools else m)
    return models[0].with_fallbacks(models[1:]) if len(models) > 1 else models[0]


def ask(role: str, prompt: str, system: str | None = None) -> Answer:
    """One question, one text answer, trying each model of the chain until one succeeds."""
    entries = chain(role)
    if not entries:
        raise NoModelAvailable(NO_KEY)
    messages: list[BaseMessage] = ([SystemMessage(system)] if system else []) + [HumanMessage(prompt)]
    errors = []
    for provider, model in entries:
        start = time.monotonic()
        try:
            reply = chat_model(provider, model, role).invoke(messages)
        except Exception as e:  # any provider error: log it and try the next model
            _record(role, provider, model, start, None, e)
            errors.append(f"{provider}:{model}: {type(e).__name__}: {str(e)[:200]}")
            log.warning("LLM %s:%s failed, trying next: %s", provider, model, e)
            continue
        _record(role, provider, model, start, reply, None)
        return Answer(text=_text(reply.content), provider=provider, model=model)
    raise NoModelAvailable("Aucun modèle n'a répondu (quotas gratuits atteints ou service indisponible), "
                           "réessaie plus tard. Détail :\n" + "\n".join(errors))


def _text(content: Any) -> str:
    """Providers return either a string or a list of content blocks; keep only the text."""
    if isinstance(content, str):
        return content
    return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)


def _record(role: str, provider: str, model: str, start: float, reply: Any, error: Exception | None) -> None:
    """Log the call in the database (best effort: a logging failure never breaks an answer)."""
    try:
        from sqlalchemy.orm import Session

        from .db import get_engine
        from .models import LlmCall

        usage = getattr(reply, "usage_metadata", None) or {}
        with Session(get_engine()) as s:
            s.add(LlmCall(role=role, provider=provider, model=model, ok=error is None,
                          latency_ms=int((time.monotonic() - start) * 1000),
                          input_tokens=usage.get("input_tokens", 0),
                          output_tokens=usage.get("output_tokens", 0),
                          error=None if error is None else f"{type(error).__name__}: {str(error)[:500]}"))
            s.commit()
    except Exception as e:
        log.debug("Could not record LLM call: %s", e)


def status(settings: Settings | None = None) -> dict[str, list[dict[str, str]]]:
    """For the dashboard: which models each role will use, without ever exposing a key."""
    settings = settings or get_settings()
    return {role: [{"provider": p, "model": m} for p, m in chain(role, settings)] for role in ROLES}
