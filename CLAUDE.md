# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the API server (dev)
uvicorn app.main:app --reload

# Run via Docker (includes PostgreSQL)
docker-compose up

# Lint
ruff check app/
ruff format app/

# Run all tests
pytest

# Run a single test file
pytest tests/path/to/test_file.py

# Run a single test
pytest tests/path/to/test_file.py::test_function_name

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"
alembic downgrade -1
```

## Architecture

**Stack:** FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL (asyncpg) + Alembic + Pydantic v2

**Request flow:** `app/main.py` → middleware stack → `app/api/v1/router.py` → route handler → service → DB session → auto-commit on response

**Session commit pattern:** `get_db()` in `app/db/session.py` auto-commits after the request yields and auto-rolls back on exception. Services use `flush()` (not `commit()`) to make writes visible within the same transaction.

**Layered structure:**
- `app/api/v1/` — route handlers only: parse request, call service, build response schema
- `app/services/` — all business logic, DB queries, ownership checks
- `app/models/` — SQLAlchemy ORM models (one per file), all inherit `TimestampMixin` + `Base`
- `app/schemas/` — Pydantic request/response models; API uses camelCase, DB uses snake_case (mapping happens in service layer)
- `app/core/` — enums, exceptions, security utilities

**Auth:** `HTTPBearer` JWT. `get_current_user` dep validates token and returns `User`. `require_role(*roles)` wraps it for RBAC. Refresh tokens are managed by `app/services/token_service.py`.

**Middleware stack** (outer → inner): CORS → `CorrelationIdMiddleware` → `LoggingMiddleware` → `RateLimitMiddleware`. Exception handlers are registered separately via `register_exception_handlers`.

**Key relationships:**
- `User` → `Profile` (1:1) — employer company info lives on `Profile.company`, not on `Job`
- `User` → `Job` (1:many via `employer_id`)
- `User` → `Bookmark` → `Job` (many-to-many, unique constraint on user+job)
- `Job` → `Application` → `Interview` (linear pipeline)
- `Application` and `Interview` denormalize `job_title`, `company`, `applicant_name` for historical preservation

**`company` on jobs:** The `Job` model has no `company` column. All job-fetch queries (`get_by_id`, `list_jobs`, `get_recommended`) join `profiles` on `profiles.user_id = jobs.employer_id` and return `(Job, company_str)` tuples. Route handlers unpack these before building `JobResponse`.

**Application status state machine** (in `app/services/application_service.py`):
```
PENDING → SHORTLISTED | REJECTED
SHORTLISTED → INTERVIEW_SCHEDULED | REJECTED
INTERVIEW_SCHEDULED → HIRED | REJECTED
```

**Date fields:** `Job.posted_date`, `Job.application_deadline`, `Application.applied_date` are `Date` columns (not strings). Services set them with `date.today()`.

**Migrations:** Chain — `ae2ae4399a6d` (initial) → `1fa07e0b34e7` (profile fields) → `b7f3a1c92e45` (date columns) → `c1e2f3a4b5d6` (drop jobs.company).

**Config:** `app/config.py` uses `pydantic-settings` with `.env` file. Access via `get_settings()` (LRU-cached singleton).

**AI features:**
- `app/llm/client.py` — Gemini client singleton with tenacity retry logic. Falls back to a stub JSON response when `GEMINI_API_KEY` is unset.
- `app/agents/` — three agents: `InterviewAgent` (question generation + response evaluation, fully wired), `JobMatchAgent` (candidate-job fit scoring, wired), `ResumeAgent` (PDF/DOC parsing via Gemini vision, wired).
- `app/prompts/` — prompt builders for each agent (`interview_question.py`, `interview_evaluation.py`, `job_match.py`, `resume_parse.py`).
- `app/tasks/scoring.py` — background task for batch match scoring; currently a stub (does not call agents yet).

**Vector store:** ChromaDB HTTP client in `app/vectordb/`. Two collections: `jobs` and `resumes`, both using cosine similarity. Access via `get_jobs_collection()` / `get_resumes_collection()` — never construct `Collection` objects directly. In Docker: `CHROMA_HOST=chromadb, CHROMA_PORT=8000`; local dev defaults to `localhost:8001`.

**File uploads:** Cloudinary via `app/services/cloudinary_service.py`. Resume uploads (PDF/DOC/DOCX, max 10 MB) stored under `jobez/resumes/`. Configured lazily on first use via `CLOUDINARY_*` env vars.

**Logging:** `structlog` throughout. Configure with `configure_logging(debug=...)` in lifespan. All log calls use `structlog.get_logger()` — never use the stdlib `logging` directly.

**Relationships use `lazy="noload"`** — no relationships are auto-loaded. Explicit joins are required in service queries when related data is needed.
