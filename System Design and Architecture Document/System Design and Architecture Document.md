# System Design and Architecture Document
**Project Title:** Waxi's Smart Inventory & AI-Powered Predictive Procurement System **Client:** SND FOODS INTERNATIONAL INC. (Waxi's) **Target SDG:** SDG 12 - Responsible Consumption & Production
## 1. Executive Summary
The proposed system transitions Waxi's from a manual, reactive inventory tracking method (Google Sheets) into an automated, proactive web-based ecosystem. By creating dedicated interfaces for both Kitchen Staff and Operations Management, the system captures stock depletion in real-time. Furthermore, it introduces a **dual-mode predictive procurement engine** that combines:
- **Consumption-based forecasting** — rolling 30-day usage analysis to predict stockout dates
- **Supplier Rhythm forecasting** (Agrilytics) — historical delivery interval analysis to predict supplier delivery windows

All forecasting is **pure Python/statistics** with zero external AI dependencies (no LLMs, no API keys).
## 2. High-Level System Architecture
The system follows a unified Django monolith (Model-View-Template) architecture, leveraging Django's full-stack capabilities for both frontend rendering and backend logic to ensure maintainability, rapid development, and scalability at Waxi's single-site scale.
## A. Frontend (Client-Side)
* **Framework:** Django Templates (Server-Rendered) + HTMX for reactive partial updates (no SPA).
* **Styling:** Bootstrap 5.3.3 + Bootstrap Icons (responsive grid, touch-friendly `form-control-lg` targets); complements the Django ecosystem.
* **Design Philosophy:** Mobile/Tablet-first for the Kitchen Hub (48dp touch targets, large deduction form); Desktop-optimized for the Admin Dashboard (data-heavy tables and charts).
* **Data Visualization:** Chart.js via CDN for dynamic dashboard analytics (Storage Distribution doughnut, turnover), rendered from Django context `json_script`. Fixed canvas dimensions for reliable rendering.
* **Interactivity:** HTMX `hx-get` with `delay:300ms` for kitchen search autocomplete; HTMX partials for Procurement Radar, Executive Summary, Forecast tabs; gracefully degrading to standard GET filter when JS disabled.
## B. Backend (Server-Side)
* **Framework:** Django (Python) 4.2 LTS
* **API Architecture:** Django Views handling form POST/GET between template frontend and PostgreSQL via ORM; no decoupled SPA JSON required. HTMX partials return HTML fragments rather than JSON.
* **Forecasting Engine (Zero External AI):**
    * **Consumption Forecast:** Pure-Python rolling-average time-series (30-day `StockTransaction` aggregation) with heuristic fallbacks; analyzes `StockTransaction` to predict depletion dates and auto-generates `AI_Procurement_Alerts`. Nightly `manage.py compute_forecasts` via system cron (`0 2 * * *`).
    * **Supplier Rhythm (Agrilytics):** Inter-Arrival Time (IAT) analysis on `InboundShipment` history (min 3 deliveries per supplier/ingredient). Calculates mean interval, std deviation, confidence score (CV-based), predicts delivery windows with ±buffer. Output cached in `SupplierDeliveryPrediction`.
    * **Dual-Mode Intelligence:** Combines both — downgrades risk if supplier delivering soon (window ≤7 days), escalates if no delivery window in 14+ days with HIGH consumption risk.
* **PO Email Generation:** Deterministic template (no LLM) with priority-specific language, inventory status, supplier rating, lead time.
* **Executive Summary:** Rule-based structured HTML list with enumerated items + explanations, color-coded by severity (Critical=red, Low=yellow, Healthy=green).
## C. Database (Data Layer)
* **DBMS:** PostgreSQL (Relational Database)
* **Reasoning:** A relational database is required to strictly enforce data integrity between inventory items, suppliers, active purchase orders, and historical logs.
## 3. Core System Modules
## Module 1: Kitchen Hub (Staff Interface)
A touch-optimized tablet interface located in the kitchen.
* **Function:** Allows staff to quickly search for raw ingredients and input exact numerical deductions as they are consumed during shifts.
* **Architecture Impact:** Every deduction triggers a POST request to the backend, immediately updating the `Ingredient` table and writing a timestamped record to `StockTransaction` (Activity_Logs).

