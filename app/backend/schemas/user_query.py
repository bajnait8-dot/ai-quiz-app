from __future__ import annotations

from pydantic import BaseModel


class input_validation_response(BaseModel):
    is_valid: bool
    error: str | None = None
