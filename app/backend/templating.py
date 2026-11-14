"""Template rendering helpers shared by the HTML routes."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from core.config import BACKEND_DIR, settings

templates = Jinja2Templates(directory=str(BACKEND_DIR / "templates"))
templates.env.globals.update(
    quiz_min=settings.quiz_min_questions,
    quiz_max=settings.quiz_max_questions,
    topic_min=settings.topic_min_length,
    topic_max=settings.topic_max_length,
)


def _context(request: Request, context: dict[str, Any]) -> dict[str, Any]:
    context.setdefault("csrf_token", getattr(request.state, "csrf_token", ""))
    context.setdefault("request", request)
    return context


def render_page(
    request: Request,
    template_name: str,
    *,
    status_code: int = 200,
    **context: Any,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        template_name,
        _context(request, context),
        status_code=status_code,
    )


def render_partial(request: Request, template_name: str, **context: Any) -> str:
    template = templates.env.get_template(template_name)
    return template.render(**_context(request, context))
