from __future__ import annotations

from typing import Literal

from pydantic import Field

IntensityType = Literal["easy", "medium", "hard"]

IntensityValues: tuple[str, ...] = ("easy", "medium", "hard")

QuizLengthConstraints = Field(
    ge=5,
    le=15,
    description="Number of questions in the quiz should be between 5 and 15",
)

QuizTopicConstraints = Field(max_length=150, min_length=10)

QuizIntensityConstraints = Field(description="Intensity of quiz easy, medium or hard")

QuizIdConstraints = Field(description="Unique uuid4 id for quiz")

RelatedTopicsConstraints = Field(
    description=(
        "List of related topics for the quiz, relevant to the core quiz topic. "
        "Each topic must be a full descriptive phrase (not abbreviations), "
        "e.g. 'API Design Fundamentals' rather than 'API'."
    ),
    min_length=3,
    max_length=3,
)
