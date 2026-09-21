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

## Module 6: Crew Dashboard — Deduct Stock Grid
A responsive, mobile-first ingredient grid replacing the single-form deduction page.
* **Function:** Displays all ingredients in a responsive card grid (1/2/3/4 columns) with inline deduct forms. Crew can search (300ms debounce), scroll through all items (no pagination), and deduct stock without page reloads via HTMX.
* **Key Features:**
  * Responsive grid: `grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4`
  * Each card: white background, `rounded-2xl`, subtle border, current stock badge
  * Inline deduct form with quantity input, reason dropdown, submit button
  * Zero-stock items visually disabled (`opacity-50`, `disabled` attribute)
  * HTMX-powered: search (300ms debounce), **scrollable list (no pagination)**, form submission all via partial swaps
  * Subtle toast notification on successful deduction
  * Zero-stock items disabled (`disabled` attribute + `opacity-50`)
* **Architecture Impact:** 
  * Single view (`deduct_stock`) handles both list mode (full page with search) and item mode (HTMX partial card)
  * `StockDeductionForm` adapts: ingredient field hidden when `item_id` provided
  * HTMX partial swaps (`hx-swap="outerHTML"`) keep crew on dashboard
  * Zero-stock items disabled at form + template level
  * Scrollable container: `h-[calc(100vh-350px)] overflow-y-auto` adapts to viewport

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
## 6. Management Commands & Cron
| Command | Purpose | Schedule |
|---------|---------|----------|
| `backfill_inbound_shipments` | One-time historical data load from PRs + StockTransaction | Manual |
| `compute_forecasts` | Daily: consumption alerts + supplier rhythms | Cron `0 2 * * *` |
| `compute_forecasts --rhythm-only` | Standalone rhythm refresh | Optional |