from __future__ import annotations

from starlette.datastructures import FormData

from core.config import settings
from schemas.constants import IntensityValues


class ValidationError(Exception):
    """A user-presentable form validation failure."""


def validate_generate_form(
    topic: str | None, intensity: str | None, length: str | None
) -> tuple[str, str, int]:
    topic = (topic or "").strip()
    if len(topic) < settings.topic_min_length:
        raise ValidationError(
            f"Please enter a topic of at least {settings.topic_min_length} characters."
        )
    if len(topic) > settings.topic_max_length:
        raise ValidationError(
            f"Please keep the topic under {settings.topic_max_length} characters."
        )

    intensity = (intensity or "easy").strip().lower()
    if intensity not in IntensityValues:
        raise ValidationError("Choose a difficulty: easy, medium or hard.")

    try:
        question_count = int(str(length))
    except (TypeError, ValueError):
        raise ValidationError("Choose a valid number of questions.")

    if not settings.quiz_min_questions <= question_count <= settings.quiz_max_questions:
        raise ValidationError(
            f"Choose between {settings.quiz_min_questions} and "
            f"{settings.quiz_max_questions} questions."
        )

    return topic, intensity, question_count


def parse_answers(form: FormData, question_count: int) -> list[int]:
    """Read and validate the 1-based selected option for each question."""

    answers: list[int] = []
    missing: list[int] = []

    for index in range(1, question_count + 1):
        raw = form.get(f"question-{index}")
        if raw is None or str(raw).strip() == "":
            missing.append(index)
            answers.append(0)
            continue

        try:
            value = int(str(raw))
        except (TypeError, ValueError):
            raise ValidationError("One of your answers was invalid. Please try again.")

        if value not in (1, 2, 3, 4):
            raise ValidationError("One of your answers was invalid. Please try again.")

        answers.append(value)

    if missing:
        labels = ", ".join(str(index) for index in missing)
        raise ValidationError(
            f"Please answer every question before checking your score "
            f"(missing: {labels})."
        )

    return answers
