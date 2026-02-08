# Fly.io Deployment - Step by Step

Quick guide to deploy Episteme to Fly.io (you're here after registering).

---

## Current Status

✅ Fly.io account registered  
✅ flyctl installed  
✅ Logged in as fy538@nyu.edu  
✅ App 'episteme' exists  

**Next:** Configure and deploy!

---

## Quick Deploy (10 commands)

```bash
# 1. Reload terminal for flyctl
source ~/.zshrc

# 2. Create Postgres (free dev tier - 1GB)
flyctl postgres create --name episteme-db --region sjc --initial-cluster-size 1

# 3. Attach Postgres to app
flyctl postgres attach episteme-db --app episteme

# 4. Create Redis (Upstash free tier)
flyctl redis create --name episteme-redis --region sjc

# 5. Attach Redis to app
flyctl redis attach episteme-redis --app episteme

# 6. Set secrets
flyctl secrets set \
  SECRET_KEY=$(openssl rand -base64 32) \
  OPENAI_API_KEY=sk-your-key-here \
  GOOGLE_API_KEY=your-gemini-key-here \
  DJANGO_SETTINGS_MODULE=config.settings.production \
  ALLOWED_HOSTS=episteme.fly.dev \
  --app episteme

# 7. Deploy
flyctl deploy --app episteme

# 8. Run migrations
flyctl ssh console --app episteme -C "python manage.py migrate"

# 9. Create superuser (interactive)
flyctl ssh console --app episteme
# Inside VM:
python manage.py createsuperuser
exit

# 10. Open app
flyctl open --app episteme
```

**Done! Your backend is live at https://episteme.fly.dev**

---

## Deploy Frontend to Vercel (5 commands)

```bash
cd frontend

# 1. Install Vercel CLI (if needed)
npm i -g vercel

# 2. Login to Vercel
vercel login

# 3. Set API URL for production
# Create frontend/.env.production:
echo "NEXT_PUBLIC_API_URL=https://episteme.fly.dev/api" > .env.production

# 4. Deploy
vercel

# 5. Deploy to production
vercel --prod
```

**Done! Your frontend is live at https://your-app.vercel.app**

---

## Verify Deployment

### Check Backend

```bash
# Visit your app
https://episteme.fly.dev/admin

# Check API
curl https://episteme.fly.dev/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}'

# Should return JWT tokens
```

### Check Frontend

Visit your Vercel URL, should see Episteme landing page.

---

## Cost Monitoring

```bash
# Check your usage
flyctl dashboard billing

# Check app metrics
flyctl status --app episteme

# View detailed metrics
flyctl dashboard metrics
```

**Set billing alerts** in Fly.io dashboard to avoid surprises.

---

## Updating After Changes

### Update Backend

```bash
# Make changes to code
# Then deploy:
flyctl deploy --app episteme

# Logs:
flyctl logs --app episteme
```

### Update Frontend

```bash
cd frontend

# Vercel auto-deploys from GitHub if connected
# Or manually:
vercel --prod
```

---

## Rollback if Something Breaks

```bash
# List releases
flyctl releases --app episteme

# Rollback to previous version
flyctl releases rollback --app episteme
```

---

## Common Issues

### "502 Bad Gateway"

App might be starting. Wait 30 seconds, then:
```bash
flyctl logs --app episteme
```

### "Database connection failed"

```bash
# Check DATABASE_URL is set
flyctl ssh console --app episteme -C "env | grep DATABASE"
```

### "Out of memory"

```bash
# Scale up (costs more)
flyctl scale memory 1024 --app episteme  # 1GB RAM
```

---

## Expected Timeline

- **Database creation:** 2-3 minutes
- **Redis creation:** 1 minute  
- **First deploy:** 5-10 minutes (builds Docker image)
- **Subsequent deploys:** 2-5 minutes (cached layers)
- **Migrations:** 10-30 seconds

**Total first deployment: ~15-20 minutes**

---

## What You'll Have

After deployment:

- **Backend:** https://episteme.fly.dev
- **Frontend:** https://your-app.vercel.app
- **Admin:** https://episteme.fly.dev/admin
- **API:** https://episteme.fly.dev/api

**Cost:** $0-10/month (likely free under $5 usage)

---

## Next Steps

1. Run the 10 commands above
2. Test at your Fly.io URL
3. Deploy frontend to Vercel
4. Update CORS_ALLOWED_ORIGINS with your Vercel domain
5. Start dogfooding!

Ready to deploy? Just copy-paste the commands! 🚀