## Module 6: Crew Operations — Dedicated 2-Tab Kitchen Interface
A purpose-built, distraction-free interface for kitchen staff, strictly restricted to two primary tabs: **Deduct Stock** and **My Transactions**.
* **Role Isolation & UX:**
  * Crew accounts automatically land on `/inventory/deduct/` upon authentication or root `/` navigation.
  * Sidebar navigation for Crew renders strictly 2 items: **Deduct Stock** and **My Transactions** (with session Logout at bottom). General dashboard and manager inventory tables are role-guarded and hidden.
* **Kitchen Hub Deduct Grid (`_deduct_grid.html` / `_deduct_card.html`):**
  * Displays ingredients in a responsive card grid (`grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4`) with live HTMX search (300ms debounce) and continuous scroll.
  * **Touch Ergonomics (WCAG 2.2 AA):** Minimum 48px touch targets for inputs and submit buttons; base 16px font size preventing iOS Safari viewport auto-zoom; quick-increment step pills (`+1`, `+5`, `+10`, `Max`) allowing touch deduction without a virtual keyboard.
  * **Zero-Stock Guard:** Depleted items display an explicit `OUT OF STOCK` badge and disable submission inputs.
  * **Reactive HTMX Swaps:** In-place card replacement on deduction (`hx-swap="outerHTML"`) with instant toast feedback. Form errors (e.g. over-deduction) return HTTP 422 and swap error banners directly into the card.
* **My Transactions (`templates/inventory/transactions.html`):**
  * Filtered view showing only deductions and transactions performed by the authenticated crew member, wrapped in a responsive container for tablets and mobile devices.

## Module 2: Command Dashboard (Admin Interface)
The central hub for the Operations Manager and Owner.
* **Function:** Displays high-level analytics, including Total SKUs, Critical/Low Stock alerts, Pending Procurement, **Storage Distribution doughnut chart**, and a live movement ticker.
* **AI Integration:** **Executive Summary** — rule-based structured HTML list with enumerated items + explanations, color-coded severity headers, actionable recommendation box.
* **Procurement Radar:** HTMX partial (`forecasting/_procurement_radar.html`, Bootstrap + Waxi brand) showing upcoming supplier delivery windows (CONTACT_NOW ≤7 days / UPCOMING >7 days) with confidence scores. "Lock In Order" → HTMX `204 + HX-Redirect` to pre-filled PR create. Refresh button + 60–90s auto-polling on forecast page and dashboards. Shared enrichment via `forecasting/selectors.py` (`get_radar_alerts`).
* **Forecasting Tab:** 3-tab interface — Consumption Forecast (stockout risk, HTMX risk filter with `hx-push-url`) + Supplier Radar (delivery windows) + Stockout Timeline (Chart.js bar colored by combined risk). Dual-mode badges show combined risk source. Shared partials `_forecast_table.html` / `_radar_panel.html` reused by forecast page and Owner "View All" HTMX partial.
## Module 3: PO Manager & Predictive Procurement
The core innovation of the Capstone project.
* **Function:** Proactive alerts based on dual-mode forecasting. Instead of manually checking stock, the system generates alerts (e.g., "Expected to run out of Chicken Wings by Saturday" / "Supplier typically delivers in 3 days").
* **Workflow:** 1. AI flags an item based on dual-mode risk. 2. Manager reviews the suggested restock quantity. 3. System generates deterministic PO email template. 4. Once dispatched, the order is tracked in the "Active Purchase Orders" pipeline until marked as "Delivered" (which automatically restocks the inventory and creates `InboundShipment` for rhythm learning).
## Module 4: Supplier Directory (CRUD)
* **Function:** A complete management tab for vendor profiles.
* **Architecture Impact:** Dynamically feeds the PO Manager dropdowns and Procurement Radar, ensuring purchase orders and rhythm predictions are routed to the correct external vendor.
## Module 5: Data Backfill & Rhythm Learning
* **Backfill Command:** `backfill_inbound_shipments` — extracts historical deliveries from `ProcurementRequest` (DELIVERED with `actual_delivery_date`, ORDERED with `expected_delivery_date`) and `StockTransaction` (ADDED with `supplier_fk`). Deduplicates on (supplier, ingredient, date, quantity).
* **Rhythm Computation:** Integrated into daily `compute_forecasts` cron. Requires ≥3 deliveries per supplier/ingredient pair. Outputs `SupplierDeliveryPrediction` cache table.
## 4. Data Architecture (Entity Relationship summary)
The PostgreSQL database is normalized and relies on the following core entities and relationships:
1. **Users/Profiles:** Manages authentication and role-based access (Developer, Owner, Manager, Crew).
2. **Ingredient:** Master catalog of ingredients (stock level, reorder point, storage type, supplier FK).
3. **Supplier:** Directory of vendors (contact info, category, lead time, rating).
4. **ProcurementRequest:** Tracks active orders. *Relates to* Ingredient + Supplier. Status: PENDING→APPROVED→ORDERED→DELIVERED. `auto_generated` flag for AI alerts.
5. **StockTransaction:** The audit trail. *Relates to* Ingredient + User. Types: ADDED, DEDUCTED, ADJUSTMENT, SPOILAGE, RETURN. Used by consumption forecast.
6. **InboundShipment:** Historical delivery records for rhythm analysis. *Relates to* Supplier + Ingredient + optional ProcurementRequest. Source for Agrilytics IAT.
7. **AIProcurementAlert:** Consumption-based stockout predictions. *Relates to* Ingredient. Status: PENDING→CONVERTED/REJECTED. Variance tracking for accuracy.
8. **SupplierDeliveryPrediction:** Agrilytics output cache. Unique per (Supplier, Ingredient). Fields: last_delivery, predicted_cycle_days, window_start/end, estimated_volume, confidence_score, status (UPCOMING/ACTIVE/MISSED).
## 5. Security & Constraints
* **Role-Based Access Control (RBAC):** Strict isolation between Kitchen Hub (write-only deductions) and Admin Portal (full CRUD + analytics). `role_required` decorator enforces per-view permissions.
* **Referential Integrity:** Enforced at SQL level (e.g., ProcurementRequest cannot exist without valid Ingredient/Supplier).
* **Zero External Secrets:** No API keys required — all AI/forecasting runs locally via pure Python.

