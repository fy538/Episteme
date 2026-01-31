# Deploying Episteme to Fly.io

Complete guide for deploying your Django + Postgres + Redis + Celery stack to Fly.io.

---

## Prerequisites

- [x] Fly.io account registered
- [x] flyctl installed and logged in
- [ ] GitHub repo with your code

---

## Understanding Docker vs Fly.io

**Docker (Local Development):**
- Your `docker-compose.yml` runs on your laptop
- Easy development with hot-reload
- All services on one machine
- **Keep using this for development!**

**Fly.io (Production):**
- Uses your `Dockerfile` to build the app
- Runs on Fly.io's servers (globally distributed VMs)
- Manages Postgres, Redis separately
- **Replace AWS/GCP for production**

**Bottom line:** You still maintain Dockerfile. Fly.io just runs it for you.

---

## Step-by-Step Deployment

### Step 1: Reload Terminal (flyctl in PATH)

```bash
source ~/.zshrc
flyctl version  # Should work now
```

### Step 2: Create Fly.io App

The app 'episteme' already exists (you created it). Let's configure it:

```bash
# Deploy the main Django app
flyctl apps create episteme --org personal
# (if already exists, skip this)
```

### Step 3: Create PostgreSQL Database

```bash
# Create managed Postgres (free dev tier)
flyctl postgres create --name episteme-db --region sjc

# Attach to your app
flyctl postgres attach episteme-db --app episteme

# This sets DATABASE_URL automatically
```

Fly.io will automatically inject `DATABASE_URL` into your app.

### Step 4: Create Redis

```bash
# Create Upstash Redis (free tier)
flyctl redis create --name episteme-redis --region sjc

# Attach to your app  
flyctl redis attach episteme-redis --app episteme

# This sets REDIS_URL automatically
```

### Step 5: Set Environment Secrets

```bash
# Django secret key
flyctl secrets set SECRET_KEY=$(openssl rand -base64 32) --app episteme

# API keys
flyctl secrets set OPENAI_API_KEY=sk-your-key --app episteme
flyctl secrets set GOOGLE_API_KEY=your-gemini-key --app episteme

# Django settings
flyctl secrets set DJANGO_SETTINGS_MODULE=config.settings.production --app episteme
flyctl secrets set ALLOWED_HOSTS=episteme.fly.dev --app episteme
```

### Step 6: Deploy Django App

```bash
# Deploy (uses fly.toml config)
flyctl deploy --app episteme

# Watch logs
flyctl logs --app episteme
```

### Step 7: Run Migrations

```bash
# SSH into the app
flyctl ssh console --app episteme

# Inside the VM:
python manage.py migrate
python manage.py createsuperuser
exit
```

### Step 8: Deploy Celery Worker (Optional)

```bash
# Create separate app for Celery
flyctl apps create episteme-celery --org personal

# Attach same database and Redis
flyctl postgres attach episteme-db --app episteme-celery
flyctl redis attach episteme-redis --app episteme-celery

# Copy secrets
flyctl secrets set SECRET_KEY=$(openssl rand -base64 32) --app episteme-celery
flyctl secrets set OPENAI_API_KEY=sk-your-key --app episteme-celery
flyctl secrets set GOOGLE_API_KEY=your-gemini-key --app episteme-celery

# Deploy worker
flyctl deploy --app episteme-celery --config fly-celery.toml
```

### Step 9: Deploy Frontend to Vercel (FREE)

```bash
cd frontend

# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Set environment variable:
# NEXT_PUBLIC_API_URL=https://episteme.fly.dev/api

# Deploy to production
vercel --prod
```

---

## Cost Breakdown

### Fly.io Costs

**Free Tier Allowance:**
- $5/month free credit
- 3 shared-cpu VMs (256MB)
- 3GB Postgres storage
- Often enough for side projects!

**If You Exceed Free Tier:**
- Django app (512MB): ~$3-5/month
- Postgres dev: ~$3/month
- Redis (Upstash free): $0
- Celery worker: ~$2/month
- **Total: ~$8-10/month**

