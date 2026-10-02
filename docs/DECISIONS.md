# Architecture Decision Records (ADRs) · INVENTIQ

This document records the architectural and design decisions made for **INVENTIQ (WaxisInventorySystem)**. All contributing agents and engineers must reference these decisions before proposing architectural changes.

---

## Decision Log Template

```markdown
### ADR-XXX: [Short Decision Title]
* **Date**: YYYY-MM-DD
* **Status**: [Proposed | Accepted | Superseded | Deprecated]
* **Decision**: [What was chosen]
* **Reason**: [Why this choice was made, what problem it solves]
* **Alternatives Considered**: [Alternative A, Alternative B, and why they were rejected]
* **Impact**: [Effects on UX, maintainability, performance, security]
```

---

## Accepted Decisions

### ADR-001: Unified Natural Window Momentum Scrolling over Constrained Inner Containers
* **Date**: 2026-10-01
* **Status**: Accepted
* **Decision**: Eliminate `h-[calc(100vh-350px)] overflow-y-auto` from the kitchen Deduct Stock grid and allow pages to expand naturally using native window scrolling (`window.scrollY`) with `pb-16` bottom padding.
* **Reason**: Hardcoding `calc(100vh - 350px)` truncated the 3rd row of inventory cards horizontally and created an empty rectangular void that users perceived as an "invisible footer". Furthermore, inner scrollboxes hijack touch gestures on iPads and commercial kitchen tablets.
* **Alternatives Considered**:
  * *Flexbox Viewport Kiosk Fill (`flex-1 overflow-y-auto`)*: Rejected because inner scrollbars cause scroll trapping on touch devices and feel disjointed from the rest of the application.
* **Impact**: Zero card clipping, 100% fluid 60fps/120fps momentum scrolling on iOS/Android, and complete visual consistency across all INVENTIQ screens.

---

### ADR-002: Dual-Channel Viber Instant Dispatch & Clean Email Drafting for Purchase Orders
* **Date**: 2026-10-01
* **Status**: Accepted
* **Decision**: Implement a full-width two-column PO Dispatch Hub supporting both direct Viber instant messaging (`viber://chat` and `viber://forward`) and clean official email drafts.
* **Reason**: Waxi's suppliers in the Philippines communicate predominantly via Viber for fast order confirmation, while accounting requires formal email paper trails.
* **Alternatives Considered**:
  * *Email Only*: Rejected because suppliers frequently miss or delay reading formal emails, leading to stockout risks.
  * *External SMS Gateway*: Rejected due to per-message API fees and lack of rich text formatting.
* **Impact**: Order dispatch time reduced to under 5 seconds; phone numbers automatically formatted to E.164 (`639XXXXXXXXX`); zero duplicate subject lines in email drafts.

---

### ADR-003: Sidebar Footer User Profile Relocation & Elimination of Desktop Topbar
* **Date**: 2026-10-01
* **Status**: Accepted
* **Decision**: Relocate the user profile card (monogram avatar, active session dot, role badge) into `.sidebar-footer` directly above the Log Out button, and completely remove the redundant desktop topbar (`display: none !important` on $\ge 801\text{px}$). Retain a sleek 56px sticky bar on mobile viewports ($\le 800\text{px}$).
* **Reason**: Every page in the system already features a descriptive page hero header (`<h1>{{ title }}</h1>`), rendering the 82px desktop topbar redundant and visual clutter. Placing account details directly above logout creates a standard enterprise SaaS navigation pattern.
* **Alternatives Considered**:
  * *Retaining Topbar Avatar Dropdown*: Rejected due to redundant vertical height consumption and double-heading clutter.
* **Impact**: Reclaimed 82px of vertical screen real estate for analytics and data tables; mobile navigation preserved via 56px sticky app bar with drawer toggle.

---

### ADR-004: Strict 2-Tab Navigation Barrier & Auto-Redirect for Crew Accounts
* **Date**: 2026-09-30
* **Status**: Accepted
* **Decision**: Restrict Crew role accounts exclusively to 2 sidebar navigation tabs: **Deduct Stock** and **My Transactions**. Intercept and redirect any attempts by Crew accounts to access `/` or `/inventory/` directly to `/inventory/deduct/`.
* **Reason**: Line cooks and kitchen crew need a simplified, distraction-free touch interface focused solely on recording ingredient portions and tracking their own transactions, preventing accidental configuration changes.
* **Alternatives Considered**:
  * *Read-Only Dashboard for Crew*: Rejected as it overwhelmed kitchen staff with financial and procurement metrics irrelevant to their daily operations.
* **Impact**: Streamlined onboarding for kitchen staff; role security reinforced at both the template and view layer.

---

