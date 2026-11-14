"""Application configuration.

All values are read from the environment (a local .env is loaded when present).
Importing this module never fails; missing API credentials are surfaced when a
generation is attempted so the health endpoint and UI stay usable.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BACKEND_DIR.parent

# backend/.env wins over app/.env, but both are honoured for local development.
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(APP_DIR / ".env")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


class Settings:
    """Immutable-ish settings object built once at import time."""

    def __init__(self) -> None:
        self.groq_api_key: str = os.getenv("GROQ_API_KEY", "").strip()
        self.llm_model: str = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
        self.llm_timeout: float = _env_float("LLM_TIMEOUT_SECONDS", 30.0)
        # Groq's client sleeps for the Retry-After header on 429s, which can make a
        # request hang for ~30s. Keep retries off; the generation service retries
        # once itself and evaluation falls back to local tips on any failure.
        self.llm_max_retries: int = _env_int("LLM_MAX_RETRIES", 0)

        self.topic_min_length: int = _env_int("TOPIC_MIN_LENGTH", 10)
        self.topic_max_length: int = _env_int("TOPIC_MAX_LENGTH", 150)
        self.quiz_min_questions: int = _env_int("QUIZ_MIN_QUESTIONS", 5)
        self.quiz_max_questions: int = _env_int("QUIZ_MAX_QUESTIONS", 15)

        self.database_path: str = os.getenv(
            "DATABASE_PATH", str(BACKEND_DIR / "data" / "quiz.db")
        )

        self.rate_limit_enabled: bool = _env_bool("RATE_LIMIT_ENABLED", True)
        self.rate_limit_requests: int = _env_int("RATE_LIMIT_REQUESTS", 20)
        self.rate_limit_window_seconds: int = _env_int("RATE_LIMIT_WINDOW_SECONDS", 60)

        self.cookie_secure: bool = _env_bool("COOKIE_SECURE", False)
        self.environment: str = os.getenv("ENVIRONMENT", "development")
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()

        self.quiz_generation_attempts: int = _env_int("QUIZ_GENERATION_ATTEMPTS", 2)

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}


settings = Settings()
