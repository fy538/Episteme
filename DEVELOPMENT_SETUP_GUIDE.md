# Development Setup Guide: Docker + Local Frontend

## Recommended Setup for Solo Development

**Backend + Services**: Docker (isolated, consistent)  
**Frontend**: Local (fast hot reload)

---

## Step 1: Stop Any Local Services

```bash
# Stop local Postgres if running
brew services stop postgresql@14  # or your version

# Kill any Django processes
pkill -f "manage.py runserver"
pkill -f "manage.py runasgi"

# Kill any Celery workers
pkill -f "celery"
```

---

## Step 2: Configure Environment

Create/update `.env` in project root:

```bash
# Copy example if not exists
cp .env.example .env

# Edit .env
nano .env  # or your editor
```

Ensure these settings for Docker:
```env
# Database (Docker service)
DATABASE_URL=postgresql://episteme:episteme@db:5432/episteme

# Redis & Celery (Docker services)
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Django
DEBUG=True
SECRET_KEY=your-secret-key-here-change-in-production
DJANGO_SETTINGS_MODULE=config.settings.development

# CORS (for local frontend)
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# AI Keys (your actual keys)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
GOOGLE_API_KEY=AIza...
DEEPSEEK_API_KEY=sk-...
GROQ_API_KEY=gsk-...

# Model Selection
AI_MODEL_REASONING=openai:gpt-4o-mini
AI_MODEL_FAST=openai:gpt-4o-mini
AI_MODEL_EXTRACTION=openai:gpt-4o-mini
```

---

## Step 3: Start Docker Services

```bash
# Build images (first time or after dependency changes)
docker-compose build

# Start all services
docker-compose up -d

# Check they're running
docker-compose ps

# Should see:
# - db (postgres)
# - redis
# - backend
# - celery
# - celery-beat
```

---

## Step 4: Run Migrations

```bash
# Run migrations in Docker backend
docker-compose exec backend python manage.py migrate

# Create superuser
docker-compose exec backend python manage.py createsuperuser
# Username: admin
# Email: admin@example.com
# Password: (your password)

# Load example skills (optional)
docker-compose exec backend python manage.py load_example_skills
```

---

## Step 5: Start Frontend Locally

```bash
cd frontend

# Install dependencies (first time)
npm install

# Start dev server
npm run dev

# Frontend will run on http://localhost:3000
```

---

## Step 6: Verify Everything Works

**Backend API**:
```bash
# Test backend is accessible
curl http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"your-password"}'

# Should return JWT tokens
```

**Database**:
```bash
# Connect to Postgres in Docker
docker-compose exec db psql -U episteme -d episteme

# Run a test query
SELECT COUNT(*) FROM auth_user;

# Exit
\q
```

**Frontend**:
- Open http://localhost:3000
- Should see login page
- Login with admin credentials

---

## Daily Development Workflow

### Starting Your Day

```bash
# Start Docker services (backend, db, redis, celery)
docker-compose up -d

# Check everything is running
docker-compose ps

# Start frontend (in separate terminal)
cd frontend && npm run dev
```

**Important**: Docker Compose **automatically starts the backend server**!  
You don't need to run `python manage.py runserver` or `runasgi` - it's already running.

### View Logs

```bash
# Backend logs (like watching terminal output)
docker-compose logs -f backend

# Celery logs
docker-compose logs -f celery

# All logs
docker-compose logs -f

# Frontend logs (in terminal where npm run dev is running)
```

### Making Code Changes

**Backend changes (NO REBUILD NEEDED!)**:
- Edit Python files in your IDE
- Volume mount syncs to Docker automatically
- Django auto-reloads (just like local dev)
- See changes at http://localhost:8000
- **No restart, no rebuild!**

**Frontend changes**:
- Edit React/TypeScript files
- Next.js hot reloads automatically
- See changes instantly at http://localhost:3000

**When You DO Need to Rebuild**:
```bash
# Only rebuild when you change:
# - requirements/*.txt (added/updated Python packages)
# - Dockerfile
# - System packages (apt-get)

docker-compose build backend
docker-compose up -d backend
```

**Migrations**:
```bash
# Generate migrations
docker-compose exec backend python manage.py makemigrations

# Apply migrations
docker-compose exec backend python manage.py migrate
```

### Running Django Commands

**Don't run**: `./venv/bin/python manage.py <command>`  
**Do run**: `docker-compose exec backend python manage.py <command>`

```bash
# Django shell
docker-compose exec backend python manage.py shell

# Create superuser
docker-compose exec backend python manage.py createsuperuser

# Run tests
docker-compose exec backend python manage.py test

# Any custom command
docker-compose exec backend python manage.py load_example_skills
```

### Stopping Services

```bash
# Stop but keep data
docker-compose down

# Stop and remove volumes (DELETES ALL DATA!)
docker-compose down -v

# Stop frontend
# Ctrl+C in terminal running npm
```

---

## Troubleshooting

### "Port already in use"

**Problem**: Local service using same port

