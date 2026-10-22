"""Settings read from the environment (or a .env file). Secrets never live in the code."""
from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DATABASE_URL = "sqlite:///data/trade_assistant.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # "dev" on your machine, "prod" once deployed (secure cookies, strict checks).
    env: str = "dev"

    # Single-user login. In prod both are mandatory; in dev an empty password disables the login.
    app_password: str = ""
    secret_key: str = "dev-only-change-me"
    session_days: int = 30

    # SQLite locally; a postgresql+psycopg://... URL (Neon) in production.
    database_url: str = DEFAULT_DATABASE_URL

    # LLM keys: only the ones you have are needed, the router skips the others.
    nvidia_api_key: str = ""
    google_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""

    # Optional overrides of the model chains, "provider:model,provider:model" (see llm.py).
    llm_chain_reasoning: str = ""
    llm_chain_long_context: str = ""
    llm_chain_fast: str = ""

    # Investment profile (validated in the plan: PEA, 70 % core ETF, 30 % stocks).
    initial_amount_eur: float = 500.0
    monthly_amount_eur: float = 100.0
    core_share: float = 0.70
    account_type: str = "PEA"

    @field_validator("database_url")
    @classmethod
    def _default_when_empty(cls, v: str) -> str:
        # A host form left blank sets DATABASE_URL="": fall back to SQLite instead of crashing.
        return v.strip() or DEFAULT_DATABASE_URL

    @property
    def is_prod(self) -> bool:
        return self.env.lower() == "prod"

    def check(self) -> None:
        """Refuse to start in production with an insecure configuration."""
        if not self.is_prod:
            return
        if not self.app_password:
            raise RuntimeError("APP_PASSWORD must be set in production")
        if self.secret_key == "dev-only-change-me" or len(self.secret_key) < 32:
            raise RuntimeError("SECRET_KEY must be set to a random string of 32+ characters in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()