**Likely Cost for Episteme:**
- **$0-5/month** during dogfooding (low traffic)
- **$8-15/month** with regular use
- **Far cheaper than AWS/GCP ($50-200/month)**

### Vercel (Frontend)

- **Free** for personal projects
- Auto-deploy from GitHub
- Global CDN included

---

## Production Settings

Update [`backend/config/settings/production.py`](../backend/config/settings/production.py):

```python
# Already mostly configured, just verify:

# Database comes from Fly.io (DATABASE_URL env var)
DATABASES = {
    'default': env.db('DATABASE_URL')
}

# Redis comes from Fly.io (REDIS_URL env var)
CELERY_BROKER_URL = env('REDIS_URL')

# CORS for Vercel frontend
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    'https://your-app.vercel.app',
])

# Static files (add WhiteNoise)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add this
    # ... rest
]
```

Add to `requirements/production.txt`:
```txt
whitenoise==6.6.0  # Serve static files
gunicorn==21.2.0   # Production server
```

---

## Deployment Commands Reference

```bash
# Deploy backend
flyctl deploy --app episteme

# View logs
flyctl logs --app episteme

# SSH into app
flyctl ssh console --app episteme

# Run Django command
flyctl ssh console --app episteme -C "python manage.py migrate"

# Scale resources (if needed)
flyctl scale vm shared-cpu-1x --app episteme  # 1 CPU, 2GB RAM (+$10/month)

# Check status
flyctl status --app episteme

# Check costs
flyctl dashboard billing
```

---

## Troubleshooting

### "Could not find Dockerfile"

Fly.io is looking in root. You have it in `docker/backend.Dockerfile`.

**Solution:** The `fly.toml` already specifies `dockerfile = "docker/backend.Dockerfile"`

### "Database connection failed"

```bash
# Check DATABASE_URL is set
flyctl ssh console --app episteme -C "env | grep DATABASE"

# Should show: DATABASE_URL=postgres://...
```

### "Redis connection failed"

```bash
# Check REDIS_URL
flyctl ssh console --app episteme -C "env | grep REDIS"
```

### Static files not loading

Add WhiteNoise (see Production Settings above).

---

## GitHub Integration (Auto-Deploy)

```bash
# Set up GitHub Actions for auto-deploy

# Create .github/workflows/deploy.yml:
name: Deploy to Fly.io

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: superfly/flyctl-actions/setup-flyctl@master
      - run: flyctl deploy --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}

# Get token:
flyctl tokens create deploy

# Add to GitHub secrets as FLY_API_TOKEN
```

---

## Docker: What to Keep vs Remove

### KEEP (Local Development)

✅ `docker-compose.yml` - For local development  
✅ `docker/backend.Dockerfile` - Fly.io uses this  
✅ `.env.example` - Template for local setup  

**Use for:** Daily development on your laptop

### REMOVE/IGNORE

❌ Don't deploy docker-compose.yml to Fly.io  
❌ Don't need docker-compose in production  

**Fly.io handles:** Postgres, Redis, networking, scaling

---

## Summary

**Your workflow:**

**Development (Laptop):**
```bash
docker-compose up -d  # Local Postgres + Redis + Django
npm run dev           # Local frontend
```

**Production (Fly.io):**
```bash
flyctl deploy         # Builds Dockerfile, runs on Fly.io's VMs
                      # Fly.io manages Postgres, Redis
```

**You maintain:**
- Dockerfile (how to build your app)
- fly.toml (Fly.io config)
- Django code

**You don't maintain:**
- Servers (Fly.io manages)
- Database backups (Fly.io manages)
- Networking (Fly.io manages)

---

## Next Steps

1. **Review fly.toml** (I just created it)
2. **Update production settings** (add WhiteNoise)
3. **Deploy:** `flyctl deploy --app episteme`
4. **Run migrations:** `flyctl ssh console -C "python manage.py migrate"`
5. **Deploy frontend to Vercel** (free)

Want me to:
- A) Create the production settings updates?
- B) Create GitHub Actions workflow for auto-deploy?
- C) Help troubleshoot the first deployment?

What would be most helpful?