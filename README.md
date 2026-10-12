# INVENTIQ · Waxi's Inventory Intelligence System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-4.2%20LTS-092E20?logo=django&logoColor=white)
![Database](https://img.shields.io/badge/PostgreSQL-Supabase-3ECF8E?logo=supabase&logoColor=white)
![Hosting](https://img.shields.io/badge/Hosted%20on-Render-46E3B7?logo=render&logoColor=white)
![PWA](https://img.shields.io/badge/PWA-Installable%20Offline%20Ready-5A0FC8?logo=pwa&logoColor=white)
![WCAG](https://img.shields.io/badge/Accessibility-WCAG%202.2%20AA-success)
![HTMX](https://img.shields.io/badge/Frontend-HTMX%20%2B%20Bootstrap%205-3366CC?logo=htmx&logoColor=white)

**Enterprise-grade Inventory Management & Dual-Mode Predictive Procurement System for SND Foods International Inc. (Waxi's).**

[Live Demo](#quick-start) • [Architecture Docs](docs/architecture/system_design.md) • [Forecasting Engine](docs/ai_forecasting.md) • [Deployment Guide](docs/deployment/render_supabase.md) • [Design System](docs/design_system.md)

</div>

---

## 🌟 Executive Summary

**INVENTIQ** is an end-to-end, kitchen-tested inventory intelligence platform built specifically for fast-casual restaurant operations. It unifies high-speed kitchen stock deductions, executive financial oversight, and automated procurement dispatch into a single high-performance monolith.

### 💡 Core Pillars
* **Dual-Mode Predictive Engine**: Combines **30-day rolling consumption burn-rates** with **Agrilytics Supplier Rhythm (Inter-Arrival Time)** forecasting to predict exact stockout dates without external AI API dependencies.
* **Closed-Loop Procurement**: Convert AI stockout alerts into formal Purchase Requests (PRs) in 1 click, dispatching instantly via formatted Viber messages or clean email drafts.
* **Kitchen Touch Ergonomics**: A dedicated Crew Kitchen Hub with $\ge$48px touch targets, quick-increment step pills (`+1`, `+5`, `+10`, `Max`), and zero-stock guards designed for messy kitchen tablet use.
* **Progressive Web App (PWA)**: Full offline service worker caching, custom branded recovery screen, and borderless fullscreen installation across iPads, Android tablets, and desktop workstations.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Clients["Device & Client Layer"]
        C1["Kitchen Tablet (Crew PWA / iPad)"]
        C2["Manager Workstation (Desktop Chrome)"]
        C3["Executive Mobile (iOS / Android)"]
    end

    subgraph CDN_Gateway["Network & Edge Layer"]
        WAF["Render Edge / SSL Gateway"]
        SW["Service Worker (sw.js / Offline Fallback)"]
        WN["WhiteNoise Static Engine (Compressed Manifest)"]
    end

    subgraph Core["Django Application Monolith (Python 3.11)"]
        Auth["Accounts & RBAC (Crew / Manager / Owner / Dev)"]
        KHub["Kitchen Hub (Fast Deductions & History)"]
        Dash["Executive Dashboards (KPIs, Storage Mix, Trends)"]
        Fore["Dual-Mode Forecasting (Burn-Rate + Agrilytics)"]
        Proc["Procurement & Dispatch (Viber / Email POs)"]
        Aud["Compliance & Audit Engine (Immutable Logs)"]
    end

    subgraph DataLayer["Persistence & Infrastructure"]
        DB[("Supabase PostgreSQL (Transaction Pooler :6543)")]
        Cron["Render Cron Job (Daily 18:00 UTC compute_forecasts)"]
    end

    C1 & C2 & C3 --> SW
    SW --> WAF
    WAF --> WN
    WN --> Core
    Core --> DB
    Cron -.->|Nightly Run| Fore
    Fore -->|Auto-Generate| Proc
```

---

## 👥 Role-Based Access Control (RBAC)

| Role | Target Persona | Primary Interface & Scope |
| :--- | :--- | :--- |
| **Crew** | Line cooks, kitchen prep staff | **Kitchen Hub strictly**: High-speed stock deduction grid, item search, personal transaction history. |
| **Manager** | Store / branch managers | **Operational Hub**: Live stock inventory, supplier directory, forecasting tabs, procurement approvals, and dispatch. |
| **Owner** | Franchisees & brand executives | **Executive Suite**: Full financial inventory valuation, gross margin impact, waste analytics (SDG 12), and turnover KPIs. |
| **Developer**| System administrators | **Django Admin & Audit**: Infrastructure, system checks, database migrations, and raw audit trails. |

---

## 🚀 Quick Start (Local Development)

### 1. Prerequisites
* Python 3.11+
* Git
* SQLite (local dev) or PostgreSQL

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/LuisPingul/WaxisInventorySystem.git
cd WaxisInventorySystem

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS / Linux
# venv\Scripts\activate   # Windows

# Install locked dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env

# Apply database migrations
python manage.py migrate

# Seed rich demonstration dataset (Categories, Ingredients, Transactions, Suppliers)
python manage.py seed_demo

# Create administrator account
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

Open **`http://127.0.0.1:8000/accounts/login/`** in your browser.

---

## 🔮 Dual-Mode Forecasting (Zero-AI Architecture)

INVENTIQ delivers predictive intelligence using pure deterministic statistics (`statistics` module) with **zero external API costs, latency, or rate limits**:

1. **Consumption Forecast Model**:
   * Evaluates rolling 30-day historical usage from `StockTransaction`.
   * Projects daily burn rate ($B = \frac{\sum U}{30}$) and calculates days until zero stock ($D = \frac{S_{\text{current}}}{B}$).
   * Automatically classifies stockout risk into `HIGH` ($\le 3$ days), `MEDIUM` ($\le 7$ days), or `LOW`.
2. **Supplier Rhythm Model (Agrilytics)**:
   * Analyzes historical delivery intervals on `InboundShipment` records (minimum 3 deliveries).
   * Calculates mean delivery cadence and variance to forecast the next expected arrival window.
3. **Dual-Risk Matrix**:
   * Synthesizes consumption urgency with supplier cadence:
     * *Escalates to HIGH* if stock will deplete before the next expected delivery.
     * *Downgrades urgency* if a supplier delivery is confirmed within the safe inventory horizon.
4. **Automated Cron**:
   * Executed daily via Render Cron: `python manage.py compute_forecasts`.

---

## 🛠️ Management Commands

```bash
# Compute consumption alerts and supplier rhythms
python manage.py compute_forecasts [--days=30] [--dry-run] [--rhythm-only]

# Backfill historical inbound delivery rhythms from POs and transactions
python manage.py backfill_inbound_shipments [--dry-run] [--clear]

# Seed demo catalog with realistic fast-casual restaurant data
python manage.py seed_demo
```

---

## 🌐 Production Deployment (Render + Supabase)

Detailed step-by-step instructions are documented in [**`docs/deployment/render_supabase.md`**](docs/deployment/render_supabase.md).

* **Hosting**: Render Web Service (`Python`) + Render Cron Job
* **Build Command**: `./build.sh`
* **Start Command**: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
* **Database**: Supabase PostgreSQL Transaction Pooler (Port `6543`)
* **Static Assets**: WhiteNoise with `CompressedManifestStaticFilesStorage`

### Required Production Environment Variables
| Key | Example / Description |
| :--- | :--- |
| `DATABASE_URL` | `postgresql://postgres.[REF]:[PASS]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require` |
| `DJANGO_SECRET_KEY` | 50+ character random cryptographic key |
| `DJANGO_DEBUG` | `0` (Switches on secure cookies and disables debug tracebacks) |
| `ALLOWED_HOSTS` | `.onrender.com,waxis-inventory.onrender.com` |
| `CSRF_TRUSTED_ORIGINS`| `https://*.onrender.com,https://waxis-inventory.onrender.com` |
| `PYTHON_VERSION` | `3.11.9` |

---

## 📚 Documentation Directory

Explore the dedicated documentation in the [`docs/`](docs/) directory:

* 🏛️ **[System Architecture](docs/architecture/system_design.md)** — Architectural diagrams, data models, and specifications.
* 📈 **[Dual-Mode Forecasting Engine](docs/ai_forecasting.md)** — In-depth mathematical formulas and Agrilytics rhythms.
* 🎨 **[Design System & Ergonomics](docs/design_system.md)** — Waxi's Maroon/Orange/Gold tokens and WCAG rules.
* 🚀 **[Production Deployment Plan](docs/deployment/render_supabase.md)** — Full Render Web & Supabase setup.
* 📜 **[Architectural Decision Records](docs/DECISIONS.md)** — ADR-001 through ADR-012 records.
* 📋 **[Project State & Invariants](docs/PROJECT_STATE.md)** — Feature registry and non-regression rules.
* ⏱️ **[Task Log](docs/TASK_LOG.md)** — Complete chronological engineering trajectory.
* 🤖 **[Agent Guidelines](docs/agents.md)** — Operational guidelines for AI coding assistants.

---

## 🤝 Contributing & Security

* **Contribution Guidelines**: Please review [**`CONTRIBUTING.md`**](CONTRIBUTING.md) before submitting pull requests.
* **Security Disclosures**: Please review [**`SECURITY.md`**](SECURITY.md) for vulnerability reporting.

---

<div align="center">
Built with ❤️ for <b>SND Foods International Inc. (Waxi's)</b>.
</div>
