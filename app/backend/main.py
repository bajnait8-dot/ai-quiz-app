"""Single FastAPI application that serves both the HTML UI and the quiz logic."""

from __future__ import annotations

import html
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.config import BACKEND_DIR, settings
from core.logging_config import configure_logging
from core.security import apply_security_headers, csrf_token_for_request, set_csrf_cookie
from db import count_quizzes, init_db
from routers import pages, quiz
from templating import render_page

configure_logging()
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    if not settings.groq_api_key:
        logger.warning(
            "GROQ_API_KEY is not set; quiz generation will fail until it is configured"
        )
    logger.info(
        "ai-quiz-app starting env=%s model=%s db=%s",
        settings.environment,
        settings.llm_model,
        settings.database_path,
    )
    yield
    logger.info("ai-quiz-app stopping")


app = FastAPI(
    title="AI Quiz Generator",
    version="2.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.mount(
    "/static",
    StaticFiles(directory=str(BACKEND_DIR / "static")),
    name="static",
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    request.state.request_id = request_id

    token, created = csrf_token_for_request(request)
    request.state.csrf_token = token

    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "unhandled request error",
            extra={"request_id": request_id},
        )
        raise

    if created:
        set_csrf_cookie(response, token)

    apply_security_headers(response)
    response.headers["X-Request-ID"] = request_id

    if not request.url.path.startswith("/static"):
        duration_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "%s %s -> %s %.0fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={"request_id": request_id},
        )

    return response


@app.api_route("/health", methods=["GET", "HEAD"])
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.api_route("/health/ready", methods=["GET", "HEAD"])
async def ready() -> JSONResponse:
    return JSONResponse({"status": "ready", "quizzes": count_quizzes()})


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if request.headers.get("HX-Request") == "true":
        return HTMLResponse(html.escape(str(exc.detail)), status_code=exc.status_code)

    titles = {
        404: "Page not found",
        405: "Method not allowed",
    }
    return render_page(
        request,
        "error.html",
        status_code=exc.status_code,
        title=titles.get(exc.status_code, "Something went wrong"),
        message=str(exc.detail),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "unhandled application error",
        extra={"request_id": getattr(request.state, "request_id", "-")},
    )
    return render_page(
        request,
        "error.html",
        status_code=500,
        title="Something went wrong",
        message="The server hit an unexpected error. Please try again.",
    )


app.include_router(pages.router)
app.include_router(quiz.router)
