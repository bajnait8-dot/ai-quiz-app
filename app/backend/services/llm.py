"""Shared LLM client configuration."""

from __future__ import annotations

from functools import lru_cache
from typing import Type

from langchain_core.language_models import BaseChatModel
from langchain_groq import ChatGroq
from pydantic import BaseModel

from core.config import settings


class LLMNotConfiguredError(RuntimeError):
    """Raised when the Groq API key is missing."""


@lru_cache(maxsize=1)
def get_llm() -> ChatGroq:
    if not settings.groq_api_key:
        raise LLMNotConfiguredError(
            "GROQ_API_KEY is not set. Add it to your environment or .env file."
        )
    return ChatGroq(
        model=settings.llm_model,
        api_key=settings.groq_api_key,
        temperature=0.4,
        max_retries=settings.llm_max_retries,
        request_timeout=settings.llm_timeout,
    )


@lru_cache(maxsize=None)
def get_structured_llm(schema: Type[BaseModel]) -> BaseChatModel:
    return get_llm().with_structured_output(schema)
