# INVENTIQ Deployment Plan - Render (All-in-One) + Supabase Free

## Overview
Deploy the Django monolith to Render Free tier + Supabase Free Singapore, no Vercel.

**Zero external AI dependencies** — all forecasting is deterministic Python/statistics.

## Hosts
- **Compute:** Render Web Service (Free) + Render Cron Job (Free)
- **Database:** Supabase Free `waxis-inventory` `ap-southeast-1` Transaction Pooler `6543`
- **No Vercel**

---

## 🟢 SESSION STATE (2026-09-30) — **RESUME HERE**

### ✅ COMPLETED
- **UI/UX Modernization & Ergonomics (2026-09-30)**:
  - **Split-Screen Responsive Login** (`templates/accounts/login.html`): `lg:flex-row` desktop showcase with brand pillars + mobile touch card, password toggle, 16px iOS zoom protection, semantic status pills.
  - **Dedicated Crew 2-Tab Navigation** (`templates/base.html`, `dashboard/views.py`, `inventory/views.py`): Crew restricted strictly to `Deduct Stock` and `My Transactions`, auto-landing on Kitchen Hub, general inventory role-guarded.
  - **Kitchen Touch Ergonomics** (`_deduct_card.html`): 48px touch targets, quick-increment pills (`+1`, `+5`, `+10`, `Max`), zero-stock guards, HTTP 422 error handling.
  - **Logout Session Message Leak Fix** (`accounts/views.py`, `inventory/views.py`, `config/settings.py`): Message storage purged on logout, HTMX partials prevented from poisoning cookies, `MESSAGE_TAGS` 25 error override removed.
  - **Real-Time Inbound Delivery Ingestion** (`procurement/views.py:mark_delivered`): Automatically logs `InboundShipment` records upon PO delivery for continuous Agrilytics rhythm learning.
  - **Documentation**: Standardized `DESIGN_SYSTEM.md`, renamed and updated `ai_integration.md`, updated `System Design and Architecture Document.md` and `README.md`.
- **Forecasting UI & Engine (`c568432`)**: `forecasting/selectors.py` shared enrichment, brand-aligned radar (`radar-card`), HTMX `HX-Redirect` order flow, deduplicated partials, dual-risk highlights, timeline chart, variance UI, radar polling.
- **Doughnut Chart**: Category dynamic binding (`Dry Goods` $\rightarrow$ Amber, `Chilled` $\rightarrow$ Orange, `Frozen` $\rightarrow$ Maroon) with 65% cutout; empty data guards.
- **Infrastructure Patches**: `requirements.txt` (Django 4.2 LTS, `gunicorn`, `whitenoise`, `dj-database-url`), `render.yaml` Blueprint, `config/settings.py` database pooler + WhiteNoise staticfiles.

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
