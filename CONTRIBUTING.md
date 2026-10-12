# Contributing to INVENTIQ

Thank you for your interest in contributing to **INVENTIQ** (Waxis Inventory Management System). This guide outlines the development standards, workflow, and expectations for all engineers and contributors.

---

## 🛠️ Local Development Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/LuisPingul/WaxisInventorySystem.git
   cd WaxisInventorySystem
   ```

2. **Virtual Environment & Dependencies**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # macOS / Linux
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and configure local parameters:
   ```bash
   cp .env.example .env
   ```

4. **Run Migrations & Seed Local Database**:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   # Optional: Seed demo dataset
   python manage.py seed_demo
   ```

5. **Start Development Server**:
   ```bash
   python manage.py runserver
   ```
   Navigate to `http://127.0.0.1:8000/accounts/login/`.

---

## 🌿 Git Branching Strategy

* **`main`**: Production-ready branch. All commits must pass CI checks.
* **Feature Branches**: Branch from `main` using structured naming:
  * `feat/short-description` (New capabilities)
  * `fix/short-description` (Bug fixes)
  * `perf/short-description` (Performance improvements)
  * `docs/short-description` (Documentation updates)
  * `chore/short-description` (Maintenance, tooling, refactors)

---

## 🧪 Testing & Pre-Commit Verification

Before submitting any Pull Request or pushing code:

1. **Verify Django Configuration**:
   ```bash
   python manage.py check
   ```
2. **Check for Uncommitted Migrations**:
   ```bash
   python manage.py makemigrations --check --dry-run
   ```
3. **Execute Test Suite**:
   ```bash
   python manage.py test
   ```
4. **Validate Static Files Collection**:
   ```bash
   python manage.py collectstatic --no-input
   ```

---

## 🎨 UI & UX Standards

All UI contributions must adhere to the **INVENTIQ Design System** ([`docs/design_system.md`](docs/design_system.md)):
* **Brand Color Palette**:
  * Deep Maroon: `#871F09` (Primary branding & headers)
  * Electric Orange: `#FE5F10` (Accents & CTAs)
  * Warm Amber / Gold: `#FED216` (Highlight icons & badges)
  * Warm Off-White / Cream: `#FDF8F4` (Background canvas)
* **Touch Ergonomics**: All kitchen touch targets (e.g., Crew Deduct cards) must be at least **48px** in height and width.
* **Accessibility**: Maintain WCAG 2.2 AA contrast ($\ge$4.5:1 for normal text, $\ge$3:1 for large UI components).
* **Zero External AI**: All forecasting models must remain deterministic Python algorithms (`statistics`, rolling averages, Agrilytics inter-arrival intervals). No third-party LLM APIs for core inventory calculations.

---

## 📝 Updating Documentation

Every significant code modification must be logged in:
* [`docs/TASK_LOG.md`](docs/TASK_LOG.md) — Follow the template at the top of the file.
* [`docs/DECISIONS.md`](docs/DECISIONS.md) — Record any architectural shifts as a new ADR.
* [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) — Update active feature status or invariants if modified.
