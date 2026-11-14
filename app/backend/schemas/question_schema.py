from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field, field_validator


class Question(BaseModel):
    question: str = Field(description="The quiz question")
    options: List[str] = Field(description="Exactly 4 answer options")
    correct_answer: int = Field(
        description="1-based index (1, 2, 3 or 4) of the correct option"
    )
    short_explanation: str = Field(
        description="Short explanation of why the answer is correct"
    )

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question must not be empty")
        return value

    @field_validator("options")
    @classmethod
    def exactly_four_options(cls, value: List[str]) -> List[str]:
        cleaned = [option.strip() for option in value]
        if len(cleaned) != 4:
            raise ValueError("Each question must have exactly 4 options")
        if any(not option for option in cleaned):
            raise ValueError("Options must not be empty")
        return cleaned

    @field_validator("correct_answer")
    @classmethod
    def correct_answer_in_range(cls, value: int) -> int:
        if value not in (1, 2, 3, 4):
            raise ValueError("correct_answer must be 1, 2, 3 or 4")
        return value

    @field_validator("short_explanation")
    @classmethod
    def explanation_not_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("short_explanation must not be empty")
        return value
