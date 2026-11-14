# AI Quiz Generator

A single-service **FastAPI + Jinja2 + htmx** quiz app. Generate a multiple-choice
quiz on any topic, answer it, get a deterministic score with AI-written feedback,
retake it, or print a blank paper version for students.

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
- **Printable paper quizzes**: a minimal black-and-white print view keeps the
  title, questions and inline A/B/C/D options, with no answers or results, so
  teachers can hand it out for students to solve on paper.
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

You need Docker Engine with the **Compose V2** plugin (`docker compose`, not the
legacy `docker-compose` command). Check it with:

```bash
docker compose version
```

Then from the repository root:

```bash
cd app
cp .env.example .env
# Edit .env and set GROQ_API_KEY
docker compose up --build -d
docker compose logs -f app
```

Open **http://localhost:8000** once the container is healthy.

Useful commands:

```bash
docker compose ps                 # container status and health
docker compose logs -f app        # follow application logs
docker compose down               # stop the app
docker compose down -v            # stop and delete the quiz database volume
```

The SQLite database lives in the `quiz-data` Docker volume, so quizzes and saved
results survive container restarts. Removing the volume with `-v` is destructive.

## Using the app

1. **Generate a quiz**: enter a topic, choose Easy / Medium / Hard and a question
   count, then submit. Generation can take up to about 30 seconds.
2. **Answer and score**: select one option for every question and click
   **Check Score**. The score is calculated from the stored answer key.
3. **Review feedback**: the results panel shows correct/incorrect counts,
   improvement tips and optional resource links.
4. **Retake**: click **Retake Quiz** to clear the saved evaluation and unlock the
   questions. Refreshing the page also shows the unsolved quiz.
5. **Share**: the quiz URL (`/quiz/<id>`) is stable and can be sent to someone
   else; saved results are included when they open it.
6. **Print for paper**: click **Print Quiz** on an unsolved or solved quiz. The
   print view always opens blank, with the title, name/date line, numbered
   questions and inline A/B/C/D options. Use the browser's print dialog or
   **Save as PDF**. Answers, explanations and results are never included.

## Local development

Requires Python 3.12+.

```bash
cd app/backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt

cp ../.env.example ../.env   # edit ../.env and set GROQ_API_KEY
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000**.

The local database defaults to `app/backend/data/quiz.db`. The app loads
`app/backend/.env` first and then `app/.env`, so either location works for local
configuration.

### Health checks

```bash
curl http://localhost:8000/health
# {"status":"ok"}

curl http://localhost:8000/health/ready
# {"status":"ready","quizzes":0}
```

## Configuration

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
| `RATE_LIMIT_ENABLED` | `true` | Enable per-IP request limiting |
| `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS` | `20` / `60` | Per-IP limits |
| `COOKIE_SECURE` | `false` | Set `true` when served over HTTPS |
| `ENVIRONMENT` / `LOG_LEVEL` | `development` / `INFO` | Runtime |

Docker Compose overrides `DATABASE_PATH` to `/app/data/quiz.db` and mounts the
`quiz-data` volume there.

## Routes

| Route | Method | Description |
| --- | --- | --- |
| `/` | GET | Dashboard (form + intro) |
| `/quiz/{quiz_id}` | GET | Shareable quiz page, including saved results |
| `/generate-quiz` | POST | Form endpoint; returns a quiz HTML fragment |
| `/quiz/{quiz_id}/evaluate` | POST | Form endpoint; returns solved quiz + results |
| `/quiz/{quiz_id}/retry` | POST | Clears the saved result and returns the quiz unsolved |
| `/quiz/{quiz_id}/print` | GET | Blank black-and-white paper quiz for printing |
| `/health` | GET | Liveness check |
| `/health/ready` | GET | Readiness check with quiz count |

Page routes (`/`, `/quiz/{quiz_id}` and `/quiz/{quiz_id}/print`) also accept
`HEAD`.

## Tests

```bash
cd app/backend
python -m pytest -q
```

The suite covers form validation, answer parsing, deterministic scoring, link
sanitisation, generation/evaluation routes, CSRF rejection, retakes, share and
print pages, and the health endpoints. LLM calls are stubbed, so tests run
offline.

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
│  ├─ templates/             # Jinja pages, partials and print layout
│  ├─ static/                # compiled CSS, print CSS/JS, htmx, app.js, logo
│  ├─ assets/input.css       # Tailwind source
│  ├─ tests/
│  └─ Dockerfile
├─ docker-compose.yml        # one service
└─ .env.example
```

## Production notes

- Set `ENVIRONMENT=production` and `COOKIE_SECURE=true` when serving over HTTPS.
- Terminate TLS at a reverse proxy and forward requests to the app on port 8000.
- The app is designed as a single service. SQLite uses a single-writer model and
  the rate limiter is in-process, so run one app process unless you add a shared
  database and external rate-limit store.
- Persist `/app/data` (or your configured `DATABASE_PATH`) across deployments.
- Point container health checks at `/health` and readiness checks at
  `/health/ready`.

## Troubleshooting

### `docker-compose` crashes with `KeyError: 'id'`

You are using legacy Compose V1 (for example `docker-compose 1.29.x`) with a
newer Docker Engine. Compose V1 is end-of-life and incompatible with the event
format used by recent engines. Install Compose V2 and use the space-separated
command:

```bash
sudo apt update
sudo apt install docker-compose-v2
docker compose up --build -d
```

The legacy package can then be removed with `sudo apt remove docker-compose`.

### `docker: unknown command: docker compose`

The Compose V2 plugin is not installed. Install Docker Desktop, or on
Ubuntu/Debian install the `docker-compose-v2` package shown above.

### Generation fails or takes too long

Check that `GROQ_API_KEY` is set in `app/.env`, then inspect the logs:

```bash
docker compose logs -f app
```

Without a valid key the UI and health checks still work, but generation and
evaluation cannot call the LLM.

### Port 8000 is already in use

Stop the process using the port, or map a different host port:

```bash
docker compose down
# or run with a different host port:
# change "8000:8000" to "8001:8000" in app/docker-compose.yml
```

## Rebuilding the CSS

The compiled stylesheet is committed, so Node is not needed to run the app. If
you change templates or Tailwind classes:

```bash
cd app/backend
npx --yes tailwindcss@3.4.19 -c tailwind.config.js -i assets/input.css -o static/css/app.css --minify
```

The print page has its own static stylesheet at
`app/backend/static/css/print.css`, so it does not depend on the Tailwind build.

## Security and robustness

- Server-side validation of topic, difficulty, question count and every answer.
- CSRF double-submit cookie protection on all form endpoints.
- Per-IP sliding-window rate limiting (single-process).
- Strict CSP and standard security headers; no third-party scripts.
- LLM output validated with Pydantic before it can reach the UI.
- Prompt-injection resistant prompts: user topics are delimited as data.
- Resource links restricted to `http(s)` and rendered with `noopener`.
- Structured logs with request IDs.
- The app has no user accounts; anyone with a quiz URL can view that quiz.

## License

MIT
