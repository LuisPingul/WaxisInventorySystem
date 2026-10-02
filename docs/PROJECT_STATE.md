# Project State · INVENTIQ (WaxisInventorySystem)

> **Last Updated**: 2026-10-02  
> **Client / Organization**: Waxi's / SND Foods International  
> **Repository**: `WaxisInventorySystem`

---

## 1. Current Project Goal

INVENTIQ is a production-grade restaurant inventory management and predictive procurement web application. The core objective is streamlining commercial kitchen stock operations, automating procurement recommendations with dual-mode AI/statistical forecasting, providing executive operational briefing dashboards, and tracking food waste reduction in Philippine Pesos (₱) to support UN Sustainable Development Goal 12 (Responsible Consumption and Production).

---

## 2. Auto-Detected Tech Stack

* **Language**: Python 3.11+
* **Framework**: Django 4.2 LTS (`Django>=4.2,<5.0`)
* **Dynamic Frontend Layer**: `django-htmx>=1.19`, Tailwind CSS (CDN), Bootstrap 5.3 (CDN), Bootstrap Icons 1.11, Chart.js 4.4 (CDN)
* **Database**:
  * Local Development: SQLite (`db.sqlite3`)
  * Production Deployment: PostgreSQL via `psycopg[binary]>=3.2` and `dj-database-url>=2.2`
* **Static Assets**: WhiteNoise 6.6 (`whitenoise.middleware.WhiteNoiseMiddleware`)
* **WSGI / Production Server**: Gunicorn 22.0 (`gunicorn>=22.0`)
* **Deployment Specification**: Render Blueprint (`render.yaml`)

---

## 3. Architecture Overview & Key Folders

```
WaxisInventorySystem/
├── accounts/          # User authentication, profiles, role management (OWNER, MANAGER, CREW, DEVELOPER)
├── dashboard/         # Role-based landing views, operational metrics, executive briefing service
├── inventory/         # Ingredients, units, stock deductions, transactions, kitchen touch cards
├── procurement/       # Purchase orders, PO approval workflow, dual-channel Viber & Email dispatch hub
├── forecasting/       # Dual-mode predictive engine (Statistical Holt-Winters + AI), supplier delivery rhythm
├── reports/           # Executive reports, spoilage in ₱ (SDG 12), supplier reliability, fast-moving items
├── audit/             # Centralized audit logging (log_action) for inventory and authentication events
├── suppliers/         # Vendor profiles, lead time tracking, contact info, linked ingredient FKs
├── templates/         # Master layouts (base.html), role-specific templates, HTMX component partials
├── static/            # CSS tokens (style.css), brand assets, images (waxis_w.png, logo)
├── docs/              # System documentation, PROJECT_STATE, DECISIONS, TASK_LOG, plans
└── config/            # Django root settings, URL configuration, WSGI/ASGI entrypoints
```

---

## 4. Completed & Stabilized Features

1. **Enterprise Role-Based Access Control (RBAC)**:
   * **Owner**: Full executive oversight, reports, forecast, users, and procurement approvals.
   * **Manager**: Full operational management, inventory tracking, PO generation, and executive briefing.
   * **Crew**: Locked strictly to 2 tabs (**Deduct Stock** and **My Transactions**). Auto-redirects prevent navigation to management tabs.
   * **Developer**: Full system administration plus direct Django Admin link.
2. **Kitchen Operations Hub (Touch-Ergonomic Stock Deduction)**:
   * Minimum `48px` touch target scale with `16px` base typography (eliminates iOS Safari auto-zoom).
   * One-tap portion increment pills (`+1`, `+5`, `+10`, `Max`) for 1-second stock deduction.
   * Floating sticky action panel with 1-tap category quick-filters (**All Items**, **Dry Goods**, **Chilled**, **Frozen**).
   * Fluid, natural page scrolling (`pb-16`) replacing the previous `calc(100vh - 350px)` inner scroll trap.
3. **Dual-Channel Purchase Order Dispatch Hub**:
   * Single-click **Viber Instant Dispatch** formatted with emojis, bolding, order reference, and auto-normalized phone (`639XXXXXXXXX`).
   * Clean **Official Email Draft** with sender/recipient copies, clear delivery addresses, and zero subject-line duplication.
   * Inline supplier phone editing and 1-click "Mark as Dispatched (ORDERED)" directly on the dispatch page.
4. **Predictive AI Procurement Radar & Supplier Rhythm**:
   * Automated cadence forward-projection (`last_delivery + cycle_days`) projecting upcoming delivery windows (`Active Now`, `in Xd`).
   * Dual-mode forecasting (Statistical cadence + AI alert variance detection).
5. **Executive Operations Briefing & Operational Health Score (0–100)**:
   * Multi-metric health scoring evaluating depleted ingredients, bottleneck PRs, and cold-chain sensitivity.
   * Strategic Directive action bar with high-contrast hover buttons (`Review Pending PRs`, `Stock Replenishment`, `Copy for Viber`).
