# Agent Operations Manual · INVENTIQ (WaxisInventorySystem)

Welcome to **INVENTIQ**, the intelligent restaurant inventory & procurement system developed for **Waxi's / SND Foods International**.

All AI agents and contributing engineers operating within this repository **MUST** adhere to the guidelines, inspection protocols, and safety rules below before creating or modifying code.

---

## 1. Mandatory Pre-Flight Protocol

Before performing any code edits, running destructive commands, or proposing refactors, you **MUST ALWAYS READ**:
1. [`docs/PROJECT_STATE.md`](file:///Users/luispingul/WaxisInventorySystem/docs/PROJECT_STATE.md) — Live system architecture, tech stack, active features, and the **Do Not Redo** registry.
2. [`docs/DECISIONS.md`](file:///Users/luispingul/WaxisInventorySystem/docs/DECISIONS.md) — Formal Architecture Decision Records (ADRs) explaining *why* components are structured this way.
3. [`docs/TASK_LOG.md`](file:///Users/luispingul/WaxisInventorySystem/docs/TASK_LOG.md) — Chronological history of recently completed tasks and next steps.

---

## 2. Core Operational Rules

1. **Do NOT Redo Completed Work**:
   - Check the **Do Not Redo** section in `docs/PROJECT_STATE.md`.
   - Never dismantle or roll back verified components (e.g., dual-channel Viber/Email PO dispatch, natural window page flow, crew 2-tab lock, sticky kitchen filters, executive health score).
2. **Always Inspect Before Editing**:
   - Inspect files with read/view tools before executing edits. Never assume file contents or CSS line numbers.
3. **Make Small, Scoped Changes**:
   - Work in small, verifiable steps. Modify only the exact lines or templates required for the task.
   - Do not refactor unrelated modules, change package versions, or reformat entire files.
4. **Update TASK_LOG After Every Task**:
   - Immediately log the completed task in `docs/TASK_LOG.md` with: Date, Task, Summary, Files Changed, Tests Run, Result, and Next Steps.
5. **Update PROJECT_STATE for Major Architectural Changes**:
   - Keep `docs/PROJECT_STATE.md` synchronized whenever a major feature is added, modified, or stabilized.

---

## 3. Auto-Detected Tech Stack & Environment Commands

| Category | Technology | Details |
| :--- | :--- | :--- |
| **Backend Framework** | Python 3.11+, Django 4.2+ | `Django>=4.2,<5.0`, `django-htmx>=1.19` |
| **Database** | SQLite (dev) / PostgreSQL (prod) | `db.sqlite3` locally, `psycopg[binary]>=3.2` on Render |
| **Static & Serving** | WhiteNoise 6.6, Gunicorn 22.0 | `whitenoise>=6.6`, `gunicorn>=22.0` |
| **Frontend Styling** | Tailwind CDN, Bootstrap 5.3 CDN, Chart.js 4.4 | Brand palette: Maroon `#871F09`, Orange `#FE5F10`, Amber `#FED216` |

### Standard Development Commands
```bash
# 1. Start development server
./venv/bin/python manage.py runserver 0.0.0.0:8000

# 2. Django system integrity check
./venv/bin/python manage.py check

# 3. Static asset collection (mandatory after editing style.css or images)
./venv/bin/python manage.py collectstatic --noinput

# 4. Interactive Django shell testing
./venv/bin/python manage.py shell

# 5. Database migrations
./venv/bin/python manage.py makemigrations
./venv/bin/python manage.py migrate

# 6. Django unit tests
./venv/bin/python manage.py test
```

---

## 4. Task Completion Checklist

Before reporting completion to the user, ensure you have completed:
- [ ] Read relevant files and verified existing implementation.
- [ ] Applied scoped, clean edits matching established design tokens.
- [ ] Executed `./venv/bin/python manage.py collectstatic --noinput` if static files were touched.
- [ ] Executed automated shell / test assertions verifying HTTP 200 and visual rendering.
- [ ] Confirmed zero regressions across Owner, Manager, and Crew account roles.
- [ ] Updated [`docs/TASK_LOG.md`](file:///Users/luispingul/WaxisInventorySystem/docs/TASK_LOG.md).
