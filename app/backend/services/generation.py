from __future__ import annotations

import logging
import uuid

from agent.graph import quiz_agent
from core.config import settings
from db import save_quiz
from services.llm import LLMNotConfiguredError

logger = logging.getLogger(__name__)


class GenerationError(Exception):
    """A user-presentable generation failure."""


async def generate_quiz(topic: str, intensity: str, length: int) -> dict:
    """Run the generation graph, retrying once when the model misbehaves."""

    quiz_id = str(uuid.uuid4())
    retry_feedback: str | None = None
    last_error: str | None = None

    for attempt in range(1, max(1, settings.quiz_generation_attempts) + 1):
        initial_state = {
            "topic": topic,
            "intensity": intensity,
            "length": length,
            "quiz_json": None,
            "error": None,
            "retry_feedback": retry_feedback,
        }

        try:
            result = await quiz_agent.ainvoke(initial_state)
        except LLMNotConfiguredError:
            raise GenerationError(
                "Quiz generation is not configured yet. Add a GROQ_API_KEY and try again."
            )
        except Exception:
            logger.exception("generation graph failed (attempt %s)", attempt)
            last_error = "The quiz service is busy right now. Please try again."
            continue

        quiz = result.get("quiz_json")
        error = result.get("error")

        if quiz and not error:
            questions = quiz.get("questions") or []
            if len(questions) != length:
                last_error = (
                    "The quiz came back with the wrong number of questions. "
                    "Please try again."
                )
            else:
                quiz["quiz_id"] = quiz_id
                quiz["length"] = len(questions)
                save_quiz(quiz)
                logger.info(
                    "generated quiz quiz_id=%s questions=%s attempt=%s",
                    quiz_id,
                    len(questions),
                    attempt,
                )
                return quiz

        last_error = error or last_error or "Unable to generate quiz."
        produced = len((quiz or {}).get("questions") or [])
        retry_feedback = (
            f"The previous attempt produced {produced} questions but exactly "
            f"{length} are required. Return exactly {length} questions, each with "
            "four options and a 1-based correct_answer."
        )
        logger.warning(
            "generation attempt %s rejected: %s (questions=%s)",
            attempt,
            error,
            produced,
        )

    raise GenerationError(last_error or "Unable to generate quiz. Please try again.")
