from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class EvaluationFeedback(BaseModel):
    """The only part of an evaluation written by the LLM."""

    improvement_tips: str = Field(
        description=(
            "Brief, specific feedback for the learner: what they got wrong and "
            "how to improve. Around 400-500 characters. No links."
        )
    )
    links: List[str] = Field(
        description="1 to 5 http(s) resource links relevant to the topic",
        min_length=1,
        max_length=5,
    )


class quiz_evaluation(BaseModel):
    """Full evaluation returned to the UI (score is computed deterministically)."""

    topic: str
    score: float
    incorrect_answers_index: List[int]
    correct_answers_index: List[int]
    improvement_tips: str
    links: List[str] = Field(default_factory=list)
