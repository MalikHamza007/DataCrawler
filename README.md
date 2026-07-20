# Backend Setup

Milestone 3 provides the FastAPI, SQLAlchemy 2, Alembic, SQLite, Lahore map dashboard, and Google Places discovery foundation.

## Setup

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Set the optional browser map key in `.env`:

```bash
GOOGLE_MAPS_BROWSER_API_KEY=your_browser_key
```

Restrict the browser key to:

```text
http://localhost/*
http://127.0.0.1/*
```

The key is used only for the Google Maps JavaScript API.

For Google Places discovery, use a separate server-side key:

```bash
GOOGLE_PLACES_ENABLED=true
GOOGLE_PLACES_SERVER_API_KEY=your_server_key
GOOGLE_PLACES_DRY_RUN=false
```

Keep this key restricted to Places API on the server side. It is never rendered into HTML, JavaScript, `/api/map-config`, or `/api/places/status`.

## Database Migration

```bash
python -m alembic upgrade head
```

## Run Server

```bash
python -m uvicorn app.main:app --reload
```

## Run Local Worker

Start the FastAPI server and worker in separate terminals:

```bash
python -m app.workers.runner
```

Useful local options:

```bash
python -m app.workers.runner --once
python -m app.workers.runner --job-id 12
python -m app.workers.runner --poll-interval 2
python -m app.workers.runner --log-level INFO
```

The worker uses a SQLite-backed singleton lease, claims queued `places_discovery` jobs, updates progress, supports cancellation, and recovers stale running jobs after interrupted execution. FastAPI does not use `BackgroundTasks` or in-process threads for collection.

Health check:

```bash
curl http://127.0.0.1:8000/health
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

Dashboard:

```text
http://127.0.0.1:8000/
```

## Test

```bash
python -m pytest
```

Tests use temporary SQLite databases and do not use `alduor.db`.

## Current Scope

Implemented:

- FastAPI app
- `/health`
- SQLAlchemy 2 models
- Alembic initial migration
- SQLite foreign-key enforcement
- Pydantic 2 schemas
- Repository and service layers
- CRUD APIs for Milestone 1 entities
- Automated tests
- One-page Lahore map dashboard
- Validated search configuration for queued `places_discovery` jobs
- Google Places API New Text Search client
- Search-plan preview for `places_discovery` jobs
- Explicit development-only discovery execution endpoint
- Project candidate persistence from mocked/live Places responses
- Google Places source evidence and discovery provenance
- Separate local worker process for queued Google Places discovery
- Worker lease, job heartbeat, cancellation, retry, stale recovery, and job logs

Not implemented in this milestone:

- Website crawling
- Social-media capture
- Classification or duplicate detection
- Exports
- Authentication

Milestone 3 can call Google Places only through explicit discovery execution. Creating a collection job and previewing a search plan do not make Google API requests. Automated tests use mocked HTTP responses only.