## 7. UI/UX Fixes Applied (2026-09-18)

### Storage Distribution Chart Rendering Fix
**Issue:** Doughnut charts rendered as blank whitespace due to Chart.js v4 responsive container height collapse.

**Root Cause:** Canvas container `<div style="max-width:520px; margin:auto">` had no explicit height. Chart.js v4 `responsive:true` + `maintainAspectRatio:false` requires parent with definite height.

**Fix Applied:**
1. Added explicit `height:300px` to container divs in both dashboards
2. Added CSS fallback in `static/css/style.css`:
   ```css
   #storageChartOwner, #storageChartManager {
     display: block; width: 100%; height: 300px; max-width: 520px;
   }
   ```
3. Added Chart.js UMD registration guard in `base.html`:
   ```javascript
   (function() {
     var checkChart = function() {
       if (window.Chart) return;
       console.warn('Chart.js not ready, retrying...');
       setTimeout(checkChart, 50);
     };
     checkChart();
   })();
   ```

### Panel Body Padding for Chart Container
**Issue:** Chart container was direct child of `.panel` (overflow:hidden) with no padding.

**Fix:** Added `.panel-body { padding: 20px; }` CSS rule and wrapped chart containers in `<div class="panel-body">`.

### Generate Report Button Text Readability
**Issue:** "Generate Report" button text was unreadable (dark text on orange gradient).

**Root Cause:** `.panel-header a { color: var(--accent-dark); }` specificity overrode `.btn-primary { color: #fff; }`.

**Fix:** Added specificity override in `static/css/style.css`:
```css
.panel-header .btn-primary,
.panel-header .btn-primary:hover { color: #fff !important; }
```

### Primary Button Text Color (Global)
**Fix:** Added explicit `color: #fff;` to `.btn-primary` and `.btn-primary:hover` in `static/css/style.css` (4 locations) to ensure white text on all primary buttons.