6. **Sidebar Navigation & User Profile Re-Alignment**:
   * Modern `.user-profile-card` embedded in `.sidebar-footer` directly above the Log Out button.
   * Redundant 82px desktop topbar removed, saving vertical canvas across all screens while preserving a 56px sticky mobile app bar.
7. **Forecast High-Contrast Segmented Tabs & URL State Synchronization**:
   * Scoped legacy `.nav-link` CSS to `.sidebar .nav-link` to prevent white-on-white text bleeding into page content.
   * Modern Option A Segmented Pill Tab Bar (`.forecast-tabs-container`, `.forecast-tab-btn`) with high-contrast slate text (`#475569`, 7.2:1 contrast, WCAG AAA), tactile warm hover state, Waxi's brand maroon active pill (`#871F09` to `#5E1507`), Brand Gold icon (`#FED216`), and live count badges (`8 AI Alerts`, `Live Rhythm`, `Top 12`).
   * Browser URL synchronization (`window.history.replaceState`) and auto-activation from `?tab=...` on load with smooth Chart.js timeline rendering.
8. **Procurement Status Tabs, Interactive KPI Cards & Closed-Loop Forecast Integration**:
   * Upgraded `/procurement/` with high-contrast segmented pill tab bar: **All Requests**, **Pending Approval**, **Ready to Dispatch**, **In Transit**, and **Delivered History**, matching the touch-first design of the Forecast Tab.
   * Interactive top KPI stat cards synchronized with status tabs and instant HTMX partial swapping (`_list_table.html`).
   * Rich AI traceability badges (`.ai-source-badge`) linking procurement requests directly back to `/forecast/`.
   * Closed-loop notification toast integration connecting "Convert to PR" with instant procurement review.
9. **Unified Forecast & Procurement Hub with Operational Sidebar Hierarchy**:
   * Sidebar navigation re-ordered to mirror real kitchen operations: Dashboard $\rightarrow$ Inventory $\rightarrow$ Transactions $\rightarrow$ **Forecast** $\rightarrow$ **Suppliers** $\rightarrow$ Reports $\rightarrow$ Audit Logs. Standalone top-level Procurement link removed.
   * Unified 4-tab Forecast Hub: **Consumption Forecast**, **Procurement Requests** (adjacent!), **Supplier Radar**, and **Stockout Timeline**.
   * 1-Click "Convert to PR" micro-UX automatically shifts active tab to Procurement Requests, highlights the new PR with `.row-highlighted` glow, and provides instant Viber/Email dispatch.
   * 100% backward compatibility redirect from `/procurement/` to `/forecast/?tab=procurement` with HTMX partial table swaps preserved.

---

## 5. In-Progress Features & Active Roadmap

1. **Automated Unit & Integration Test Expansion**: Comprehensive coverage for stock deduction transactions and role redirects.
2. **Alert Notification Webhooks**: Exploring push notification triggers for critical zero-stock thresholds.

---

## 6. Known Constraints & Production Notes

* **Static Assets**: Because WhiteNoise post-processes static files with hash manifests in production, always execute `./venv/bin/python manage.py collectstatic --noinput` after making edits to `static/css/style.css`.
* **HTMX 422 Handling**: `base.html` includes an `htmx:beforeSwap` listener that permits HTTP 422 responses to swap into the DOM so form error validation cards render cleanly without raw page reloads.

---

## 7. "Do Not Redo" Registry (Strictly Stabilized Systems)

Agents must **NEVER** modify or roll back the following systems:
* ⛔ **Do NOT re-introduce inner scroll containers** (`calc(100vh - ...)` or `overflow-y-auto`) to `/inventory/deduct/` or general list pages. Natural window scrolling (`window.scrollY`) is mandatory.
* ⛔ **Do NOT move the User Profile Card back to the topbar**. It is permanently anchored in `.sidebar-footer` above Log Out.
* ⛔ **Do NOT grant Crew access to general dashboard/inventory routes**. The 2-tab crew lock is an established security and UX constraint.
* ⛔ **Do NOT alter brand tokens in `static/css/style.css`**: Maroon (`#871F09`), Orange (`#FE5F10`), Amber (`#FED216`), Charcoal (`#1E293B`).
* ⛔ **Do NOT un-scope `.sidebar .nav-link` or re-introduce global `.nav-link` color overrides** that turn inactive tabs white or invisible. All in-page tabs must maintain high contrast (WCAG AA/AAA compliant).
* ⛔ **Do NOT restore standalone top-level 'Procurement' in the sidebar**. Procurement is unified inside the Forecast Hub (`/forecast/?tab=procurement`), and `/procurement/` redirects to it.
* ⛔ **Do NOT re-introduce `MESSAGE_TAGS = { 25: "error" }` in `config/settings.py`**.
