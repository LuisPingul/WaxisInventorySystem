# Waxi's Inventory Management System (INVENTIQ)

Django inventory system for SND Foods International Inc. (Waxi's) with **dual-mode AI forecasting**:
- **Consumption-based** — Rolling 30-day usage predicts stockout dates
- **Supplier Rhythm** — Historical delivery intervals (Agrilytics) predict supplier windows

Zero external AI dependencies — all forecasting is pure Python/statistics.

## Roles

- Developer — technical superuser (Django admin)
- Owner — business superuser (full dashboard + radar + forecast)
- Manager — operational management (dashboard + radar + HTMX forecast)
- Crew — kitchen/stock operations (deduct stock, my transactions)

Business hierarchy: Owner > Manager > Crew  
Developer = technical admin (outside hierarchy)

## Quick Start

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
# In Django admin: edit user's Profile → Role = OWNER
python manage.py runserver
```

Open: http://127.0.0.1:8000/accounts/login/

## Key Features

| Module | Description |
|--------|-------------|
| **Kitchen Hub** | Touch-optimized deduction entry (HTMX autocomplete) |
| **Crew Dashboard** | Responsive ingredient grid with inline deduct forms, HTMX search, scrollable (no pagination), zero-stock disabling |
| **Owner/Manager Dashboards** | Stats, Executive Summary (structured list), Procurement Radar, Storage Distribution chart, High Demand Products chart |
| **Forecasting** | 3-tab UI: Consumption (HTMX risk filter) + Supplier Radar (60s polling) + Stockout Timeline (Chart.js) |
| **Procurement Radar** | "Active Hunter" — upcoming supplier delivery windows, Refresh + auto-polling on dashboards |
| **PO Manager** | Alerts → PRs → Supplier emails (deterministic templates) |
| **Reports** | Turnover, waste, variance tracking (SDG 12) |

## Forecasting Engine (Zero-AI)

1. **Consumption Forecast** (`compute_forecasts` cron) — 30-day rolling avg from `StockTransaction`, predicts stockout date, suggests reorder, classifies risk (HIGH/MEDIUM/LOW)
2. **Supplier Rhythm** (Agrilytics) — Inter-Arrival Time analysis on `InboundShipment` history (min 3 deliveries), predicts delivery windows with confidence score
3. **Dual-Mode** — Combines both: downgrades risk if supplier delivering soon, escalates if no delivery window in sight
4. **Shared selectors** (`forecasting/selectors.py`) — `get_enriched_rows` + `get_radar_alerts` + `build_forecast_context` reused by forecast page and dashboard partials (no duplicated logic)
5. **Variance tracking** — `AIProcurementAlert` logs predicted vs actual zero date (`variance_days`, `accuracy_note`), surfaced in `forecasting/alerts.html`

## Management Commands

```bash
# Backfill historical inbound shipments (from PRs + StockTransaction)
python manage.py backfill_inbound_shipments [--dry-run] [--clear]

# Daily cron: consumption alerts + supplier rhythms
python manage.py compute_forecasts [--days=30] [--dry-run] [--rhythm-only]
```

## Requirements

- Python 3.9+
- Django 4.2 (LTS)
- PostgreSQL (production) / SQLite (dev)
- No external AI APIs (zero `google-generativeai`)

## Environment Variables

```bash
DJANGO_SECRET_KEY=...
DJANGO_DEBUG=1
ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=postgresql://...  # optional, else SQLite
```

## Deployment (Render + Supabase)

See `DEPLOYMENT_PLAN.md` for Render Web Service + Supabase Free (Singapore) + Cron Job setup.

## Architecture

- **Frontend**: Django Templates + HTMX (partials, `HX-Redirect`, polling) + Bootstrap 5 + Chart.js (CDN)
- **Backend**: Django 4.2 (LTS), pure Python forecasting (`statistics` module)
- **DB**: PostgreSQL (Supabase) / SQLite (dev)
- **Zero external AI** — no Gemini, no API keys required

## AI Development Skills (OpenCode)

Installed via [vintasoftware/django-ai-plugins](https://github.com/vintasoftware/django-ai-plugins) in `.opencode/plugins/django-ai-plugins/`.

| Skill | Purpose | Applies To |
|-------|---------|------------|
| `django-expert` | Models, ORM, views, security, testing, deployment | ✅ All Django work |
| `django-safe-migration` | Zero-downtime PostgreSQL migrations (concurrent indexes, FK validation, db_default) | ✅ Migrations (supplier FK, etc.) |
| `django-reviewer` | Code review for Django/DRF anti-patterns | ✅ PR review, refactoring |
| `django-celery-expert` | Celery task patterns | ⚠️ Not used (management commands) |
| `cdrf-expert` | DRF class-based view guidance | ⚠️ Not used (HTMX + FBVs) |

**Usage in OpenCode:**
```bash
opencode run "Review forecasting/services.py for N+1 queries"
opencode run "Check migration 0002 for zero-downtime safety"
opencode run "Best practice for adding a new Ingredient field"
```