### Storage Distribution Blank Chart — Double-Encoded Data (2026-09-22)
**Issue:** Doughnut charts invisible (blank canvas) on Owner + Manager dashboards despite the 2026-09-18 height fix. Not a layout/clipping issue.

**Root Cause:** `dashboard/views.py:_chart_data()` returned a `json.dumps()` **string**, which templates then passed through `|json_script` — serializing a second time. `JSON.parse()` in the init script yielded a string, so `data.labels` / `data.counts` were `undefined` and Chart.js drew nothing.

**Fix Applied:**
1. `_chart_data()` returns a `dict` (`{"labels":..., "counts":...}`); `|json_script` performs the single encoding. Removed unused `import json`.
2. Owner/manager init scripts guard empty data: no labels → replace `.panel-body` content with "No category data yet" empty state instead of a blank canvas.

**Rule:** Never pre-serialize with `json.dumps()` when the template uses `|json_script` — it encodes exactly once.

### Dashboard Navigation Cleanup (2026-09-22)
- Owner "View All" buttons redirect to the Forecast page instead of expanding in place: Forecast Highlights → `/forecast/` (Consumption tab), Procurement Radar (Owner + Manager) → `/forecast/?tab=radar` (Supplier Radar tab via server-side `active_tab`, validated with Consumption fallback).
- Removed dead code: `forecast_partial()` view, `forecast-partial/` route, `_forecast_tabs.html` (the duplicate Radar tab beside Consumption is gone; radar lives solely in the standalone panels).
- Owner Executive Summary unified with Manager's (visual + on-demand `?ai=1` behavior, shared `#ai-summary-box` id).

