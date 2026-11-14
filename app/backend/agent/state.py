from __future__ import annotations

from typing import TypedDict


class State(TypedDict, total=False):
    topic: str
    intensity: str
    length: int
    quiz_json: dict | None
    error: str | None
    retry_feedback: str | None
