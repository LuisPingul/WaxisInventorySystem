# Forecasting UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use godmode:task-runner to implement this plan task-by-task.

**Goal:** Finish forecasting UI with brand-aligned radar, fixed HTMX flows, deduplicated templates, and revamp additions (polling, timeline chart, variance UI).

**Architecture:** Extract shared `forecasting/selectors.py` as single source for enriched rows + radar alerts; convert radar partial to Bootstrap + Waxi CSS vars; make radar order HTMX-aware via `HX-Redirect`; split forecast table/radar into reusable partials.

**Tech Stack:** Django 4.2, HTMX 1.9, Bootstrap 5, Chart.js 4, SQLite/Postgres

---

### Task 1: Shared selectors (B1)

**Files:**
- Create: `forecasting/selectors.py`
- Modify: `forecasting/views.py:16-20`, `dashboard/views.py`

**Step 1:** Create `forecasting/selectors.py` with `get_enriched_rows`, `get_radar_alerts`, `build_forecast_context`, `is_htmx`.
**Step 2:** `python3 manage.py shell -c "from forecasting.selectors import build_forecast_context; print(len(build_forecast_context()['rows']))"` Expected: `13` (or current count).
**Step 3:** Rewrite `forecasting/views.forecast` + `dashboard/views.forecast_partial` to call it.
**Step 4:** `python3 manage.py check` Expected: `no issues`.
**Step 5:** Commit `git commit -m "refactor: extract forecasting selectors"`

### Task 2: Brand radar + risk-critical (B2)

**Files:**
- Modify: `templates/forecasting/_procurement_radar.html`, `static/css/style.css`

**Step 1:** Add `.risk-critical`, `.radar-card/.urgent/.soon` to `style.css`.
**Step 2:** Rewrite `_procurement_radar.html` to Bootstrap cards, `radar_id` var, HTMX `hx-post hx-swap="none"`, empty-state with backfill CTA.
**Step 3:** Verify `curl` or test client shows `radar-card` class.
**Step 4:** Commit `git commit -m "style: brand-aligned procurement radar + risk-critical"`

### Task 3: HTMX order fix (B3)

**Files:**
- Modify: `forecasting/views.py:radar_create_pr`, `procurement/views.py:create_request`

**Step 1:** Return `204 + HX-Redirect` when `is_htmx`, else `redirect`. Extend `create_request` initial with `supplier/reason/priority`.
**Step 2:** Test: `POST /forecast/radar/<id>/order/ HX-Request:true` → `204` + `HX-Redirect: /procurement/create/...`.
**Step 3:** Commit `git commit -m "fix: HTMX radar order redirect + PR prefill"`

### Task 4: Deduplicate templates (B4)

**Files:**
- Create: `templates/forecasting/_forecast_table.html`, `templates/forecasting/_radar_panel.html`
- Modify: `templates/forecasting/dashboard.html`, `templates/forecasting/_forecast_tabs.html`

**Step 1:** Extract table + radar panel partials; rewrite dashboard + HTMX tabs to include them.
**Step 2:** `manage.py shell` template load check for all 8 templates.
**Step 3:** Commit `git commit -m "refactor: deduplicate forecast templates"`

### Task 5: Owner dual highlights (B5)

**Files:**
- Modify: `dashboard/views.py:owner/manager`, `templates/dashboard/owner.html`, `templates/dashboard/manager.html`, `forecasting/views.py:procurement_radar`

**Step 1:** Use `get_enriched_rows` for highlights; show `combined_risk + Dual` badge; preserve `HX-Target` as `radar_id`; add polling wrappers + refresh buttons.
**Step 2:** `GET /` → contains `radar-card` + `Dual`.
**Step 3:** Commit `git commit -m "feat: dual-risk highlights + radar polling"`

### Task 6: Revamp C1–C5

**Files:**
- Modify: `templates/forecasting/dashboard.html` (timeline tab + filter `hx-trigger=change`), `templates/forecasting/alerts.html` (variance), `forecasting/views.py:forecast` (HTMX partial return)

**Step 1:** Timeline Chart.js bar from DOM table; filter returns `_forecast_table.html` on HTMX; alerts show predicted→actual + variance badges.
**Step 2:** Verify: `GET /forecast/ HX-Request:true` returns partial (no nav-tabs); `GET /forecast/alerts/` contains `Variance`.
**Step 3:** Commit `git commit -m "feat: forecast timeline, variance UI, filter persistence"`
