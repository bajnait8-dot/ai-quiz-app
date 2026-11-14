# AI Quiz Generator

A single-service **FastAPI + htmx** quiz app. Generate a multiple-choice quiz on any
topic, answer it, and get a deterministic score with AI-written feedback and
resource links.

The backend renders the UI with Jinja templates and swaps HTML fragments with
htmx, so there is no separate frontend to deploy, no client-side data fetching,
and no JavaScript build step at runtime.

## Features

- **Dynamic quiz generation** on any topic with easy / medium / hard difficulty.
- **5–15 questions** per quiz, with structure enforced server-side.
- **Deterministic scoring**: the score is calculated in Python from the stored
  answer key, never by the LLM.
- **AI feedback**: personalised improvement tips and resource links, with a
  local fallback if the LLM is unavailable.
- **Shareable quizzes**: every quiz lives at `/quiz/<id>` and survives restarts.
- **Refresh-safe results**: submitted answers and evaluations are persisted in
  SQLite, so reloading a results page keeps the score.
- **Retake any quiz**: a server-backed reset clears the saved result and unlocks
  the questions so you can solve them again.
- **Related topics** that fill the topic form in one click.
- **Accessible, responsive UI** with server-rendered error and loading states.

## How it works

```
Browser ──POST /generate-quiz──▶ FastAPI ──▶ LangGraph ──▶ Groq LLM
   ▲                                  │
   └──── HTML fragment (htmx swap) ◀──┴──▶ SQLite (quizzes, evaluations)

Browser ──POST /quiz/{id}/evaluate──▶ FastAPI ──▶ Python scoring
   ▲                                        │
   └──── solved quiz + results (htmx) ◀─────┴──▶ LLM tips (optional)
```

- **Generation graph** (`agent/graph.py`): `validate topic → generate → validate
  structure and length`. A failed generation is retried once, then surfaced as a
  friendly message.
- **Evaluation** (`services/evaluation.py`): score and correct/incorrect indexes
  are computed locally; the LLM only writes the tips and links. Links are
  sanitised to `http(s)` before rendering.
- **Persistence** (`db.py`): SQLite via the standard library. No external
  database or in-memory LangGraph checkpointer is required.

## Tech stack

| Layer | Choice |
| --- | --- |
| Web framework | FastAPI |
| Templates | Jinja2 |
| Interactivity | htmx 2 (vendored locally) |
| Styling | Tailwind CSS (compiled to one static file) |
| AI orchestration | LangGraph + LangChain |
| LLM provider | Groq |
| Storage | SQLite (WAL mode) |
| Tests | pytest + FastAPI TestClient |

## Quick start with Docker

```bash
cd app
cp .env.example .env      # then add your GROQ_API_KEY
docker compose up --build
```

Open **http://localhost:8000**. The SQLite database lives in the `quiz-data`
volume, so quizzes survive container restarts.

## Local development

Requires Python 3.12+.

```bash
cd app/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt

cp ../.env.example ../.env   # add GROQ_API_KEY
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000**.

### Configuration

All settings are environment variables (see `app/.env.example`):

| Variable | Default | Purpose |
| --- | --- | --- |
| `GROQ_API_KEY` | — | Required for quiz generation |
| `GROQ_MODEL` | `qwen/qwen3.8-27b` | Model used for all LLM calls |
| `LLM_TIMEOUT_SECONDS` | `30` | Per-request LLM timeout |
| `LLM_MAX_RETRIES` | `0` | Groq client retries (kept low to avoid long 429 sleeps) |
| `DATABASE_PATH` | `./data/quiz.db` | SQLite file |
| `TOPIC_MIN_LENGTH` / `TOPIC_MAX_LENGTH` | `10` / `150` | Topic validation |
| `QUIZ_MIN_QUESTIONS` / `QUIZ_MAX_QUESTIONS` | `5` / `15` | Quiz length |
| `QUIZ_GENERATION_ATTEMPTS` | `2` | Regeneration attempts |
| `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS` | `20` / `60` | Per-IP limits |
| `COOKIE_SECURE` | `false` | Set `true` when served over HTTPS |
| `ENVIRONMENT` / `LOG_LEVEL` | `development` / `INFO` | Runtime |

## Routes

| Route | Method | Description |
| --- | --- | --- |
| `/` | GET | Dashboard (form + intro) |
| `/quiz/{quiz_id}` | GET | Shareable quiz page, including saved results |
| `/generate-quiz` | POST | Form endpoint; returns a quiz HTML fragment |
| `/quiz/{quiz_id}/evaluate` | POST | Form endpoint; returns solved quiz + results |
| `/quiz/{quiz_id}/retry` | POST | Clears the saved result and returns the quiz unsolved |
| `/health` | GET | Liveness check |
| `/health/ready` | GET | Readiness check with quiz count |

## Tests

```bash
cd app/backend
python -m pytest -q
```

The suite covers form validation, answer parsing, deterministic scoring, link
sanitisation, generation/evaluation routes, CSRF rejection, share pages and the
health endpoints. LLM calls are stubbed, so tests run offline.

## Project structure

```
app/
├─ backend/
│  ├─ main.py                # app, middleware, error pages, health
│  ├─ db.py                  # SQLite persistence
│  ├─ templating.py          # Jinja helpers
│  ├─ agent/                 # LangGraph generation pipeline
│  ├─ services/              # generation, evaluation, validation, LLM config
│  ├─ routers/               # pages + htmx form endpoints
│  ├─ templates/             # Jinja pages and partials
│  ├─ static/                # compiled CSS, htmx, app.js, logo
│  ├─ assets/input.css       # Tailwind source
│  ├─ tests/
│  └─ Dockerfile
├─ docker-compose.yml        # one service
└─ .env.example
```

## Security and robustness notes

- Server-side validation of topic, difficulty, question count and every answer.
- CSRF double-submit cookie protection on both form endpoints.
- Per-IP sliding-window rate limiting (single-process).
- Strict CSP and standard security headers; no third-party scripts.
- LLM output validated with Pydantic before it can reach the UI.
- Prompt-injection resistant prompts: user topics are delimited as data.
- Resource links restricted to `http(s)` and rendered with `noopener`.
- Structured logs with request IDs.

## Rebuilding the CSS

The compiled stylesheet is committed, so Node is not needed to run the app. If
you change templates or Tailwind classes:

```bash
cd app/backend
npx --yes tailwindcss@3.4.19 -c tailwind.config.js -i assets/input.css -o static/css/app.css --minify
```

## License

MIT