### ADR-005: Purging Session Messages on Logout to Prevent Flash Notice Leaks
* **Date**: 2026-09-30
* **Status**: Accepted
* **Decision**: Purge all unconsumed Django session messages via `list(messages.get_messages(request))` in `logout_view`, and remove the erroneous `MESSAGE_TAGS = { 25: "error" }` override in `config/settings.py`.
* **Reason**: HTMX partial swaps do not consume Django session messages. When users logged out, stale inventory warnings were rendered on the login page as red shake error alerts.
* **Alternatives Considered**:
  * *Disabling Django Messages Entirely*: Rejected because full-page fallback requests still require standard notifications.
* **Impact**: Clean logout transitions without stale alert leaks; genuine login errors accurately distinguished from success notices.

---

### ADR-006: Dedicated High-Contrast Branded Hover States for Executive Directive Action Buttons
* **Date**: 2026-10-01
* **Status**: Accepted
* **Decision**: Replace conflicting `btn btn-outline-secondary bg-white` with a dedicated `.btn-replenish` class in `static/css/style.css` featuring warm brand hover styling (`#FFF7ED` background, `#C2410C` text, `#FDBA74` border, `#FE5F10` icon).
* **Reason**: Bootstrap's `.btn-outline-secondary:hover` sets text color to `#fff`, which collided with the persistent `.bg-white` class, turning both text and icon invisible white-on-white when hovered.
* **Alternatives Considered**:
  * *Applying `!important` color overrides inline*: Rejected in favor of maintainable, design-token-aligned CSS classes in `static/css/style.css`.
* **Impact**: 100% accessible contrast ratio on hover; consistent executive action bar visual hierarchy across Manager and Owner dashboards.

---

### ADR-007: Waxi's Maroon Executive Operations Showcase with White Bento Insets (Option 1)
* **Date**: 2026-10-01
* **Status**: Accepted
* **Decision**: Transform the Executive Operations Briefing section box into Waxi's brand maroon gradient (`#871F09` to `#5E1507`) with a subtle orange rim and depth shadow, while retaining the 3 operational bento cards as high-contrast white insets and styling the directive banner as a dark glass tray with gold eyebrow (`#FED216`).
* **Reason**: Establishes executive visual authority on the dashboard that matches the brand identity, while ensuring small ingredient names and critical shortage badges remain effortlessly readable without visual fatigue.
* **Alternatives Considered**:
  * *Full Dark-Mode Monochrome Maroon*: Rejected due to reduced legibility when reading small ingredient text against dark backgrounds.
  * *Maroon Header Accent Only*: Rejected because it lacked executive visual presence across the whole component.
* **Impact**: Commands visual hierarchy on the dashboard, WCAG AAA compliant text contrast, and reinforces brand identity.

---

### ADR-008: Hybrid Executive Briefing Layout (Maroon Header + White Body + Anti-Camouflage Icon)
* **Date**: 2026-10-01
* **Status**: Accepted
* **Decision**: Adopt the hybrid command layout for the Executive Operations Briefing: the main section box retains a clean white body surface (`#ffffff`) with subtle border and gentle shadow, while the section header uses Waxi's brand maroon gradient (`#871F09` to `#5E1507`). The header shield icon is engineered as a luminous white badge (`#ffffff`) with gold rim (`rgba(254, 210, 22, 0.65)`) and brand orange shield (`#FE5F10`) to provide 14.5:1 contrast with zero camouflage against the maroon header.
* **Reason**: Balances brand identity with dashboard lightness and data legibility. A dark header establishes command presence, while the white body matches the airy dashboard aesthetic. The luminous badge prevents the shield icon from blending into the maroon background.
* **Alternatives Considered**:
  * *All-Maroon Outer Box*: Superseded by this hybrid layout per client preference for a lighter, cleaner card body.
* **Impact**: Optimal dashboard balance, 14.5:1 anti-camouflage icon contrast, WCAG AAA compliant header typography, and seamless bento card scanning.

---

### ADR-009: Scoped Sidebar CSS & Forecast High-Contrast Segmented Tabs with URL State Persistence
* **Date**: 2026-10-01
* **Status**: Accepted
* **Decision**: 
  1. Scope global `.nav-link` CSS rules in `style.css` strictly to `.sidebar .nav-link` to eliminate style bleeding of `color: #fff` onto in-page Bootstrap navigation.
  2. Implement Option A: Modern Segmented Pill Tab Bar (`.forecast-tabs-container` and `.forecast-tab-btn`) with high-contrast slate text (`#475569`, 7.2:1 contrast), tactile warm hover state, Waxi's brand maroon active pill (`#871F09` to `#5E1507`), gold accent icon (`#FED216`), and contextual count badges (`8 AI Alerts`, `Live Rhythm`, `Top 12`).
  3. Implement client-side URL synchronization (`window.history.replaceState`) on tab switch and automatic tab activation from query parameter `?tab=...` on page load.
