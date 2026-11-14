from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from schemas.constants import IntensityType, RelatedTopicsConstraints
from schemas.question_schema import Question


class GeneratedQuiz(BaseModel):
    """Shape the LLM must return. Server-owned fields are added afterwards."""

    topic: str = Field(description="Topic of the quiz")
    intensity: IntensityType = Field(description="easy, medium or hard")
    length: int = Field(description="Number of questions in the quiz")
    questions: List[Question] = Field(description="The quiz questions")
    related_topics: List[str] = RelatedTopicsConstraints


class Quiz(GeneratedQuiz):
    """A generated quiz with its server-assigned identifier."""

    quiz_id: str


class QuizAnswers(BaseModel):
    question_index: int
    selected_option: int