**Solution**:
```bash
# Check what's on port 5432 (Postgres)
lsof -i :5432

# Kill it
kill -9 <PID>

# Or stop service
brew services stop postgresql
```

### "Database connection failed"

**Problem**: Database not ready yet

**Solution**:
```bash
# Wait a bit, then retry
sleep 5
docker-compose exec backend python manage.py migrate

# Or check db logs
docker-compose logs db
```

### "Module not found"

**Problem**: New Python package not installed in Docker

**Solution**:
```bash
# Rebuild backend
docker-compose build backend

# Restart
docker-compose up -d backend
```

### "Migration conflicts"

**Problem**: Migration order issues

**Solution**:
```bash
# Reset database (DELETES ALL DATA!)
docker-compose down -v
docker-compose up -d
sleep 10
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser
```

---

## Architecture

```
┌─────────────────────────────────────────┐
│  Your Local Machine                     │
├─────────────────────────────────────────┤
│                                         │
│  Frontend (Local)                       │
│  └─ npm run dev                         │
│     └─ http://localhost:3000            │
│        ↓ API calls                      │
│        ↓                                │
│  ┌─────────────────────────────────┐   │
│  │  Docker Containers              │   │
│  ├─────────────────────────────────┤   │
│  │                                 │   │
│  │  Backend (Django)               │   │
│  │  └─ http://localhost:8000       │   │
│  │     ↓                           │   │
│  │  Database (Postgres)            │   │
│  │  └─ port 5432                   │   │
│  │     ↓                           │   │
│  │  Redis                          │   │
│  │  └─ port 6379                   │   │
│  │     ↓                           │   │
│  │  Celery Worker                  │   │
│  │  Celery Beat (scheduler)        │   │
│  │                                 │   │
│  └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

---

## Benefits of This Setup

### For You (Solo Founder)
- ✅ **No port conflicts** - Everything isolated
- ✅ **Clean state** - `docker-compose down -v` resets everything
- ✅ **Fast frontend** - Local Next.js is faster than Docker
- ✅ **Production-like** - Same environment as deployment

### For Development
- ✅ **Hot reload** - Both backend and frontend auto-reload
- ✅ **Easy debugging** - Attach to backend logs
- ✅ **Migration safety** - Can reset DB anytime

### For Deployment
- ✅ **Same containers** - Dev = production
- ✅ **Easy deploy** - Already containerized
- ✅ **Portable** - Works on any machine

---

## Quick Commands Reference

```bash
# ═══════════════════════════════════════
# Starting Development
# ═══════════════════════════════════════

# Start Docker services
docker-compose up -d

# Start frontend (separate terminal)
cd frontend && npm run dev

# View backend logs (optional, separate terminal)
docker-compose logs -f backend


# ═══════════════════════════════════════
# Code Changes (NO REBUILD!)
# ═══════════════════════════════════════

# Edit Python files → Auto-reloads
# Edit React files → Hot reloads
# Just save and test!


# ═══════════════════════════════════════
# Django Commands
# ═══════════════════════════════════════

# Migrations
docker-compose exec backend python manage.py makemigrations
docker-compose exec backend python manage.py migrate

# Shell
docker-compose exec backend python manage.py shell

# Tests
docker-compose exec backend python manage.py test

# Custom commands
docker-compose exec backend python manage.py load_example_skills


# ═══════════════════════════════════════
# Database Access
# ═══════════════════════════════════════

# Connect to Postgres
docker-compose exec db psql -U episteme -d episteme

# Bash shell in backend
docker-compose exec backend bash


# ═══════════════════════════════════════
# Stopping
# ═══════════════════════════════════════

# Stop all (keeps data)
docker-compose down

# Stop and delete everything
docker-compose down -v


# ═══════════════════════════════════════
# Troubleshooting
# ═══════════════════════════════════════

# Reset database (fresh start)
docker-compose down -v
docker-compose up -d
sleep 10
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser

# Rebuild (only after dependency changes)
docker-compose build
docker-compose up -d

# Check what's running
docker-compose ps

# View logs
docker-compose logs -f backend  # Backend
docker-compose logs -f celery   # Celery  
docker-compose logs -f          # All
```

### Convenient Aliases (Optional)

Add to `~/.zshrc`:
```bash
alias dexec='docker-compose exec backend python manage.py'
alias dlogs='docker-compose logs -f backend'
alias dup='docker-compose up -d'
alias ddown='docker-compose down'

# Then use:
dexec migrate
dexec shell
dlogs
```

---

## Next Steps

1. **Stop local Postgres** (if running)
2. **Update .env** (use Docker service names)
3. **Build Docker** (`docker-compose build`)
4. **Start services** (`docker-compose up -d`)
5. **Run migrations** (`docker-compose exec backend python manage.py migrate`)
6. **Create superuser** (`docker-compose exec backend python manage.py createsuperuser`)
7. **Start frontend** (local: `cd frontend && npm run dev`)

You're ready! 🚀