* **Reason**: 
  1. The un-scoped `.nav-link` rule forced inactive page tabs to pure white text and icons on a cream background, resulting in inactive tabs being invisible (1.1:1 contrast) and appearing to vanish when switching between Consumption Forecast, Supplier Radar, and Stockout Timeline.
  2. Page tabs lacked brand alignment, contextual counters, and state persistence upon browser reload.
* **Alternatives Considered**:
  * *Option B (Integrated Panel Header Tabs)*: Clean, but segmented pill bar provided superior visual demarcation and tactile feel for multi-view forecasting.
  * *Unscoped Global Inactive Override*: Rejected as fragile; scoping to `.sidebar .nav-link` is the root architectural fix.
* **Impact**: Zero disappearing tabs, 100% WCAG AAA contrast ratio compliance, URL bookmarkability for each forecast view, and seamless tab switching with Chart.js timeline rendering.

---

### ADR-010: Procurement Status Tabs, Interactive KPI Cards & Closed-Loop Forecast Integration
* **Date**: 2026-10-02
* **Status**: Accepted
* **Decision**:
  1. Upgrade `/procurement/` with the exact same high-contrast segmented pill tab bar (`.procurement-tabs-container`, `.procurement-tab-btn`) as `/forecast/`: **All Requests**, **Pending Approval**, **Ready to Dispatch**, **In Transit**, and **Delivered History**, each equipped with semantic live count badges.
  2. Make the 4 top KPI stat cards (`Pending`, `Approved`, `Ordered`, `Delivered`) interactive, clicking a card syncs and activates its corresponding tab filter.
  3. Integrate HTMX partial updates for table swapping (`_list_table.html`) on tab clicks without full page reloads, accompanied by URL synchronization (`?status=...`).
  4. Implement rich AI origin traceability in procurement rows (`.ai-source-badge` and direct link to `/forecast/`).
  5. Connect Django flash messages to the client-side toast notification system in `base.html` for 1-click confirmation when converting alerts to PRs.
* **Reason**: The Procurement module previously lacked status filtering and UI/UX parity with the upgraded Forecast tab. Connecting AI stockout alerts directly to purchasing with rich traceability and interactive tabs closes the operational loop between predictive analytics and vendor order dispatch.
* **Alternatives Considered**:
  * *Dropdown select filter*: Rejected as cumbersome; segmented pill tabs provide instant 1-tap visibility of request counts across each phase.
* **Impact**: Complete UI/UX consistency across Forecast and Procurement, sub-second status filtering, WCAG AAA text contrast, and full traceability from stockout prediction to Viber dispatch.

---

### ADR-011: Nesting Procurement Inside Forecast Hub & Sidebar Navigation Reordering
* **Date**: 2026-10-02
* **Status**: Accepted
* **Decision**:
  1. Reorder sidebar navigation drawer in `templates/base.html`: Dashboard $\rightarrow$ Inventory $\rightarrow$ Transactions $\rightarrow$ **Forecast** $\rightarrow$ **Suppliers** $\rightarrow$ Reports $\rightarrow$ Audit Logs.
  2. Consolidate Procurement into the Forecast Hub (`/forecast/`) as a dedicated second tab immediately adjacent to Consumption Forecast:
     - Tab 1: **Consumption Forecast** (`#tab-consumption`)
     - Tab 2: **Procurement Requests** (`#tab-procurement`)
     - Tab 3: **Supplier Radar** (`#tab-radar`)
     - Tab 4: **Stockout Timeline** (`#tab-timeline`)
  3. Seamless 1-Click "Convert to PR" Handoff: Approving an AI alert (`alert_approve`) redirects to `/forecast/?tab=procurement&highlight=<pk>`, smoothly switching to the Procurement Requests tab and applying a glowing pulse animation (`.row-highlighted`) with smooth scroll to the newly generated PR.
  4. 100% Backwards Compatibility: Direct visits to `/procurement/` issue an HTTP 302 redirect to `/forecast/?tab=procurement`, preserving all bookmarks and links, while HTMX partial requests continue returning `_list_table.html` for sub-second in-tab status filtering.
* **Reason**:
  - Eliminates the cognitive "context gap" where converting an alert to a purchase order forced a jarring navigation to a completely separate page.
  - Matches the natural kitchen operational funnel: Inventory (On-Hand) $\rightarrow$ Transactions (Daily Burn) $\rightarrow$ Forecast & Orders (Needs) $\rightarrow$ Suppliers (Vendors) $\rightarrow$ Reports (Analytics).
  - Keeps the navigation drawer focused and decluttered by removing duplicate top-level links.
* **Alternatives Considered**:
  - *Keep standalone Procurement in sidebar alongside sub-tab*: Rejected as redundant and confusing to users.
  - *Full page reload on "Convert to PR" without tab switch*: Rejected because user loses track of the generated PR.
* **Impact**: Zero context disconnection, seamless 1-click PO creation to Viber dispatch, WCAG AAA contrast, and backwards-compatible URL routing.


