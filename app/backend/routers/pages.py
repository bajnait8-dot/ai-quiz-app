from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from core.config import settings
from db import get_evaluation, get_quiz
from templating import render_page

router = APIRouter()


def _page_context(quiz: dict | None = None, evaluation: dict | None = None) -> dict:
    return {
        "initial_quiz": quiz,
        "initial_evaluation": evaluation,
        "form": {
            "topic": quiz["topic"] if quiz else "",
            "intensity": quiz["intensity"] if quiz else "easy",
            "length": quiz["length"] if quiz else settings.quiz_min_questions,
        },
        "related_topics": (quiz.get("related_topics") or []) if quiz else [],
        "error": "",
    }


@router.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    return render_page(request, "dashboard.html", **_page_context())


@router.api_route("/quiz/{quiz_id}", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def quiz_page(request: Request, quiz_id: str) -> HTMLResponse:
    quiz = get_quiz(quiz_id)
    if not quiz:
        return render_page(
            request,
            "error.html",
            status_code=404,
            title="Quiz not found",
            message="This quiz link is invalid. Generate a new quiz to get started.",
        )

    evaluation = get_evaluation(quiz_id)
    return render_page(
        request, "dashboard.html", **_page_context(quiz=quiz, evaluation=evaluation)
    )
