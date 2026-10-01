# INVENTIQ Design System Specification

> Design intelligence derived from `ui-ux-pro-max` for **SND Foods International Inc. (Waxi's)**.
> Optimized for hybrid **Kitchen Hub touch environments** (tablets/terminals) and **Executive Dashboards** (management/ownership).

---

## 1. Brand & Semantic Color Tokens

### 1.1 Core Brand Identity (Brand-Locked)
| Token | Variable | Hex | Usage |
|:---|:---|:---|:---|
| **Deep Maroon** | `--brand-maroon` | `#871F09` | Primary brand identity, dark headers, frozen product categories, key callouts |
| **Electric Orange** | `--brand-orange` | `#FE5F10` | Primary action CTA, focus highlights, chilled product categories, brand accent |
| **Warm Amber/Yellow**| `--brand-yellow` | `#FED216` | Warm secondary accent, dry goods categories, alerts & highlights |
| **Charcoal Dark** | `--brand-dark` | `#1E293B` | High-contrast typography, sidebar base, executive elements |

### 1.2 Surface & Neutral Palette
| Token | Variable | Hex | Tailwind Equivalent | Usage |
|:---|:---|:---|:---|:---|
| **App Background** | `--bg-app` | `#F8FAFC` | `bg-slate-50` | Main canvas background |
| **Card Surface** | `--surface-card` | `#FFFFFF` | `bg-white` | Content containers, panels, ingredient cards |
| **Surface Muted** | `--surface-muted` | `#F1F5F9` | `bg-slate-100` | Table headers, secondary pills, disabled state |
| **Border Subtle** | `--border-subtle` | `#E2E8F0` | `border-slate-200` | Card borders, table dividers |
| **Border Focus** | `--border-focus` | `#FE5F10` | `border-orange-500` | Active form input rings |

### 1.3 Semantic Status Palette (WCAG AA Compliant)
| Status | Variable | Text / Badge Hex | Background Hex | Tailwind Tokens |
|:---|:---|:---|:---|:---|
| **In Stock (GOOD)** | `--status-good` | `#15803D` | `#DCFCE7` | `text-green-700 bg-green-100` |
| **Low Stock (LOW)** | `--status-low` | `#B45309` | `#FEF3C7` | `text-amber-700 bg-amber-100` |
| **Critical (CRITICAL)**| `--status-critical`| `#B91C1C` | `#FEE2E2` | `text-red-700 bg-red-100` |
| **Out of Stock (OUT)** | `--status-out` | `#475569` | `#F1F5F9` | `text-slate-600 bg-slate-100` |

---

## 2. Typography Scale

- **Primary Font**: `Inter`, `-apple-system`, `BlinkMacSystemFont`, `"Segoe UI"`, `Roboto`, `sans-serif`
- **Monospace Font** (Numbers, SKUs, Timestamps): `ui-monospace`, `SFMono-Regular`, `Menlo`, `Monaco`, `monospace`

| Level | Size | Weight | Line Height | Application |
|:---|:---|:---|:---|:---|
| **Hero / Stat** | `32px` (`2rem`) | `800` (Extrabold) | `1.1` | Dashboard KPI big numbers |
| **Heading 1** | `24px` (`1.5rem`) | `700` (Bold) | `1.25` | Page titles (`topbar-title`) |
| **Heading 2** | `18px` (`1.125rem`) | `700` (Bold) | `1.3` | Panel titles, card headings |
| **Body (Default)** | `15px` (`0.9375rem`) | `400` (Regular) | `1.5` | Form inputs, table cells, descriptions |
| **Caption / Subtext**| `12px` (`0.75rem`) | `600` (Semibold) | `1.4` | Category badges, timestamps, helper text |

---

## 3. Touch & Kitchen Terminal Ergonomics

Designed specifically for **kitchen staff working in fast-paced environments** with tablet terminals (e.g. iPad, Galaxy Tab, kitchen kiosks):

1. **Touch Target Size**:
   - Minimum interactive element height: **`48px`** (matches Apple HIG 44pt / Material 48dp minimum).
   - Quantity inputs & reason dropdowns: `min-h-[48px]` (`py-3 px-4`).
   - Quick-increment pill buttons: `min-h-[40px]` with generous tap area.
2. **Touch Spacing**:
   - Minimum gap between adjacent interactive targets: **`8px`** (`gap-2`).
3. **No Auto-Zoom on iOS**:
   - Input font sizes must be at least `16px` on mobile/tablet viewports to prevent iOS Safari auto-zooming into inputs.
4. **Tactile Zero-Stock Treatment**:
   - When `quantity == 0`, card reflects a dimmed opacity (`opacity-60`), disable submit button, and display an explicit **`OUT OF STOCK`** badge.
5. **Quick Quantity Step Pills**:
   - Dedicated `+1`, `+5`, `+10`, `All` buttons allow rapid deductions without needing to evoke a software keyboard.

---

## 4. Data Visualization & Charts (Chart.js Guidelines)

### 4.1 Storage Distribution (Doughnut Chart)
- **Colors**:
  - `Dry Goods`: Brand Yellow (`#FED216`)
  - `Chilled`: Brand Orange (`#FE5F10`)
  - `Frozen`: Brand Maroon (`#871F09`)
- **Center cutout**: `65%` (clean doughnut for density).
- **Tooltips**: Include item count + percentage of total inventory.

### 4.2 High Demand Products (Trend Line Chart)
- **Palette**: Use distinct brand hues with 20% alpha fill for area contrast.
- **Tension**: `0.3` (gentle curve).
- **Point radius**: `4px` with hover radius `6px`.
- **Gridlines**: Subtle slate border (`#F1F5F9`) with no vertical grid clutter.

---

## 5. Pre-Delivery & Quality Checklist

- [x] Minimum 48px touch targets for all primary buttons and form controls in Kitchen Hub.
- [x] Input font sizes ≥ 16px to prevent iOS Safari input zoom.
- [x] Contrast ratio ≥ 4.5:1 for all normal text against backgrounds.
- [x] Responsive data tables wrapped with horizontal scroll (`overflow-x-auto`).
- [x] Clear loading and feedback states for HTMX operations (`hx-indicator`, toast notifications).
- [x] Accessible `:focus-visible` ring on keyboard navigation (`outline: 2px solid var(--brand-orange)`).
