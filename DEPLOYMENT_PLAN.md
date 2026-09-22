# INVENTIQ Deployment Plan - Render (All-in-One) + Supabase Free

## Overview
Deploy the Django monolith to Render Free tier + Supabase Free Singapore, no Vercel.

**Zero external AI dependencies** — all forecasting is deterministic Python/statistics.

## Hosts
- **Compute:** Render Web Service (Free) + Render Cron Job (Free)
- **Database:** Supabase Free `waxis-inventory` `ap-southeast-1` Transaction Pooler `6543`
- **No Vercel**

---

## 🟢 SESSION STATE (2026-09-22) — **RESUME HERE**

### ✅ COMPLETED
- Forecasting UI finished (`c568432`): `forecasting/selectors.py` shared enrichment, brand-aligned radar (`radar-card`), HTMX `HX-Redirect` order flow, deduplicated `_forecast_table.html`/`_radar_panel.html` partials, dual-risk owner highlights, timeline chart, variance UI, radar polling
- Doughnut chart blank fix (local, uncommitted): `_chart_data()` returned `json.dumps()` string double-encoded by `|json_script` → now returns `dict`; empty-data guard in owner/manager templates
- Dashboard batch (local, uncommitted): View All → Forecast redirects (`?tab=radar` deep link, `forecast_partial` removed), Owner summary = Manager summary, seamless topbar, hidden sidebar scrollbar, High Demand line chart (Owner + Manager, rolling-30d daily series), doughnut product tooltips (Owner + Manager)
- `requirements.txt`: Django 4.2 LTS, `gunicorn>=22.0` `whitenoise>=6.6` `dj-database-url>=2.2` (no `google-generativeai`)
- `config/settings.py`: `DATABASE_URL` pooler parse (`ssl_require=True`, `conn_max_age=0`), `ALLOWED_HOSTS .onrender.com` auto, `CSRF_TRUSTED_ORIGINS`, `STATIC_ROOT` + `WhiteNoise`, `SECURE_PROXY_SSL_HEADER`, `sslmode=require` fallback
- `.env.example`: + `DATABASE_URL`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`
- `render.yaml`: Free Web + Cron (`0 18 * * * compute_forecasts`) Blueprint
- Local verify: `manage.py check` 0, `collectstatic`, `backfill_inbound_shipments`, `compute_forecasts` (consumption + rhythm)

### ⏳ REMAINING (MANUAL)
| Step | Action | Where | Credentials needed |
|------|--------|-------|---------------------|
| 1 | Create Supabase Free project | `https://supabase.com/dashboard` | Name: `waxis-inventory`, Region: `Singapore (ap-southeast-1)`, Plan: `Free`, DB Password: *generate & save* |
| 2 | Get Transaction Pooler URL | Supabase → Settings → Database → Connection pooling → Transaction (port 6543) | Copy URI: `postgresql://postgres.<REF>:<PASS>@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require` |
| 3 | Deploy via Render Blueprint | `https://dashboard.render.com → New → Blueprint` | Connect `LuisPingul/WaxisInventorySystem` → Apply |
| 4 | Set Render env vars | Render Web Service → Environment | `DATABASE_URL` = pooler URI from Step 2; `DJANGO_SECRET_KEY` (auto-generate); **No `GEMINI_API_KEY` needed** |
| 5 | Verify live | `https://waxis-inventory.onrender.com/accounts/login/` | `developer` / `dev12su` |

---

## Phase 0 - Supabase New Project (Manual)
1. `https://supabase.com/dashboard → New Project` `waxis-inventory` `Region Singapore ap-southeast-1` `Plan Free`
2. `Database → Connect → Transaction pooler` → collect `postgresql://postgres.<REF>:<PASS>@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require`
3. Anti-pause: daily `compute_forecasts` `AuditLog` write + `UptimeRobot` 5min ping keeps both Render Web and Supabase alive

## Phase 1 - Code Patches (Already Applied)
- `requirements.txt`: Django 4.2 LTS, `gunicorn>=22.0` `whitenoise>=6.6` `dj-database-url>=2.2` — **No `google-generativeai`**
- `config/settings.py`:
  - `ALLOWED_HOSTS` auto `.onrender.com` if `RENDER`
  - `CSRF_TRUSTED_ORIGINS` from env
  - `DATABASES` priority: `DATABASE_URL` via `dj_database_url.parse(..., conn_max_age=0, ssl_require=True)` > `DB_NAME` with `sslmode=require` > sqlite
  - `STATIC_ROOT`, `STORAGES` WhiteNoise, `SECURE_PROXY_SSL_HEADER`
  - `MIDDLEWARE`: `WhiteNoiseMiddleware` after `SecurityMiddleware`
- `.env.example`: `DATABASE_URL` `DJANGO_SECRET_KEY` `DJANGO_DEBUG` `ALLOWED_HOSTS` `CSRF_TRUSTED_ORIGINS`

## Phase 2 - Render Config
- `render.yaml`: Web Service (Free) + Cron Job (Free) `0 18 * * *` `compute_forecasts`
- Env vars on dashboard: `DATABASE_URL` pooler, `DJANGO_SECRET_KEY` (auto-generate), **No `GEMINI_API_KEY` required**
- `ALLOWED_HOSTS .onrender.com`, `CSRF_TRUSTED_ORIGINS https://waxis-inventory.onrender.com`

## Phase 3 - Reliability (Free)
- Supabase Free `7` day pause mitigated by daily cron + `UptimeRobot` `5min` ping
- Render Free `15min` sleep mitigated by `UptimeRobot` ping
- **No external AI timeout concerns** — all forecasting is local Python

## Post-Deploy Verify
- `GET /accounts/login/` `200` `developer/dev12su`
- `GET /reports/` `200` turnover/waste reports
- `GET /procurement/<pk>/email/` → **Deterministic template** (no LLM)
- `Cron → Run Now` → `Forecasts computed: X ingredients, Y rhythms` `AuditLog CRON_FORECAST`
- `GET /forecast-partial/` → HTMX forecast tabs load
- `GET /forecast/radar/` → Procurement Radar shows CONTACT_NOW/UPCOMING