### Chrome + Charts (2026-09-22)
- Sidebar scrollbar hidden globally (`.no-scrollbar`, scroll still works); topbar seamless globally (`var(--bg)`, no border/shadow/blur).
- "High Demand Products" card beside Storage Distribution on Owner + Manager (theme `.panel`, `lg:grid-cols-2`): filled line chart of daily deductions over rolling 30 days for top 5 ingredients by **deduction count** (`DEDUCTED` + `NORMAL_USAGE`) via `dashboard/services.top_demanded_ingredients()` — zero-filled daily series (`TruncDate`), count-based so mixed units stay comparable.
- Doughnut tooltips (Owner + Manager) list per-category products with stock via `chart_details` payload (`tooltipLabel` callback, multiline).
- Reverted experiment (not shipped): per-product HTML legend under the doughnut — removed after it rendered a literal `{# #}` (Django tags can't span lines) and the chart regressed. Tooltips cover the use case.
## 6. Management Commands & Cron
| Command | Purpose | Schedule |
|---------|---------|----------|
| `backfill_inbound_shipments` | One-time historical data load from PRs + StockTransaction | Manual |
| `compute_forecasts` | Daily: consumption alerts + supplier rhythms | Cron `0 2 * * *` |
| `compute_forecasts --rhythm-only` | Standalone rhythm refresh | Optional |

## 8. UI/UX Modernization & Architecture Hardening (2026-09-30)

### 8.1 Design System Integration (`DESIGN_SYSTEM.md`)
- **Brand Tokens**: Formally standardized Waxi's / SND Foods corporate palette:
  - Deep Maroon (`#871F09`) — primary identity, dark headers, frozen categories.
  - Electric Orange (`#FE5F10`) — primary interactive action, focus rings, chilled categories.
  - Warm Amber (`#FED216`) — secondary accents, warnings, dry goods categories.
  - Charcoal (`#1E293B`) — high-contrast typography and base surfaces.
- **Doughnut Category Palette**: Updated Chart.js storage breakdown across Owner and Manager dashboards to dynamically bind brand colors (`Dry Goods` $\rightarrow$ Amber, `Chilled` $\rightarrow$ Orange, `Frozen` $\rightarrow$ Maroon) with a modern 65% cutout.
- **Skill Adoption**: Installed `ui-ux-pro-max` into `.opencode/skills/ui-ux-pro-max/` to guide future UI component development.

### 8.2 Responsive Split-Screen Login Architecture (`templates/accounts/login.html`)
- **Dual-Mode Layout**:
  - **Desktop / Tablet Landscape ($\ge 1024\text{px}$)**: Left-column brand showcase featuring SND Foods / INVENTIQ branding, gradient backdrop (`#3E1006` to `#871F09`), live operational status indicator, and three enterprise feature cards (Kitchen Hub, Dual-Mode AI Forecasting, Active Procurement Radar). Right column contains a spacious authentication form.
  - **Mobile / Tablet Portrait ($< 1024\text{px}$)**: Gracefully collapses into a centered high-contrast touch card with prominent branding.
- **Ergonomics & Accessibility**:
  - Minimum 48px touch targets for username/password fields and sign-in CTA button.
  - Base input typography set to 16px to prevent iOS Safari auto-zoom behavior on focus.
  - Interactive password visibility toggle button (`bi-eye` / `bi-eye-slash`) with `aria-label`.
  - Semantic alert banners: green emerald pill for positive notifications (e.g. logout), amber for warnings, and red shake alert for invalid credentials.

### 8.3 Crew Role Isolation (Strict 2-Tab Navigation)
- **Navigation Streamlining**: Moved Dashboard and Inventory navigation links inside the non-crew conditional block in `templates/base.html`. The Crew sidebar now displays strictly 2 tabs:
  1. **Deduct Stock** (`/inventory/deduct/`)
  2. **My Transactions** (`/inventory/transactions/`)
- **Automatic Landing & Guards**:
  - `dashboard.views.home` redirects Crew members directly to `deduct_stock` upon login or accessing root `/`.
  - Sidebar logo link automatically directs Crew to `deduct_stock`.
  - `inventory.views.inventory_list` guards general inventory table from Crew, redirecting to `deduct_stock`.
- **Touch Ergonomics in Kitchen Hub (`_deduct_card.html`)**:
  - Enforced 48px touch targets for quantity inputs and deduction buttons.
  - Added quick-increment deduction pills (`+1`, `+5`, `+10`, `Max`) so kitchen staff can log usage without summoning the virtual software keyboard.
  - Added visual category pills (`Dry Goods`, `Chilled`, `Frozen`) and explicit `OUT OF STOCK` badges for depleted items.

### 8.4 Session Message Leakage Resolution & Logout Purge
- **Issue**: Lingering stock alerts (e.g., `"Chicken Thigh is now low stock."`) and deduction toasts appeared on the public login page after logging out.
- **Root Cause**:
  1. HTMX deduction requests in `inventory/views.py` queued messages into Django's fallback session/cookie storage, but because HTMX swapped only the card partial (`_deduct_card.html`), messages were never consumed in the DOM.
  2. Upon logging out, Django's default behavior retained unread messages in the request object and saved both the unread notices and `"You have been logged out."` into the login redirect cookie.
  3. An erroneous `MESSAGE_TAGS = { 25: "error" }` in `config/settings.py` mapped Django `SUCCESS` (25) to `"error"`, rendering even the logout message as a red error alert with a shake animation.
- **Fixes Applied**:
  1. `accounts.views.logout_view`: Added `list(messages.get_messages(request))` prior to `logout(request)` to exhaust all queued messages, guaranteeing zero session bleed to the login page.
  2. `inventory.views.deduct_stock`: Guarded `messages.warning` and `messages.success` to only fire on non-HTMX requests (`if not request.htmx`), using client-side `window.showToast` for HTMX.
  3. `config/settings.py`: Removed the incorrect `MESSAGE_TAGS = { 25: "error" }` override.
  4. `templates/accounts/login.html`: Styled messages according to message tag semantics.

### 8.5 Real-Time Agrilytics Rhythm Synchronization
- **Fix in `procurement/views.py`**: Updated `mark_delivered` to create an `InboundShipment` record immediately when a Purchase Order is marked as delivered, allowing Agrilytics rhythm tracking to calculate delivery intervals in real-time without requiring a batch backfill command.
- **Validation**: Fixed `deduct_stock` error handling so over-deduction or form errors return HTTP 422 with validation errors swapped directly into the card partial rather than showing false success toasts.