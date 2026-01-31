# Local Dev Mini Runbook

This is a quick, practical guide to start, stop, and restart the local stack.

## What runs locally
- Postgres (Docker)
- Redis (Docker)
- Django backend (local venv)
- Frontend (Next.js)
- Celery worker (optional)
- Celery beat (optional)

## One-time setup
- Install Python deps:
  - `cd backend`
  - `./venv/bin/python -m pip install -r requirements/development.txt`
- Create DB tables:
  - `./venv/bin/python manage.py migrate --run-syncdb`
- Create local superuser:
  - `./venv/bin/python manage.py createsuperuser`

## Start everything (recommended order)
1) Start Postgres + Redis:
   - `cd /Users/feihuyan/episteme`
   - `docker compose up -d db redis`
2) Start backend:
   - `cd backend`
   - `./venv/bin/python manage.py runserver`
3) Start frontend:
   - `cd frontend`
   - `npm run dev`
4) Optional: start Celery worker:
   - `cd backend`
   - `./venv/bin/celery -A tasks.celery worker --loglevel=info`
5) Optional: start Celery beat:
   - `cd backend`
   - `./venv/bin/celery -A tasks.celery beat --loglevel=info`

## Stop everything
- Stop backend/frontend/celery: Ctrl+C in each terminal.
- Stop Postgres/Redis:
  - `cd /Users/feihuyan/episteme`
  - `docker compose down`

## Restart guidance
### When you DO need to restart
- Backend code changes are picked up automatically by `runserver`, but restart if:
  - You changed `settings` or `.env`
  - You updated dependencies (pip install)
  - You added/changed environment variables
- Frontend auto-reloads, but restart if:
  - You changed `NEXT_PUBLIC_*` env vars
  - You updated dependencies (npm install)
- Celery MUST be restarted to pick up code changes or config changes.
- Redis/Postgres: restart if you changed docker config or volumes.

### When you DON'T need to restart
- Most backend Python code changes (views, serializers, models) are picked up by `runserver`.
- Most frontend UI changes hot-reload.

## Quick health checks
- Backend: `http://localhost:8000/api/` (should return JSON or 404, not 500)
- Frontend: `http://localhost:3000/`
- Postgres: `docker compose ps` should show `db` healthy
- Redis: `docker compose ps` should show `redis` healthy

## Common issues
- "connection to server at localhost:5432 failed"
  - Postgres is not running. Start with `docker compose up -d db`.
- "Authentication credentials were not provided"
  - Log in or use a valid JWT.
- "Celery tasks not running"
  - Start Redis and Celery worker.

