from __future__ import annotations

import logging

from agent.state import State
from core.config import settings

logger = logging.getLogger(__name__)


def validate_quiz_node(state: State) -> dict:
    """Enforce structural and length guarantees before a quiz is stored."""

    quiz = state.get("quiz_json")
    expected_length = int(state.get("length") or settings.quiz_min_questions)

    if not quiz:
        return {"error": "We could not generate a quiz for that topic. Please try again."}

    questions = quiz.get("questions") or []

    if len(questions) < settings.quiz_min_questions:
        return {
            "quiz_json": quiz,
            "error": (
                "The quiz came back too short. Please try again with a slightly "
                "broader topic."
            ),
        }

    if len(questions) > expected_length:
        logger.warning(
            "trimming generated quiz from %s to %s questions",
            len(questions),
            expected_length,
        )
        questions = questions[:expected_length]

    if len(questions) < expected_length:
        return {
            "quiz_json": quiz,
            "error": (
                f"The quiz came back incomplete ({len(questions)} of {expected_length} "
                "questions). Please try again."
            ),
        }

    quiz["questions"] = questions
    quiz["length"] = len(questions)
    quiz["topic"] = state.get("topic") or quiz.get("topic")
    quiz["intensity"] = state.get("intensity") or quiz.get("intensity")

    # Normalise related topics: trim, drop blanks/duplicates, cap at three.
    related: list[str] = []
    for item in quiz.get("related_topics") or []:
        title = str(item).strip()
        if title and title.lower() not in {t.lower() for t in related}:
            related.append(title)
    quiz["related_topics"] = related[:3]

    return {"quiz_json": quiz, "error": None}
