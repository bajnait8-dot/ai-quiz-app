from __future__ import annotations

import html
import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from core.security import csrf_is_valid, client_ip, rate_limiter
from db import delete_evaluation, get_evaluation, get_quiz, save_evaluation
from services.evaluation import build_evaluation
from services.generation import GenerationError, generate_quiz
from services.validation import ValidationError, parse_answers, validate_generate_form
from templating import render_partial

logger = logging.getLogger(__name__)

router = APIRouter()


def _error_response(message: str, target: str) -> HTMLResponse:
    """Ask htmx to place a validation message in an existing slot."""

    response = HTMLResponse(html.escape(message))
    response.headers["HX-Retarget"] = target
    response.headers["HX-Reswap"] = "innerHTML"
    return response


def _stage_error(
    request: Request, message: str, current_quiz_id: str | None = None
) -> HTMLResponse:
    """Keep the stage usable after a failed generate request.

    If the user already had a quiz open, restore it; otherwise show the intro.
    The error itself is delivered out-of-band to the form's error slot.
    """

    quiz = get_quiz(current_quiz_id) if current_quiz_id else None
    evaluation = get_evaluation(quiz["quiz_id"]) if quiz else None

    if quiz:
        body = render_partial(
            request,
            "partials/quiz.html",
            quiz=quiz,
            evaluation=evaluation,
            selected_options=(evaluation or {}).get("selected_options"),
        )
    else:
        body = render_partial(request, "partials/intro.html")

    body += render_partial(
        request,
        "partials/generate_oob.html",
        error=message,
        initial_quiz=quiz,
        related_topics=(quiz.get("related_topics") or []) if quiz else [],
    )
    return HTMLResponse(body)


@router.post("/generate-quiz", response_class=HTMLResponse)
async def generate(request: Request) -> HTMLResponse:
    form = await request.form()
    current_quiz_id = str(form.get("current_quiz_id") or "").strip() or None

    if not csrf_is_valid(request, form.get("csrf_token")):
        return _stage_error(
            request,
            "Your session expired. Please refresh the page and try again.",
            current_quiz_id,
        )

    allowed, retry_after = rate_limiter.check(f"{client_ip(request)}:generate")
    if not allowed:
        return _stage_error(
            request,
            f"Too many quiz requests. Please wait {retry_after} seconds and try again.",
            current_quiz_id,
        )

    try:
        topic, intensity, length = validate_generate_form(
            form.get("topic"), form.get("intensity"), form.get("length")
        )
        quiz = await generate_quiz(topic, intensity, length)
    except ValidationError as exc:
        return _stage_error(request, str(exc), current_quiz_id)
    except GenerationError as exc:
        logger.warning("generation rejected: %s", exc)
        return _stage_error(request, str(exc), current_quiz_id)
    except Exception:
        logger.exception("unhandled error while generating quiz")
        return _stage_error(
            request,
            "Something went wrong while generating your quiz. Please try again.",
            current_quiz_id,
        )

    body = render_partial(
        request,
        "partials/quiz.html",
        quiz=quiz,
        evaluation=None,
        selected_options=None,
    )
    body += render_partial(
        request,
        "partials/generate_oob.html",
        error="",
        initial_quiz=quiz,
        related_topics=quiz.get("related_topics") or [],
    )

    response = HTMLResponse(body)
    response.headers["HX-Push-Url"] = f"/quiz/{quiz['quiz_id']}"
    return response


@router.post("/quiz/{quiz_id}/evaluate", response_class=HTMLResponse)
async def evaluate(request: Request, quiz_id: str) -> HTMLResponse:
    quiz = get_quiz(quiz_id)
    if not quiz:
        return _stage_error(
            request,
            "This quiz link is invalid. Generate a new quiz to get started.",
        )

    # Re-submitting an evaluated quiz is a safe no-op.
    existing = get_evaluation(quiz_id)
    if existing:
        body = render_partial(
            request,
            "partials/quiz.html",
            quiz=quiz,
            evaluation=existing,
            selected_options=existing.get("selected_options"),
        )
        return HTMLResponse(body)

    form = await request.form()

    if not csrf_is_valid(request, form.get("csrf_token")):
        return _error_response(
            "Your session expired. Please refresh the page and try again.",
            "#quiz-error",
        )

    allowed, retry_after = rate_limiter.check(f"{client_ip(request)}:evaluate")
    if not allowed:
        return _error_response(
            f"Too many submissions. Please wait {retry_after} seconds and try again.",
            "#quiz-error",
        )

    try:
        answers = parse_answers(form, len(quiz["questions"]))
    except ValidationError as exc:
        return _error_response(str(exc), "#quiz-error")

    try:
        evaluation = await build_evaluation(quiz, answers)
        save_evaluation(quiz_id, evaluation)
    except Exception:
        logger.exception("unhandled error while evaluating quiz quiz_id=%s", quiz_id)
        return _error_response(
            "Something went wrong while checking your score. Please try again.",
            "#quiz-error",
        )

    body = render_partial(
        request,
        "partials/quiz.html",
        quiz=quiz,
        evaluation=evaluation,
        selected_options=answers,
    )
    return HTMLResponse(body)


@router.post("/quiz/{quiz_id}/retry", response_class=HTMLResponse)
async def retry(request: Request, quiz_id: str) -> HTMLResponse:
    """Clear a saved evaluation and render the quiz ready to be solved again."""

    quiz = get_quiz(quiz_id)
    if not quiz:
        return _stage_error(
            request,
            "This quiz link is invalid. Generate a new quiz to get started.",
        )

    form = await request.form()
    if not csrf_is_valid(request, form.get("csrf_token")):
        return _error_response(
            "Your session expired. Please refresh the page and try again.",
            "#quiz-error",
        )

    delete_evaluation(quiz_id)
    logger.info("reset quiz for retake quiz_id=%s", quiz_id)

    body = render_partial(
        request,
        "partials/quiz.html",
        quiz=quiz,
        evaluation=None,
        selected_options=None,
    )
    response = HTMLResponse(body)
    response.headers["HX-Push-Url"] = f"/quiz/{quiz_id}"
    return response
