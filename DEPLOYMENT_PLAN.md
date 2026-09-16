# INVENTIQ Deployment Plan - Render (All-in-One) + Supabase Free

## Overview
Deploy the Django monolith to Render Free tier + Supabase Free Singapore, no Vercel.

## Hosts
- **Compute:** Render Web Service (Free) + Render Cron Job (Free)
- **Database:** Supabase Free `waxis-inventory` `ap-southeast-1` Transaction Pooler `6543`
- **No Vercel**

---

## 🟢 SESSION STATE (2026-09-16) — **RESUME HERE**

### ✅ COMPLETED (pushed to `LuisPingul/WaxisInventorySystem:main` commit `36a15ca`)
- `requirements.txt`: + `gunicorn>=22.0` `whitenoise>=6.6` `dj-database-url>=2.2`
- `config/settings.py`: `DATABASE_URL` pooler parse (`ssl_require=True`, `conn_max_age=0`), `ALLOWED_HOSTS .onrender.com` auto, `CSRF_TRUSTED_ORIGINS`, `STATIC_ROOT` + `WhiteNoise`, `SECURE_PROXY_SSL_HEADER`, `sslmode=require` fallback
- `.env.example`: + `DATABASE_URL`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`
- `render.yaml`: Free Web + Cron (`0 18 * * * compute_forecasts`) Blueprint
- `DEPLOYMENT_PLAN.md`: this file
- Local verify: `manage.py check` 0, `collectstatic` 172, `seed_demo` 12/40/8/3, `compute_forecasts` import OK

### ⏳ REMAINING (MANUAL — needs you)
| Step | Action | Where | Credentials needed |
|------|--------|-------|---------------------|
| 1 | Create Supabase Free project | `https://supabase.com/dashboard` | Name: `waxis-inventory`, Region: `Singapore (ap-southeast-1)`, Plan: `Free`, DB Password: *generate & save* |
| 2 | Get Transaction Pooler URL | Supabase → Settings → Database → Connection pooling → Transaction (port 6543) | Copy URI: `postgresql://postgres.<REF>:<PASS>@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require` |
| 3 | Deploy via Render Blueprint | `https://dashboard.render.com → New → Blueprint` | Connect `LuisPingul/WaxisInventorySystem` → Apply |
| 4 | Set Render env vars | Render Web Service → Environment | `DATABASE_URL` = pooler URI from Step 2; `GEMINI_API_KEY` = *(from local `.env`)*; `DJANGO_SECRET_KEY` (auto-generate) |
| 5 | Verify live | `https://waxis-inventory.onrender.com/accounts/login/` | `developer` / `dev12su` |

---

## Phase 0 - Supabase New Project (Manual)
1. `https://supabase.com/dashboard → New Project` `waxis-inventory` `Region Singapore ap-southeast-1` `Plan Free`
2. `Database → Connect → Transaction pooler` → collect `postgresql://postgres.<REF>:<PASS>@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require`
3. Anti-pause: daily `compute_forecasts` `AuditLog` write + `UptimeRobot` 5min ping keeps both Render Web and Supabase alive

## Phase 1 - Code Patches
- `requirements.txt`: add `gunicorn>=22.0` `whitenoise>=6.6` `dj-database-url>=2.2`
- `config/settings.py`:
  - `ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS","127.0.0.1,localhost,testserver").split(",")` + auto `.onrender.com` if `RENDER`
  - `CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_TRUSTED_ORIGINS","").split(",")` if set
  - `DATABASES` priority: `DATABASE_URL` via `dj_database_url.parse(..., conn_max_age=0, ssl_require=True)` > `DB_NAME` with `OPTIONS {"sslmode":"require"}` > sqlite
  - `STATIC_ROOT = BASE_DIR / "staticfiles"` `STORAGES = {"staticfiles": {"BACKEND":"whitenoise.storage.CompressedManifestStaticFilesStorage"}}` `SECURE_PROXY_SSL_HEADER`
  - `MIDDLEWARE`: insert `WhiteNoiseMiddleware` after `SecurityMiddleware`
- `.env.example`: add `DATABASE_URL` `DJANGO_SECRET_KEY` `DJANGO_DEBUG` `ALLOWED_HOSTS` `CSRF_TRUSTED_ORIGINS`

## Phase 2 - Render Config
- `render.yaml`: Web Service (Free) + Cron Job (Free) `0 18 * * *` `compute_forecasts`
- Env vars on dashboard: `DATABASE_URL` pooler, `GEMINI_API_KEY`, `DJANGO_SECRET_KEY` (generate), `ALLOWED_HOSTS .onrender.com`, `CSRF_TRUSTED_ORIGINS https://waxis-inventory.onrender.com`

## Phase 3 - Reliability (Free)
- Supabase Free `7` day pause mitigated by daily cron + `UptimeRobot` `5min` ping
- Render Free `15min` sleep mitigated by `UptimeRobot` ping
- AI `Gemini 3.6-flash` works within `gunicorn 120s` timeout

## Post-Deploy Verify
- `GET /accounts/login/` `200` `developer/dev12su`
- `GET /reports/` `200` `₱24,600` `38.1%` `5 fast-movers`
- `GET /procurement/<pk>/email/` → Gemini `Subject: Purchase Order Request`
- `Cron → Run Now` → `Forecasts computed: 12 ingredients` `AuditLog CRON_FORECAST`
